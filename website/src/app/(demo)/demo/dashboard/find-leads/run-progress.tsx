"use client";

import { Check } from "lucide-react";
import { Card, Spinner } from "@demo/components/ui";
import { cn } from "@demo/lib/utils";
import { STEPS, sourceTotals, type LiveRun, type RunStep } from "./lib";

const HEADLINE: Record<RunStep, string> = {
  plan: "Turning your briefs into searches",
  collect: "Finding people",
  screen: "Shortlisting the people found",
  enrich: "Checking the shortlist's recent activity",
  judge: "Checking each person is worth contacting",
};

export function RunProgress({ live }: { live: LiveRun }) {
  const current = live.step ?? "plan";
  const at = STEPS.indexOf(current);
  const totals = sourceTotals(live.sources);
  const judged = live.judged;
  const pct = judged && judged.total > 0
    ? Math.min(100, Math.round(80 + (judged.judged / judged.total) * 20))
    : Math.round((at / STEPS.length) * 100);

  const found = [
    Object.keys(live.sources).some((k) => k.startsWith("posts:"))
      ? `Post authors ${totals.posts}${totals.postsStored ? ` (${totals.postsStored} already stored)` : ""}`
      : null,
    live.sources.linkedin ? `LinkedIn ${totals.linkedin}` : null,
    live.sources.web ? `Web ${totals.web}` : null,
  ].filter(Boolean);

  const tiles: Array<{ id: RunStep; title: string; detail: string }> = [
    {
      id: "plan",
      title: "Search plan",
      detail: live.searches
        ? `${live.searches} ${live.searches === 1 ? "search" : "searches"} from ${live.briefs} ${live.briefs === 1 ? "brief" : "briefs"}`
        : "Reading your briefs",
    },
    { id: "collect", title: "Finding people", detail: found.length ? found.join(" · ") : "Waiting" },
    {
      id: "screen",
      title: "Shortlist",
      detail: live.screened
        ? live.screened.screened < live.screened.total
          ? `${live.screened.screened} of ${live.screened.total} checked · ${live.screened.kept} kept`
          : `${live.screened.total} → ${live.screened.kept}`
        : "Waiting",
    },
    {
      id: "enrich",
      title: "Recent activity",
      detail: live.enriched
        ? live.enriched.error && live.enriched.status === "error"
          ? "Could not read activity; judging on what was found"
          : live.enriched.status === "running"
            ? "Reading profiles"
            : `${live.enriched.people} ${live.enriched.people === 1 ? "person" : "people"} checked`
        : "Waiting",
    },
    {
      id: "judge",
      title: "Final check",
      detail: judged ? `${judged.judged} checked · ${judged.kept} kept` : "Waiting",
    },
  ];

  return (
    <Card className="space-y-3.5 p-4 sm:p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div className="space-y-0.5">
          {live.round && (
            <p className="text-[12.5px] font-medium tabular-nums text-accent">
              Round {live.round.round} of up to {live.round.maxRounds} ·{" "}
              {live.round.kept + (judged?.kept ?? 0)} of {live.round.target} leads found
            </p>
          )}
          <h2 className="text-[15px] font-semibold text-ink">{HEADLINE[current]}</h2>
        </div>
        <p className="text-[13px] text-sub">People who pass appear below as they come in. Stopping keeps them.</p>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-edge">
        <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${Math.max(pct, 4)}%` }} />
      </div>
      <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-5">
        {tiles.map((t, i) => {
          const done = i < at;
          const active = i === at;
          return (
            <div
              key={t.id}
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
                {t.title}
              </span>
              <span className="text-[13px] tabular-nums text-sub">{t.detail}</span>
            </div>
          );
        })}
      </div>
      {live.error && <p className="text-sm text-bad">{live.error}</p>}
    </Card>
  );
}
