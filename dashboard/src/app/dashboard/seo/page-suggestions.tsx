"use client";

import { useCallback, useMemo, useState } from "react";
import {
  Check,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  FilePlus,
  FileEdit,
  FileX,
  Lightbulb,
  X,
} from "lucide-react";
import {
  Badge,
  Button,
  EmptyState,
  Select,
  Spinner,
  Tabs,
  type BadgeTone,
} from "@/components/ui";
import { api, usePagedApi } from "@/lib/use-api";
import { cn, formatRelative } from "@/lib/utils";
import {
  PAGE_SUGGESTION_ACTIONS,
  type PageSuggestion,
  type PageSuggestionAction,
  type PageSuggestionState,
  type SeoPageFacts,
} from "@/lib/types";

const PAGE_SIZE = 50;

type TabState = Exclude<PageSuggestionState, "draft" | "reviewed">;

const STATE_LABEL: Record<TabState, string> = {
  ready: "Ready",
  done: "Done",
  user_rejected: "Turned down",
  llm_rejected: "Screened out",
  stale: "Stale",
};

const ACTION_LABEL: Record<PageSuggestionAction, string> = {
  add: "Add page",
  edit: "Edit page",
  delete: "Merge and delete",
};

const ACTION_TONE: Record<PageSuggestionAction, BadgeTone> = {
  add: "good",
  edit: "accent",
  delete: "bad",
};

const ACTION_ICON = { add: FilePlus, edit: FileEdit, delete: FileX };

const STRATEGY_LABEL: Record<string, string> = {
  gsc: "ranks, barely covers",
  cluster: "missing subtopics",
  ctr: "ranks, not clicked",
  questions: "unanswered questions",
  decay: "clicks fell",
  cannibalisation: "cannibalisation",
  gap: "competitor gap",
  topic: "topic",
  agent: "written by the agent",
};

const EMPTY: Record<TabState, string> = {
  ready:
    "Nothing ready. Run a strategy above and the suggestions that survive the pipeline land here.",
  done: "Nothing marked done yet.",
  user_rejected: "Nothing turned down yet.",
  llm_rejected: "The agent has not screened anything out.",
  stale:
    "Nothing has gone stale. A suggestion does when its page leaves the crawl.",
};

