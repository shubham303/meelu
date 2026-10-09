"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import type { Editor } from "@tiptap/react";
import { ArrowLeft, Check, Copy, PanelRight, Sparkles } from "lucide-react";
import { Button, Card, ConfirmDelete, Spinner } from "@/components/ui";
import { api, useApi } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import { cn, formatRelative } from "@/lib/utils";
import type { ContentPiece, PieceIssue } from "../types";
import { ChecksPanel, CheckIcon } from "./checks-panel";
import { buildProposal, pendingCount, resolve, type Proposal } from "./diff";
import { Document, scrollToAnchor } from "./document";
import { PageFields } from "./page-fields";
import { ProposalReview } from "./proposal-review";
import { Rail } from "./rail";
import { useAgent } from "./use-agent";
import { formFrom, useAutosave, type SaveState } from "./use-autosave";
import { useAgentTasks } from "../../agent-tasks";

type Panel = "rail" | "checks" | null;

const pieceTasks = new Map<string, string>();

function issuesDraft(issues: PieceIssue[]): string | undefined {
  if (issues.length === 0) return undefined;
  return issues
    .map((i, n) =>
      [
        `${n + 1}. ${i.title}`,
        i.detail ? ` — ${i.detail}` : "",
        i.anchorText ? ` Where: """${i.anchorText}"""` : "",
        i.suggestion ? ` Suggested: """${i.suggestion}"""` : "",
      ].join(""),
    )
    .join("\n");
}

interface CheckResult {
  summary: Record<string, unknown> | null;
  issues: Array<{ code: string; title: string; detail?: string | null; anchorText?: string | null; suggestion?: string | null }>;
}

interface ChecksBridge {
  checkContent?: (payload: {
    text: string;
    tools?: string[];
    siteId?: string;
    excludePageIds?: string[];
    excludeUrls?: string[];
  }) => Promise<{
    results?: Record<string, CheckResult>;
    error?: string;
  }>;
}

function checksBridge(): ChecksBridge | undefined {
  if (typeof window === "undefined") return undefined;
  return (window as Window & { meeluAgent?: ChecksBridge }).meeluAgent;
}

const SAVE_LABEL: Record<SaveState, string> = {
  idle: "",
  dirty: "Unsaved",
  saving: "Saving…",
  saved: "Saved",
  error: "Could not save",
};

function readingTime(words: number): string {
  return `${Math.max(1, Math.round(words / 238))} min read`;
}

