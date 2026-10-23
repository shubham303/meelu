"use client";

import { Check } from "lucide-react";
import { Card, Spinner } from "@/components/ui";
import { cn } from "@/lib/utils";
import { SKIP_HOURS, skippedLine, type LiveRun, type RunStep } from "./lib";

const ORDER: RunStep[] = ["terms", "searching", "meaning", "judging"];

const HEADLINE: Record<RunStep, string> = {
  terms: "Turning your lines into search terms",
  searching: "Searching the platforms",
  meaning: "Keeping posts close in meaning",
  judging: "Checking each post fits what you wrote",
};

export function RunProgress({ live, platformLabel }: { live: LiveRun; platformLabel: (id: string) => string }) {
  const current = live.step ?? "terms";
  const at = ORDER.indexOf(current);
  const judged = live.judged;
  const pct = judged && judged.total > 0 ? Math.min(100, Math.round((judged.judged / judged.total) * 100)) : null;
  const platforms = Object.entries(live.platforms);
  const skipped = platforms
    .map(([id, s]) => [id, s.skippedQueries ?? []] as [string, NonNullable<typeof s.skippedQueries>])
    .filter(([, items]) => items.length > 0);
  const skippedCount = skipped.reduce((n, [, items]) => n + items.length, 0);

  const steps: Array<{ id: RunStep; title: string; detail: string }> = [
    {
      id: "terms",
      title: "Search terms",
      detail: live.phrases
        ? `${live.phrases} phrases from ${live.lines} ${live.lines === 1 ? "line" : "lines"}`
        : "Reading your lines",
    },
    {
      id: "searching",
      title: "Keyword search",
      detail:
        platforms.length > 0
          ? platforms
              .map(([id, s]) =>
                s.status === "error"
                  ? `${platformLabel(id)} failed`
                  : s.status === "fetching"
                    ? `${platformLabel(id)} …`
                    : id === "web"
                      ? `${platformLabel(id)} ${s.fromVendor ?? 0} found`
                      : `${platformLabel(id)} ${s.fromVendor ?? 0} fetched · ${s.fromDatabase ?? 0} shared`,
              )
              .join(" · ")
          : "Waiting",
    },
    {
      id: "meaning",
      title: "Close in meaning",
      detail: live.gate
        ? `${live.inserted || live.fetched} → ${live.gate.kept}${live.gate.pending > 0 ? ` · ${live.gate.pending} waiting` : ""}`
        : "Waiting",
    },
    {
      id: "judging",
      title: "Checking fit",
      detail: judged ? `${judged.judged} of ${judged.total} · ${judged.kept} kept` : "Waiting",
    },
  ];

  return (
    <Card className="space-y-3.5 p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <h2 className="text-[15px] font-semibold text-ink">{HEADLINE[current]}</h2>
        <p className="text-[13px] tabular-nums text-sub">
          {judged ? `${judged.judged} of ${judged.total} checked · ` : ""}kept posts appear below as they come in
        </p>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-edge">
        <div
          className={cn("h-full rounded-full bg-accent transition-[width] duration-300", pct === null && "w-1/3 animate-pulse")}
          style={pct === null ? undefined : { width: `${pct}%` }}
        />
      </div>
      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((s, i) => {
          const done = i < at;
          const active = i === at;
          return (
            <div
              key={s.id}
              className={cn(
                "flex flex-col gap-1 rounded-xl border px-3.5 py-3",
                active ? "border-accent/40 bg-accent-soft" : "border-edge bg-bg",
              )}
            >
              <span
                className={cn(
                  "inline-flex items-center gap-1.5 text-[13px] font-semibold",
                  active ? "text-accent" : "text-ink",
                )}
              >
                {done && <Check size={13} className="text-good" />}
                {active && <Spinner className="h-3 w-3 py-0" />}
                {s.title}
              </span>
              <span className="text-[13px] tabular-nums text-sub">{s.detail}</span>
            </div>
          );
        })}
      </div>
      {skippedCount > 0 && (
        <p className="text-[13px] text-sub">
          Skipped {skippedCount} {skippedCount === 1 ? "search" : "searches"} already run in the last {SKIP_HOURS} hours:{" "}
          {skippedLine(skipped, platformLabel)}
        </p>
      )}
      {live.problems.map((message) => (
        <p key={message} className="text-[13px] text-bad">
          Some posts were not checked: {message}
        </p>
      ))}
      {live.error && <p className="text-sm text-bad">{live.error}</p>}
    </Card>
  );
}
