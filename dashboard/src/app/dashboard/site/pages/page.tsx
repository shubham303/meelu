"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  ListFilter,
  Search as SearchIcon,
  X,
} from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import {
  Badge,
  Button,
  Drawer,
  EmptyState,
  PageHeader,
  Spinner,
  type BadgeTone,
} from "@/components/ui";
import { apiPaged, useApi, type Paged } from "@/lib/use-api";
import { formatRelative } from "@/lib/utils";
import { SiteAskButton } from "../site-ask";
import type { SitePage, SitePageAnalysis } from "@/lib/types";
import * as chips from "@/features/prompt-chips/site";

const KIND_TONE: Record<string, BadgeTone> = {
  home: "good",
  product: "good",
  pricing: "good",
  article: "neutral",
  category: "neutral",
  docs: "neutral",
  about: "neutral",
  contact: "neutral",
  legal: "neutral",
  other: "neutral",
};

const SORT_FIELDS = [
  { value: "url", label: "URL", dir: "asc" },
  { value: "words", label: "Words", dir: "asc" },
  { value: "inlinks", label: "Inbound links", dir: "desc" },
  { value: "score", label: "Link score", dir: "desc" },
  { value: "depth", label: "Clicks from home", dir: "desc" },
  { value: "status", label: "Status code", dir: "desc" },
  { value: "crawled", label: "Last crawled", dir: "asc" },
  { value: "changed", label: "Content changed", dir: "asc" },
] as const;

type SortField = (typeof SORT_FIELDS)[number]["value"];

const KINDS = [
  "home",
  "product",
  "pricing",
  "article",
  "category",
  "docs",
  "about",
  "contact",
  "legal",
  "other",
] as const;

const STATUSES = [
  { value: "ok", label: "OK (200)" },
  { value: "redirect", label: "Redirects" },
  { value: "gone", label: "Gone (404/410)" },
  { value: "blocked", label: "Blocked (401/403/429)" },
  { value: "serverError", label: "Server error (5xx)" },
  { value: "unreachable", label: "Unreachable" },
  { value: "error", label: "Any failure" },
] as const;

type ParamDef =
  | {
      key: string;
      label: string;
      input: "enum";
      param: string;
      options: readonly { value: string; label: string }[];
      append?: boolean;
    }
  | { key: string; label: string; input: "text"; param: string; placeholder?: string }
  | { key: string; label: string; input: "bool"; param: string }
  | { key: string; label: string; input: "range"; minParam: string; maxParam: string }
  | { key: string; label: string; input: "dates"; afterParam: string; beforeParam: string };

const PARAMS: readonly ParamDef[] = [
  {
    key: "kind",
    label: "Kind",
    input: "enum",
    param: "kind",
    options: KINDS.map((k) => ({ value: k, label: k })),
  },
  { key: "status", label: "Status", input: "enum", param: "status", options: STATUSES },
  {
    key: "stage",
    label: "Crawl stage",
    input: "enum",
    param: "stage",
    options: ["pending", "blocked", "failed", "skipped", "crawled", "indexed"].map((v) => ({
      value: v,
      label: v,
    })),
  },
  {
    key: "format",
    label: "Article format",
    input: "enum",
    param: "format",
    options: ["how-to", "listicle", "comparison", "case study"].map((v) => ({
      value: v,
      label: v,
    })),
  },
  {
    key: "missing",
    label: "Missing field",
    input: "enum",
    param: "missing",
    append: true,
    options: [
      { value: "title", label: "Title" },
      { value: "metaDescription", label: "Meta description" },
      { value: "h1", label: "H1" },
      { value: "bodyText", label: "Body text" },
    ],
  },
  { key: "lang", label: "Language", input: "text", param: "lang", placeholder: "en" },
  { key: "urlContains", label: "URL contains", input: "text", param: "urlContains" },
  { key: "titleContains", label: "Title contains", input: "text", param: "titleContains" },
  { key: "metaContains", label: "Meta description contains", input: "text", param: "metaContains" },
  { key: "textContains", label: "Body text contains", input: "text", param: "textContains" },
  { key: "words", label: "Words", input: "range", minParam: "minWords", maxParam: "maxWords" },
  {
    key: "inlinks",
    label: "Inbound links",
    input: "range",
    minParam: "minInlinks",
    maxParam: "maxInlinks",
  },
  {
    key: "depth",
    label: "Clicks from home",
    input: "range",
    minParam: "minDepth",
    maxParam: "maxDepth",
  },
  {
    key: "crawled",
    label: "Crawled",
    input: "dates",
    afterParam: "crawledAfter",
    beforeParam: "crawledBefore",
  },
  {
    key: "changed",
    label: "Content changed",
    input: "dates",
    afterParam: "changedAfter",
    beforeParam: "changedBefore",
  },
  {
    key: "published",
    label: "Published",
    input: "dates",
    afterParam: "publishedAfter",
    beforeParam: "publishedBefore",
  },
  { key: "inSitemap", label: "In sitemap", input: "bool", param: "inSitemap" },
  { key: "orphan", label: "Orphan", input: "bool", param: "orphan" },
  { key: "noindex", label: "Noindex", input: "bool", param: "noindex" },
  { key: "shallow", label: "Skipped as shallow", input: "bool", param: "shallow" },
  { key: "blockedByRobots", label: "Blocked by robots", input: "bool", param: "blockedByRobots" },
  {
    key: "canonicalElsewhere",
    label: "Canonical elsewhere",
    input: "bool",
    param: "canonicalElsewhere",
  },
  { key: "redirects", label: "Redirects", input: "bool", param: "redirects" },
  { key: "needsAudit", label: "Needs audit", input: "bool", param: "needsAudit" },
];

