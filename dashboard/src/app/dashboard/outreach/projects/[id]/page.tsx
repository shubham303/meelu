"use client";

import { useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  Check,
  Copy,
  Download,
  ExternalLink,
  Globe,
  Inbox,
  Loader2,
  Mail,
  Play,
  Pencil,
  Send,
  Sparkles,
  Trash2,
  Users,
} from "lucide-react";
import type { PaginationState, SortingState } from "@tanstack/react-table";
import { PageEnter } from "@/components/animate";
import {
  Badge,
  Button,
  Card,
  ConfirmDelete,
  Drawer,
  EmptyState,
  Field,
  IconButton,
  Input,
  Modal,
  Select,
  Spinner,
  Textarea,
  type BadgeTone,
} from "@/components/ui";
import { PROSPECT_STATUS_LABEL, ProspectsTable } from "../../prospects-table";
import { activeSiteId } from "@/lib/current-site";
import { api, useApi } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import { AgentLaunchButton, runInlineTurn, useAgentTasks } from "../../../agent-tasks";
import { refuseOnWeb, Revise, streamTurn } from "@/components/agent";
import { sendingAsSentence, useSendingAs } from "../../sending-as";
import {
  ProjectFormModal,
  projectToForm,
  type ProjectForm,
} from "../../project-form-modal";
import { cn, formatDate, formatRelative } from "@/lib/utils";
import type {
  Campaign,
  CampaignStatus,
  ConversationMessage,
  OutreachProject,
  Prospect,
  ProspectStatus,
} from "@/lib/types";
import * as chips from "@/features/prompt-chips/outreach";

type Run = Campaign & { found: number };

const PROSPECT_STATUSES: ProspectStatus[] = [
  "found",
  "contacted",
  "replied",
  "won",
  "rejected",
];

const runTone: Record<CampaignStatus, BadgeTone> = {
  running: "accent",
  done: "good",
  failed: "bad",
};

function startOfToday(): string {
  const d = new Date();
  d.setHours(0, 0, 0, 0);
  return d.toISOString();
}