export function PageSuggestions({ onChanged }: { onChanged: () => void }) {
  const [state, setState] = useState<TabState>("ready");
  const [action, setAction] = useState<PageSuggestionAction | "">("");
  const [page, setPage] = useState(1);

  const path = useMemo(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(PAGE_SIZE),
      state,
    });
    if (action) params.set("action", action);
    return `/api/v1/seo/page-suggestions?${params}`;
  }, [page, state, action]);

  const {
    data: paged,
    loading,
    error,
    refresh,
  } = usePagedApi<PageSuggestion>(path);
  const { data: pages } = usePagedApi<SeoPageFacts>(
    "/api/v1/seo/pages?page_size=100&live=true",
  );
  const urls = useMemo(() => {
    const map = new Map<string, SeoPageFacts>();
    for (const p of pages?.data ?? []) map.set(p.pageId, p);
    return map;
  }, [pages]);

  const rows = paged?.data ?? null;
  const pagination = paged?.pagination ?? null;
  const reload = useCallback(() => {
    void refresh();
    onChanged();
  }, [refresh, onChanged]);

  return (
    <div>
      <Tabs
        active={state}
        onChange={(k) => {
          setState(k as TabState);
          setPage(1);
        }}
        tabs={(Object.keys(STATE_LABEL) as TabState[]).map((k) => ({
          key: k,
          label: STATE_LABEL[k],
        }))}
      />
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <Select
          value={action}
          onChange={(e) => {
            setAction(e.target.value as PageSuggestionAction | "");
            setPage(1);
          }}
          className="w-auto text-xs"
        >
          <option value="">Any action</option>
          {PAGE_SUGGESTION_ACTIONS.map((a) => (
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
      {rows !== null &&
        rows.length === 0 &&
        (state === "ready" && !action ? (
          <EmptyState
            icon={Lightbulb}
            title="No suggestions ready"
            hint={EMPTY.ready}
          />
        ) : (
          <p className="text-sm text-sub">
            {action ? "Nothing matches this filter." : EMPTY[state]}
          </p>
        ))}
      {rows !== null && rows.length > 0 && (
        <div className="divide-y divide-edge overflow-hidden rounded-2xl border border-edge bg-panel">
          {rows.map((row) => (
            <SuggestionRow
              key={row.id}
              row={row}
              urls={urls}
              onChanged={reload}
            />
          ))}
        </div>
      )}
      {pagination && pagination.total_pages > 1 && (
        <div className="mt-3 flex items-center justify-between text-xs text-sub">
          <span>
            Page {pagination.page} of {pagination.total_pages} ·{" "}
            {pagination.total} suggestions
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
    </div>
  );
}

function SuggestionRow({
  row,
  urls,
  onChanged,
}: {
  row: PageSuggestion;
  urls: Map<string, SeoPageFacts>;
  onChanged: () => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [busy, setBusy] = useState(false);
  const Icon = ACTION_ICON[row.action];
  const page = row.pageId ? urls.get(row.pageId) : null;
  const merge = row.mergeIntoPageId ? urls.get(row.mergeIntoPageId) : null;

  const settle = async (verb: "done" | "reject") => {
    setBusy(true);
    try {
      await api(`/api/v1/seo/page-suggestions/${row.id}/${verb}`, {
        method: "POST",
      });
      onChanged();
    } finally {
      setBusy(false);
    }
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
            <Badge tone={ACTION_TONE[row.action]}>
              <Icon size={11} className="mr-1 inline" />
              {ACTION_LABEL[row.action]}
            </Badge>
            <span className="font-medium text-ink">{row.topicKey}</span>
            {page && <PageLink url={page.url} />}
            {merge && (
              <>
                <span className="text-faint">→</span>
                <PageLink url={merge.url} />
              </>
            )}
          </div>
          <p
            className={cn(
              "text-[13px] leading-relaxed text-ink",
              !expanded && "line-clamp-2",
            )}
          >
            {row.suggestion}
          </p>
          <div className="flex flex-wrap items-center gap-2 text-xs text-faint">
            {row.strategies.map((s) => (
              <Badge key={s} tone="neutral">
                {STRATEGY_LABEL[s] ?? s}
              </Badge>
            ))}
            {row.pairId && <Badge tone="neutral">paired</Badge>}
            <span>{formatRelative(row.createdAt)}</span>
          </div>
        </div>
        <div
          className="flex shrink-0 items-center gap-1"
          onClick={stop}
          onKeyDown={stop}
        >
          {row.state === "ready" && (
            <>
              <Button
                variant="outline"
                size="sm"
                disabled={busy}
                onClick={() => settle("done")}
              >
                <Check size={13} /> Done
              </Button>
              <Button
                variant="ghost"
                size="sm"
                disabled={busy}
                onClick={() => settle("reject")}
              >
                <X size={13} /> Turn down
              </Button>
            </>
          )}
        </div>
      </div>
      {expanded && <Evidence row={row} />}
    </div>
  );
}

function Evidence({ row }: { row: PageSuggestion }) {
  const entries = Object.entries(row.evidence ?? {}).filter(
    ([k]) => k !== "content_hash",
  );
  return (
    <div className="space-y-2 px-4 pb-4 pl-[42px] text-xs">
      {entries.map(([key, value]) => (
        <div key={key} className="grid gap-x-6 sm:grid-cols-[120px_1fr]">
          <span className="text-faint">{key.replace(/_/g, " ")}</span>
          <span className="text-sub">{renderValue(value)}</span>
        </div>
      ))}
      {row.score !== null && row.score !== undefined && (
        <div className="grid gap-x-6 sm:grid-cols-[120px_1fr]">
          <span className="text-faint">rank</span>
          <span className="text-sub">{row.score.toFixed(2)}</span>
        </div>
      )}
      {row.confidence !== null && row.confidence !== undefined && (
        <div className="grid gap-x-6 sm:grid-cols-[120px_1fr]">
          <span className="text-faint">screen</span>
          <span className="text-sub">
            {Math.round(row.confidence * 100)}% yes
          </span>
        </div>
      )}
    </div>
  );
}

function renderValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined) return "—";
  if (Array.isArray(value)) {
    return (
      <ul className="space-y-0.5">
        {value.slice(0, 12).map((item, i) => (
          <li key={i} className="font-mono">
            {typeof item === "object" && item !== null
              ? Object.entries(item as Record<string, unknown>)
                  .filter(([, v]) => v !== null && v !== undefined)
                  .map(([k, v]) => `${k}: ${String(v)}`)
                  .join(" · ")
              : String(item)}
          </li>
        ))}
        {value.length > 12 && (
          <li className="text-faint">… {value.length - 12} more</li>
        )}
      </ul>
    );
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
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
