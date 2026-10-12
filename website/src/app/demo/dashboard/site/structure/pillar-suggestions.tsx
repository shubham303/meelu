"use client";

import { useCallback, useState } from "react";
import { Check, ChevronDown, ChevronRight, ExternalLink, Layers, RotateCcw, Trash2, X } from "lucide-react";
import { Badge, Button, ConfirmDelete, EmptyState, Spinner, Tabs, type BadgeTone } from "@demo/components/ui";
import { api, useApi, usePagedApi } from "@demo/lib/use-api";
import { cn, formatRelative } from "@demo/lib/utils";
import type {
  LinkSuggestionState,
  PillarSuggestion,
  PillarSuggestionAction,
  PillarSuggestionSummary,
} from "@demo/lib/types";

const PAGE_SIZE = 20;

type TabState = Exclude<LinkSuggestionState, "draft">;

const STATE_LABEL: Record<TabState, string> = {
  ready: "Ready",
  done: "Done",
  user_rejected: "Turned down",
  llm_rejected: "Screened out",
  stale: "Stale",
};

const ACTION_LABEL: Record<PillarSuggestionAction, string> = {
  create: "New pillar",
  expand: "Expand page",
};

const ACTION_TONE: Record<PillarSuggestionAction, BadgeTone> = {
  create: "good",
  expand: "accent",
};

const EMPTY: Record<TabState, string> = {
  ready: "No pillar pages ready. Ask the agent which topics lack a hub, and they land here.",
  done: "No pillar marked done yet.",
  user_rejected: "Nothing turned down yet.",
  llm_rejected: "The agent has not screened anything out.",
  stale: "No suggestion has gone stale. One does when most of its pages leave the crawl.",
};

const EMPTY_SUMMARY: PillarSuggestionSummary = {
  draft: 0,
  ready: 0,
  llm_rejected: 0,
  user_rejected: 0,
  done: 0,
  stale: 0,
};

