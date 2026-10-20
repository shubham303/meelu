"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { Loader2, MessageCircleQuestion, Plus, RotateCw, Sparkles, Square, Trash2 } from "lucide-react";
import { PageEnter } from "@/components/animate";
import { Badge, Button, ConfirmDelete, IconButton, Modal, PageHeader, Spinner, Textarea } from "@/components/ui";
import { api, useApi } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import type { GeoQuery, GeoSummary } from "@/lib/types";
import { cn, formatRelative } from "@/lib/utils";
import { useAgentTasks } from "../agent-tasks";
import { INTENT, VERDICT, citedBy, finishedCheck, isRunning, pathOf } from "./lib";

const POLL_MS = 3000;

function StatusCell({ query }: { query: GeoQuery }) {
  const check = query.latestCheck;
  if (!check) return <span className="text-sub">Not checked</span>;
  if (check.status === "running") {
    return (
      <span className="inline-flex items-center gap-1.5 text-sub">
        <Loader2 size={13} className="animate-spin" /> Checking
      </span>
    );
  }
  if (check.status === "error") return <Badge tone="bad">Check failed</Badge>;
  if (check.status === "stopped") return <span className="text-sub">Stopped</span>;
  if (!check.verdict) return <span className="text-sub">—</span>;
  const v = VERDICT[check.verdict];
  return (
    <span title={v.hint}>
      <Badge tone={v.tone}>{v.label}</Badge>
    </span>
  );
}

function Tile({ label, value, className }: { label: string; value: string; className: string }) {
  return (
    <div className="rounded-2xl border border-edge bg-panel px-4 py-3">
      <p className="text-[12.5px] text-sub">{label}</p>
      <p className={cn("mt-0.5 text-2xl font-semibold tabular-nums", className)}>{value}</p>
    </div>
  );
}

