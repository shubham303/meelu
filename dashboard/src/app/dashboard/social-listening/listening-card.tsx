"use client";

import { useState } from "react";
import { ChevronUp, Pencil, Plus, X } from "lucide-react";
import { Button, Card } from "@/components/ui";
import { cn } from "@/lib/utils";
import { api } from "@/lib/use-api";
import type { SocialListeningConfig, SocialListeningQuery } from "@/lib/types";
import type { PlatformInfo } from "./lib";

const SUMMARY_CHIPS = 3;
const FIND_AFTER = 5;
const WEAK_FOUND = 20;

function isWeak(q: SocialListeningQuery): boolean {
  return q.enabled && q.kept === 0 && q.found > WEAK_FOUND;
}

export function ListeningCard({
  queries,
  config,
  platformInfo,
  expanded,
  onExpand,
  onCollapse,
  refreshQueries,
  refreshConfig,
}: {
  queries: SocialListeningQuery[];
  config: SocialListeningConfig | null;
  platformInfo: PlatformInfo[] | null;
  expanded: boolean;
  onExpand: () => void;
  onCollapse: () => void;
  refreshQueries: () => Promise<void>;
  refreshConfig: () => Promise<void>;
}) {
  const [error, setError] = useState<string | null>(null);
  const editing = expanded || queries.length === 0;

  const guarded = async (work: () => Promise<unknown>, refresh: () => Promise<void>) => {
    setError(null);
    try {
      await work();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The change did not save.");
    }
    await refresh();
  };

  const togglePlatform = (id: string) => {
    if (!config) return;
    const on = config.platforms.includes(id);
    void guarded(
      () =>
        api("/api/v1/social-listening/config", {
          method: "PUT",
          body: { platforms: on ? config.platforms.filter((p) => p !== id) : [...config.platforms, id] },
        }),
      refreshConfig,
    );
  };

  return (
    <Card className="p-4 sm:p-5 space-y-4">
      {editing ? (
        <LineEditor
          queries={queries}
          canCollapse={queries.length > 0}
          onCollapse={onCollapse}
          run={(work) => guarded(work, refreshQueries)}
        />
      ) : (
        <LineSummary queries={queries} onExpand={onExpand} />
      )}
      {error && <p className="text-sm text-bad">{error}</p>}
      <div className="h-px bg-edge" />
      <PlatformRow config={config} platformInfo={platformInfo} onToggle={togglePlatform} />
    </Card>
  );
}

function LineSummary({
  queries,
  onExpand,
}: {
  queries: SocialListeningQuery[];
  onExpand: () => void;
}) {
  const shown = queries.filter((q) => q.enabled).slice(0, SUMMARY_CHIPS);
  const more = queries.length - shown.length;
  return (
    <div className="flex items-start gap-3">
      <span className="w-24 shrink-0 pt-1.5 text-[13px] text-sub">Listening for</span>
      <div className="flex min-w-0 flex-1 flex-wrap gap-2">
        {shown.map((q) => (
          <span
            key={q.id}
            className="inline-flex items-center gap-2 rounded-full border border-accent/30 bg-accent-soft py-1 pl-3 pr-1.5 text-[13px] text-accent"
          >
            {q.text}
            <span className="rounded-full bg-panel2 px-2 text-[11.5px] tabular-nums text-sub">{q.kept}</span>
          </span>
        ))}
        {shown.length === 0 && <span className="pt-1.5 text-[13px] text-sub">Every line is turned off.</span>}
        {more > 0 && (
          <button
            type="button"
            onClick={onExpand}
            className="cursor-pointer rounded-full border border-edge2 bg-panel2 px-3 py-1 text-[13px] font-medium text-ink hover:border-accent/40"
          >
            +{more} more
          </button>
        )}
      </div>
      <Button size="sm" variant="outline" className="shrink-0" onClick={onExpand}>
        <Pencil size={13} /> Edit lines
      </Button>
    </div>
  );
}

