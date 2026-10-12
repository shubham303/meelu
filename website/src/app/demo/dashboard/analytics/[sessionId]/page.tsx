"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import {
  ArrowLeft,
  BarChart3,
  Download,
  Eye,
  FolderOpen,
  Pencil,
  Plus,
  Sparkles,
  TriangleAlert,
  Trash2,
} from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import {
  Button,
  Card,
  ConfirmDelete,
  Drawer,
  Field,
  IconButton,
  Input,
  Modal,
  Spinner,
  Table,
  TCell,
  Textarea,
  THead,
  TRow,
} from "@demo/components/ui";
import { api, useApi } from "@demo/lib/use-api";
import { useIsApp } from "@demo/lib/use-app-mode";
import { formatRelative } from "@demo/lib/utils";
import type { AnalyticsReport, AnalyticsSession, AnalyticsSource } from "@demo/lib/types";
import * as chips from "@demo/features/prompt-chips/analytics";
import { useAgentTasks } from "../../agent-tasks";

type ReportSummary = Omit<AnalyticsReport, "html"> & { htmlBytes: number };

type LocalCheck = { engine: "none" | "present" | "missing"; missing: string[]; ok: boolean };

type SourcePreview = {
  name: string;
  path: string;
  bytes: number;
  columns: string[];
  rows: string[][];
  more: boolean;
};

