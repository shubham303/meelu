"use client";

import { useRef, useState } from "react";
import { AlertTriangle, CalendarClock, Loader2 } from "lucide-react";
import { CLUSTER_LIMITS, LANGUAGES, LOCATIONS } from "@/lib/keyword-clusters/limits";
import type {
  ClusterError,
  ClusterRunResult,
  ClusterStreamEvent,
} from "@/lib/keyword-clusters/types";
import { ClusterResults } from "./results";

type Phase =
  | { kind: "idle" }
  | { kind: "running"; message: string; step: number; steps: number }
  | { kind: "done"; result: ClusterRunResult }
  | { kind: "failed"; error: ClusterError };

const fieldClass =
  "w-full rounded-lg border border-edge2 bg-bg px-3.5 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30";

const labelClass = "font-mono text-[11px] uppercase tracking-widest text-faint";

function seedList(text: string): string[] {
  return text
    .split(/[\n,]/)
    .map((s) => s.trim())
    .filter(Boolean);
}

export function KeywordClusterTool() {
  const [seeds, setSeeds] = useState("");
  const [locationCode, setLocationCode] = useState(LOCATIONS[0].code);
  const [languageCode, setLanguageCode] = useState(LOCATIONS[0].language);
  const [minVolume, setMinVolume] = useState(String(CLUSTER_LIMITS.defaultMinVolume));
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const abort = useRef<AbortController | null>(null);

  const running = phase.kind === "running";
  const seedCount = seedList(seeds).length;
  const tooMany = seedCount > CLUSTER_LIMITS.maxSeeds;

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    if (running) return;

    const controller = new AbortController();
    abort.current = controller;
    setPhase({ kind: "running", message: "Starting", step: 0, steps: 5 });

    let response: Response;
    try {
      response = await fetch("/api/tools/keyword-clusters", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          seeds: seedList(seeds),
          locationCode,
          languageCode,
          minVolume: Number(minVolume),
        }),
        signal: controller.signal,
      });
    } catch {
      setPhase({
        kind: "failed",
        error: { code: "provider-failed", message: "Could not reach the clustering tool." },
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
          code: (body?.code as ClusterError["code"]) ?? "provider-failed",
          message: body?.error ?? "The run could not be started.",
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
          let event: ClusterStreamEvent;
          try {
            event = JSON.parse(line) as ClusterStreamEvent;
          } catch {
            continue;
          }
          if (event.type === "phase") {
            setPhase({ kind: "running", message: event.message, step: event.step, steps: event.steps });
          } else if (event.type === "done") {
            setPhase({ kind: "done", result: event.result });
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
                code: "provider-failed",
                message: "The connection dropped before the run finished.",
              },
            },
      );
    }
    setPhase((prev) =>
      prev.kind === "running"
        ? {
            kind: "failed",
            error: { code: "provider-failed", message: "The run ended without a result." },
          }
        : prev,
    );
  }

  return (
    <div>
      <form onSubmit={submit} className="rounded-2xl border border-edge bg-panel p-5 sm:p-6">
        <label htmlFor="kc-seeds" className={labelClass}>
          Seed keywords, one per line
        </label>
        <textarea
          id="kc-seeds"
          name="seeds"
          required
          rows={3}
          spellCheck={false}
          value={seeds}
          onChange={(e) => setSeeds(e.target.value)}
          placeholder={"blue light glasses\ncomputer glasses"}
          className={`${fieldClass} mt-2 py-2.5 leading-relaxed`}
        />
        <p className={`mt-1.5 text-xs ${tooMany ? "text-warn" : "text-faint"}`}>
          {tooMany
            ? `Only the first ${CLUSTER_LIMITS.maxSeeds} seeds are used in one run.`
            : `Up to ${CLUSTER_LIMITS.maxSeeds} seeds. Each one is expanded into related searches, and anything off-topic for its seed is removed.`}
        </p>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div>
            <label htmlFor="kc-location" className={labelClass}>
              Country
            </label>
            <select
              id="kc-location"
              value={locationCode}
              onChange={(e) => {
                const next = LOCATIONS.find((l) => l.code === Number(e.target.value)) ?? LOCATIONS[0];
                setLocationCode(next.code);
                setLanguageCode(next.language);
              }}
              className={`${fieldClass} mt-2 h-11`}
            >
              {LOCATIONS.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="kc-language" className={labelClass}>
              Language
            </label>
            <select
              id="kc-language"
              value={languageCode}
              onChange={(e) => setLanguageCode(e.target.value)}
              className={`${fieldClass} mt-2 h-11`}
            >
              {LANGUAGES.map((l) => (
                <option key={l.code} value={l.code}>
                  {l.name}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label htmlFor="kc-min" className={labelClass}>
              Min. monthly searches
            </label>
            <input
              id="kc-min"
              type="number"
              min={0}
              step={10}
              inputMode="numeric"
              value={minVolume}
              onChange={(e) => setMinVolume(e.target.value)}
              className={`${fieldClass} mt-2 h-11`}
            />
          </div>
        </div>

        <div className="mt-5 flex flex-col items-start gap-3 sm:flex-row sm:items-center sm:justify-between">
          <p className="text-xs text-faint">
            Free, no sign-up. Each run takes about a minute and the tool allows{" "}
            {CLUSTER_LIMITS.dailyRuns} runs a day across everyone.
          </p>
          <button
            type="submit"
            disabled={running || seedCount === 0}
            className="inline-flex h-11 shrink-0 items-center justify-center gap-2 rounded-lg bg-accent px-5 text-sm font-medium text-white transition-colors hover:bg-accent-hi disabled:opacity-60"
          >
            {running && <Loader2 size={15} className="animate-spin" />}
            {running ? "Clustering…" : "Cluster keywords"}
          </button>
        </div>
      </form>

      {phase.kind === "running" && (
        <Progress message={phase.message} step={phase.step} steps={phase.steps} />
      )}

      {phase.kind === "failed" && (
        <ErrorCard error={phase.error} onReset={() => setPhase({ kind: "idle" })} />
      )}

      {phase.kind === "done" && (
        <ClusterResults result={phase.result} onReset={() => setPhase({ kind: "idle" })} />
      )}
    </div>
  );
}

function Progress({ message, step, steps }: { message: string; step: number; steps: number }) {
  const percent = steps > 0 ? Math.round((step / (steps + 1)) * 100) : 0;
  return (
    <div className="mt-6 rounded-2xl border border-edge bg-panel p-5" aria-live="polite">
      <div className="flex items-center justify-between gap-4">
        <p className="flex items-center gap-2 text-sm text-ink">
          <Loader2 size={14} className="animate-spin text-accent" />
          {message}
        </p>
        <p className="font-mono text-xs text-faint tabular-nums">
          {step > 0 ? `Step ${step} of ${steps}` : ""}
        </p>
      </div>
      <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-panel2">
        <div
          className="h-full rounded-full bg-accent transition-all duration-500"
          style={{ width: `${Math.max(percent, 4)}%` }}
        />
      </div>
      <p className="mt-3 text-xs text-faint">
        The keyword data, the intent split and Google&rsquo;s top 10 results are fetched live, so a
        run usually takes thirty to ninety seconds.
      </p>
    </div>
  );
}

function ErrorCard({ error, onReset }: { error: ClusterError; onReset: () => void }) {
  const limited = error.code === "daily-limit";
  const Icon = limited ? CalendarClock : AlertTriangle;
  return (
    <div className="mt-6 rounded-2xl border border-warn/25 bg-warn/5 p-5" role="alert">
      <div className="flex items-start gap-3">
        <Icon size={18} className="mt-0.5 text-warn" />
        <div>
          <p className="text-sm font-medium text-ink">{error.message}</p>
          {error.hint && <p className="mt-1.5 text-sm leading-relaxed text-sub">{error.hint}</p>}
          <p className="mt-2 font-mono text-[11px] uppercase tracking-widest text-faint">
            {error.code}
          </p>
          {!limited && (
            <button
              type="button"
              onClick={onReset}
              className="mt-3 text-sm text-accent transition-colors hover:text-accent-hi"
            >
              Try again
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