function csvCell(v: string | undefined | null): string {
  const s = v ?? "";
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

function BriefField({ label, value }: { label: string; value?: string | null }) {
  if (!value) return null;
  return (
    <div>
      <p className="text-xs text-sub uppercase tracking-wide mb-1.5">{label}</p>
      <p className="text-sm text-ink leading-relaxed whitespace-pre-wrap">{value}</p>
    </div>
  );
}

export default function ProjectDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();

  const {
    data: project,
    loading: projectLoading,
    error: projectError,
    refresh: refreshProject,
  } = useApi<OutreachProject>(id ? `/api/v1/outreach/projects/${id}` : null);
  const { data: runs, refresh: refreshRuns } = useApi<Run[]>(
    id ? `/api/v1/outreach/campaigns?projectId=${id}&page_size=100` : null,
  );
  const {
    data: prospects,
    loading: prospectsLoading,
    error: prospectsError,
    refresh: refreshProspects,
  } = useApi<Prospect[]>(id ? `/api/v1/outreach/prospects?projectId=${id}&page_size=100` : null);
  const { data: messages, refresh: refreshMessages } = useApi<ConversationMessage[]>(
    "/api/v1/outreach/conversations?page_size=100",
  );

  const prospectIds = useMemo(
    () => new Set((prospects ?? []).map((p) => p.id)),
    [prospects],
  );

  const messagesByProspect = useMemo(() => {
    const m = new Map<string, ConversationMessage[]>();
    for (const msg of messages ?? []) {
      if (!prospectIds.has(msg.prospectId)) continue;
      const list = m.get(msg.prospectId);
      if (list) list.push(msg);
      else m.set(msg.prospectId, [msg]);
    }
    for (const list of m.values()) {
      list.sort((a, b) => a.createdAt.localeCompare(b.createdAt));
    }
    return m;
  }, [messages, prospectIds]);

  const prospectsWithoutADraft = useMemo(
    () =>
      (prospects ?? []).filter(
        (p) => p.status !== "rejected" && (messagesByProspect.get(p.id) ?? []).length === 0,
      ),
    [prospects, messagesByProspect],
  );

  const runDate = useMemo(
    () => new Map((runs ?? []).map((r) => [r.id, r.createdAt] as const)),
    [runs],
  );

  const [actionErr, setActionErr] = useState<string | null>(null);
  const [syncNote, setSyncNote] = useState<string | null>(null);

  const runAction = async (fn: () => Promise<unknown>) => {
    setActionErr(null);
    try {
      await fn();
    } catch (e) {
      setActionErr(e instanceof Error ? e.message : "Something went wrong");
    }
  };

  const [editOpen, setEditOpen] = useState(false);
  const [editKey, setEditKey] = useState(0);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const editTaskRef = useRef<string | null>(null);
  const editFormRef = useRef<ProjectForm | null>(null);

  const { launchTask, updateTaskDraft } = useAgentTasks();
  const isApp = useIsApp();
  const mailbox = useSendingAs();

  const deriveEditDraft = (form: ProjectForm): Record<string, string | undefined> => ({
    project: project ? `${project.name} (id ${project.id})` : undefined,
    ...form,
  });

  const [runModal, setRunModal] = useState(false);
  const [runCount, setRunCount] = useState("10");
  const [runErr, setRunErr] = useState<string | null>(null);
  const [runBusy, setRunBusy] = useState(false);

  const startRun = async () => {
    if (!project) return;
    const count = Math.floor(Number(runCount));
    if (!Number.isInteger(count) || count < 1 || count > 100) {
      setRunErr("Pick a whole number between 1 and 100.");
      return;
    }
    setRunBusy(true);
    setRunErr(null);
    try {
      const run = await api<Run>("/api/v1/outreach/campaigns", {
        method: "POST",
        body: { projectId: project.id, requestedCount: count },
      });
      setRunModal(false);
      await refreshRuns();
      launchTask({
        title: `Run campaign: ${project.name}`,
        endpoint: "/api/agent/run-campaign",
        emptyHint:
          "Meelu is searching the web for prospects that match this project's brief. Interject any time to steer it.",
        draft: {
          project: `${project.name} (id ${project.id})`,
          campaign: `run (id ${run.id})`,
          requestedCount: String(count),
        },
        autoStart: `Run the campaign: find ${count} prospect${count === 1 ? "" : "s"} for this project and add them to run ${run.id}.`,
        onCreated: async () => {
          await Promise.all([refreshProspects(), refreshRuns()]);
        },
      });
    } catch (e) {
      setRunErr(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setRunBusy(false);
    }
  };

  const openAsk = () => {
    if (!project) return;
    launchTask({
      title: `Meelu: ${project.name}`,
      endpoint: "/api/agent/project-assist",
      emptyHint:
        "Ask or instruct — this project, its runs, its prospects and their conversations are all yours to change from here. Meelu reads before it writes and confirms anything it would delete.",
      suggestions: chips.project(prospectsWithoutADraft.length),
      draft: {
        project: `${project.name} (id ${project.id})`,
        prospects: String((prospects ?? []).length),
        runs: String((runs ?? []).length),
      },
      onCreated: async () => {
        await Promise.all([refreshRuns(), refreshProspects(), refreshMessages()]);
      },
    });
  };

  const [syncing, setSyncing] = useState(false);
  const checkInbox = async () => {
    const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
    if (!bridge?.mailboxSyncProspects) {
      setActionErr("Checking the inbox needs the Meelu app and a connected mailbox.");
      return;
    }
    const addressed = (prospects ?? [])
      .filter((p) => p.email)
      .map((p) => ({ id: p.id, email: p.email as string }));
    if (addressed.length === 0) {
      setActionErr("No prospect here has an email address yet.");
      return;
    }

    setActionErr(null);
    setSyncing(true);
    try {
      const newest = (messages ?? [])
        .filter((m) => m.status === "received" && prospectIds.has(m.prospectId))
        .reduce<string | null>(
          (max, m) => (max === null || m.createdAt > max ? m.createdAt : max),
          null,
        );
      const since = newest ?? startOfToday();

      const res = await bridge.mailboxSyncProspects({
        since,
        prospects: addressed,
        siteId: activeSiteId(),
      });
      if ("error" in res) {
        setActionErr(res.error);
        return;
      }
      let added = 0;
      if (res.messages.length > 0) {
        const result = await api<{ added: unknown[]; skipped: number }>(
          "/api/v1/outreach/conversations",
          { method: "POST", body: { messages: res.messages } },
        );
        added = result.added.length;
        await Promise.all([refreshMessages(), refreshProspects()]);
      }
      setSyncNote(
        added === 0
          ? `No new replies (${res.scanned} message${res.scanned === 1 ? "" : "s"} since ${formatDate(res.since)}).`
          : `Pulled in ${added} repl${added === 1 ? "y" : "ies"}.`,
      );
    } catch (err) {
      setActionErr(err instanceof Error ? err.message : "The inbox check failed.");
    } finally {
      setSyncing(false);
    }
  };

  const exportCsv = () => {
    const rows = prospects ?? [];
    if (rows.length === 0) return;
    const header = [
      "name", "company", "role", "email", "website",
      "sourceUrl", "fitReason", "status", "addedAt",
    ];
    const csv = [
      header.join(","),
      ...rows.map((p) =>
        [
          p.name, p.company, p.role, p.email, p.website,
          p.sourceUrl, p.fitReason, p.status, p.createdAt,
        ]
          .map((v) => csvCell(v as string | undefined))
          .join(","),
      ),
    ].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `${(project?.name ?? "prospects").replace(/[^\w-]+/g, "-")}-prospects.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const [deleteProspect, setDeleteProspect] = useState<Prospect | null>(null);

  const changeProspectStatus = (p: Prospect, status: ProspectStatus) =>
    runAction(async () => {
      await api(`/api/v1/outreach/prospects/${p.id}`, { method: "PUT", body: { status } });
      await refreshProspects();
    });

  const editProspectWithMeelu = (p: Prospect) => {
    launchTask({
      title: `Edit prospect: ${p.name}`,
      endpoint: "/api/agent/edit-prospect",
      emptyHint:
        "Tell Meelu what changed — a status, a corrected email, a sharper fit note — and it updates just this prospect.",
      suggestions: chips.prospectEdit,
      draft: {
        prospect: `${p.name} (id ${p.id})`,
        project: project ? `${project.name} (id ${project.id})` : undefined,
        status: p.status,
      },
      onCreated: async () => {
        await refreshProspects();
      },
    });
  };

  const [prospectFilter, setProspectFilter] = useState("");
  const [prospectSorting, setProspectSorting] = useState<SortingState>([
    { id: "createdAt", desc: true },
  ]);
  const [prospectPagination, setProspectPagination] = useState<PaginationState>({
    pageIndex: 0,
    pageSize: 15,
  });

  const [selectedSnapshot, setSelectedSnapshot] = useState<Prospect | null>(null);
  const [prospectDrawerOpen, setProspectDrawerOpen] = useState(false);

  const selectedProspect = useMemo(
    () =>
      (prospects ?? []).find((p) => p.id === selectedSnapshot?.id) ?? selectedSnapshot,
    [prospects, selectedSnapshot],
  );

  const conversation = useMemo(
    () => (selectedProspect ? (messagesByProspect.get(selectedProspect.id) ?? []) : []),
    [messagesByProspect, selectedProspect],
  );

  const lastReceived = useMemo(
    () => [...conversation].reverse().find((m) => m.status === "received"),
    [conversation],
  );

  const [composeSubject, setComposeSubject] = useState("");
  const [composeBody, setComposeBody] = useState("");
  const [composeErr, setComposeErr] = useState<string | null>(null);
  const [usedDraftId, setUsedDraftId] = useState<string | null>(null);
  const [drafting, setDrafting] = useState(false);
  const [sending, setSending] = useState(false);
  const [confirmingSend, setConfirmingSend] = useState(false);
  const [copied, setCopied] = useState<string | null>(null);
  const [deleteMessage, setDeleteMessage] = useState<ConversationMessage | null>(null);

  const replySubject = (p: Prospect): string => {
    const last = [...(messagesByProspect.get(p.id) ?? [])]
      .reverse()
      .find((m) => m.status !== "draft");
    if (!last?.subject) return project ? `${project.name}` : "";
    return /^re:/i.test(last.subject) ? last.subject : `Re: ${last.subject}`;
  };

  const copyMessage = async (m: ConversationMessage) => {
    try {
      await navigator.clipboard.writeText(`Subject: ${m.subject}\n\n${m.body}`);
      setCopied(m.id);
      setTimeout(() => setCopied((id) => (id === m.id ? null : id)), 2000);
    } catch {
    }
  };

  const reviseComposed = async (p: Prospect, req: { instruction: string; selection: string | null; text: string }) => {
    if (refuseOnWeb("outreach-email revise")) return null;
    const res = await streamTurn({
      action: "outreach-email",
      message: [
        `You wrote this outreach email. Subject: "${composeSubject || replySubject(p)}"`,
        "",
        req.text,
        "",
        `It goes to ${p.company || p.name}. The reason they are on the list: ${p.fitReason ?? "not recorded"}.`,
        "",
        "Rules for this turn:",
        "· If what I say is a QUESTION about the draft, answer it with a view — say what you would do and why — and change nothing. Start your reply with ANSWER: on its own line.",
        `· If it is an INSTRUCTION, reply with the replacement ${req.selection ? "sentence" : "body"} and NOTHING else — no preamble, no quotes, no fence.`,
        "· Keep the hook that makes this not a template.",
        "· Never call a write tool — this screen saves the draft.",
        "",
        req.selection ? `About this passage: "${req.selection}"` : "",
        `What I want: ${req.instruction}`,
      ]
        .filter(Boolean)
        .join("\n"),
    }).result;
    if (!res.ok) throw new Error(res.error ?? "That did not go through.");
    const text = res.text.trim();
    if (/^ANSWER:/i.test(text)) return { answer: text.replace(/^ANSWER:\s*/i, "").trim() };
    return text ? { text } : null;
  };

  const draftWithMeelu = async (p: Prospect) => {
    setComposeErr(null);
    setDrafting(true);
    try {
      const typed = composeBody.trim();
      const text = await runInlineTurn({
        action: "compose-reply",
        message: typed
          ? "Rephrase and tighten what I've written in the box, keeping my intent and any fact I stated. Reply with the message only."
          : "Write the next message to this prospect. Reply with the message only.",
        form: {
          project: project ? `${project.name} (id ${project.id})` : undefined,
          prospect: `${p.name} (id ${p.id})`,
          company: p.company ?? undefined,
          theirEmail: p.email ?? undefined,
          messagesSoFar: String(conversation.length),
          theyReplied: lastReceived ? "yes" : "no",
          draftInTheBox: typed || undefined,
        },
      });
      if (text) setComposeBody(text);
      else setComposeErr("Meelu came back empty — try again, or write it yourself.");
    } catch (err) {
      setComposeErr(err instanceof Error ? err.message : "Meelu could not draft that.");
    } finally {
      setDrafting(false);
    }
  };

  const sendComposed = async (p: Prospect) => {
    const bridge = typeof window !== "undefined" ? window.meeluAgent : undefined;
    if (!bridge?.mailboxSend) {
      setComposeErr("Sending needs the Meelu app with a mailbox connected.");
      return;
    }
    if (!p.email) {
      setComposeErr("No email address on file for this prospect.");
      return;
    }
    const subject = composeSubject.trim() || replySubject(p);
    const body = composeBody.trim();
    if (!body) return;

    setComposeErr(null);
    setSending(true);
    let left = false;
    try {
      const res = await bridge.mailboxSend({
        to: [p.email],
        subject,
        body,
        replyToMessageId: lastReceived?.messageId ?? undefined,
        siteId: activeSiteId(),
      });
      if ("error" in res) {
        setComposeErr(res.error);
        return;
      }
      left = true;

      const record = {
        subject,
        body,
        status: "sent",
        from: res.from ?? mailbox.address ?? null,
        to: p.email,
        messageId: res.messageId || null,
        threadRef: lastReceived?.messageId ?? null,
      };
      if (usedDraftId) {
        await api(`/api/v1/outreach/conversations/${usedDraftId}`, {
          method: "PUT",
          body: record,
        });
      } else {
        await api("/api/v1/outreach/conversations", {
          method: "POST",
          body: { ...record, prospectId: p.id },
        });
      }
      setComposeBody("");
      setComposeSubject("");
      setUsedDraftId(null);
      await Promise.all([refreshMessages(), refreshProspects()]);
    } catch (err) {
      const detail = err instanceof Error ? err.message : String(err);
      const stale = /No handler registered/i.test(detail);
      setComposeErr(
        stale
          ? "This version of the Meelu app can't send yet — quit and reopen it, then try again. Nothing was sent."
          : left
            ? `Sent, but recording it failed: ${detail}. The message did go out — don't send it again.`
            : `Could not send: ${detail}`,
      );
    } finally {
      setSending(false);
    }
  };

  const [drawerTab, setDrawerTab] = useState<"conversation" | "details">("conversation");

  if (projectLoading) {
    return (
      <PageEnter>
        <Spinner />
      </PageEnter>
    );
  }

  if (projectError || !project) {
    return (
      <PageEnter>
        <Link
          href="/dashboard/outreach"
          className="inline-flex items-center gap-1.5 text-sm text-sub hover:text-ink transition-colors mb-4"
        >
          <ArrowLeft size={14} /> Back to Outreach
        </Link>
        <p className="text-sm text-bad">{projectError ?? "Project not found."}</p>
      </PageEnter>
    );
  }

  return (
    <PageEnter>
      <Link
        href="/dashboard/outreach"
        className="inline-flex items-center gap-1.5 text-sm text-sub hover:text-ink transition-colors mb-4"
      >
        <ArrowLeft size={14} /> Back to Outreach
      </Link>

      <div className="flex flex-wrap items-end justify-between gap-4 mb-6">
        <div>
          <h1 className="font-display text-2xl text-ink">{project.name}</h1>
          <p className="text-sm text-sub mt-1 max-w-2xl">
            {project.goal || "A standing outreach brief — every run below executes it."}
          </p>
          {!mailbox.unknown && (
            <p
              className={
                mailbox.ambiguous ? "text-xs text-warn mt-1" : "text-xs text-faint mt-1"
              }
            >
              {mailbox.line}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {isApp && (
            <Button onClick={() => {
              setRunCount("10");
              setRunErr(null);
              setRunModal(true);
            }}>
              <Play size={14} /> Run campaign
            </Button>
          )}
          <Button variant="outline" onClick={() => {
            editFormRef.current = projectToForm(project);
            editTaskRef.current = null;
            setEditKey((k) => k + 1);
            setEditOpen(true);
          }}>
            <Pencil size={14} /> Edit brief
          </Button>
          {isApp && (
            <Button variant="outline" onClick={checkInbox} disabled={syncing}>
              <Inbox size={14} /> {syncing ? "Checking…" : "Check inbox"}
            </Button>
          )}
          {isApp && (
            <IconButton
              title="Run a task"
              aria-label="Run a task"
              className="border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent"
              onClick={openAsk}
            >
              <Sparkles size={15} />
            </IconButton>
          )}
          <IconButton onClick={() => setDeleteOpen(true)} aria-label="Delete project">
            <Trash2 size={15} />
          </IconButton>
        </div>
      </div>

      {actionErr && <p className="text-sm text-bad mb-4">{actionErr}</p>}
      {syncNote && <p className="text-sm text-sub mb-4">{syncNote}</p>}

      {(runs ?? []).length > 0 && (
        <div className="mb-8">
          <h2 className="font-display text-lg text-ink mb-2">Runs</h2>
          <div className="space-y-2">
            {(runs ?? []).map((r) => (
              <div
                key={r.id}
                className="flex flex-wrap items-baseline gap-x-3 gap-y-1 rounded-xl border border-edge bg-panel px-3.5 py-2.5"
              >
                <Badge tone={runTone[r.status]}>{r.status}</Badge>
                <span className="text-sm text-ink">
                  asked {r.requestedCount} · found {r.found}
                </span>
                <span className="text-xs text-faint">{formatRelative(r.createdAt)}</span>
                {r.summary && (
                  <span className="basis-full text-xs text-sub leading-relaxed">
                    {r.summary}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="flex flex-wrap items-end justify-between gap-2 mb-3">
        <div>
          <h2 className="font-display text-lg text-ink">Prospects</h2>
          <p className="text-xs text-faint mt-1">
            Everyone this project's runs have found. Click a row to read the
            conversation and write the next message.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            value={prospectFilter}
            onChange={(e) => setProspectFilter(e.target.value)}
            placeholder="Search prospects…"
            className="w-56"
            aria-label="Search prospects"
          />
          <Button
            size="sm"
            variant="outline"
            onClick={exportCsv}
            disabled={(prospects ?? []).length === 0}
          >
            <Download size={14} /> Export CSV
          </Button>
        </div>
      </div>
      {prospectsError && <p className="text-sm text-bad mb-3">{prospectsError}</p>}
      {prospectsLoading ? (
        <Spinner />
      ) : (prospects ?? []).length === 0 ? (
        <EmptyState
          icon={Users}
          title="No prospects yet"
          hint='Hit "Run campaign" — Meelu searches the web against this brief and fills this list.'
        />
      ) : (
        <div className="mb-8">
          <ProspectsTable
            prospects={prospects ?? []}
            globalFilter={prospectFilter}
            onGlobalFilterChange={setProspectFilter}
            sorting={prospectSorting}
            onSortingChange={setProspectSorting}
            pagination={prospectPagination}
            onPaginationChange={setProspectPagination}
            onOpen={(p) => {
              setSelectedSnapshot(p);
              setDrawerTab("conversation");
              setComposeBody("");
              setComposeSubject(replySubject(p));
              setComposeErr(null);
              setUsedDraftId(null);
              setProspectDrawerOpen(true);
            }}
          />
        </div>
      )}

      <div className="mt-8 mb-3">
        <h2 className="font-display text-lg text-ink">The brief</h2>
        <p className="text-xs text-faint mt-1">
          What every run executes. Edit with the pencil above.
        </p>
      </div>
      <Card>
        <div className="space-y-5">
          <BriefField label="Prompt" value={project.prompt} />
          <BriefField label="Prospect profile" value={project.prospectProfile} />
          <BriefField label="Search criteria" value={project.searchCriteria} />
          <BriefField label="Email tone" value={project.emailTone} />
          <BriefField label="Value prop" value={project.valueProp} />
          <BriefField label="Call to action" value={project.cta} />
          <div className="border-t border-edge pt-4 text-xs text-faint space-y-1">
            <p>
              Created {formatDate(project.createdAt)} · {formatRelative(project.createdAt)}
            </p>
            {project.updatedAt !== project.createdAt && (
              <p>Updated {formatRelative(project.updatedAt)}</p>
            )}
          </div>
        </div>
      </Card>

      <Drawer
        open={prospectDrawerOpen}
        onClose={() => setProspectDrawerOpen(false)}
        title={
          selectedProspect && (
            <div className="min-w-0">
              <h2 className="font-display text-lg text-ink leading-snug truncate">
                {selectedProspect.name}
              </h2>
              {(selectedProspect.company || selectedProspect.role) && (
                <p className="text-xs text-sub mt-0.5 truncate">
                  {[selectedProspect.role, selectedProspect.company]
                    .filter(Boolean)
                    .join(" · ")}
                </p>
              )}
            </div>
          )
        }
        actions={
          selectedProspect && (
            <IconButton
              aria-label="Delete prospect"
              onClick={() => setDeleteProspect(selectedProspect)}
            >
              <Trash2 size={14} />
            </IconButton>
          )
        }
      >
        {selectedProspect && (
          <div className="space-y-5">
            <div role="tablist" className="flex items-center gap-1 border-b border-edge -mt-1">
              {(
                [
                  ["conversation", "Conversation"],
                  ["details", "Details"],
                ] as Array<[typeof drawerTab, string]>
              ).map(([key, label]) => (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={drawerTab === key}
                  onClick={() => setDrawerTab(key)}
                  className={`-mb-px px-3 py-2 text-sm border-b-2 transition-colors cursor-pointer ${
                    drawerTab === key
                      ? "border-accent text-ink font-medium"
                      : "border-transparent text-sub hover:text-ink"
                  }`}
                >
                  {label}
                  {key === "conversation" && conversation.length > 0 && (
                    <span className="ml-1.5 text-xs text-faint">{conversation.length}</span>
                  )}
                </button>
              ))}
            </div>

            <div hidden={drawerTab !== "details"} className="space-y-5">
              <AgentLaunchButton
                title="Ask Meelu about this prospect"
                hint="Who they are, why they were picked, what to say next — and it can make the change to their row when you agree. Running tasks stay under Tasks at bottom-right."
                onClick={() => editProspectWithMeelu(selectedProspect)}
              />
              <div>
                <p className="text-xs text-sub uppercase tracking-wide mb-2">Status</p>
                <Select
                  value={selectedProspect.status}
                  onChange={(e) =>
                    changeProspectStatus(selectedProspect, e.target.value as ProspectStatus)
                  }
                  className="w-40"
                  aria-label={`Status for ${selectedProspect.name}`}
                >
                  {PROSPECT_STATUSES.map((s) => (
                    <option key={s} value={s}>
                      {PROSPECT_STATUS_LABEL[s]}
                    </option>
                  ))}
                </Select>
              </div>

              <div>
                <p className="text-xs text-sub uppercase tracking-wide mb-2">Contact</p>
                <div className="space-y-1.5 text-sm">
                  {selectedProspect.email ? (
                    <p>
                      <a
                        href={`mailto:${selectedProspect.email}`}
                        className="inline-flex items-center gap-1.5 text-ink hover:text-accent transition-colors"
                      >
                        <Mail size={14} className="text-sub" /> {selectedProspect.email}
                      </a>
                    </p>
                  ) : (
                    <p className="text-faint">No email on file</p>
                  )}
                  {selectedProspect.website && (
                    <p>
                      <a
                        href={selectedProspect.website}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-ink hover:text-accent transition-colors"
                      >
                        <Globe size={14} className="text-sub" /> {selectedProspect.website}
                      </a>
                    </p>
                  )}
                  {selectedProspect.sourceUrl && (
                    <p>
                      <a
                        href={selectedProspect.sourceUrl}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1.5 text-ink hover:text-accent transition-colors"
                      >
                        <ExternalLink size={14} className="text-sub" /> Source
                      </a>
                    </p>
                  )}
                </div>
              </div>

              <div>
                <p className="text-xs text-sub uppercase tracking-wide mb-2">Why they fit</p>
                {selectedProspect.fitReason ? (
                  <p className="text-sm text-ink leading-relaxed whitespace-pre-wrap">
                    {selectedProspect.fitReason}
                  </p>
                ) : (
                  <p className="text-sm text-faint">No reason recorded.</p>
                )}
                {selectedProspect.status !== "rejected" && (
                  <Button
                    className="mt-3"
                    size="sm"
                    variant="outline"
                    onClick={() => changeProspectStatus(selectedProspect, "rejected")}
                  >
                    Not a fit
                  </Button>
                )}
              </div>

              <div className="border-t border-edge pt-4 text-xs text-faint space-y-1">
                <p>
                  Found by the run of{" "}
                  {formatDate(
                    runDate.get(selectedProspect.campaignId) ?? selectedProspect.createdAt,
                  )}
                </p>
                <p>
                  Added {formatDate(selectedProspect.createdAt)} ·{" "}
                  {formatRelative(selectedProspect.createdAt)}
                </p>
              </div>
            </div>

            <div hidden={drawerTab !== "conversation"} className="flex flex-col min-h-0">
              <div className="flex-1 space-y-3 pb-4">
                {conversation.length === 0 && (
                  <p className="text-sm text-faint py-6 text-center">
                    Nothing sent yet — write the first message below.
                  </p>
                )}
                {conversation.map((m) =>
                  m.status !== "received" ? (
                    <div key={m.id} className="flex justify-end">
                      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-accent-soft border border-accent/20 px-3.5 py-2.5">
                        {m.subject && (
                          <p className="text-xs text-sub mb-1 truncate">{m.subject}</p>
                        )}
                        <p className="text-sm text-ink leading-relaxed whitespace-pre-wrap">
                          {m.body}
                        </p>
                        <div className="flex items-center justify-end gap-2 mt-1.5">
                          {m.status === "draft" && (
                            <>
                              <button
                                type="button"
                                onClick={() => {
                                  setComposeSubject(m.subject);
                                  setComposeBody(m.body);
                                  setUsedDraftId(m.id);
                                  setComposeErr(null);
                                }}
                                className="text-[11px] text-accent hover:underline cursor-pointer"
                              >
                                Use
                              </button>
                              <button
                                type="button"
                                onClick={() => setDeleteMessage(m)}
                                aria-label="Delete draft"
                                className="text-faint hover:text-bad transition-colors cursor-pointer"
                              >
                                <Trash2 size={12} />
                              </button>
                            </>
                          )}
                          <span className="text-[11px] text-faint">
                            {m.status === "draft"
                              ? `draft · ${formatRelative(m.createdAt)}`
                              : formatRelative(m.createdAt)}
                          </span>
                          <button
                            type="button"
                            onClick={() => copyMessage(m)}
                            aria-label="Copy message"
                            className="text-faint hover:text-ink transition-colors cursor-pointer"
                          >
                            {copied === m.id ? <Check size={12} /> : <Copy size={12} />}
                          </button>
                        </div>
                      </div>
                    </div>
                  ) : (
                    <div key={m.id} className="flex justify-start">
                      <div className="max-w-[85%] rounded-2xl rounded-bl-md bg-panel2 border border-edge px-3.5 py-2.5">
                        {m.subject && (
                          <p className="text-xs text-sub mb-1 truncate">{m.subject}</p>
                        )}
                        <p className="text-sm text-ink leading-relaxed whitespace-pre-wrap">
                          {m.body}
                        </p>
                        <span className="block text-[11px] text-faint mt-1.5">
                          {formatRelative(m.createdAt)}
                        </span>
                      </div>
                    </div>
                  ),
                )}
              </div>

              {isApp && (
                <div className="sticky bottom-0 bg-panel border-t border-edge pt-3 space-y-2">
                  {composeErr && <p className="text-xs text-bad">{composeErr}</p>}
                  <input
                    value={composeSubject}
                    onChange={(ev) => setComposeSubject(ev.target.value)}
                    placeholder="Subject"
                    aria-label="Subject"
                    className="w-full bg-transparent text-xs text-sub outline-none border-b border-transparent focus:border-edge py-1"
                  />
                  {composeBody.trim() ? (
                    <Revise
                      kind="email"
                      value={composeBody}
                      onChange={setComposeBody}
                      onRevise={(req) => reviseComposed(selectedProspect, req)}
                    />
                  ) : (
                    <Textarea
                      value={composeBody}
                      onChange={(ev) => setComposeBody(ev.target.value)}
                      placeholder={
                        drafting ? "Meelu is writing…" : "Write a message, or ask Meelu to draft it…"
                      }
                      rows={3}
                      aria-label="Message"
                    />
                  )}

                  <p
                    className={cn(
                      "text-[11px] leading-relaxed",
                      mailbox.ambiguous || mailbox.none ? "text-warn" : "text-faint",
                    )}
                  >
                    <span className="uppercase tracking-wide">Sending as</span>{" "}
                    {sendingAsSentence(mailbox)}
                  </p>

                  {confirmingSend ? (
                    <div className="rounded-xl border border-accent/30 bg-accent-soft p-3 space-y-2.5">
                      <p className="text-[11px] font-medium uppercase tracking-wide text-accent">
                        This is what goes out
                      </p>
                      <p className="text-xs text-sub">
                        To {selectedProspect.email} · from {mailbox.address} ·{" "}
                        {composeSubject.trim() || replySubject(selectedProspect)}
                      </p>
                      <p className="max-h-40 overflow-y-auto whitespace-pre-wrap rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm leading-relaxed text-ink">
                        {composeBody}
                      </p>
                      <div className="flex flex-wrap gap-1.5">
                        <Button
                          size="sm"
                          disabled={sending}
                          onClick={async () => {
                            setConfirmingSend(false);
                            await sendComposed(selectedProspect);
                          }}
                        >
                          {sending ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                          Yes — send it
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => setConfirmingSend(false)}
                          disabled={sending}
                        >
                          Not yet
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <div className="flex items-center justify-between gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => draftWithMeelu(selectedProspect)}
                        disabled={drafting || sending}
                      >
                        {drafting ? (
                          <Loader2 size={14} className="animate-spin" />
                        ) : (
                          <Sparkles size={14} />
                        )}
                        {drafting ? "Drafting…" : composeBody.trim() ? "Rephrase with Meelu" : "Draft with Meelu"}
                      </Button>
                      <Button
                        size="sm"
                        onClick={() => setConfirmingSend(true)}
                        disabled={
                          sending ||
                          drafting ||
                          !composeBody.trim() ||
                          !selectedProspect.email ||
                          !mailbox.address
                        }
                        title={
                          mailbox.address
                            ? undefined
                            : "No mailbox settled for this website — bind one in Settings."
                        }
                      >
                        <Send size={14} /> Send…
                      </Button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        )}
      </Drawer>

      <Modal open={runModal} onClose={() => setRunModal(false)} title="Run campaign">
        <div className="space-y-4">
          <p className="text-sm text-sub">
            Meelu searches the web against this project&apos;s brief, verifies each lead on a
            real page, and adds them here. The only thing to pick:
          </p>
          <Field label="How many prospects?">
            <Input
              type="number"
              min={1}
              max={100}
              value={runCount}
              onChange={(e) => setRunCount(e.target.value)}
              autoFocus
            />
          </Field>
          {runErr && <p className="text-sm text-bad">{runErr}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setRunModal(false)}>
              Cancel
            </Button>
            <Button onClick={startRun} disabled={runBusy}>
              {runBusy ? <Loader2 size={14} className="animate-spin" /> : <Play size={14} />}
              Start the run
            </Button>
          </div>
        </div>
      </Modal>

      <ProjectFormModal
        key={editKey}
        open={editOpen}
        onClose={() => {
          editTaskRef.current = null;
          setEditOpen(false);
        }}
        project={project}
        onSaved={refreshProject}
        onFormChange={(form) => {
          editFormRef.current = form;
          if (editTaskRef.current) {
            updateTaskDraft(editTaskRef.current, deriveEditDraft(form));
          }
        }}
        agentSlot={
          <AgentLaunchButton
            title="Edit the brief with Meelu"
            hint="Starts a fresh task pinned to this project — describe the change and Meelu proposes the edit, saving only when you approve. Anything typed below counts as your draft; running tasks stay under Tasks at bottom-right."
            onClick={() => {
              const taskId = launchTask({
                title: "Edit project",
                endpoint: "/api/agent/edit-project",
                emptyHint:
                  "Say what should change — “tighten the prospect profile to fintech newsletters only”, “rewrite the CTA” — or paste feedback and let Meelu propose the edit. Nothing is saved until you say so.",
                suggestions: chips.projectEdit,
                draft: deriveEditDraft(editFormRef.current ?? projectToForm(project)),
                onCreated: async () => {
                  if (editTaskRef.current === taskId) {
                    editTaskRef.current = null;
                    setEditOpen(false);
                  }
                  await refreshProject();
                },
              });
              editTaskRef.current = taskId;
            }}
          />
        }
      />

      <ConfirmDelete
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        what={`project "${project.name}"`}
        onConfirm={async () => {
          await api(`/api/v1/outreach/projects/${project.id}`, { method: "DELETE" });
          router.push("/dashboard/outreach");
        }}
      />

      <ConfirmDelete
        open={deleteProspect !== null}
        onClose={() => setDeleteProspect(null)}
        what={deleteProspect ? `prospect "${deleteProspect.name}"` : "prospect"}
        onConfirm={async () => {
          if (!deleteProspect) return;
          await api(`/api/v1/outreach/prospects/${deleteProspect.id}`, { method: "DELETE" });
          if (deleteProspect.id === selectedProspect?.id) setProspectDrawerOpen(false);
          await Promise.all([refreshProspects(), refreshRuns()]);
        }}
      />

      <ConfirmDelete
        open={deleteMessage !== null}
        onClose={() => setDeleteMessage(null)}
        what="draft message"
        onConfirm={async () => {
          if (!deleteMessage) return;
          await api(`/api/v1/outreach/conversations/${deleteMessage.id}`, {
            method: "DELETE",
          });
          if (usedDraftId === deleteMessage.id) setUsedDraftId(null);
          await refreshMessages();
        }}
      />
    </PageEnter>
  );
}