export function PillarSuggestions() {
  const [state, setState] = useState<TabState>("ready");
  const [page, setPage] = useState(1);

  const { data: summary, refresh: refreshSummary } = useApi<PillarSuggestionSummary>(
    "/api/v1/site/structure/pillar-suggestions/summary",
  );
  const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), state });
  const { data: paged, loading, error, refresh } = usePagedApi<PillarSuggestion>(
    `/api/v1/site/structure/pillar-suggestions?${params}`,
  );
  const rows = paged?.data ?? null;
  const pagination = paged?.pagination ?? null;

  const reload = useCallback(() => {
    void refresh();
    void refreshSummary();
  }, [refresh, refreshSummary]);

  const counts = summary ?? EMPTY_SUMMARY;
  const total = Object.values(counts).reduce((a, b) => a + b, 0);
  const nothingAtAll = summary !== null && total === 0;

  return (
    <div className="mt-10">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-lg text-ink">Pillar pages</h2>
        <span className="text-xs text-faint">
          Topics the site covers in pieces with no page that introduces them. You build the page, then mark it done.
        </span>
      </div>

      {counts.draft > 0 && (
        <p className="mb-3 text-xs text-sub">
          {counts.draft} suggestion{counts.draft === 1 ? "" : "s"} still being screened by the agent.
        </p>
      )}

      {nothingAtAll ? (
        <EmptyState
          icon={Layers}
          title="No pillar pages suggested yet"
          hint="Ask the agent which topics lack a hub. Each group of pages that passes its screening shows up here with the page it needs."
        />
      ) : (
        <>
          <Tabs
            active={state}
            onChange={(k) => {
              setState(k as TabState);
              setPage(1);
            }}
            tabs={(Object.keys(STATE_LABEL) as TabState[]).map((k) => ({
              key: k,
              label: STATE_LABEL[k],
              count: counts[k],
            }))}
          />
          {error && <p className="text-sm text-bad">{error}</p>}
          {loading && rows === null && !error && (
            <div className="flex justify-center py-10">
              <Spinner />
            </div>
          )}
          {rows !== null && rows.length === 0 && <p className="text-sm text-sub">{EMPTY[state]}</p>}
          {rows !== null && rows.length > 0 && (
            <div className="divide-y divide-edge overflow-hidden rounded-2xl border border-edge bg-panel">
              {rows.map((row) => (
                <PillarRow key={row.id} row={row} onChanged={reload} />
              ))}
            </div>
          )}
          {pagination && pagination.total_pages > 1 && (
            <div className="mt-3 flex items-center justify-between text-xs text-sub">
              <span>
                Page {pagination.page} of {pagination.total_pages} · {pagination.total} suggestions
              </span>
              <div className="flex gap-1.5">
                <Button size="sm" variant="outline" disabled={!pagination.has_prev} onClick={() => setPage((p) => p - 1)}>
                  Previous
                </Button>
                <Button size="sm" variant="outline" disabled={!pagination.has_next} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}

function PillarRow({ row, onChanged }: { row: PillarSuggestion; onChanged: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [busy, setBusy] = useState(false);

  const move = async (to: LinkSuggestionState) => {
    setBusy(true);
    try {
      await api(`/api/v1/site/structure/pillar-suggestions/${row.id}`, {
        method: "PATCH",
        body: { state: to },
      });
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    await api(`/api/v1/site/structure/pillar-suggestions/${row.id}`, { method: "DELETE" });
    onChanged();
  };

  const toggle = () => {
    if (window.getSelection()?.toString()) return;
    setExpanded((v) => !v);
  };
  const stop = (e: React.SyntheticEvent) => e.stopPropagation();

  return (
    <div className="select-text">
      <div
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onClick={toggle}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            toggle();
          }
        }}
        className="flex cursor-pointer items-start gap-3 px-4 py-3.5 transition-colors hover:bg-panel2/50"
      >
        <span className="mt-1 shrink-0 text-sub">
          {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </span>
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-sm">
            <Badge tone={ACTION_TONE[row.action]}>{ACTION_LABEL[row.action]}</Badge>
            <span className="font-medium text-ink">{row.topic}</span>
            <span className="text-xs text-faint">
              {row.members.length} page{row.members.length === 1 ? "" : "s"}
            </span>
            {row.action === "expand" && row.coveringUrl && <PageLink url={row.coveringUrl} />}
          </div>
          <p className={cn("text-[13px] leading-relaxed text-ink", !expanded && "line-clamp-2")}>
            {row.suggestion}
          </p>
          <div className="flex flex-wrap items-center gap-2.5 text-xs text-faint">
            <span>{formatRelative(row.createdAt)}</span>
            {row.state === "user_rejected" && <Badge tone="neutral">Turned down</Badge>}
            {row.state === "llm_rejected" && <Badge tone="neutral">Screened out</Badge>}
            {row.state === "stale" && <Badge tone="warn">Stale</Badge>}
            {row.state === "done" && <Badge tone="good">Done</Badge>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1" onClick={stop} onKeyDown={stop}>
          {row.state === "ready" && (
            <>
              <Button variant="outline" size="sm" disabled={busy} onClick={() => move("done")}>
                <Check size={13} /> Done
              </Button>
              <Button variant="ghost" size="sm" disabled={busy} onClick={() => move("user_rejected")}>
                <X size={13} /> Turn down
              </Button>
            </>
          )}
          {row.state !== "ready" && (
            <Button variant="ghost" size="sm" disabled={busy} onClick={() => move("ready")}>
              <RotateCcw size={13} /> Reopen
            </Button>
          )}
          <Button variant="ghost" size="sm" disabled={busy} onClick={() => setDeleting(true)} title="Delete this suggestion for good">
            <Trash2 size={13} />
          </Button>
        </div>
      </div>

      {expanded && (
        <div className="grid gap-x-6 gap-y-1 px-4 pb-4 pl-[42px] text-xs sm:grid-cols-[auto_1fr]">
          <span className="text-faint">Pages</span>
          <ul className="space-y-0.5">
            {row.members.map((m) => (
              <li key={m.id} className="flex min-w-0 items-center gap-2">
                <PageLink url={m.url} />
                {m.title && <span className="truncate text-sub">{m.title}</span>}
              </li>
            ))}
          </ul>
          {row.searchScore !== null && row.searchScore !== undefined && (
            <>
              <span className="text-faint">Cohesion</span>
              <span className="text-sub">{row.searchScore.toFixed(2)}</span>
            </>
          )}
          {row.confidence !== null && row.confidence !== undefined && (
            <>
              <span className="text-faint">Screen</span>
              <span className="text-sub">passed at {Math.round(row.confidence * 100)}% confidence</span>
            </>
          )}
          {row.score !== null && row.score !== undefined && (
            <>
              <span className="text-faint">Rank</span>
              <span className="text-sub">{row.score.toFixed(2)}</span>
            </>
          )}
        </div>
      )}

      <ConfirmDelete open={deleting} onClose={() => setDeleting(false)} onConfirm={remove} what="this pillar page suggestion" />
    </div>
  );
}

function PageLink({ url }: { url: string }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      onClick={(e) => e.stopPropagation()}
      className="inline-flex min-w-0 max-w-full items-center gap-1 truncate font-mono text-xs text-sub hover:text-accent"
    >
      <span className="truncate">{url}</span>
      <ExternalLink size={11} className="shrink-0 text-faint" />
    </a>
  );
}
