"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  ExternalLink,
  Link2,
  LocateFixed,
  RefreshCw,
  RotateCcw,
  Search as SearchIcon,
  Trash2,
  X,
} from "lucide-react";
import { Badge, Button, ConfirmDelete, EmptyState, Select, Spinner, Tabs, type BadgeTone } from "@/components/ui";
import { api, usePagedApi } from "@/lib/use-api";
import { cn, formatRelative } from "@/lib/utils";
import {
  LINK_SUGGESTION_ACTIONS,
  type LinkSuggestion,
  type LinkSuggestionAction,
  type SuggestionState,
  type SuggestionSummary,
} from "@/lib/types";

const PAGE_SIZE = 50;

const FRAGMENT_WORDS = 5;

type TabState = Extract<SuggestionState, "review_approved" | "user_rejected">;

const STATE_LABEL: Record<TabState, string> = {
  review_approved: "Approved",
  user_rejected: "Turned down",
};

const SUMMARY_KEY: Record<TabState, keyof SuggestionSummary> = {
  review_approved: "reviewApproved",
  user_rejected: "userRejected",
};

const ACTION_LABEL: Record<LinkSuggestionAction, string> = {
  create: "Add link",
  delete: "Remove link",
};

const ACTION_TONE: Record<LinkSuggestionAction, BadgeTone> = {
  create: "good",
  delete: "bad",
};

const EMPTY: Record<TabState, string> = {
  review_approved:
    "No approved link suggestions. Ask the agent to find internal links worth adding, and the ones that pass review land here.",
  user_rejected: "Nothing turned down yet.",
};

const EMPTY_SUMMARY: SuggestionSummary = {
  draft: 0,
  screeningRejected: 0,
  screeningApproved: 0,
  reviewApproved: 0,
  reviewRejected: 0,
  userRejected: 0,
};

