"use client";

import { useRef, useState } from "react";
import { AlertTriangle, Loader2, ShieldAlert } from "lucide-react";
import type { SlimResult } from "@/lib/seo-audit/audit";
import type { AuditError, StreamEvent } from "@/lib/seo-audit/types";
import { AuditResults } from "./results";

type Phase =
  | { kind: "idle" }
  | { kind: "running"; message: string; fetched: number; total: number }
  | { kind: "done"; result: SlimResult; shareUrl: string | null }
  | { kind: "failed"; error: AuditError };

const BLOCKED_CODES = new Set([
  "robots-disallow",
  "bot-protection",
  "http-refused",
  "unreachable",
]);

export function AuditTool() {
  const [url, setUrl] = useState("");
  const [scope, setScope] = useState<"auto" | "page">("auto");
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const abort = useRef<AbortController | null>(null);

  const running = phase.kind === "running";

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (running) return;

    const controller = new AbortController();
    abort.current = controller;
    setPhase({ kind: "running", message: "Starting", fetched: 0, total: 100 });

    let response: Response;
    try {
      response = await fetch("/api/tools/seo-audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url, scope }),
        signal: controller.signal,
      });
    } catch {
      setPhase({
        kind: "failed",
        error: { code: "unreachable", message: "Could not reach the audit service." },
      });
      return;
    }

    if (!response.ok || !response.body) {
      const body = (await response.json().catch(() => null)) as {
        error?: string;
        hint?: string;
        code?: string;
      } | null;
      setPhase({
        kind: "failed",
        error: {
          code: (body?.code as AuditError["code"]) ?? "unreachable",
          message: body?.error ?? "The audit could not be started.",
          hint: body?.hint,
        },
      });
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.trim()) continue;
          let event: StreamEvent;
          try {
            event = JSON.parse(line) as StreamEvent;
          } catch {
            continue;
          }
          if (event.type === "phase") {
            setPhase((prev) =>
              prev.kind === "running"
                ? { ...prev, message: event.message }
                : { kind: "running", message: event.message, fetched: 0, total: 100 },
            );
          } else if (event.type === "progress") {
            setPhase((prev) =>
              prev.kind === "running"
                ? { ...prev, fetched: event.fetched, total: event.total }
                : prev,
            );
          } else if (event.type === "done") {
            setPhase({
              kind: "done",
              result: event.result as unknown as SlimResult,
              shareUrl: event.shareUrl ?? null,
            });
          } else if (event.type === "error") {
            setPhase({ kind: "failed", error: event.error });
          }
        }
      }
    } catch {
      setPhase((prev) =>
        prev.kind === "done"
          ? prev
          : {
              kind: "failed",
              error: {
                code: "unreachable",
                message: "The connection dropped before the audit finished.",
              },
            },
      );
    }
  }

  return (
    <div>
      <form
        onSubmit={submit}
        className="rounded-2xl border border-edge bg-panel p-5 sm:p-6"
      >
        <label
          htmlFor="audit-url"
          className="font-mono text-[11px] uppercase tracking-widest text-faint"
        >
          Website, page or sitemap URL
        </label>
        <div className="mt-2 flex flex-col gap-2 sm:flex-row">
          <input
            id="audit-url"
            name="url"
            type="text"
            required
            inputMode="url"
            autoComplete="url"
            spellCheck={false}
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="example.com or example.com/sitemap.xml"
            className="h-11 w-full rounded-lg border border-edge2 bg-bg px-3.5 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
          <button
            type="submit"
            disabled={running || url.trim().length === 0}
            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-white transition-colors hover:bg-accent-hi disabled:opacity-60"
          >
            {running && <Loader2 size={15} className="animate-spin" />}
            {running ? "Auditing…" : "Run free audit"}
          </button>
        </div>

        <fieldset className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-2">
          <legend className="sr-only">How much to crawl</legend>
          {(
            [
              ["auto", "Crawl the site — up to 100 pages"],
              ["page", "Just this one URL"],
            ] as const
          ).map(([value, label]) => (
            <label key={value} className="flex items-center gap-2 text-sm text-sub">
              <input
                type="radio"
                name="scope"
                value={value}
                checked={scope === value}
                onChange={() => setScope(value)}
                className="size-3.5 accent-[var(--color-accent)]"
              />
              {label}
            </label>
          ))}
        </fieldset>

        <p className="mt-3 text-xs text-faint">
          Free, no sign-up. We read your pages the way Googlebot does. Each report is
          saved under a private link you can share.
        </p>
      </form>

      {phase.kind === "running" && (
        <Progress message={phase.message} fetched={phase.fetched} total={phase.total} />
      )}

      {phase.kind === "failed" && (
        <ErrorCard error={phase.error} onReset={() => setPhase({ kind: "idle" })} />
      )}

      {phase.kind === "done" && (
        <AuditResults
          result={phase.result}
          shareUrl={phase.shareUrl}
          onReset={() => {
            setPhase({ kind: "idle" });
            setUrl("");
          }}
        />
      )}
    </div>
  );
}

function Progress({
  message,
  fetched,
  total,
}: {
  message: string;
  fetched: number;
  total: number;
}) {
  const percent = total > 0 ? Math.min(100, Math.round((fetched / total) * 100)) : 0;
  return (
    <div className="mt-6 rounded-2xl border border-edge bg-panel p-5">
      <div className="flex items-center justify-between gap-4">
        <p className="flex items-center gap-2 text-sm text-ink">
          <Loader2 size={14} className="animate-spin text-accent" />
          {message}
        </p>
        <p className="font-mono text-xs text-faint tabular-nums">
          {fetched > 0 ? `${fetched} / ${total} pages` : ""}
        </p>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-panel2">
        <div
          className="h-full rounded-full bg-accent transition-all duration-500"
          style={{ width: `${Math.max(percent, 4)}%` }}
        />
      </div>
      <p className="mt-3 text-xs text-faint">
        A hundred pages takes about thirty seconds. The crawl waits between batches
        so it never becomes load on your server.
      </p>
    </div>
  );
}

function ErrorCard({ error, onReset }: { error: AuditError; onReset: () => void }) {
  const isBlocked = BLOCKED_CODES.has(error.code);
  const Icon = isBlocked ? ShieldAlert : AlertTriangle;
  return (
    <div
      className={`mt-6 rounded-2xl border p-5 ${
        isBlocked ? "border-bad/25 bg-bad/5" : "border-warn/25 bg-warn/5"
      }`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <Icon size={18} className={isBlocked ? "mt-0.5 text-bad" : "mt-0.5 text-warn"} />
        <div>
          <p className="text-sm font-medium text-ink">{error.message}</p>
          {error.hint && (
            <p className="mt-1.5 text-sm leading-relaxed text-sub">{error.hint}</p>
          )}
          <p className="mt-2 font-mono text-[11px] uppercase tracking-widest text-faint">
            {error.code}
          </p>
          <button
            type="button"
            onClick={onReset}
            className="mt-3 text-sm text-accent transition-colors hover:text-accent-hi"
          >
            Try another URL
          </button>
        </div>
      </div>
    </div>
  );
}
