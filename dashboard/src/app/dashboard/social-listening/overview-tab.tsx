"use client";

import { Check } from "lucide-react";
import { Button, Card, Spinner, StatCard } from "@/components/ui";
import { cn, formatRelative } from "@/lib/utils";
import type {
  SocialListeningConfig,
  SocialListeningPost,
  SocialListeningQuery,
  SocialListeningSummary,
} from "@/lib/types";
import { PostCard } from "./post-card";
import type { LiveRun } from "./page";

const pct = (p: { judged: number; total: number }) =>
  p.total > 0 ? Math.min(100, Math.round((p.judged / p.total) * 100)) : 0;

export function OverviewTab({
  summary,
  config,
  queries,
  best,
  live,
  running,
  onStop,
  platformLabel,
  onSkip,
  onDraft,
  onSetupTab,
}: {
  summary: SocialListeningSummary | null;
  config: SocialListeningConfig | null;
  queries: SocialListeningQuery[];
  best: SocialListeningPost[];
  live: LiveRun;
  running: boolean;
  onStop: () => void;
  platformLabel: (id: string) => string;
  onSkip: (post: SocialListeningPost) => void;
  onDraft: (post: SocialListeningPost) => void;
  onSetupTab: () => void;
}) {
  const lastRun = summary?.lastRun ?? null;
  const filtered =
    lastRun && lastRun.fetchedCount > 0
      ? Math.round((1 - lastRun.keptCount / lastRun.fetchedCount) * 100)
      : null;

  return (
    <div>
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5 mb-4">
        <StatCard
          label="Kept last run"
          value={lastRun?.keptCount ?? 0}
          hint={
            lastRun && filtered !== null
              ? `of ${lastRun.fetchedCount} fetched · ${filtered}% filtered as noise`
              : "No run yet"
          }
        />
        <StatCard
          label="Awaiting review"
          value={summary?.unprocessed ?? 0}
          hint={
            (summary?.unprocessed ?? 0) > 0
              ? "picked up by the next run"
              : "every fetched post is reviewed"
          }
        />
        <StatCard label="Awaiting your reply" value={summary?.needsReply ?? 0} hint="in the post inbox" />
        <StatCard label="Replied" value={summary?.replied ?? 0} hint={`${summary?.drafted ?? 0} drafted`} />
        <StatCard
          label="Brand mentions"
          value={summary?.brandMentions ?? 0}
          hint={
            (summary?.sentiment.negative ?? 0) > 0
              ? `${summary?.sentiment.negative} negative need attention`
              : "none negative"
          }
        />
      </div>

      {(running || Object.keys(live.platformState).length > 0) && (
        <Card className="mb-4">
          <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
            <span className="font-medium text-ink">
              {running ? live.stageDetail || "Run in progress…" : "Last run"}
            </span>
            {Object.entries(live.platformState).map(([id, s]) => (
              <span
                key={id}
                className="inline-flex items-center gap-1.5 rounded-full border border-edge2 bg-panel px-2.5 py-0.5 text-xs text-sub"
              >
                {s.status === "done" && <Check size={12} className="text-good" />}
                {s.status === "fetching" && <Spinner className="h-3 w-3 py-0" />}
                {s.status === "error" && (
                  <span className="text-bad" title={s.error}>
                    ✗
                  </span>
                )}
                {platformLabel(id)}
                {s.count != null && ` · ${s.count}`}
              </span>
            ))}
            {running && (
              <Button size="sm" variant="ghost" className="ml-auto" onClick={onStop}>
                Stop
              </Button>
            )}
          </div>
          {running && (
            <div className="mt-3">
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-edge2">
                <div
                  className={cn(
                    "h-full rounded-full bg-accent transition-[width] duration-300",
                    !live.progress && "w-1/3 animate-pulse",
                  )}
                  style={live.progress ? { width: `${pct(live.progress)}%` } : undefined}
                />
              </div>
              {live.progress && (
                <p className="mt-1.5 text-xs text-sub">
                  {live.progress.judged} of {live.progress.total} posts reviewed · {pct(live.progress)}%
                </p>
              )}
              {!live.progress && live.gate && (
                <p className="mt-1.5 text-xs text-sub">
                  {live.gate.kept} close enough · {live.gate.filtered} too far
                  {live.gate.pending > 0 ? ` · ${live.gate.pending} still embedding` : ""}
                </p>
              )}
            </div>
          )}
          {live.error && <p className="mt-2 text-sm text-bad">{live.error}</p>}
        </Card>
      )}

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium uppercase tracking-wide text-faint mb-2.5">
            Best matches from the last run
          </p>
          {best.length === 0 ? (
            <p className="text-sm text-sub">Nothing kept yet — run listening to fill the inbox.</p>
          ) : (
            <div className="space-y-3">
              {best.map((p) => (
                <PostCard
                  key={p.id}
                  post={p}
                  platformLabel={platformLabel}
                  onSkip={onSkip}
                  onDraft={onDraft}
                />
              ))}
            </div>
          )}
        </div>

        <div className="w-full lg:w-72 shrink-0 space-y-4">
          <Card>
            <p className="text-xs font-medium uppercase tracking-wide text-faint mb-2">Schedule</p>
            <p className="text-[13px] text-ink">
              {config?.schedule
                ? `Runs ${config.schedule}, locally in the app.`
                : "No schedule — runs only when you press the button."}
            </p>
            {lastRun && (
              <p className="text-xs text-faint mt-1">
                Last run {formatRelative(lastRun.startedAt)}
                {lastRun.status !== "done" && ` · ${lastRun.status}`}
              </p>
            )}
            <Button size="sm" variant="ghost" className="mt-2" onClick={onSetupTab}>
              Change schedule
            </Button>
          </Card>
          <Card>
            <p className="text-xs font-medium uppercase tracking-wide text-faint mb-2">
              Top queries by kept posts
            </p>
            {summary && summary.keptByQuery.length > 0 ? (
              <div className="space-y-2 text-[13px]">
                {summary.keptByQuery.map((q) => (
                  <div key={q.id} className="flex justify-between gap-3">
                    <span className="truncate text-ink" title={q.text}>
                      {queries.find((x) => x.id === q.id)?.text ?? q.text}
                    </span>
                    <span className="text-faint tabular-nums">{q.kept}</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-[13px] text-sub">Nothing kept yet.</p>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
