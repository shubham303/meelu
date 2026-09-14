"use client";

import { Suspense, useMemo, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { FileSpreadsheet, MessageSquareText, Plus, Trash2 } from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import { Button, ConfirmDelete, EmptyState, Spinner } from "@/components/ui";
import { api, useApi } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import { cn, formatRelative } from "@/lib/utils";
import type { AnalyticsReport, AnalyticsSession, AnalyticsSource } from "@/lib/types";

type ReportSummary = Omit<AnalyticsReport, "html"> & { htmlBytes: number };

interface Workspace {
  sessions: AnalyticsSession[];
  sources: AnalyticsSource[];
  reports: ReportSummary[];
}

type SortMode = "recent" | "name";

export default function AnalyticsPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <AnalyticsBody />
    </Suspense>
  );
}

function AnalyticsBody() {
  const focusId = useSearchParams().get("focus");
  const router = useRouter();
  const isApp = useIsApp();

  const {
    data: workspace,
    loading,
    error: workspaceError,
    refresh,
  } = useApi<Workspace>("/api/v1/analytics/workspace");

  const sources = workspace?.sources ?? [];

  const [starting, setStarting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<AnalyticsSession | null>(null);
  const [sort, setSort] = useState<SortMode>("recent");
  const [dragOver, setDragOver] = useState(false);
  const dropInputRef = useRef<HTMLInputElement>(null);

  const rows = useMemo(() => {
    const sessions = workspace?.sessions ?? [];
    const allSources = workspace?.sources ?? [];
    const reports = workspace?.reports ?? [];
    const mapped = sessions
      .map((s) => {
        const attached = allSources.filter((src) => src.sessionId === s.id);
        const sessionReports = reports.filter((r) => r.sessionId === s.id);
        return {
          session: s,
          files: attached,
          kept: sessionReports.length,
          activeAt: sessionReports.reduce(
            (latest, r) => (r.createdAt > latest ? r.createdAt : latest),
            s.createdAt,
          ),
        };
      })
      .filter(
        ({ session, files, kept }) => Boolean(session.sessionKey) || files.length > 0 || kept > 0,
      );
    if (sort === "name") {
      return mapped.sort((a, b) => a.session.title.localeCompare(b.session.title));
    }
    return mapped.sort((a, b) => (a.activeAt < b.activeAt ? 1 : -1));
  }, [workspace, sort]);

  const startSession = async (files?: File[]) => {
    if (starting) return;
    setStarting(true);
    setError(null);
    const csvs = (files ?? []).filter((f) => /\.csv$/i.test(f.name));
    try {
      const created = await api<AnalyticsSession>("/api/v1/analytics/sessions", {
        method: "POST",
        body: csvs.length > 0 ? { title: csvs[0].name.replace(/\.csv$/i, "") } : {},
      });
      const save = window.meeluAgent?.analyticsSaveSource;
      if (save) {
        for (const file of csvs) {
          const content = await file.text();
          const stored = await save({
            sessionId: created.id,
            sourceId: crypto.randomUUID(),
            content,
          });
          if ("error" in stored) throw new Error(stored.error);
          await api(`/api/v1/analytics/sessions/${created.id}/sources`, {
            method: "POST",
            body: { name: file.name.replace(/\.csv$/i, ""), filePath: stored.relativePath },
          });
        }
      }
      router.push(`/dashboard/analytics/${created.id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not start a session");
      setStarting(false);
    }
  };

  const removeSession = async (session: AnalyticsSession) => {
    setError(null);
    try {
      await api(`/api/v1/analytics/sessions/${session.id}`, { method: "DELETE" });
      for (const source of sources) {
        if (source.sessionId === session.id && source.filePath) {
          await window.meeluAgent?.analyticsDeleteSource?.({ relativePath: source.filePath });
        }
      }
      await refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not delete the session");
    }
  };

  return (
    <PageEnter>
      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-3xl text-ink">Sessions</h1>
          <p className="mt-2 max-w-xl text-sm text-sub">
            Your data stays loaded. Reopen a session and keep asking, or drop in another CSV and it
            joins the same workspace. The analysis runs on your device; raw files never leave it.
          </p>
        </div>
        {isApp && (
          <Button disabled={starting} onClick={() => void startSession()}>
            <Plus size={14} /> New session
          </Button>
        )}
      </div>

      {(workspaceError || error) && (
        <p className="mb-4 text-sm text-bad">{workspaceError ?? error}</p>
      )}

      {isApp && (
        <>
          <input
            ref={dropInputRef}
            type="file"
            accept=".csv,text/csv"
            multiple
            className="hidden"
            onChange={(e) => {
              const files = Array.from(e.target.files ?? []);
              e.target.value = "";
              if (files.length > 0) void startSession(files);
            }}
          />
          <div
            role="button"
            tabIndex={0}
            onClick={() => dropInputRef.current?.click()}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") dropInputRef.current?.click();
            }}
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragOver(false);
              const files = Array.from(e.dataTransfer.files ?? []);
              if (files.length > 0) void startSession(files);
            }}
            className={cn(
              "mb-8 flex cursor-pointer items-center gap-4 rounded-xl border border-dashed border-edge2 bg-panel2/60 px-6 py-5 transition-colors",
              dragOver ? "border-accent bg-accent-soft" : "hover:border-accent/50",
            )}
          >
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-panel shadow-sm">
              <FileSpreadsheet size={16} className="text-accent" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold text-ink">
                {starting ? "Starting…" : "Drop CSVs here to start a new session"}
              </p>
              <p className="mt-0.5 text-xs text-sub">
                Several files load as one dataset · click to browse files
              </p>
            </div>
          </div>
        </>
      )}

      {loading ? (
        <Spinner />
      ) : rows.length === 0 ? (
        <EmptyState
          icon={MessageSquareText}
          title="No sessions yet"
          hint={
            isApp
              ? "Drop a CSV above, or start an empty session and ask Meelu to pull the numbers it can already read."
              : "Sessions are started in the Meelu app, where your data lives."
          }
        />
      ) : (
        <>
          <div className="flex items-baseline gap-4 border-b border-edge pb-2.5">
            <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-faint">
              All sessions
            </span>
            <div className="ml-auto flex gap-4 text-xs">
              <button
                type="button"
                onClick={() => setSort("recent")}
                className={cn(
                  "cursor-pointer transition-colors",
                  sort === "recent" ? "font-semibold text-ink" : "text-faint hover:text-ink",
                )}
              >
                Recent
              </button>
              <button
                type="button"
                onClick={() => setSort("name")}
                className={cn(
                  "cursor-pointer transition-colors",
                  sort === "name" ? "font-semibold text-ink" : "text-faint hover:text-ink",
                )}
              >
                Name
              </button>
            </div>
          </div>

          <div className="grid grid-cols-[1fr_130px_110px_28px] gap-x-3 px-1 py-2.5 font-mono text-[10px] uppercase tracking-[0.08em] text-faint max-md:hidden">
            <span>Session</span>
            <span>Data</span>
            <span className="text-right">Active</span>
            <span />
          </div>

          <Stagger className="flex flex-col">
            {rows.map(({ session: s, files, kept, activeAt }) => (
              <div
                key={s.id}
                className={cn(
                  "stagger-item grid grid-cols-[1fr_130px_110px_28px] items-center gap-x-3 rounded-lg border-t border-edge px-1 py-3.5 transition-colors hover:bg-panel2 max-md:grid-cols-[1fr_28px]",
                  focusId === s.id && "bg-accent-soft",
                )}
              >
                <button
                  type="button"
                  onClick={() => router.push(`/dashboard/analytics/${s.id}`)}
                  className="min-w-0 cursor-pointer text-left"
                >
                  <span className="block truncate font-display text-[16px] text-ink">
                    {s.title}
                  </span>
                  <span
                    className="mt-0.5 block truncate font-mono text-[10.5px] text-faint"
                    title={files.map((f) => f.name).join(" · ")}
                  >
                    {files.length > 0
                      ? files.map((f) => f.name).join(" · ")
                      : (s.about || "no files attached")}
                  </span>
                </button>
                <span className="font-mono text-xs text-sub max-md:hidden">
                  {files.length} file{files.length === 1 ? "" : "s"}
                  {kept > 0 ? ` · ${kept} rpt` : ""}
                </span>
                <span className="text-right text-xs text-sub max-md:hidden">
                  {formatRelative(activeAt)}
                </span>
                <button
                  type="button"
                  aria-label="Delete session"
                  title="Delete session"
                  onClick={() => setDeleting(s)}
                  className="cursor-pointer justify-self-end text-faint transition-colors hover:text-bad"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </Stagger>
        </>
      )}

      <ConfirmDelete
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        what={deleting ? `session "${deleting.title}"` : "session"}
        onConfirm={() => {
          if (deleting) return removeSession(deleting);
        }}
      />
    </PageEnter>
  );
}