export default function ContentPiecePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const isApp = useIsApp();
  const { data: fetched, loading, error } = useApi<ContentPiece>(`/api/v1/content/pieces/${id}`);
  const [saved, setSaved] = useState<ContentPiece | null>(null);
  const piece = saved ?? fetched;

  const initial = useMemo(() => (fetched ? formFrom(fetched) : null), [fetched]);
  const { form, setForm, state: saveState, error: saveError, savedAt, flush, current } = useAutosave(
    id,
    initial,
    setSaved,
  );

  const [panel, setPanel] = useState<Panel>(null);
  const [deleting, setDeleting] = useState(false);
  const [copied, setCopied] = useState(false);
  const [docVersion, setDocVersion] = useState(0);
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const editorRef = useRef<Editor | null>(null);
  const togglePanel = (next: Exclude<Panel, null>) => setPanel((p) => (p === next ? null : next));

  const { data: issueRows, refresh: refreshIssues } = useApi<PieceIssue[]>(
    `/api/v1/content/pieces/${id}/issues`,
  );
  const issues = useMemo(() => issueRows ?? [], [issueRows]);
  const [activeIssue, setActiveIssue] = useState<string | null>(null);
  const [checksRunning, setChecksRunning] = useState(false);
  const [checksError, setChecksError] = useState<string | null>(null);
  const canRunChecks = isApp && !!checksBridge()?.checkContent;
  const openIssues = useMemo(() => issues.filter((i) => i.state === "open"), [issues]);
  const openIssuesRef = useRef(openIssues);
  useEffect(() => {
    openIssuesRef.current = openIssues;
  }, [openIssues]);
  const activeAnchor = issues.find((i) => i.id === activeIssue)?.anchorText ?? null;

  const getDraft = useCallback(() => current(), [current]);
  const getIssues = useCallback(() => openIssuesRef.current, []);
  const agent = useAgent(id, getDraft, getIssues);
  const { launchTask, openTask, hasTask, updateTaskDraft, updateTaskHooks } = useAgentTasks();

  const wordCount = useMemo(
    () => (form?.bodyMarkdown.match(/\S+/g) ?? []).length,
    [form?.bodyMarkdown],
  );

  const propose = useCallback(
    (next: string, note: string): number => {
      const base = current()?.bodyMarkdown ?? "";
      const built = buildProposal(base, next, note);
      if (!built) return 0;
      setProposal(built);
      setActiveIssue(null);
      return pendingCount(built);
    },
    [current],
  );

  const applyMarkdown = useCallback(
    (markdown: string) => {
      setForm((f) => {
        const patch: Partial<typeof f> = { bodyMarkdown: markdown };
        if (!f.h1.trim()) {
          const heading = markdown.match(/^#\s+(.+?)\s*$/m);
          if (heading) patch.h1 = heading[1].trim();
        }
        return patch;
      });
      setDocVersion((v) => v + 1);
    },
    [setForm],
  );

  const finishProposal = useCallback(
    (settled: Proposal) => {
      setProposal(null);
      applyMarkdown(resolve(settled));
    },
    [applyMarkdown],
  );

  const takeAgentSave = useCallback(async () => {
    const fresh = await api<ContentPiece>(`/api/v1/content/pieces/${id}`);
    const live = current();
    if (!live) return;
    const fields = formFrom(fresh);
    const changed = (["title", "h1", "metaDescription", "slug", "targetKeyword"] as const).filter(
      (key) => fields[key] !== live[key],
    );
    if (changed.length > 0) setForm(Object.fromEntries(changed.map((key) => [key, fields[key]])));
    if (fresh.bodyMarkdown !== live.bodyMarkdown) {
      const proposed = propose(fresh.bodyMarkdown, "From the conversation");
      if (proposed === 0) applyMarkdown(fresh.bodyMarkdown);
    }
  }, [applyMarkdown, current, id, propose, setForm]);

  const taskDraft = useMemo(
    () => ({
      piece: `"${form?.title ?? ""}" (id ${id})`,
      title: form?.title || "(empty)",
      h1: form?.h1 || "(empty)",
      metaDescription: form?.metaDescription || "(empty)",
      slug: form?.slug || "(empty)",
      targetKeyword: form?.targetKeyword || "(empty)",
      text: form?.bodyMarkdown ? `"""${form.bodyMarkdown}"""` : "(empty so far)",
      openIssues: issuesDraft(openIssues),
    }),
    [form, id, openIssues],
  );

  useEffect(() => {
    const taskId = pieceTasks.get(id);
    if (!taskId || !hasTask(taskId)) return;
    updateTaskDraft(taskId, taskDraft);
  }, [hasTask, id, taskDraft, updateTaskDraft]);

  useEffect(() => {
    const taskId = pieceTasks.get(id);
    if (!taskId || !hasTask(taskId)) return;
    updateTaskHooks(taskId, { onWrote: takeAgentSave });
  }, [hasTask, id, takeAgentSave, updateTaskHooks]);

  const openAgent = () => {
    const existing = pieceTasks.get(id);
    if (existing && hasTask(existing)) {
      openTask(existing);
      return;
    }
    const taskId = launchTask({
      title: `Edit: ${form?.title || "Untitled piece"}`,
      endpoint: "/api/agent/content-draft",
      emptyHint:
        "Say what you want and it lands in the draft as marked changes you keep or discard. Ask a question and it answers instead of writing." +
        (openIssues.length > 0 ? " It can see every open issue the checks flagged." : ""),
      draft: taskDraft,
      suggestions: [
        ...(openIssues.length > 0
          ? [
              {
                label: `Fix all ${openIssues.length} flagged issues`,
                prompt: "Fix every open issue the checks flagged, all in one pass. Keep every fact and the structure.",
              },
            ]
          : []),
        {
          label: "Better keyword and links",
          prompt: "Check the target keyword against our search data and the internal links against our crawled pages, then improve both.",
        },
        { label: "Tighten the opening", prompt: "Tighten the opening paragraph. Keep every fact." },
        { label: "Is anything unclear?", prompt: "Is anything in this piece unclear or unsupported? Answer, don't rewrite." },
      ],
      onWrote: takeAgentSave,
    });
    if (taskId) pieceTasks.set(id, taskId);
  };

  const replaceSelection = useCallback(
    (passage: string, replacement: string) => {
      const base = current()?.bodyMarkdown ?? "";
      const at = base.indexOf(passage);
      if (at >= 0 && base.indexOf(passage, at + 1) < 0) {
        propose(base.slice(0, at) + replacement + base.slice(at + passage.length), "Rewrote the selection");
        return;
      }
      const editor = editorRef.current;
      if (!editor) return;
      editor.chain().focus().insertContent(replacement).run();
    },
    [current, propose],
  );

  const fixIssue = async (issue: PieceIssue) => {
    if (!issue.anchorText || agent.busy) return;
    setActiveIssue(issue.id);
    const instruction = [
      `A check flagged this passage: ${issue.title}.`,
      issue.detail ?? "",
      issue.suggestion ? `A suggested replacement: "${issue.suggestion}"` : "",
      "Fix it.",
    ]
      .filter(Boolean)
      .join(" ");
    const replacement = await agent.rewritePassage({ instruction, passage: issue.anchorText });
    if (replacement === null) return;
    const base = current()?.bodyMarkdown ?? "";
    const at = base.indexOf(issue.anchorText);
    if (at < 0) return;
    propose(
      base.slice(0, at) + replacement + base.slice(at + issue.anchorText.length),
      `Fix for: ${issue.title}`,
    );
  };

  const setIssueState = async (issue: PieceIssue, state: PieceIssue["state"]) => {
    await api(`/api/v1/content/pieces/${id}/issues/${issue.id}`, { method: "PATCH", body: { state } });
    await refreshIssues();
  };

  const runChecks = async () => {
    const bridge = checksBridge();
    if (!bridge?.checkContent || !form) return;
    setChecksRunning(true);
    setChecksError(null);
    try {
      await flush();
      const res = await bridge.checkContent({
        text: form.bodyMarkdown,
        siteId: piece?.siteId,
        excludePageIds: piece?.sourcePageId ? [piece.sourcePageId] : [],
      });
      if (res.error) throw new Error(res.error);
      for (const [tool, result] of Object.entries(res.results ?? {})) {
        await api(`/api/v1/content/pieces/${id}/issues`, {
          method: "POST",
          body: { tool, issues: result.issues },
        });
      }
      await refreshIssues();
    } catch (e) {
      setChecksError(e instanceof Error ? e.message : "The checks could not run.");
    } finally {
      setChecksRunning(false);
    }
  };

  const copyMarkdown = async () => {
    await flush();
    const res = await fetch(`/api/v1/content/pieces/${id}/markdown`);
    const text = await res.text();
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  const selectIssue = (issue: PieceIssue) => {
    setActiveIssue(issue.id);
    if (issue.anchorText && editorRef.current) scrollToAnchor(editorRef.current, issue.anchorText);
  };

  if (loading || (piece && !form)) {
    return (
      <div className="py-10">
        <Spinner />
      </div>
    );
  }

  if (error || !piece || !form) {
    return (
      <div>
        <Back />
        <Card className="text-sm text-sub">{error ?? "That piece is not here any more."}</Card>
      </div>
    );
  }

  const saveLabel =
    saveState === "saved" && savedAt
      ? `Saved · ${formatRelative(savedAt.toISOString())}`
      : SAVE_LABEL[saveState];

  return (
    <div data-full-bleed className="-mx-8 -my-8 flex h-screen flex-col overflow-hidden">
      <div className="flex h-14 shrink-0 items-center justify-between border-b border-edge bg-panel px-8">
        <Back />
        <div className="flex items-center gap-3">
          <span className={cn("text-xs", saveState === "error" ? "text-bad" : "text-faint")} title={saveError ?? undefined}>
            {saveLabel}
          </span>
          <Button
            variant="outline"
            size="sm"
            disabled={saveState !== "dirty" && saveState !== "error"}
            onClick={() => void flush()}
          >
            Save
          </Button>
          <button
            type="button"
            onClick={() => void copyMarkdown()}
            title="Copy markdown"
            aria-label="Copy markdown"
            className="inline-flex h-8 w-8 items-center justify-center rounded-lg text-sub transition-colors hover:bg-panel2 hover:text-ink cursor-pointer"
          >
            {copied ? <Check size={16} className="text-good" /> : <Copy size={16} />}
          </button>
          <TopToggle active={panel === "rail"} onClick={() => togglePanel("rail")}>
            <PanelRight size={14} /> Details
          </TopToggle>
          <TopToggle active={panel === "checks"} onClick={() => togglePanel("checks")}>
            <CheckIcon /> Checks
            {openIssues.length > 0 && (
              <span className="inline-flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-warn/10 px-1.5 text-[11px] text-warn">
                {openIssues.length}
              </span>
            )}
          </TopToggle>
          {isApp && (
            <TopToggle active={false} onClick={openAgent}>
              <Sparkles size={14} className="text-accent" /> Agent
            </TopToggle>
          )}
        </div>
      </div>

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-1 overflow-y-auto px-16 py-14">
          <div className="mx-auto max-w-[680px]">
            <PageFields
              form={form}
              onChange={setForm}
              meta={
                <>
                  <span>{wordCount} words</span>
                  <span>·</span>
                  <span>{readingTime(wordCount)}</span>
                  <span>·</span>
                  <span>edited {formatRelative(piece.updatedAt)}</span>
                </>
              }
            />

            {proposal ? (
              <ProposalReview proposal={proposal} onChange={setProposal} onDone={finishProposal} />
            ) : (
              <Document
                markdown={form.bodyMarkdown}
                version={docVersion}
                onChange={(md) => setForm({ bodyMarkdown: md })}
                onSelectionRequest={isApp ? agent.rewritePassage : undefined}
                onReplaceSelection={isApp ? replaceSelection : undefined}
                anchors={activeAnchor ? [activeAnchor] : []}
                activeAnchor={activeAnchor}
                editorRef={editorRef}
              />
            )}
          </div>
        </div>

        {panel === "rail" && <Rail piece={piece} onDelete={() => setDeleting(true)} />}
        {panel === "checks" && (
          <ChecksPanel
            issues={issues}
            activeId={activeIssue}
            running={checksRunning}
            canRun={canRunChecks}
            runError={checksError}
            agentBusy={agent.busy}
            onClose={() => setPanel(null)}
            onRun={() => void runChecks()}
            onSelect={selectIssue}
            onEdit={selectIssue}
            onFix={isApp ? (issue) => void fixIssue(issue) : () => {}}
            onState={(issue, state) => void setIssueState(issue, state)}
          />
        )}
      </div>

      <ConfirmDelete
        open={deleting}
        onClose={() => setDeleting(false)}
        what={`“${form.title || "this piece"}”`}
        onConfirm={async () => {
          await api(`/api/v1/content/pieces/${id}`, { method: "DELETE" });
          router.push("/dashboard/content");
        }}
      />
    </div>
  );
}

function TopToggle({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <Button
      variant="outline"
      size="sm"
      onClick={onClick}
      className={cn(active && "border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft")}
    >
      {children}
    </Button>
  );
}

function Back() {
  return (
    <Link
      href="/dashboard/content"
      className="inline-flex items-center gap-1.5 text-sm text-sub transition-colors hover:text-ink"
    >
      <ArrowLeft size={14} /> Content
    </Link>
  );
}