function LineEditor({
  queries,
  canCollapse,
  onCollapse,
  run,
}: {
  queries: SocialListeningQuery[];
  canCollapse: boolean;
  onCollapse: () => void;
  run: (work: () => Promise<unknown>) => Promise<void>;
}) {
  const [find, setFind] = useState("");
  const [draft, setDraft] = useState("");
  const on = queries.filter((q) => q.enabled).length;
  const needle = find.trim().toLowerCase();
  const visible = needle ? queries.filter((q) => q.text.toLowerCase().includes(needle)) : queries;
  const anyWeak = queries.some(isWeak);

  const add = () => {
    const text = draft.trim();
    if (!text) return;
    setDraft("");
    void run(() => api("/api/v1/social-listening/queries", { method: "POST", body: [{ text }] }));
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-baseline gap-2.5">
          <h2 className="text-sm font-semibold text-ink">Listening for</h2>
          <span className="text-[13px] text-sub">
            {queries.length} {queries.length === 1 ? "line" : "lines"} · {on} on
          </span>
        </div>
        <div className="flex items-center gap-2">
          {queries.length > FIND_AFTER && (
            <input
              aria-label="Find a line"
              placeholder="Find a line"
              value={find}
              onChange={(e) => setFind(e.target.value)}
              className="h-8 w-48 rounded-lg border border-edge2 bg-panel2 px-2.5 text-[13px] text-ink placeholder:text-faint focus:border-accent focus:outline-none"
            />
          )}
          {canCollapse && (
            <Button size="sm" variant="outline" onClick={onCollapse}>
              <ChevronUp size={13} /> Collapse
            </Button>
          )}
        </div>
      </div>
      <p className="max-w-2xl text-[13px] text-sub">
        Describe each conversation the way you&apos;d tell a colleague. Meelu turns it into search terms, keeps posts
        close in meaning, then reads each post to check it fits.
      </p>

      {queries.length > 0 && (
        <div>
          <div className="grid grid-cols-[44px_minmax(0,1fr)_56px_56px_32px] gap-2 px-2 pb-1 text-[11px] font-semibold uppercase tracking-wide text-sub">
            <span>On</span>
            <span>Line</span>
            <span className="text-right">Kept</span>
            <span className="text-right">Found</span>
            <span />
          </div>
          <div className="space-y-0.5">
            {visible.map((q) => (
              <div
                key={q.id}
                className="grid grid-cols-[44px_minmax(0,1fr)_56px_56px_32px] items-center gap-2 rounded-lg px-2 py-1.5 hover:bg-panel2/60"
              >
                <Switch
                  on={q.enabled}
                  label={q.enabled ? "Turn this line off" : "Turn this line on"}
                  onToggle={() =>
                    void run(() =>
                      api(`/api/v1/social-listening/queries/${q.id}`, {
                        method: "PATCH",
                        body: { enabled: !q.enabled },
                      }),
                    )
                  }
                />
                <p className={cn("text-[13.5px]", q.enabled ? "text-ink" : "text-sub")}>{q.text}</p>
                <span
                  className={cn(
                    "text-right text-[13px] font-semibold tabular-nums",
                    isWeak(q) ? "text-warn" : q.enabled ? "text-ink" : "text-sub",
                  )}
                >
                  {q.kept}
                </span>
                <span className="text-right text-[13px] tabular-nums text-sub">{q.found}</span>
                <button
                  type="button"
                  aria-label="Remove line"
                  className="inline-flex h-7 w-7 cursor-pointer items-center justify-center rounded-md text-sub hover:bg-panel2 hover:text-bad"
                  onClick={() =>
                    void run(() => api(`/api/v1/social-listening/queries/${q.id}`, { method: "DELETE" }))
                  }
                >
                  <X size={14} />
                </button>
              </div>
            ))}
            {visible.length === 0 && <p className="px-2 py-2 text-[13px] text-sub">No line matches “{find}”.</p>}
          </div>
        </div>
      )}

      <div className="flex gap-2 pl-2">
        <input
          aria-label="Describe a conversation to listen for"
          placeholder={
            queries.length === 0
              ? "e.g. people asking which tool tracks their Google rankings"
              : "Describe a conversation to listen for"
          }
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && add()}
          className="h-9 min-w-0 flex-1 rounded-lg border border-dashed border-edge2 bg-transparent px-3 text-[13.5px] text-ink placeholder:text-faint focus:border-accent focus:outline-none"
        />
        <Button size="sm" variant="outline" onClick={add} disabled={!draft.trim()}>
          <Plus size={13} /> Add
        </Button>
      </div>
      {anyWeak && (
        <p className="pl-2 text-xs text-sub">
          A line that finds many posts but keeps none is shown in amber. Try rewording it.
        </p>
      )}
      {canCollapse && (
        <button
          type="button"
          onClick={onCollapse}
          className="flex w-full cursor-pointer items-center justify-center gap-1.5 border-t border-edge pt-2.5 text-[13px] text-sub hover:text-ink"
        >
          <ChevronUp size={13} /> Show less
        </button>
      )}
    </div>
  );
}

function Switch({ on, label, onToggle }: { on: boolean; label: string; onToggle: () => void }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      aria-label={label}
      onClick={onToggle}
      className={cn(
        "relative h-5 w-[34px] cursor-pointer rounded-full transition-colors",
        on ? "bg-accent" : "bg-edge2",
      )}
    >
      <span
        className={cn(
          "absolute top-[3px] h-3.5 w-3.5 rounded-full bg-white transition-[left]",
          on ? "left-[17px]" : "left-[3px]",
        )}
      />
    </button>
  );
}

function PlatformRow({
  config,
  platformInfo,
  onToggle,
}: {
  config: SocialListeningConfig | null;
  platformInfo: PlatformInfo[] | null;
  onToggle: (id: string) => void;
}) {
  const chosen = config?.platforms ?? [];
  const paid = (platformInfo ?? []).filter((p) => p.access === "apify").map((p) => p.label);
  return (
    <div className="flex items-start gap-3">
      <span className="w-24 shrink-0 pt-1.5 text-[13px] text-sub">On</span>
      <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2">
        {platformInfo === null ? (
          chosen.length > 0 ? (
            chosen.map((id) => (
              <span
                key={id}
                className="rounded-full border border-accent/30 bg-accent-soft px-3 py-1 text-[13px] text-accent"
              >
                {id}
              </span>
            ))
          ) : (
            <span className="pt-1.5 text-[13px] text-sub">Pick platforms in the Meelu app.</span>
          )
        ) : (
          platformInfo.map((p) => {
            const on = p.available && chosen.includes(p.id);
            return (
              <button
                key={p.id}
                type="button"
                disabled={!p.available}
                title={p.available ? undefined : "Needs the server's Apify key."}
                onClick={() => onToggle(p.id)}
                className={cn(
                  "rounded-full border px-3 py-1 text-[13px] transition-colors",
                  !p.available
                    ? "cursor-not-allowed border-edge text-faint opacity-60"
                    : on
                      ? "cursor-pointer border-accent/30 bg-accent-soft text-accent"
                      : "cursor-pointer border-edge2 text-sub hover:text-ink",
                )}
              >
                {p.label}
              </button>
            );
          })
        )}
        {paid.length > 0 && <span className="text-xs text-sub">{listOf(paid)} use credits per result</span>}
      </div>
    </div>
  );
}

function listOf(items: string[]): string {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}
