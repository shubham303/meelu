"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ListFilter, Search as SearchIcon, X } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import {
  Badge,
  Button,
  EmptyState,
  PageHeader,
  Spinner,
  Table,
  TCell,
  THead,
  TRow,
  type BadgeTone,
} from "@demo/components/ui";
import { apiPaged, useApi, type Paged } from "@demo/lib/use-api";
import { formatRelative } from "@demo/lib/utils";
import { SiteAskButton } from "../site-ask";
import type { SitePage } from "@demo/lib/types";
import * as chips from "@demo/features/prompt-chips/site";

const PAGE_TYPE_TONE: Record<string, BadgeTone> = {
  money: "good",
  hub: "good",
};

const SORT_COLUMNS = [
  { col: "Page", value: "url", dir: "asc" },
  { col: "Status", value: "status", dir: "desc" },
  { col: "Score", value: "score", dir: "desc" },
  { col: "Words", value: "words", dir: "asc" },
  { col: "In-links", value: "inlinks", dir: "desc" },
  { col: "Changed", value: "changed", dir: "desc" },
] as const;

type SortField = (typeof SORT_COLUMNS)[number]["value"];

const PAGE_TYPES = [
  "money",
  "hub",
  "informational",
  "support",
  "company",
  "legal",
  "utility",
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
    key: "pageType",
    label: "Kind",
    input: "enum",
    param: "pageType",
    options: PAGE_TYPES.map((t) => ({ value: t, label: t })),
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

const FIELD =
  "h-8 rounded-md border border-edge2 bg-panel px-2.5 text-xs text-ink focus:border-accent focus:outline-none";

export default function SitePagesPage() {
  const router = useRouter();
  const [sortField, setSortField] = useState<SortField>("url");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [rows, setRows] = useState<FilterRow[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const nextId = useRef(1);

  const [text, setText] = useState("");

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
        href="/demo/dashboard/site"
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
          <div className="rounded-xl border border-edge bg-panel2/60 p-3">
            {rows.length > 0 && (
              <div className="mb-2 divide-y divide-edge/60">
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
              </div>
            )}
            <select
              value=""
              onChange={(e) => e.target.value && addRow(e.target.value)}
              className={`${FIELD} w-auto border-dashed text-sub transition-colors hover:text-ink`}
            >
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
        ) : semanticRows && semanticRows.length === 0 ? (
          <EmptyState
            icon={SearchIcon}
            title="Nothing on the site covers that"
            hint="Which is itself useful — it means this is a gap rather than a duplicate."
          />
        ) : (
          <Table>
            <THead
              cols={["Page", "Kind", "Status", "Score", "Words", "In-links", "Changed"]}
              sortable={semanticRows ? [] : SORT_COLUMNS.map((c) => c.col)}
              sort={{ col: SORT_COLUMNS.find((c) => c.value === sortField)?.col ?? "Page", dir: sortDir }}
              onSort={(col) => {
                const def = SORT_COLUMNS.find((c) => c.col === col);
                if (!def) return;
                if (def.value === sortField) setSortDir((d) => (d === "asc" ? "desc" : "asc"));
                else {
                  setSortField(def.value);
                  setSortDir(def.dir);
                }
              }}
            />
            <tbody>
              {(semanticRows ?? pages).map((p) => (
                <PageTableRow
                  key={p.id}
                  page={p}
                  onOpen={() => router.push(`/demo/dashboard/site/pages/${p.id}`)}
                />
              ))}
            </tbody>
          </Table>
        )}
      </div>
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
    <div className="flex flex-wrap items-center gap-2 py-1.5">
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
        className={`${FIELD} w-44 font-medium`}
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
          className={`${FIELD} w-44`}
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
          className={`${FIELD} w-64 min-w-0 placeholder:text-faint`}
        />
      )}
      {def.input === "bool" && (
        <select
          value={row.a}
          onChange={(e) => onChange({ ...row, a: e.target.value })}
          className={`${FIELD} w-24`}
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
            className={`${FIELD} w-20 placeholder:text-faint`}
          />
          <span className="text-xs text-faint">–</span>
          <input
            type="number"
            value={row.b}
            onChange={(e) => onChange({ ...row, b: e.target.value })}
            placeholder="max"
            className={`${FIELD} w-20 placeholder:text-faint`}
          />
        </>
      )}
      {def.input === "dates" && (
        <>
          <input
            type="date"
            value={row.a}
            onChange={(e) => onChange({ ...row, a: e.target.value })}
            className={FIELD}
          />
          <span className="text-xs text-faint">to</span>
          <input
            type="date"
            value={row.b}
            onChange={(e) => onChange({ ...row, b: e.target.value })}
            className={FIELD}
          />
        </>
      )}
      <button
        type="button"
        onClick={onRemove}
        title="Remove this filter"
        className="flex h-8 w-8 items-center justify-center rounded-md text-faint transition-colors hover:bg-panel hover:text-ink"
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

function PageTableRow({ page, onOpen }: { page: SitePage; onOpen: () => void }) {
  return (
    <TRow onClick={onOpen}>
      <TCell className="max-w-md">
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          <span className="truncate text-sm font-medium text-ink">{page.title || page.url}</span>
          {page.shallow && <Badge tone="neutral">{page.shallowReason ?? "skipped"}</Badge>}
        </div>
        <div className="mt-0.5 truncate text-xs text-faint">{page.url}</div>
        {page.match && <MatchExcerpt match={page.match} />}
      </TCell>
      <TCell>
        {page.pageType ? (
          <Badge tone={PAGE_TYPE_TONE[page.pageType] ?? "neutral"}>{page.pageType}</Badge>
        ) : (
          <span className="text-xs text-faint">—</span>
        )}
      </TCell>
      <TCell className="tabular-nums">{page.status ?? "—"}</TCell>
      <TCell className="tabular-nums">
        {typeof page.linkScore === "number" ? page.linkScore : "—"}
      </TCell>
      <TCell className="tabular-nums">{page.wordCount ?? "—"}</TCell>
      <TCell className="tabular-nums">{page.inlinks}</TCell>
      <TCell className="whitespace-nowrap text-xs text-sub">
        {page.contentChangedAt ? formatRelative(page.contentChangedAt) : "—"}
      </TCell>
    </TRow>
  );
}