type ColumnKind = "INT" | "NUM" | "DATE" | "BOOL" | "CAT" | "TXT";

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${Math.round(n / 1024)} KB`;
  return `${(n / (1024 * 1024)).toFixed(1)} MB`;
}

function inferColumnKind(values: string[]): ColumnKind {
  const vals = values.map((v) => (v ?? "").trim()).filter((v) => v !== "");
  if (vals.length === 0) return "TXT";
  const lower = vals.map((v) => v.toLowerCase());
  if (
    lower.every((v) => ["true", "false", "yes", "no", "0", "1"].includes(v)) &&
    new Set(lower).size <= 2
  ) {
    return "BOOL";
  }
  const numeric = vals.map((v) => v.replace(/[,%$€₹\s]/g, ""));
  if (numeric.every((v) => /^-?\d+$/.test(v))) return "INT";
  if (numeric.every((v) => /^-?\d*\.?\d+(e-?\d+)?$/i.test(v))) return "NUM";
  if (vals.every((v) => !Number.isNaN(Date.parse(v)) && /[-/:]/.test(v))) return "DATE";
  if (new Set(lower).size <= Math.max(2, Math.floor(vals.length / 4))) return "CAT";
  return "TXT";
}

const COLS_SHOWN = 10;

export default function AnalyticsSessionPage() {
  return (
    <Suspense fallback={<Spinner />}>
      <AnalyticsSessionBody />
    </Suspense>
  );
}

function AnalyticsSessionBody() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();

  const { data: sources, refresh: refreshSources } = useApi<AnalyticsSource[]>(
    sessionId ? `/api/v1/analytics/sessions/${sessionId}/sources` : null,
  );
  const {
    data: session,
    error,
    refresh: refreshSession,
  } = useApi<AnalyticsSession>(sessionId ? `/api/v1/analytics/sessions/${sessionId}` : null);
  const { data: sessionReports, refresh: refreshReports } = useApi<ReportSummary[]>(
    sessionId ? `/api/v1/analytics/reports?sessionId=${sessionId}&page_size=100` : null,
  );
  const reports = sessionReports ?? [];

  const [openReportId, setOpenReportId] = useState<string | null>(null);
  const [openReport, setOpenReport] = useState<AnalyticsReport | null>(null);
  const [reportErr, setReportErr] = useState<string | null>(null);
  const [deletingReport, setDeletingReport] = useState<ReportSummary | null>(null);
  const [deletingSource, setDeletingSource] = useState<AnalyticsSource | null>(null);
  const [sourceErr, setSourceErr] = useState<string | null>(null);
  const [previewSource, setPreviewSource] = useState<AnalyticsSource | null>(null);
  const [preview, setPreview] = useState<SourcePreview | null>(null);
  const [savedTo, setSavedTo] = useState<string | null>(null);
  const [localCheck, setLocalCheck] = useState<LocalCheck | null>(null);
  const [samples, setSamples] = useState<Record<string, SourcePreview>>({});
  const [openCols, setOpenCols] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const check = window.meeluAgent?.analyticsCheckSession;
    if (!check || !session || !sources) return;
    let alive = true;
    void check({
      sessionKey: session.sessionKey ?? null,
      paths: sources.map((s) => s.filePath).filter((p): p is string => Boolean(p)),
    })
      .then((r) => {
        if (alive) setLocalCheck("error" in r ? null : r);
      })
      .catch(() => {
        if (alive) setLocalCheck(null);
      });
    return () => {
      alive = false;
    };
  }, [session, sources]);

  useEffect(() => {
    const read = window.meeluAgent?.analyticsReadSource;
    if (!read || !sources) return;
    let alive = true;
    void (async () => {
      const next: Record<string, SourcePreview> = {};
      for (const s of sources.slice(0, 8)) {
        if (!s.filePath) continue;
        const r = await read({ relativePath: s.filePath, limit: 60 }).catch(() => null);
        if (r && !("error" in r)) next[s.id] = r;
      }
      if (alive) setSamples(next);
    })();
    return () => {
      alive = false;
    };
  }, [sources]);

  const fileColumns = useMemo(() => {
    const byFile: Record<string, Array<{ name: string; kind: ColumnKind }>> = {};
    for (const s of sources ?? []) {
      const sample = samples[s.id];
      if (!sample) continue;
      byFile[s.id] = sample.columns.map((name, i) => ({
        name,
        kind: inferColumnKind(sample.rows.map((row) => row[i] ?? "")),
      }));
    }
    return byFile;
  }, [sources, samples]);

  const [renameOpen, setRenameOpen] = useState(false);
  const [renameTitle, setRenameTitle] = useState("");
  const [renameAbout, setRenameAbout] = useState("");
  const [renaming, setRenaming] = useState(false);
  const [renameErr, setRenameErr] = useState<string | null>(null);

  const openRename = () => {
    setRenameTitle(session?.title ?? "");
    setRenameAbout(session?.about ?? "");
    setRenameErr(null);
    setRenameOpen(true);
  };

  const saveRename = async () => {
    const title = renameTitle.trim();
    if (!title || !session) return;
    setRenaming(true);
    setRenameErr(null);
    try {
      await api(`/api/v1/analytics/sessions/${session.id}`, {
        method: "PUT",
        body: { title, about: renameAbout.trim() },
      });
      setRenameOpen(false);
      await refreshSession();
    } catch (e) {
      setRenameErr(e instanceof Error ? e.message : "Could not save the session");
    } finally {
      setRenaming(false);
    }
  };

  const buildDraft = useCallback(async (): Promise<Record<string, string | undefined>> => {
    const attached = sources ?? [];
    const relative = attached.map((s) => s.filePath).filter((p): p is string => Boolean(p));
    const resolved = await window.meeluAgent
      ?.analyticsResolvePaths?.({ paths: relative })
      .then((r) => (Array.isArray(r) ? r : []))
      .catch(() => []);
    const pathOf = new Map((resolved ?? []).map((r) => [r.relativePath, r.missing ? null : r.path]));
    const sourceLines = attached.map((s) =>
      [
        `${s.name} (${s.id})`,
        s.filePath
          ? (pathOf.get(s.filePath) ?? `${s.filePath} — MISSING on this machine`)
          : "no file recorded",
      ].join(" — "),
    );

    return {
      session: session ? `${session.title} (${session.id})` : sessionId,
      "about the data": session?.about || undefined,
      "engine session_key":
        session?.sessionKey ??
        "none yet — create_session with the file paths below, then store the key with analytics_update_session",
      "data sources": sourceLines.length > 0 ? sourceLines.join("\n") : "none attached yet",
    };
  }, [session, sessionId, sources]);

  const ask = async () => {
    if (!session) return;
    const draft = await buildDraft();
    launchTask({
      title: `Ask — ${session.title}`,
      endpoint: "/api/agent/analyze-data",
      emptyHint:
        "Attach a CSV, or just ask — Meelu pulls in whatever it needs and runs the analysis on this device. Ask it to keep a dashboard and it lands under Reports.",
      suggestions: chips.ask,
      draft,
      onCreated: async () => {
        await Promise.all([refreshReports(), refreshSources(), refreshSession()]);
      },
    });
  };

  const [attaching, setAttaching] = useState(false);
  const [attachError, setAttachError] = useState<string | null>(null);
  const sourceFileInputRef = useRef<HTMLInputElement>(null);

  const attachFile = async (file: File) => {
    setAttaching(true);
    setAttachError(null);
    const save = window.meeluAgent?.analyticsSaveSource;
    if (!save) {
      setAttachError("File uploads work in the Meelu app — the data stays on your device.");
      setAttaching(false);
      return;
    }
    let storedPath: string | null = null;
    try {
      const content = await file.text();
      const stored = await save({ sessionId, sourceId: crypto.randomUUID(), content });
      if ("error" in stored) throw new Error(stored.error);
      storedPath = stored.relativePath;
      await api(`/api/v1/analytics/sessions/${sessionId}/sources`, {
        method: "POST",
        body: { name: file.name.replace(/\.csv$/i, ""), filePath: storedPath },
      });
      await refreshSources();
    } catch (e) {
      if (storedPath) {
        await window.meeluAgent
          ?.analyticsDeleteSource?.({ relativePath: storedPath })
          .catch(() => {});
      }
      setAttachError(e instanceof Error ? e.message : "Could not store the file");
    } finally {
      setAttaching(false);
    }
  };

  const viewSource = async (s: AnalyticsSource) => {
    setPreviewSource(s);
    setPreview(null);
    setSourceErr(null);
    if (!s.filePath) return;
    const read = await window.meeluAgent?.analyticsReadSource?.({
      relativePath: s.filePath,
      limit: 200,
    });
    if (!read) {
      setSourceErr("Reading files works in the Meelu app — the data stays on your device.");
      setPreviewSource(null);
    } else if ("error" in read) {
      setSourceErr(read.error);
      setPreviewSource(null);
    } else {
      setPreview(read);
    }
  };

  const revealFile = async (s: AnalyticsSource) => {
    setSourceErr(null);
    if (!s.filePath) return;
    const done = await window.meeluAgent?.analyticsRevealSource?.({ relativePath: s.filePath });
    if (done && "error" in done) setSourceErr(done.error);
  };

  const saveSourceCopy = async (s: AnalyticsSource) => {
    setSourceErr(null);
    setSavedTo(null);
    if (!s.filePath) return;
    const done = await window.meeluAgent?.analyticsExportSource?.({ relativePath: s.filePath });
    if (!done) setSourceErr("Saving a copy works in the Meelu app.");
    else if ("error" in done) setSourceErr(done.error);
    else if (done.path) setSavedTo(done.path);
  };

  const saveReport = async (r: ReportSummary) => {
    setReportErr(null);
    setSavedTo(null);
    try {
      const full = await api<AnalyticsReport>(`/api/v1/analytics/reports/${r.id}`);
      const name = `${r.title.replace(/[^\w -]+/g, "").trim() || "report"}.html`;
      const save = window.meeluAgent?.analyticsExportText;
      if (save) {
        const done = await save({ name, content: full.html });
        if ("error" in done) setReportErr(done.error);
        else if (done.path) setSavedTo(done.path);
        return;
      }
      const url = URL.createObjectURL(new Blob([full.html], { type: "text/html" }));
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e) {
      setReportErr(e instanceof Error ? e.message : "Could not save the report");
    }
  };

  const viewReport = async (id: string) => {
    setOpenReportId(id);
    setOpenReport(null);
    setReportErr(null);
    try {
      setOpenReport(await api<AnalyticsReport>(`/api/v1/analytics/reports/${id}`));
    } catch (e) {
      setReportErr(e instanceof Error ? e.message : "Could not load the report");
    }
  };

  const removeReport = async (r: ReportSummary) => {
    setReportErr(null);
    try {
      await api(`/api/v1/analytics/reports/${r.id}`, { method: "DELETE" });
      setDeletingReport(null);
      if (openReportId === r.id) setOpenReportId(null);
      await refreshReports();
    } catch (e) {
      setReportErr(e instanceof Error ? e.message : "Something went wrong");
    }
  };

  const removeSource = async (s: AnalyticsSource) => {
    setSourceErr(null);
    try {
      await api(`/api/v1/analytics/sources/${s.id}`, { method: "DELETE" });
      if (s.filePath) {
        await window.meeluAgent?.analyticsDeleteSource?.({ relativePath: s.filePath });
      }
      setDeletingSource(null);
      await refreshSources();
    } catch (e) {
      setSourceErr(e instanceof Error ? e.message : "Something went wrong");
    }
  };

  if (error) {
    return (
      <PageEnter>
        <p className="text-sm text-bad">{error}</p>
      </PageEnter>
    );
  }
  if (!session) return <Spinner />;

  return (
    <PageEnter>
      <Link
        href="/demo/dashboard/analytics"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-sub transition-colors hover:text-ink"
      >
        <ArrowLeft size={14} /> Sessions
      </Link>

      <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="font-display text-2xl text-ink">{session.title}</h1>
            <IconButton onClick={openRename} aria-label="Rename session">
              <Pencil size={13} />
            </IconButton>
          </div>
          <p className="mt-1 max-w-2xl text-sm text-sub">
            {formatRelative(session.createdAt)}
            {session.about ? ` · ${session.about}` : ""}
          </p>
        </div>
        {isApp && (
          <IconButton
            title="Ask Meelu"
            aria-label="Ask Meelu"
            className="border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent"
            onClick={() => void ask()}
          >
            <Sparkles size={16} />
          </IconButton>
        )}
      </div>

      {localCheck && !localCheck.ok && (
        <Card className="mb-6 border-warn/30 bg-warn/10 px-4 py-3">
          <div className="flex items-start gap-2.5">
            <TriangleAlert size={15} className="mt-0.5 shrink-0 text-warn" />
            <div className="min-w-0 space-y-1">
              <p className="text-sm font-medium text-ink">
                Some of this session&rsquo;s data is missing from this device
              </p>
              {localCheck.engine === "missing" && (
                <p className="text-xs text-sub">
                  The analysis engine has no ingested copy of this data any more, so the next
                  question will load it again before answering.
                </p>
              )}
              {localCheck.missing.length > 0 && (
                <div className="text-xs text-sub">
                  <p>
                    {localCheck.missing.length === 1
                      ? "One attached file is no longer on this device:"
                      : `${localCheck.missing.length} attached files are no longer on this device:`}
                  </p>
                  <ul className="mt-1 space-y-0.5">
                    {localCheck.missing.map((m) => (
                      <li key={m} className="truncate font-mono text-[11px] text-faint" title={m}>
                        {m}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </Card>
      )}

      <section className="mb-8">
        <div className="mb-3 flex items-center gap-3">
          <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-faint">
            Files · {(sources ?? []).length}
          </span>
          <div className="h-px flex-1 bg-edge" />
          {isApp && (
            <button
              type="button"
              onClick={() => sourceFileInputRef.current?.click()}
              disabled={attaching}
              className="inline-flex cursor-pointer items-center gap-1.5 rounded-lg border border-edge bg-panel px-2.5 py-1.5 text-xs font-medium text-ink transition-colors hover:border-accent/50 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <Plus size={13} /> {attaching ? "Adding…" : "Add file"}
            </button>
          )}
        </div>

        {(sources ?? []).length === 0 && (
          <p className="text-sm text-faint">
            Nothing attached yet — add a CSV, or ask and Meelu pulls the data it needs.
          </p>
        )}

        <div className="grid gap-4 lg:grid-cols-2">
          {(sources ?? []).map((s) => {
            const cols = fileColumns[s.id] ?? [];
            const expanded = openCols[s.id] ?? false;
            const shown = expanded ? cols : cols.slice(0, COLS_SHOWN);
            return (
              <Card key={s.id} className="p-4">
                <div className="flex items-center gap-2">
                  <span
                    className="min-w-0 flex-1 truncate text-sm font-semibold text-ink"
                    title={s.filePath ?? s.name}
                  >
                    {s.name}
                  </span>
                  {cols.length > 0 && (
                    <span className="font-mono text-[10.5px] text-faint">{cols.length} cols</span>
                  )}
                  <span className="flex shrink-0 items-center gap-1.5">
                    {isApp && s.filePath && (
                      <>
                        <button
                          type="button"
                          aria-label="View this file"
                          title="View this file"
                          onClick={() => void viewSource(s)}
                          className="cursor-pointer text-faint transition-colors hover:text-accent"
                        >
                          <Eye size={13} />
                        </button>
                        <button
                          type="button"
                          aria-label="Save a copy"
                          title="Save a copy"
                          onClick={() => void saveSourceCopy(s)}
                          className="cursor-pointer text-faint transition-colors hover:text-accent"
                        >
                          <Download size={13} />
                        </button>
                        <button
                          type="button"
                          aria-label="Show in Finder"
                          title="Show in Finder"
                          onClick={() => void revealFile(s)}
                          className="cursor-pointer text-faint transition-colors hover:text-accent"
                        >
                          <FolderOpen size={13} />
                        </button>
                      </>
                    )}
                    <button
                      type="button"
                      aria-label="Delete source"
                      onClick={() => setDeletingSource(s)}
                      className="cursor-pointer text-faint transition-colors hover:text-bad"
                    >
                      <Trash2 size={13} />
                    </button>
                  </span>
                </div>

                {cols.length > 0 && (
                  <div className="mt-3 space-y-0.5">
                    {shown.map((c) => (
                      <div
                        key={c.name}
                        className="flex items-center gap-2 rounded-md px-1.5 py-1 hover:bg-panel2"
                      >
                        <span className="w-8 shrink-0 font-mono text-[9px] text-faint">
                          {c.kind}
                        </span>
                        <span className="truncate font-mono text-[11px] text-ink">{c.name}</span>
                      </div>
                    ))}
                    {cols.length > COLS_SHOWN && (
                      <button
                        type="button"
                        onClick={() => setOpenCols((prev) => ({ ...prev, [s.id]: !expanded }))}
                        className="mt-1 cursor-pointer px-1.5 text-[11px] text-faint transition-colors hover:text-ink"
                      >
                        {expanded ? "Show fewer" : `${cols.length - COLS_SHOWN} more…`}
                      </button>
                    )}
                  </div>
                )}
              </Card>
            );
          })}
        </div>

        {sourceErr && <p className="mt-2 text-xs text-bad">{sourceErr}</p>}
        {attachError && <p className="mt-2 text-xs text-bad">{attachError}</p>}
        {savedTo && <p className="mt-2 truncate text-xs text-sub">Saved to {savedTo}</p>}
      </section>

      {reports.length > 0 && (
        <section className="mb-8">
          <div className="mb-3 flex items-center gap-3">
            <span className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-[0.12em] text-faint">
              <BarChart3 size={11} /> Reports
            </span>
            <div className="h-px flex-1 bg-edge" />
          </div>
          {reportErr && <p className="mb-2 text-xs text-bad">{reportErr}</p>}
          <div className="flex flex-col">
            {reports.map((r) => (
              <div
                key={r.id}
                className="group flex items-center gap-3 rounded-lg border-t border-edge px-1 py-3 transition-colors hover:bg-panel2"
              >
                <button
                  type="button"
                  onClick={() => void viewReport(r.id)}
                  className="min-w-0 flex-1 cursor-pointer truncate text-left text-sm text-ink transition-colors hover:text-accent"
                  title={r.title}
                >
                  {r.title}
                </button>
                <span className="font-mono text-[10.5px] text-faint">
                  {formatRelative(r.createdAt)}
                </span>
                <span className="flex shrink-0 items-center gap-1.5">
                  <button
                    type="button"
                    aria-label="Save this report"
                    title="Save this report"
                    onClick={() => void saveReport(r)}
                    className="cursor-pointer text-faint transition-colors hover:text-accent"
                  >
                    <Download size={13} />
                  </button>
                  <button
                    type="button"
                    aria-label="Delete report"
                    onClick={() => setDeletingReport(r)}
                    className="cursor-pointer text-faint transition-colors hover:text-bad"
                  >
                    <Trash2 size={13} />
                  </button>
                </span>
              </div>
            ))}
          </div>
        </section>
      )}

      <input
        ref={sourceFileInputRef}
        type="file"
        accept=".csv,text/csv"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0];
          e.target.value = "";
          if (file) void attachFile(file);
        }}
      />

      <Drawer
        open={previewSource !== null}
        onClose={() => {
          setPreviewSource(null);
          setPreview(null);
        }}
        title={previewSource?.name ?? "File"}
        fullscreenToggle
        actions={
          previewSource?.filePath ? (
            <div className="flex items-center gap-1">
              <IconButton
                aria-label="Save a copy"
                title="Save a copy"
                onClick={() => void saveSourceCopy(previewSource)}
              >
                <Download size={14} />
              </IconButton>
              <IconButton
                aria-label="Show in Finder"
                title="Show in Finder"
                onClick={() => void revealFile(previewSource)}
              >
                <FolderOpen size={14} />
              </IconButton>
            </div>
          ) : null
        }
      >
        {!preview ? (
          <Spinner />
        ) : (
          <div className="space-y-3">
            <p className="truncate font-mono text-[11px] text-faint" title={preview.path}>
              {preview.path}
            </p>
            <p className="text-xs text-sub">
              {formatBytes(preview.bytes)} · {preview.columns.length} columns · first{" "}
              {preview.rows.length.toLocaleString("en-US")} rows
              {preview.more ? " of the file" : ""}
            </p>
            <Table>
              <THead cols={preview.columns} />
              <tbody>
                {preview.rows.map((row, i) => (
                  <TRow key={i}>
                    {preview.columns.map((_, c) => (
                      <TCell key={c} className="whitespace-nowrap">
                        <span className="block max-w-[22rem] truncate" title={row[c] ?? ""}>
                          {row[c] ?? ""}
                        </span>
                      </TCell>
                    ))}
                  </TRow>
                ))}
              </tbody>
            </Table>
          </div>
        )}
      </Drawer>

      <Drawer
        open={openReportId !== null}
        onClose={() => setOpenReportId(null)}
        title={openReport?.title ?? "Report"}
        fullscreenToggle
        actions={
          openReport ? (
            <IconButton
              aria-label="Save this report"
              title="Save this report"
              onClick={() => {
                const summary = reports.find((r) => r.id === openReport.id);
                if (summary) void saveReport(summary);
              }}
            >
              <Download size={14} />
            </IconButton>
          ) : null
        }
      >
        {reportErr ? (
          <p className="text-sm text-bad">{reportErr}</p>
        ) : !openReport ? (
          <Spinner />
        ) : (
          <iframe
            title={openReport.title}
            sandbox=""
            srcDoc={openReport.html}
            className="h-[75vh] w-full rounded-lg border border-edge bg-white"
          />
        )}
      </Drawer>

      <Modal open={renameOpen} onClose={() => setRenameOpen(false)} title="Session">
        <div className="space-y-4">
          <Field label="Title">
            <Input
              value={renameTitle}
              onChange={(e) => setRenameTitle(e.target.value)}
              placeholder={session.title}
              autoFocus
              onKeyDown={(e) => {
                if (e.key === "Enter") void saveRename();
              }}
            />
          </Field>
          <Field
            label="What this data is"
            hint="Meelu reads this before answering — say what the numbers mean, where they came from, and what a row is."
          >
            <Textarea
              value={renameAbout}
              onChange={(e) => setRenameAbout(e.target.value)}
              rows={3}
              placeholder="Monthly Shopify orders exported from Admin — one row per order."
            />
          </Field>
          {renameErr && <p className="text-sm text-bad">{renameErr}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setRenameOpen(false)}>
              Cancel
            </Button>
            <Button onClick={() => void saveRename()} disabled={!renameTitle.trim() || renaming}>
              {renaming ? "Saving…" : "Save"}
            </Button>
          </div>
        </div>
      </Modal>

      <ConfirmDelete
        open={deletingSource !== null}
        onClose={() => setDeletingSource(null)}
        onConfirm={() => {
          if (deletingSource) void removeSource(deletingSource);
        }}
        what={deletingSource ? `source "${deletingSource.name}"` : "source"}
      />

      <ConfirmDelete
        open={deletingReport !== null}
        onClose={() => setDeletingReport(null)}
        onConfirm={() => {
          if (deletingReport) void removeReport(deletingReport);
        }}
        what={deletingReport ? `report "${deletingReport.title}"` : "report"}
      />
    </PageEnter>
  );
}