export default function GeoPage() {
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  const { data: queries, loading, refresh: refreshQueries } = useApi<GeoQuery[]>("/api/v1/geo/queries");
  const { data: summary, refresh: refreshSummary } = useApi<GeoSummary>("/api/v1/geo/summary");
  const [adding, setAdding] = useState(false);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [checking, setChecking] = useState(false);
  const [stopping, setStopping] = useState(false);
  const [removing, setRemoving] = useState<GeoQuery | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refreshAll = useCallback(async () => {
    await Promise.all([refreshQueries(), refreshSummary()]);
  }, [refreshQueries, refreshSummary]);

  const rows = queries ?? [];
  const anyRunning = rows.some(isRunning);

  useEffect(() => {
    if (!anyRunning) return;
    const timer = window.setInterval(() => void refreshAll(), POLL_MS);
    return () => window.clearInterval(timer);
  }, [anyRunning, refreshAll]);

  const startChecks = async () => {
    setChecking(true);
    setError(null);
    try {
      const res = await api<{ started: unknown[]; alreadyRunning: number }>("/api/v1/geo/checks", {
        method: "POST",
        body: {},
      });
      if (res.started.length === 0 && res.alreadyRunning === 0) {
        setError("Every question was checked in the last 7 days.");
      }
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The check did not start.");
    } finally {
      setChecking(false);
    }
  };

  const stopChecks = async () => {
    setStopping(true);
    setError(null);
    try {
      await api("/api/v1/geo/checks/stop", { method: "POST", body: {} });
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The checks did not stop.");
    } finally {
      setStopping(false);
    }
  };

  const saveQuestions = async () => {
    const texts = draft
      .split("\n")
      .map((t) => t.trim())
      .filter(Boolean);
    if (texts.length === 0) return;
    setSaving(true);
    setError(null);
    try {
      await api("/api/v1/geo/queries", { method: "POST", body: texts.map((text) => ({ text })) });
      setDraft("");
      setAdding(false);
      await refreshAll();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The questions did not save.");
    } finally {
      setSaving(false);
    }
  };

  const stopTracking = async (query: GeoQuery) => {
    await api(`/api/v1/geo/queries/${query.id}`, { method: "DELETE" });
    setRemoving(null);
    await refreshAll();
  };

  const ask = () =>
    launchTask({
      title: "Ask — GEO",
      endpoint: "/api/agent/ask-geo",
      emptyHint: "Ask why a question has no page, what the AI answers cite, or for related questions worth tracking.",
      draft: {},
      onWrote: () => void refreshAll(),
    });

  const suggest = () =>
    launchTask({
      title: "Suggest questions — GEO",
      endpoint: "/api/agent/geo-setup",
      emptyHint: "Meelu proposes questions to track from your profile and search data. You approve the wording.",
      draft: {},
      autoStart: "Suggest questions this website should track in AI search.",
      onWrote: () => void refreshAll(),
    });

  const checkedCount = summary ? summary.queries - summary.unchecked : 0;

  return (
    <PageEnter>
      <PageHeader
        title="GEO"
        description="Questions people ask AI search, and whether a page on your site answers them. Meelu checks and suggests. You decide what to change."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button variant="outline" onClick={() => setAdding(true)}>
              <Plus size={14} /> Add question
            </Button>
            {isApp && (
              <Button variant="ghost" onClick={suggest}>
                <MessageCircleQuestion size={14} /> Suggest questions
              </Button>
            )}
            {anyRunning ? (
              <Button variant="outline" onClick={() => void stopChecks()} disabled={stopping}>
                <Square size={13} /> Stop checks
              </Button>
            ) : (
              <Button onClick={() => void startChecks()} disabled={checking || rows.length === 0}>
                <RotateCw size={14} /> Check stale questions
              </Button>
            )}
            {isApp && (
              <IconButton
                title="Ask Meelu"
                aria-label="Ask Meelu"
                className="h-9 w-9 border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent"
                onClick={ask}
              >
                <Sparkles size={16} />
              </IconButton>
            )}
          </div>
        }
      />

      {loading ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <div className="flex flex-col items-center gap-2.5 rounded-2xl border border-dashed border-edge2 px-6 py-12 text-center">
          <MessageCircleQuestion size={26} className="text-sub" />
          <p className="text-[15px] font-semibold text-ink">No questions tracked yet</p>
          <p className="max-w-md text-[13.5px] text-sub">
            Add the questions your customers ask ChatGPT, Claude or Google. A check shows whether a page on your site
            answers each one, and what the AI answers say and cite.
          </p>
          <Button className="mt-1" onClick={() => setAdding(true)}>
            <Plus size={14} /> Add question
          </Button>
        </div>
      ) : (
        <div className="space-y-5">
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            <Tile label="No page" value={String(summary?.noPage ?? 0)} className="text-bad" />
            <Tile label="Partly answered" value={String(summary?.partial ?? 0)} className="text-warn" />
            <Tile label="Answered, low rank" value={String(summary?.lowRank ?? 0)} className="text-accent" />
            <Tile
              label="Cited by an AI answer"
              value={`${summary?.cited ?? 0} of ${checkedCount}`}
              className="text-good"
            />
          </div>

          <div className="flex flex-wrap items-center justify-between gap-2 text-[13px] text-sub">
            <span>
              {rows.length} question{rows.length === 1 ? "" : "s"} tracked
              {summary?.unchecked ? ` · ${summary.unchecked} not checked yet` : ""}
              {summary?.running ? ` · ${summary.running} checking` : ""}
            </span>
            {summary?.lastCheckedAt && <span>Last check {formatRelative(summary.lastCheckedAt)}</span>}
          </div>

          {error && <p className="text-sm text-bad">{error}</p>}

          <div className="overflow-x-auto rounded-2xl border border-edge bg-panel">
            <table className="w-full min-w-[760px] border-collapse text-[13.5px]">
              <thead>
                <tr className="text-left text-xs text-sub">
                  <th className="border-b border-edge px-4 py-3 font-medium">Question</th>
                  <th className="border-b border-edge px-2 py-3 font-medium">Intent</th>
                  <th className="border-b border-edge px-2 py-3 font-medium">Verdict</th>
                  <th className="border-b border-edge px-2 py-3 font-medium">Best page</th>
                  <th className="border-b border-edge px-2 py-3 font-medium">Page position</th>
                  <th className="border-b border-edge px-2 py-3 font-medium">Cited by</th>
                  <th className="border-b border-edge px-4 py-3 font-medium">Checked</th>
                  <th className="border-b border-edge px-2 py-3" aria-label="Actions" />
                </tr>
              </thead>
              <tbody>
                {rows.map((q) => {
                  const done = finishedCheck(q);
                  return (
                    <tr
                      key={q.id}
                      className={cn(
                        "transition-colors hover:bg-panel2/60",
                        !q.enabled && "opacity-60",
                      )}
                    >
                      <td className="border-b border-edge px-2 py-1.5">
                        <Link
                          href={`/dashboard/geo/${q.id}`}
                          className="inline-flex min-h-10 items-center rounded-md px-2 py-1 text-left font-medium text-ink hover:text-accent"
                        >
                          {q.text}
                        </Link>
                      </td>
                      <td className="border-b border-edge px-2 py-2.5 text-sub">
                        {done?.intent ? INTENT[done.intent] : "—"}
                      </td>
                      <td className="border-b border-edge px-2 py-2.5">
                        <StatusCell query={q} />
                      </td>
                      <td className="max-w-[220px] truncate border-b border-edge px-2 py-2.5 text-sub">
                        {done ? (done.pageUrl ? pathOf(done.pageUrl) : "no page") : "—"}
                      </td>
                      <td className="border-b border-edge px-2 py-2.5 tabular-nums">
                        {done?.position != null ? done.position.toFixed(1) : "—"}
                      </td>
                      <td className="border-b border-edge px-2 py-2.5 text-sub">{citedBy(done)}</td>
                      <td className="whitespace-nowrap border-b border-edge px-4 py-2.5 text-sub">
                        {done ? formatRelative(done.finishedAt ?? done.startedAt) : "—"}
                      </td>
                      <td className="border-b border-edge px-2 py-2.5 text-right">
                        <IconButton
                          title="Stop tracking"
                          aria-label="Stop tracking"
                          className="hover:text-bad"
                          onClick={() => setRemoving(q)}
                        >
                          <Trash2 size={14} />
                        </IconButton>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <Modal open={adding} onClose={() => setAdding(false)} title="Add questions">
        <div className="space-y-3">
          <p className="text-sm text-sub">
            One question per line, written the way a person asks ChatGPT or Google. Add related questions (the
            follow-up, the comparison), not rewordings of the same one.
          </p>
          <Textarea
            rows={6}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder={"how do I find keyword cannibalization\nwhat is the best SEO tool for a small business"}
          />
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setAdding(false)}>
              Cancel
            </Button>
            <Button onClick={() => void saveQuestions()} disabled={saving || !draft.trim()}>
              {saving ? "Saving…" : "Add"}
            </Button>
          </div>
        </div>
      </Modal>

      <ConfirmDelete
        open={removing !== null}
        onClose={() => setRemoving(null)}
        onConfirm={() => (removing ? stopTracking(removing) : undefined)}
        what="this question and its checks"
      />
    </PageEnter>
  );
}