export function LinkSuggestions({
  summary,
  refreshSummary,
}: {
  summary: SuggestionSummary | null;
  refreshSummary: () => void;
}) {
  const [state, setState] = useState<TabState>("review_approved");
  const [action, setAction] = useState<LinkSuggestionAction | "">("");
  const [q, setQ] = useState("");
  const [needle, setNeedle] = useState("");
  const [page, setPage] = useState(1);

  useEffect(() => {
    const t = setTimeout(() => {
      setNeedle(q.trim());
      setPage(1);
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  const pickState = (next: TabState) => {
    setState(next);
    setPage(1);
  };
  const pickAction = (next: LinkSuggestionAction | "") => {
    setAction(next);
    setPage(1);
  };

  const path = useMemo(() => {
    const params = new URLSearchParams({ page: String(page), page_size: String(PAGE_SIZE), state });
    if (action) params.set("action", action);
    if (needle) params.set("url", needle);
    return `/api/v1/site/structure/link-suggestions?${params}`;
  }, [page, state, action, needle]);

  const { data: paged, loading, error, refresh } = usePagedApi<LinkSuggestion>(path);
  const rows = paged?.data ?? null;
  const pagination = paged?.pagination ?? null;

  const reload = useCallback(() => {
    void refresh();
    void refreshSummary();
  }, [refresh, refreshSummary]);

  const [refreshing, setRefreshing] = useState(false);
  const refreshSuggestions = async () => {
    setRefreshing(true);
    try {
      await api("/api/v1/site/structure/link-suggestions/reconcile", { method: "POST" });
      reload();
    } finally {
      setRefreshing(false);
    }
  };

  const counts = summary ?? EMPTY_SUMMARY;
  const total = counts.reviewApproved + counts.userRejected;
  const nothingAtAll = summary !== null && total === 0;

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            disabled={refreshing}
            onClick={refreshSuggestions}
            title="Clear suggestions the site has caught up with: the link now exists, is already gone, or a page left the crawl"
          >
            <RefreshCw size={13} className={cn(refreshing && "animate-spin")} /> Refresh
          </Button>
        </div>
        <span className="text-xs text-faint">
          Internal links the agent proposes. Make the change on the site; after the next crawl, Refresh clears it.
        </span>
      </div>


      {nothingAtAll ? (
        <EmptyState
          icon={Link2}
          title="No link suggestions yet"
          hint="Ask the agent which pages deserve a link from where. Each suggestion that passes its screening shows up here for you to act on."
        />
      ) : (
        <>
          <Tabs
            active={state}
            onChange={(k) => pickState(k as TabState)}
            tabs={(Object.keys(STATE_LABEL) as TabState[]).map((k) => ({
              key: k,
              label: STATE_LABEL[k],
              count: counts[SUMMARY_KEY[k]],
            }))}
          />

          <div className="mb-4 flex flex-wrap items-center gap-2">
            <div className="relative min-w-[220px] flex-1">
              <SearchIcon size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-faint" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Filter by URL"
                className="w-full rounded-lg border border-edge2 bg-panel2 py-1.5 pl-8 pr-3 text-xs text-ink placeholder:text-faint focus:border-accent focus:outline-none"
              />
            </div>
            <Select
              value={action}
              onChange={(e) => pickAction(e.target.value as LinkSuggestionAction | "")}
              className="w-auto text-xs"
            >
              <option value="">Any action</option>
              {LINK_SUGGESTION_ACTIONS.map((a) => (
                <option key={a} value={a}>
                  {ACTION_LABEL[a]}
                </option>
              ))}
            </Select>
          </div>

          {error && <p className="text-sm text-bad">{error}</p>}
          {loading && rows === null && !error && (
            <div className="flex justify-center py-10">
              <Spinner />
            </div>
          )}
          {rows !== null && rows.length === 0 && (
            <p className="text-sm text-sub">
              {q || action ? "Nothing matches these filters." : EMPTY[state]}
            </p>
          )}
          {rows !== null && rows.length > 0 && (
            <div className="divide-y divide-edge overflow-hidden rounded-2xl border border-edge bg-panel">
              {rows.map((row) => (
                <SuggestionRow key={row.id} row={row} onChanged={reload} />
              ))}
            </div>
          )}
          {pagination && pagination.total_pages > 1 && (
            <div className="mt-3 flex items-center justify-between text-xs text-sub">
              <span>
                Page {pagination.page} of {pagination.total_pages} · {pagination.total} suggestions
              </span>
              <div className="flex gap-1.5">
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!pagination.has_prev}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  disabled={!pagination.has_next}
                  onClick={() => setPage((p) => p + 1)}
                >
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

function SuggestionRow({ row, onChanged }: { row: LinkSuggestion; onChanged: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [busy, setBusy] = useState(false);

  const move = async (to: SuggestionState) => {
    setBusy(true);
    try {
      await api(`/api/v1/site/structure/link-suggestions/${row.id}`, {
        method: "PATCH",
        body: { state: to },
      });
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    await api(`/api/v1/site/structure/link-suggestions/${row.id}`, { method: "DELETE" });
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
            <PageLink url={row.fromUrl ?? row.fromPageId} />
            <ArrowRight size={13} className="shrink-0 text-faint" />
            <PageLink url={row.toUrl ?? row.toPageId} />
          </div>
          <p className={cn("text-[13px] leading-relaxed text-ink", !expanded && "line-clamp-2")}>
            {row.suggestion}
          </p>
          {row.fromChunkText ? (
            <Passage row={row} text={row.fromChunkText} clamp={!expanded} />
          ) : (
            <p className="text-xs text-faint">
              No passage pinned: {row.action === "delete" ? "find the link" : "place the link"} anywhere in the
              body copy.
            </p>
          )}
          <div className="flex flex-wrap items-center gap-2.5 text-xs text-faint">
            {row.action === "delete" && row.anchor && (
              <span className="truncate">link text “{row.anchor}”</span>
            )}
            <span>{formatRelative(row.createdAt)}</span>
            {row.state === "user_rejected" && <Badge tone="neutral">Turned down</Badge>}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1" onClick={stop} onKeyDown={stop}>
          {row.state === "review_approved" && (
            <Button variant="ghost" size="sm" disabled={busy} onClick={() => move("user_rejected")}>
              <X size={13} /> Turn down
            </Button>
          )}
          {row.state === "user_rejected" && (
            <Button variant="ghost" size="sm" disabled={busy} onClick={() => move("review_approved")}>
              <RotateCcw size={13} /> Restore
            </Button>
          )}
          <Button
            variant="ghost"
            size="sm"
            disabled={busy}
            onClick={() => setDeleting(true)}
            title="Delete this suggestion for good"
          >
            <Trash2 size={13} />
          </Button>
        </div>
      </div>

      {expanded && (
        <div className="grid gap-x-6 gap-y-1 px-4 pb-4 pl-[42px] text-xs sm:grid-cols-[auto_1fr]">
          <span className="text-faint">From</span>
          <PageLink url={row.fromUrl ?? row.fromPageId} />
          <span className="text-faint">To</span>
          <PageLink url={row.toUrl ?? row.toPageId} />
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
          {row.searchScore !== null && row.searchScore !== undefined && (
            <>
              <span className="text-faint">Match</span>
              <span className="text-sub">{row.searchScore.toFixed(2)}</span>
            </>
          )}
        </div>
      )}

      <ConfirmDelete
        open={deleting}
        onClose={() => setDeleting(false)}
        onConfirm={remove}
        what="this link suggestion"
      />
    </div>
  );
}

function Passage({ row, text, clamp }: { row: LinkSuggestion; text: string; clamp: boolean }) {
  const [copied, setCopied] = useState(false);
  const stop = (e: React.SyntheticEvent) => e.stopPropagation();

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
    }
  };

  return (
    <div className="rounded-lg border-l-2 border-accent/60 bg-panel2/60 px-3 py-2">
      <p className="mb-1 truncate text-[11px] text-faint">
        {row.action === "delete" ? "The link sits in this passage" : "Add the link in this passage"}
        {row.fromChunkHeading && <> · under “{row.fromChunkHeading}”</>}
      </p>
      <p className={cn("whitespace-pre-line text-xs leading-relaxed text-sub", clamp && "line-clamp-3")}>
        <Marked text={text} mark={row.action === "delete" ? row.anchor : null} />
      </p>
      <div className="mt-1.5 flex flex-wrap items-center gap-3 text-[11px]" onClick={stop} onKeyDown={stop}>
        {row.fromUrl && (
          <a
            href={passageUrl(row.fromUrl, text)}
            target="_blank"
            rel="noreferrer"
            title="Opens the page scrolled to this passage, highlighted (Chrome, Edge, Safari)"
            className="inline-flex items-center gap-1 text-sub hover:text-accent"
          >
            <LocateFixed size={11} /> Open at passage
          </a>
        )}
        <button type="button" onClick={copy} className="inline-flex items-center gap-1 text-sub hover:text-accent">
          {copied ? <Check size={11} /> : <Copy size={11} />} {copied ? "Copied" : "Copy passage"}
        </button>
      </div>
    </div>
  );
}

function Marked({ text, mark }: { text: string; mark: string | null | undefined }) {
  const at = mark ? text.toLowerCase().indexOf(mark.toLowerCase()) : -1;
  if (!mark || at < 0) return <>{text}</>;
  return (
    <>
      {text.slice(0, at)}
      <mark className="rounded bg-bad/20 px-0.5 text-ink">{text.slice(at, at + mark.length)}</mark>
      {text.slice(at + mark.length)}
    </>
  );
}

function fragment(words: string[]): string {
  return encodeURIComponent(words.join(" ")).replace(/-/g, "%2D");
}

function passageUrl(url: string, text: string): string {
  const words = text.split(/\s+/).filter(Boolean);
  const base = url.split("#")[0];
  if (words.length === 0) return base;
  if (words.length <= FRAGMENT_WORDS * 2) return `${base}#:~:text=${fragment(words)}`;
  return `${base}#:~:text=${fragment(words.slice(0, FRAGMENT_WORDS))},${fragment(words.slice(-FRAGMENT_WORDS))}`;
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
