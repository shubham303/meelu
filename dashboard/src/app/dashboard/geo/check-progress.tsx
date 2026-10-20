"use client";

import { Check } from "lucide-react";
import { Spinner } from "@/components/ui";
import type { GeoCheckProgress, GeoCheckStage } from "@/lib/types";
import { cn } from "@/lib/utils";
import { PLATFORM } from "./lib";

type TileState = "waiting" | "active" | "done";

const STAGES: GeoCheckStage[] = ["pages", "question", "judge", "compare"];
const PLATFORMS = Object.values(PLATFORM);

const HEADLINE: Record<GeoCheckStage, string> = {
  pages: "Finding your closest pages",
  question: "Working out what the question needs",
  judge: "Judging your pages and asking AI search",
  compare: "Comparing your page with the AI answers",
};

export function CheckProgress({ progress }: { progress: GeoCheckProgress }) {
  const stage = progress.stage ?? "pages";
  const at = STAGES.indexOf(stage);
  const found = progress.pagesFound ?? 0;
  const judged = progress.pagesJudged ?? 0;
  const fetched = progress.answersFetched ?? 0;

  const byStage = (s: GeoCheckStage): TileState => {
    const i = STAGES.indexOf(s);
    return i < at ? "done" : i === at ? "active" : "waiting";
  };
  const parallel = (doneCount: number, total: number): TileState =>
    at > 2 || (at === 2 && doneCount >= total) ? "done" : at === 2 ? "active" : "waiting";

  const pct =
    at < 2
      ? [5, 15][at]
      : at === 2
        ? Math.round(25 + ((judged + fetched) / Math.max(found + PLATFORMS.length, 1)) * 55)
        : 85;

  const tiles: Array<{ title: string; detail: string; state: TileState }> = [
    {
      title: "Closest pages",
      detail:
        progress.pagesFound == null
          ? "Searching your site"
          : found === 0
            ? "No page on the site comes close"
            : `${found} ${found === 1 ? "page" : "pages"} to judge`,
      state: byStage("pages"),
    },
    {
      title: "What the question needs",
      detail: progress.points != null ? `${progress.points} points a good answer covers` : at < 1 ? "Waiting" : "Reading the question",
      state: byStage("question"),
    },
    {
      title: "Judging your pages",
      detail: at < 2 ? "Waiting" : found === 0 ? "Nothing to judge" : `${judged} of ${found} judged`,
      state: parallel(judged, found),
    },
    {
      title: "Asking AI search",
      detail: at < 2 ? PLATFORMS.join(", ") : `${fetched} of ${PLATFORMS.length} answers in · ${PLATFORMS.join(", ")}`,
      state: parallel(fetched, PLATFORMS.length),
    },
    {
      title: "Suggestion",
      detail: at < 3 ? "Waiting" : "Writing what to change",
      state: byStage("compare"),
    },
  ];

  return (
    <div className="space-y-3.5">
      <div className="space-y-0.5">
        <h3 className="text-[15px] font-semibold text-ink">{HEADLINE[stage]}</h3>
        <p className="text-[13px] text-sub">A check takes a minute or two. You can close this and come back.</p>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-edge">
        <div className="h-full rounded-full bg-accent transition-[width] duration-300" style={{ width: `${pct}%` }} />
      </div>
      <div className="space-y-2">
        {tiles.map((t) => (
          <div
            key={t.title}
            className={cn(
              "flex flex-col gap-1 rounded-xl border px-3.5 py-3",
              t.state === "active" ? "border-accent/40 bg-accent-soft" : "border-edge bg-bg",
            )}
          >
            <span
              className={cn(
                "inline-flex items-center gap-1.5 text-[13px] font-semibold",
                t.state === "active" ? "text-accent" : t.state === "waiting" ? "text-sub" : "text-ink",
              )}
            >
              {t.state === "done" && <Check size={13} className="text-good" />}
              {t.state === "active" && <Spinner className="h-3 w-3 py-0" />}
              {t.title}
            </span>
            <span className="text-[13px] tabular-nums text-sub">{t.detail}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