function byKey(key: string): ParamDef | undefined {
  return PARAMS.find((p) => p.key === key);
}

interface FilterRow {
  id: number;
  key: string;
  a: string;
  b: string;
}

function rowActive(row: FilterRow): boolean {
  const def = byKey(row.key);
  if (!def) return false;
  if (def.input === "range" || def.input === "dates") return !!(row.a || row.b);
  return !!row.a;
}

function applyRows(params: URLSearchParams, rows: FilterRow[]) {
  for (const row of rows) {
    const def = byKey(row.key);
    if (!def || !rowActive(row)) continue;
    switch (def.input) {
      case "enum":
        if (def.append) params.append(def.param, row.a);
        else params.set(def.param, row.a);
        break;
      case "text":
      case "bool":
        params.set(def.param, row.a);
        break;
      case "range":
        if (row.a) params.set(def.minParam, row.a);
        if (row.b) params.set(def.maxParam, row.b);
        break;
      case "dates":
        if (row.a) params.set(def.afterParam, row.a);
        if (row.b) params.set(def.beforeParam, row.b);
        break;
    }
  }
}

function rowSummary(row: FilterRow): string {
  const def = byKey(row.key);
  if (!def) return "";
  switch (def.input) {
    case "enum":
      return `${def.label}: ${def.options.find((o) => o.value === row.a)?.label ?? row.a}`;
    case "text":
      return `${def.label}: ${row.a}`;
    case "bool":
      return `${def.label}: ${row.a === "true" ? "yes" : "no"}`;
    case "range":
      if (row.a && row.b) return `${def.label}: ${row.a}–${row.b}`;
      return row.a ? `${def.label} ≥ ${row.a}` : `${def.label} ≤ ${row.b}`;
    case "dates":
      if (row.a && row.b) return `${def.label}: ${row.a} – ${row.b}`;
      return row.a ? `${def.label} after ${row.a}` : `${def.label} before ${row.b}`;
  }
}

const CONTROL =
  "rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink focus:border-accent focus:outline-none";

export default function SitePagesPage() {
  const [sortField, setSortField] = useState<SortField>("url");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [rows, setRows] = useState<FilterRow[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const nextId = useRef(1);

  const [text, setText] = useState("");
  const [open, setOpen] = useState<SitePage | null>(null);

  const [result, setResult] = useState<Paged<SitePage> | null>(null);
  const [searching, setSearching] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);

  const semanticRows = result?.data ?? null;

  const editRows = (updater: (prev: FilterRow[]) => FilterRow[]) => {
    setRows(updater);
    setResult(null);
  };
  const addRow = (key: string) => {
    const def = byKey(key);
    editRows((prev) => [
      ...prev,
      { id: nextId.current++, key, a: def?.input === "bool" ? "true" : "", b: "" },
    ]);
  };
  const activeRows = rows.filter(rowActive);

  const filterQuery = useMemo(() => {
    const params = new URLSearchParams({ pageSize: "100", sort: `${sortField}:${sortDir}` });
    applyRows(params, rows);
    return params.toString();
  }, [sortField, sortDir, rows]);
  const [listQuery, setListQuery] = useState(filterQuery);
  useEffect(() => {
    const t = setTimeout(() => setListQuery(filterQuery), 350);
    return () => clearTimeout(t);
  }, [filterQuery]);
  const { data: pageList, loading } = useApi<SitePage[]>(`/api/v1/site/pages?${listQuery}`);
  const pages = useMemo(() => pageList ?? [], [pageList]);

  const runSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = text.trim();
    if (!q) return;
    setSearching(true);
    try {
      const params = new URLSearchParams({ searchText: q, pageSize: "10" });
      applyRows(params, rows);
      setResult(await apiPaged<SitePage>(`/api/v1/site/pages?${params.toString()}`));
      setProblem(null);
    } catch (err) {
      setProblem(err instanceof Error ? err.message : "The search could not run.");
    } finally {
      setSearching(false);
    }
  };

  return (
    <PageEnter>
      <Link
        href="/dashboard/site"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-sub transition-colors hover:text-ink"
      >
        <ArrowLeft size={14} /> Site
      </Link>

      <PageHeader
        title="Pages"
        description="Every page the crawl has read. Search what the passages inside those pages actually say."
        actions={
          <SiteAskButton
            title="Ask — Pages"
            hint="Ask what the site covers, where it is thin, or what is broken. Answers come back as links to pages, not as pasted text."
            suggestions={chips.pages()}
            draft={{ searched: text.trim() || undefined }}
            endpoint="/api/agent/ask-pages"
          />
        }
      />

      <div className="space-y-4">
        <form onSubmit={runSearch} className="flex items-stretch gap-3">
          <div className="relative min-w-0 flex-1">
            <SearchIcon className="pointer-events-none absolute left-4 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
            <input
              value={text}
              onChange={(e) => {
                setText(e.target.value);
                if (!e.target.value.trim()) {
                  setResult(null);
                  setProblem(null);
                }
              }}
              placeholder="Is this covered anywhere? e.g. hiring warehouse staff in Nashik"
              className="w-full rounded-xl border border-edge2 bg-panel py-3 pl-11 pr-4 text-base text-ink placeholder:text-faint focus:border-accent focus:outline-none"
            />
          </div>
          <Button type="submit" disabled={searching || !text.trim()} className="px-6">
            {searching ? "Searching…" : "Search"}
          </Button>
        </form>

        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            onClick={() => setShowFilters((v) => !v)}
            className={`${CONTROL} inline-flex shrink-0 items-center gap-1.5 transition-colors hover:bg-panel2 ${showFilters ? "border-accent" : ""}`}
          >
            <ListFilter size={14} />
            Filters{activeRows.length ? ` (${activeRows.length})` : ""}
          </button>
          <select
            value={sortField}
            onChange={(e) => {
              const field = e.target.value as SortField;
              setSortField(field);
              setSortDir(SORT_FIELDS.find((sf) => sf.value === field)?.dir ?? "asc");
            }}
            disabled={!!semanticRows}
            className={`${CONTROL} shrink-0 disabled:cursor-not-allowed disabled:opacity-50`}
          >
            {SORT_FIELDS.map((sf) => (
              <option key={sf.value} value={sf.value}>
                Sort: {sf.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            onClick={() => setSortDir((d) => (d === "asc" ? "desc" : "asc"))}
            disabled={!!semanticRows}
            title={sortDir === "asc" ? "Ascending — click for descending" : "Descending — click for ascending"}
            className={`${CONTROL} shrink-0 transition-colors hover:bg-panel2 disabled:cursor-not-allowed disabled:opacity-50`}
          >
            {sortDir === "asc" ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
          </button>
          <span className="ml-auto shrink-0 text-sm tabular-nums text-faint">
            {result
              ? `${result.data.length} match${result.data.length === 1 ? "" : "es"}`
              : `${pages.length} pages`}
          </span>
        </div>

        {activeRows.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {activeRows.map((row) => (
              <span
                key={row.id}
                className="inline-flex items-center gap-1.5 rounded-full border border-edge2 bg-panel px-2.5 py-1 text-xs text-sub"
              >
                {rowSummary(row)}
                <button
                  type="button"
                  onClick={() => editRows((prev) => prev.filter((r) => r.id !== row.id))}
                  className="text-faint transition-colors hover:text-ink"
                >
                  <X size={12} />
                </button>
              </span>
            ))}
            <button
              type="button"
              onClick={() => editRows(() => [])}
              className="text-xs text-faint transition-colors hover:text-ink"
            >
              Clear all
            </button>
          </div>
        )}

        {showFilters && (
          <div className="space-y-2 rounded-xl border border-edge bg-panel p-4">
            {rows.map((row) => (
              <FilterRowEditor
                key={row.id}
                row={row}
                onChange={(next) =>
                  editRows((prev) => prev.map((r) => (r.id === row.id ? next : r)))
                }
                onRemove={() => editRows((prev) => prev.filter((r) => r.id !== row.id))}
              />
            ))}
            <select value="" onChange={(e) => e.target.value && addRow(e.target.value)} className={CONTROL}>
              <option value="">+ Add filter</option>
              {PARAMS.map((p) => (
                <option key={p.key} value={p.key}>
                  {p.label}
                </option>
              ))}
            </select>
          </div>
        )}

        <p className="text-sm text-sub">
          Searches the passages the crawl read, not the URLs. Use it to find whether a topic is
          covered anywhere before you write about it again.
        </p>
        {problem && <p className="text-sm text-bad">{problem}</p>}
        {result?.note && <p className="text-xs text-amber-600">{result.note}</p>}

        {loading ? (
          <Spinner />
        ) : pages.length === 0 ? (
          <EmptyState
            icon={SearchIcon}
            title="This website has not been read yet"
            hint="Crawling runs from the Site desk, in the Meelu app on your own machine."
          />
        ) : semanticRows ? (
          semanticRows.length === 0 ? (
            <EmptyState
              icon={SearchIcon}
              title="Nothing on the site covers that"
              hint="Which is itself useful — it means this is a gap rather than a duplicate."
            />
          ) : (
            <Stagger className="divide-y divide-edge overflow-hidden rounded-xl border border-edge bg-panel">
              {semanticRows.map((page) => (
                <PageRow key={page.id} page={page} onOpen={() => setOpen(page)} />
              ))}
            </Stagger>
          )
        ) : (
          <Stagger className="divide-y divide-edge overflow-hidden rounded-xl border border-edge bg-panel">
            {pages.map((p) => (
              <PageRow key={p.id} page={p} onOpen={() => setOpen(p)} />
            ))}
          </Stagger>
        )}
      </div>

      <Drawer open={!!open} onClose={() => setOpen(null)} title={open?.title ?? "Page"}>
        {open && <PageDetail page={open} />}
      </Drawer>
    </PageEnter>
  );
}

function FilterRowEditor({
  row,
  onChange,
  onRemove,
}: {
  row: FilterRow;
  onChange: (row: FilterRow) => void;
  onRemove: () => void;
}) {
  const def = byKey(row.key);
  if (!def) return null;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <select
        value={row.key}
        onChange={(e) =>
          onChange({
            ...row,
            key: e.target.value,
            a: byKey(e.target.value)?.input === "bool" ? "true" : "",
            b: "",
          })
        }
        className={CONTROL}
      >
        {PARAMS.map((p) => (
          <option key={p.key} value={p.key}>
            {p.label}
          </option>
        ))}
      </select>
      {def.input === "enum" && (
        <select
          value={row.a}
          onChange={(e) => onChange({ ...row, a: e.target.value })}
          className={CONTROL}
        >
          <option value="">choose…</option>
          {def.options.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      )}
      {def.input === "text" && (
        <input
          value={row.a}
          onChange={(e) => onChange({ ...row, a: e.target.value })}
          placeholder={def.placeholder ?? "contains…"}
          className={`${CONTROL} min-w-0 flex-1`}
        />
      )}
      {def.input === "bool" && (
        <select
          value={row.a}
          onChange={(e) => onChange({ ...row, a: e.target.value })}
          className={CONTROL}
        >
          <option value="true">yes</option>
          <option value="false">no</option>
        </select>
      )}
      {def.input === "range" && (
        <>
          <input
            type="number"
            value={row.a}
            onChange={(e) => onChange({ ...row, a: e.target.value })}
            placeholder="min"
            className={`${CONTROL} w-24`}
          />
          <span className="text-sm text-faint">–</span>
          <input
            type="number"
            value={row.b}
            onChange={(e) => onChange({ ...row, b: e.target.value })}
            placeholder="max"
            className={`${CONTROL} w-24`}
          />
        </>
      )}
      {def.input === "dates" && (
        <>
          <input
            type="date"
            value={row.a}
            onChange={(e) => onChange({ ...row, a: e.target.value })}
            className={CONTROL}
          />
          <span className="text-sm text-faint">to</span>
          <input
            type="date"
            value={row.b}
            onChange={(e) => onChange({ ...row, b: e.target.value })}
            className={CONTROL}
          />
        </>
      )}
      <button
        type="button"
        onClick={onRemove}
        className="ml-auto text-faint transition-colors hover:text-ink"
      >
        <X size={14} />
      </button>
    </div>
  );
}

function MatchExcerpt({ match }: { match: NonNullable<SitePage["match"]> }) {
  return (
    <div className="mt-1.5">
      {match.headingPath && <div className="text-xs text-faint">under {match.headingPath}</div>}
      <p className="text-xs text-sub">{match.text.slice(0, 400)}</p>
    </div>
  );
}

function PageRow({ page, onOpen }: { page: SitePage; onOpen: () => void }) {
  return (
    <button
      onClick={onOpen}
      className="flex w-full cursor-pointer items-start gap-3 px-4 py-3 text-left transition-colors hover:bg-panel2"
    >
      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="truncate text-sm font-medium text-ink">{page.title || page.url}</span>
          <Badge tone={KIND_TONE[page.kind] ?? "neutral"}>{page.kind}</Badge>
          {page.shallow && <Badge tone="neutral">{page.shallowReason ?? "skipped"}</Badge>}
        </div>
        <div className="mt-0.5 truncate text-xs text-faint">{page.url}</div>
        {page.match && <MatchExcerpt match={page.match} />}
      </div>
    </button>
  );
}

function uniqueAnchors(list: { anchor: string }[] | undefined): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const { anchor } of list ?? []) {
    const key = anchor.trim().toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(anchor.trim());
  }
  return out;
}

function uniqueUrls(urls: (string | undefined)[]): string[] {
  return [...new Set(urls.filter((u): u is string => !!u))];
}

function PageDetail({ page }: { page: SitePage }) {
  const { data: full } = useApi<SitePage>(`/api/v1/site/pages/${page.id}`);
  const { data: analysis } = useApi<SitePageAnalysis>(
    `/api/v1/site/page-analysis?pageId=${page.id}`,
  );
  const p = full ?? page;
  const anchors = uniqueAnchors(p.inboundAnchors);
  const inboundPages = uniqueUrls((p.inboundAnchors ?? []).map((a) => a.from));
  const outboundPages = uniqueUrls((p.outLinks ?? []).map((l) => l.url));
  return (
    <div className="space-y-4 text-sm">
      <a
        href={p.url}
        target="_blank"
        rel="noreferrer"
        className="flex items-center gap-1 text-xs text-sub hover:underline"
      >
        {p.url} <ExternalLink className="h-3 w-3" />
      </a>

      {typeof p.linkScore === "number" && (
        <div>
          <div className="flex items-center justify-between text-xs">
            <span className="font-medium uppercase tracking-wide text-sub">Link score</span>
            <span className="font-medium tabular-nums text-ink">{p.linkScore}</span>
          </div>
          <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-panel2">
            <div
              className="h-full rounded-full bg-accent"
              style={{ width: `${Math.min(Math.max(p.linkScore, 1), 100)}%` }}
            />
          </div>
          <p className="mt-1 text-[11px] text-faint">
            How much of the site&rsquo;s internal linking points here — the best-linked page scores 100.
          </p>
        </div>
      )}

      <dl className="grid grid-cols-2 gap-3 text-xs">
        <Detail label="Type" value={p.kind} />
        <Detail label="Format" value={p.format} />
        <Detail label="Status" value={p.status} />
        <Detail label="Stage" value={p.stage} />
        <Detail label="Inbound links" value={p.inlinks} />
        <Detail label="Clicks from home" value={p.depth} />
        <Detail label="Words" value={p.wordCount} />
        <Detail label="Language" value={p.lang} />
        <Detail label="In sitemap" value={p.inSitemap ? "yes" : "no"} />
        <Detail label="Noindex" value={p.robotsDirectives?.includes("noindex") ? "yes" : "no"} />
        <Detail
          label="Crawled"
          value={p.lastCrawledAt ? formatRelative(p.lastCrawledAt) : "—"}
        />
        <Detail
          label="Text last really changed"
          value={
            p.contentChangedAt
              ? formatRelative(p.contentChangedAt)
              : "not measured yet — the crawl has seen this page once"
          }
        />
        <Detail
          label="Published"
          value={p.publishedAt ? formatRelative(p.publishedAt) : "none declared"}
        />
        <Detail
          label="Date the page declares"
          value={p.modifiedAt ? formatRelative(p.modifiedAt) : "none"}
        />
      </dl>

      {p.canonical && p.canonical !== p.url && (
        <Block label="Canonical points elsewhere" text={p.canonical} />
      )}
      {p.redirectTo && <Block label="Redirects to" text={p.redirectTo} />}
      {p.fetchError && <Block label="Fetch error" text={p.fetchError} />}
      {p.metaDescription && <Block label="Meta description" text={p.metaDescription} />}
      {!!p.h1?.length && <Block label="H1" text={p.h1.join(" · ")} />}

      {analysis && <PageAnalysis analysis={analysis} />}

      {!!p.keywords?.length && (
        <div>
          <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-sub">Keywords</h3>
          <div className="flex flex-wrap gap-1.5">
            {p.keywords.map((k) => (
              <Badge key={k} tone="neutral">
                {k}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {!!anchors.length && (
        <div>
          <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-sub">
            What the site calls this page
          </h3>
          <ul className="space-y-1 text-xs text-sub">
            {anchors.slice(0, 10).map((a) => (
              <li key={a}>&ldquo;{a}&rdquo;</li>
            ))}
          </ul>
        </div>
      )}

      <UrlList label={`Pages that link here (${inboundPages.length})`} urls={inboundPages} />
      <UrlList
        label={`Pages this page links to (${outboundPages.length})`}
        urls={outboundPages}
      />
    </div>
  );
}

function PageAnalysis({ analysis }: { analysis: SitePageAnalysis }) {
  const empty =
    analysis.topics.length === 0 &&
    analysis.keywords.length === 0 &&
    analysis.questionsAnswered.length === 0;
  if (empty) return null;
  return (
    <div className="space-y-3 rounded-xl border border-edge2 bg-panel2/50 p-3">
      <div className="flex items-baseline justify-between">
        <h3 className="text-xs font-medium uppercase tracking-wide text-sub">
          What Meelu read in this page
        </h3>
        <span className="text-[11px] text-faint">analysed {formatRelative(analysis.analyzedAt)}</span>
      </div>

      {!!analysis.topics.length && (
        <div>
          <h4 className="mb-1 text-[11px] font-medium uppercase tracking-wide text-faint">
            Topics covered
          </h4>
          <ul className="space-y-1 text-xs text-ink">
            {analysis.topics.map((t, i) => (
              <li key={`${t.topic}-${i}`}>
                {t.topic}
                {t.section && <span className="text-faint"> — under &ldquo;{t.section}&rdquo;</span>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {!!analysis.keywords.length && (
        <div>
          <h4 className="mb-1 text-[11px] font-medium uppercase tracking-wide text-faint">
            Keywords
          </h4>
          <div className="flex flex-wrap gap-1.5">
            {analysis.keywords.map((k) => (
              <Badge key={k} tone="neutral">
                {k}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {!!analysis.questionsAnswered.length && (
        <div>
          <h4 className="mb-1 text-[11px] font-medium uppercase tracking-wide text-faint">
            Questions this page answers
          </h4>
          <ul className="space-y-1 text-xs text-sub">
            {analysis.questionsAnswered.map((q) => (
              <li key={q}>{q}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function UrlList({ label, urls }: { label: string; urls: string[] }) {
  const [expanded, setExpanded] = useState(false);
  if (urls.length === 0) return null;
  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="mb-1 flex cursor-pointer items-center gap-1 text-xs font-medium uppercase tracking-wide text-sub transition-colors hover:text-ink"
      >
        {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        {label}
      </button>
      {expanded && (
        <ul className="space-y-1 text-xs">
        {urls.map((u) => (
          <li key={u}>
            <a
              href={u}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-start gap-1 break-all text-sub hover:text-ink hover:underline"
            >
              {u} <ExternalLink className="mt-0.5 h-3 w-3 shrink-0" />
            </a>
          </li>
        ))}
        </ul>
      )}
    </div>
  );
}

function Block({ label, text }: { label: string; text: string }) {
  return (
    <div>
      <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-sub">{label}</h3>
      <p className="break-words text-xs text-sub">{text}</p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <dt className="text-sub">{label}</dt>
      <dd>{value === null || value === undefined || value === "" ? "—" : String(value)}</dd>
    </div>
  );
}
