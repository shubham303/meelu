"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Loader2, RotateCw, Search as SearchIcon } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Badge, Button, Card, EmptyState, PageHeader, Spinner } from "@demo/components/ui";
import { api, useApi, useCurrentSite } from "@demo/lib/use-api";
import { IndexationSection, type GooglePrefers } from "../indexation";
import { SiteAskButton } from "../site-ask";
import * as chips from "@demo/features/prompt-chips/site";
import { LineChart, type ChartSeries } from "./line-chart";
import {
  canInspectUrls,
  inspectPageUrl,
  useGscConnected,
  useSearchSync,
  type GscProperty,
} from "./sync";

interface Totals {
  clicks: number;
  impressions: number;
  ctr: number | null;
  position: number | null;
}

interface Overview {
  connected: boolean;
  property: string | null;
  hasData: boolean;
  operatingBlind: boolean;
  firstDay?: string;
  lastDay?: string;
  indexation?: Record<string, number>;
  neverChecked?: number;
  googlePrefers?: GooglePrefers[];
  contentQualityVerdict?: string | null;
  active?: { id: string } | null;
}

interface SeriesPoint {
  day: string;
  clicks: number;
  impressions: number;
  ctr: number | null;
  position: number | null;
}

interface SeriesResponse {
  hasData: boolean;
  lastDay: string | null;
  days: number;
  series: { page: string | null; points: SeriesPoint[] }[];
  current?: Totals;
  previous?: Totals;
}

interface PageRow {
  page: string;
  clicks: number;
  prevClicks: number;
  impressions: number;
  position: number | null;
  indexState: string | null;
  coverageState: string | null;
  googleCanonical: string | null;
  lastCrawlTime: string | null;
  indexCheckedAt: string | null;
}

interface QueryRow {
  query: string;
  page: string | null;
  inlinks: number | null;
  clicks: number;
  impressions: number;
  position: number | null;
}

type MetricKey = "clicks" | "impressions" | "ctr" | "position";
type SortKey =
  | "page"
  | "clicks"
  | "impressions"
  | "ctr"
  | "position"
  | "index"
  | "crawled"
  | "inspected";

const RANGES = [28, 90, 180];
const MAX_COMPARE = 5;
const PAGE_SIZE = 20;
const QUERY_PAGE_SIZE = 10;
const SLOT_COLORS = ["#2563eb", "#eb6834", "#1baf7a", "#d97706", "#d55181"];
const ASC_FIRST = new Set<SortKey>(["page", "position", "index", "crawled", "inspected"]);

const METRICS: Record<
  MetricKey,
  { name: string; color: string; invert: boolean; fmt: (v: number) => string }
> = {
  clicks: { name: "Clicks", color: "#2563eb", invert: false, fmt: (v) => compact(v) },
  impressions: { name: "Impressions", color: "#eb6834", invert: false, fmt: (v) => compact(v) },
  ctr: { name: "CTR", color: "#1baf7a", invert: false, fmt: (v) => `${(v * 100).toFixed(1)}%` },
  position: { name: "Avg position", color: "#d97706", invert: true, fmt: (v) => v.toFixed(1) },
};

const INDEX_META: Record<string, { label: string; color: string }> = {
  indexed: { label: "Indexed", color: "#15803d" },
  "crawled-not-indexed": { label: "Not indexed", color: "#d97706" },
  discovered: { label: "Discovered", color: "#d97706" },
  excluded: { label: "Excluded", color: "#ec835a" },
  blocked: { label: "Blocked", color: "#ec835a" },
  "unknown-to-google": { label: "Unknown", color: "#8fa0b3" },
  unknown: { label: "Unknown", color: "#8fa0b3" },
};

function compact(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 10_000) return `${(v / 1000).toFixed(1)}K`;
  return Math.round(v).toLocaleString("en-US");
}

function num(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function shortPath(url: string): string {
  try {
    const u = new URL(url);
    return u.pathname === "/" ? u.hostname : u.pathname;
  } catch {
    return url;
  }
}

function stripSlash(url: string): string {
  return url.replace(/\/+$/, "");
}

function daysAgo(iso: string | null): string {
  if (!iso) return "—";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "today";
  return `${days}d ago`;
}

interface SelectedPage {
  url: string;
  slot: number;
}

export default function SearchPerformancePage() {
  const siteId = useCurrentSite();
  const { data: overview, error: overviewError, refresh } = useApi<Overview>("/api/v1/site/search-data");
  const sync = useSearchSync(siteId, refresh, overview?.active?.id ?? null);
  const gsc = useGscConnected();

  const [range, setRange] = useState(90);
  const [metric, setMetric] = useState<MetricKey>("clicks");
  const [selected, setSelected] = useState<SelectedPage[]>([]);

  const pagesParam = selected.map((s) => s.url).join(",");
  const { data: series } = useApi<SeriesResponse>(
    overview?.hasData
      ? `/api/v1/site/search-data/series?days=${range}${pagesParam ? `&pages=${encodeURIComponent(pagesParam)}` : ""}`
      : null,
  );

  const toggleSelect = (url: string) => {
    setSelected((prev) => {
      const at = prev.findIndex((s) => stripSlash(s.url) === stripSlash(url));
      if (at >= 0) return prev.filter((_, i) => i !== at);
      if (prev.length >= MAX_COMPARE) return prev;
      const used = new Set(prev.map((s) => s.slot));
      let slot = 0;
      while (used.has(slot)) slot++;
      return [...prev, { url, slot }];
    });
  };

  return (
    <PageEnter>
      <Link
        href="/demo/dashboard/site"
        className="mb-3 inline-flex items-center gap-1.5 text-sm text-sub hover:text-ink"
      >
        <ArrowLeft size={14} /> Site
      </Link>
      <PageHeader
        title="Search performance"
        description={
          overview?.hasData
            ? `What Google actually sends — query × page × day, kept since ${overview.firstDay}. Data through ${overview.lastDay}.`
            : "What Google actually sends, measured. Connect Search Console and the desk keeps 16 months of it."
        }
        actions={
          <div className="flex items-center gap-2">
            {overview?.hasData && sync.canSync && (
              <Button variant="outline" disabled={sync.running} onClick={() => void sync.start()}>
                {sync.running && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                {sync.running ? "Syncing…" : "Sync now"}
              </Button>
            )}
            <SiteAskButton
              title="Ask — Search"
              hint="Ask about the measured search data — what changed, what dropped, what is close."
              suggestions={chips.search()}
              onRan={refresh}
            />
          </div>
        }
      />

      <div className="space-y-4">
        {gsc.connected === false && (
          <ConnectGscCard onConnect={sync.connectGsc} onConnected={gsc.markConnected} />
        )}
        {sync.running && <SyncProgressBar sync={sync} />}
        {sync.error && <Card className="border-bad/40 bg-bad/5 p-3 text-sm">{sync.error}</Card>}
        {sync.candidates && (
          <PropertyPicker
            candidates={sync.candidates}
            onPicked={async (property) => {
              await api("/api/v1/site/search-data/property", {
                method: "POST",
                body: { property },
              });
              sync.clearCandidates();
              void sync.start();
            }}
          />
        )}

        {!overview && !overviewError && <Spinner />}
        {!overview && overviewError && (
          <Card className="border-bad/40 bg-bad/5 p-3 text-sm">{overviewError}</Card>
        )}

        {overview && !overview.hasData && !sync.running && (
          <EmptyState
            icon={SearchIcon}
            title="No search data yet"
            hint={
              sync.canSync
                ? "The first sync imports 16 months of Search Console data — every query, every page, every day. It runs from this machine and costs nothing."
                : "Syncing runs in the Meelu app, where the Search Console connection lives. Open the app to import 16 months of data."
            }
            action={
              sync.canSync ? (
                <Button onClick={() => void sync.start()}>Import 16 months of search data</Button>
              ) : undefined
            }
          />
        )}

        {overview?.hasData && (
          <>
            {overview.operatingBlind && (
              <Card className="border-warn/40 bg-warn/5 p-3 text-sm">
                This site receives almost no impressions yet, so every number below is thin.
                Treat trends as noise until there is real volume — the agent is told the same.
              </Card>
            )}

            <FilterRow
              range={range}
              onRange={setRange}
              selected={selected}
              onRemove={toggleSelect}
            />
            <MetricTiles
              metric={metric}
              onMetric={setMetric}
              range={range}
              current={series?.current}
              previous={series?.previous}
            />
            <ChartCard metric={metric} series={series} selected={selected} />

            {overview.indexation && (
              <IndexationSection
                siteId={siteId}
                counts={overview.indexation}
                neverChecked={overview.neverChecked ?? 0}
                googlePrefers={overview.googlePrefers ?? []}
                verdict={overview.contentQualityVerdict ?? null}
                onChanged={refresh}
              />
            )}
            <StrikingDistance />
            <PagesTable
              siteId={siteId}
              range={range}
              selected={selected}
              onToggle={toggleSelect}
              onInspected={refresh}
            />
            <QueriesTable range={range} selected={selected} />

            <p className="text-xs text-faint">
              Property {overview.property} — chosen by you. Positions are impression-weighted
              averages from Search Console, not live checks.
            </p>
          </>
        )}
      </div>
    </PageEnter>
  );
}

function FilterRow({
  range,
  onRange,
  selected,
  onRemove,
}: {
  range: number;
  onRange: (d: number) => void;
  selected: SelectedPage[];
  onRemove: (url: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-2.5">
      <div className="inline-flex overflow-hidden rounded-lg border border-edge2 bg-panel">
        {RANGES.map((d, i) => (
          <button
            key={d}
            type="button"
            aria-pressed={range === d}
            onClick={() => onRange(d)}
            className={`cursor-pointer px-3 py-1.5 text-[13px] transition-colors ${
              range === d ? "bg-accent-soft font-medium text-accent" : "text-sub hover:bg-panel2"
            } ${i > 0 ? "border-l border-edge" : ""}`}
          >
            {d} days
          </button>
        ))}
      </div>
      {selected.map((s) => (
        <span
          key={s.url}
          className="inline-flex max-w-80 items-center gap-2 rounded-full border border-edge2 bg-panel py-1 pl-2.5 pr-1.5 text-[13px]"
        >
          <span
            className="h-2.5 w-2.5 shrink-0 rounded-sm"
            style={{ background: SLOT_COLORS[s.slot] }}
          />
          <span className="truncate font-medium text-ink">{shortPath(s.url)}</span>
          <button
            type="button"
            aria-label={`Remove ${shortPath(s.url)}`}
            onClick={() => onRemove(s.url)}
            className="h-5 w-5 shrink-0 cursor-pointer rounded-full text-sub hover:bg-panel2 hover:text-ink"
          >
            ×
          </button>
        </span>
      ))}
      {selected.length === 0 && (
        <span className="text-xs text-faint">
          Showing all pages — tick up to {MAX_COMPARE} pages below to compare.
        </span>
      )}
    </div>
  );
}

function MetricTiles({
  metric,
  onMetric,
  range,
  current,
  previous,
}: {
  metric: MetricKey;
  onMetric: (m: MetricKey) => void;
  range: number;
  current?: Totals;
  previous?: Totals;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {(Object.keys(METRICS) as MetricKey[]).map((key) => {
        const mt = METRICS[key];
        const cur = current?.[key] ?? null;
        const prev = previous?.[key] ?? null;
        const diff = cur !== null && prev !== null ? cur - prev : null;
        const good = diff !== null && (mt.invert ? diff < 0 : diff > 0);
        const active = metric === key;
        return (
          <button
            key={key}
            type="button"
            aria-pressed={active}
            onClick={() => onMetric(key)}
            className={`cursor-pointer rounded-2xl border bg-panel p-4 text-left transition-colors hover:bg-panel2 ${
              active ? "" : "border-edge"
            }`}
            style={active ? { borderColor: mt.color, boxShadow: `inset 0 3px 0 ${mt.color}` } : undefined}
          >
            <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-sub">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: mt.color }} />
              {mt.name}
            </p>
            <p className="mt-1.5 font-display text-2xl text-ink">
              {cur === null ? "—" : mt.fmt(cur)}
            </p>
            <p className={`mt-0.5 text-xs ${diff === null ? "text-faint" : good ? "text-good" : "text-bad"}`}>
              {diff === null || prev === null || Math.abs(prev) < 1e-9
                ? "no prior data"
                : `${diff >= 0 ? "▲" : "▼"} ${Math.abs((diff / Math.abs(prev)) * 100).toFixed(0)}% vs previous ${range}d`}
            </p>
          </button>
        );
      })}
    </div>
  );
}

function ChartCard({
  metric,
  series,
  selected,
}: {
  metric: MetricKey;
  series: SeriesResponse | null;
  selected: SelectedPage[];
}) {
  const mt = METRICS[metric];
  const chartSeries: ChartSeries[] = useMemo(() => {
    if (!series?.series.length) return [];
    return series.series.map((g) => {
      const match = g.page
        ? selected.find((s) => stripSlash(s.url) === stripSlash(g.page as string))
        : undefined;
      return {
        name: g.page ? shortPath(g.page) : "All pages",
        color: g.page ? SLOT_COLORS[match?.slot ?? 0] : mt.color,
        values: g.points.map((p) => p[metric]),
      };
    });
  }, [series, selected, metric, mt.color]);

  const labels = series?.series[0]?.points.map((p) => p.day) ?? [];

  return (
    <Card>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h2 className="font-display text-lg text-ink">
          {mt.name}{" "}
          <span className="text-sub">
            · {selected.length === 0
              ? "all pages"
              : selected.length === 1
                ? shortPath(selected[0].url)
                : `${selected.length} pages compared`}
          </span>
        </h2>
        <span className="text-xs text-faint">
          {mt.invert ? "per day · lower is better" : "per day"}
        </span>
      </div>
      {!series && <Spinner />}
      {series && chartSeries.length > 0 && (
        <LineChart labels={labels} series={chartSeries} format={mt.fmt} invert={mt.invert} />
      )}
      {series && chartSeries.length === 0 && (
        <p className="py-8 text-center text-sm text-sub">No data in this window.</p>
      )}
    </Card>
  );
}

function SortHeader({
  label,
  sortKey,
  sort,
  onSort,
  align = "right",
}: {
  label: string;
  sortKey: SortKey;
  sort: { key: SortKey; dir: "asc" | "desc" };
  onSort: (key: SortKey) => void;
  align?: "left" | "right";
}) {
  const active = sort.key === sortKey;
  return (
    <th
      aria-sort={active ? (sort.dir === "asc" ? "ascending" : "descending") : undefined}
      className={`pb-2 pr-3 font-medium ${align === "left" ? "text-left" : "text-right"}`}
    >
      <button
        type="button"
        onClick={() => onSort(sortKey)}
        className={`cursor-pointer whitespace-nowrap uppercase tracking-wide hover:text-accent ${active ? "text-ink" : ""}`}
      >
        {label}
        {active ? (sort.dir === "asc" ? " ▲" : " ▼") : ""}
      </button>
    </th>
  );
}

function PagesTable({
  siteId,
  range,
  selected,
  onToggle,
  onInspected,
}: {
  siteId: string | null;
  range: number;
  selected: SelectedPage[];
  onToggle: (url: string) => void;
  onInspected: () => void;
}) {
  const [sort, setSort] = useState<{ key: SortKey; dir: "asc" | "desc" }>({
    key: "clicks",
    dir: "desc",
  });
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");
  const [inspecting, setInspecting] = useState<string | null>(null);
  const [inspectError, setInspectError] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim());
      setOffset(0);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { data, refresh } = useApi<{ rows: PageRow[]; total: number }>(
    `/api/v1/site/search-data/pages?days=${range}&sort=${sort.key}&dir=${sort.dir}&limit=${PAGE_SIZE}&offset=${offset}${search ? `&search=${encodeURIComponent(search)}` : ""}`,
  );

  const onSort = (key: SortKey) => {
    setSort((prev) =>
      prev.key === key
        ? { key, dir: prev.dir === "asc" ? "desc" : "asc" }
        : { key, dir: ASC_FIRST.has(key) ? "asc" : "desc" },
    );
    setOffset(0);
  };

  const inspect = async (url: string) => {
    setInspecting(url);
    setInspectError(null);
    const res = await inspectPageUrl(siteId, url);
    setInspecting(null);
    if (res?.error) setInspectError(res.error);
    else {
      await refresh();
      onInspected();
    }
  };

  const isSelected = (url: string) =>
    selected.some((s) => stripSlash(s.url) === stripSlash(url));
  const slotOf = (url: string) =>
    selected.find((s) => stripSlash(s.url) === stripSlash(url))?.slot;
  const atCap = selected.length >= MAX_COMPARE;
  const canInspect = canInspectUrls();

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-lg text-ink">Pages · last {range} days</h2>
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Filter pages…"
          aria-label="Filter pages"
          className="rounded-lg border border-edge2 bg-panel px-3 py-1.5 text-[13px] text-ink placeholder:text-faint focus:border-accent focus:outline-none"
        />
      </div>
      {inspectError && (
        <p className="mb-2 rounded-lg border border-bad/40 bg-bad/5 p-2 text-xs text-bad">
          {inspectError}
        </p>
      )}
      {!data && <Spinner />}
      {data && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-sub">
                  <th className="w-8 pb-2" />
                  <SortHeader label="Page" sortKey="page" sort={sort} onSort={onSort} align="left" />
                  <SortHeader label="Clicks" sortKey="clicks" sort={sort} onSort={onSort} />
                  <SortHeader label="Impr." sortKey="impressions" sort={sort} onSort={onSort} />
                  <SortHeader label="CTR" sortKey="ctr" sort={sort} onSort={onSort} />
                  <SortHeader label="Pos." sortKey="position" sort={sort} onSort={onSort} />
                  <SortHeader label="Index" sortKey="index" sort={sort} onSort={onSort} align="left" />
                  <SortHeader label="Crawled" sortKey="crawled" sort={sort} onSort={onSort} />
                  <SortHeader label="Inspected" sortKey="inspected" sort={sort} onSort={onSort} />
                  {canInspect && <th className="w-8 pb-2" />}
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => {
                  const sel = isSelected(r.page);
                  const slot = slotOf(r.page);
                  const idx = r.indexState ? INDEX_META[r.indexState] : null;
                  const mismatch =
                    !!r.googleCanonical && stripSlash(r.googleCanonical) !== stripSlash(r.page);
                  return (
                    <tr
                      key={r.page}
                      className={`border-t border-edge ${sel ? "bg-accent-soft" : "hover:bg-panel2/50"}`}
                    >
                      <td className="py-2 pl-1 pr-2">
                        <input
                          type="checkbox"
                          className="h-3.5 w-3.5 cursor-pointer accent-accent"
                          checked={sel}
                          disabled={!sel && atCap}
                          aria-label={`Select ${shortPath(r.page)}`}
                          onChange={() => onToggle(r.page)}
                        />
                      </td>
                      <td
                        className={`max-w-72 truncate py-2 pr-3 text-ink ${sel ? "font-medium" : ""}`}
                        style={sel && slot !== undefined ? { boxShadow: `inset 3px 0 0 ${SLOT_COLORS[slot]}` } : undefined}
                        title={r.page}
                      >
                        {shortPath(r.page)}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{num(r.clicks)}</td>
                      <td className="py-2 pr-3 text-right tabular-nums text-sub">
                        {num(r.impressions)}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums text-sub">
                        {r.impressions > 0 ? `${((r.clicks / r.impressions) * 100).toFixed(1)}%` : "—"}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{num(r.position, 1)}</td>
                      <td
                        className="whitespace-nowrap py-2 pr-3"
                        title={r.coverageState ?? "Never inspected"}
                      >
                        <span
                          className="mr-1.5 inline-block h-2 w-2 rounded-sm align-baseline"
                          style={{ background: idx?.color ?? "#c3c2b7" }}
                        />
                        <span className="text-sub">{idx?.label ?? "—"}</span>
                        {mismatch && (
                          <span
                            className="ml-1 cursor-help font-semibold text-bad"
                            title={`Google chose a different canonical: ${r.googleCanonical}`}
                          >
                            ≠
                          </span>
                        )}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums text-sub">
                        {daysAgo(r.lastCrawlTime)}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums text-sub">
                        {daysAgo(r.indexCheckedAt)}
                      </td>
                      {canInspect && (
                        <td className="py-2 text-center">
                          <button
                            type="button"
                            title="Re-inspect this URL now"
                            aria-label={`Re-inspect ${shortPath(r.page)} now`}
                            disabled={inspecting !== null}
                            onClick={() => void inspect(r.page)}
                            className="cursor-pointer rounded-md p-1 text-sub hover:bg-panel2 hover:text-accent disabled:opacity-40"
                          >
                            <RotateCw
                              size={14}
                              className={inspecting === r.page ? "animate-spin" : ""}
                            />
                          </button>
                        </td>
                      )}
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <Pager
            offset={offset}
            shown={data.rows.length}
            total={data.total}
            note={atCap ? `selection full (${MAX_COMPARE})` : undefined}
            unit="pages"
            onPrev={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            onNext={() => setOffset(offset + PAGE_SIZE)}
          />
        </>
      )}
    </Card>
  );
}

function QueriesTable({ range, selected }: { range: number; selected: SelectedPage[] }) {
  const [offset, setOffset] = useState(0);
  const pagesParam = selected.map((s) => s.url).join(",");
  const [scopeKey, setScopeKey] = useState(pagesParam + range);
  if (scopeKey !== pagesParam + range) {
    setScopeKey(pagesParam + range);
    setOffset(0);
  }

  const { data } = useApi<{ rows: QueryRow[]; total: number }>(
    `/api/v1/site/search-data/queries?days=${range}&limit=${QUERY_PAGE_SIZE}&offset=${offset}${pagesParam ? `&pages=${encodeURIComponent(pagesParam)}` : ""}`,
  );

  return (
    <Card>
      <h2 className="mb-3 font-display text-lg text-ink">Top queries</h2>
      {!data && <Spinner />}
      {data && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-sub">
                  <th className="pb-2 pr-3 font-medium">Query</th>
                  <th className="pb-2 pr-3 font-medium">Page</th>
                  <th className="pb-2 pr-3 text-right font-medium">Clicks</th>
                  <th className="pb-2 pr-3 text-right font-medium">Impr.</th>
                  <th className="pb-2 text-right font-medium">Pos.</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => (
                  <tr key={r.query} className="border-t border-edge">
                    <td className="py-2 pr-3 text-ink">{r.query}</td>
                    <td className="max-w-56 truncate py-2 pr-3 text-sub" title={r.page ?? undefined}>
                      {r.page ? shortPath(r.page) : "—"}
                    </td>
                    <td className="py-2 pr-3 text-right tabular-nums">{num(r.clicks)}</td>
                    <td className="py-2 pr-3 text-right tabular-nums text-sub">
                      {num(r.impressions)}
                    </td>
                    <td className="py-2 text-right tabular-nums">{num(r.position, 1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pager
            offset={offset}
            shown={data.rows.length}
            total={data.total}
            unit={selected.length ? `queries · ${selected.length} selected page(s)` : "queries · all pages"}
            onPrev={() => setOffset(Math.max(0, offset - QUERY_PAGE_SIZE))}
            onNext={() => setOffset(offset + QUERY_PAGE_SIZE)}
          />
        </>
      )}
    </Card>
  );
}

function Pager({
  offset,
  shown,
  total,
  unit,
  note,
  onPrev,
  onNext,
}: {
  offset: number;
  shown: number;
  total: number;
  unit: string;
  note?: string;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div className="mt-3 flex items-center justify-between gap-3 border-t border-edge pt-2.5">
      <span className="text-xs text-faint">
        {total === 0 ? "Nothing to show." : `${offset + 1}–${offset + shown} of ${total} ${unit}`}
        {note ? ` · ${note}` : ""}
      </span>
      <span className="flex gap-1.5">
        <Button size="sm" variant="ghost" disabled={offset === 0} onClick={onPrev}>
          ‹ Prev
        </Button>
        <Button size="sm" variant="ghost" disabled={offset + shown >= total} onClick={onNext}>
          Next ›
        </Button>
      </span>
    </div>
  );
}

function ConnectGscCard({
  onConnect,
  onConnected,
}: {
  onConnect: () => Promise<Record<string, unknown> | { error: string } | undefined> | undefined;
  onConnected: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  return (
    <Card className="border-warn/40 bg-warn/5 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-ink">Search Console is not connected</p>
          <p className="mt-0.5 text-sm text-sub">
            Syncing search data and checking index status need a Google account with access to
            this site. The connection stays on this device.
          </p>
          {error && <p className="mt-1 text-sm text-bad">{error}</p>}
        </div>
        <Button
          disabled={busy}
          onClick={async () => {
            setBusy(true);
            setError(null);
            const res = await onConnect();
            setBusy(false);
            if (!res) return;
            if ("error" in res) setError(String(res.error));
            else onConnected();
          }}
        >
          {busy && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
          {busy ? "Connecting…" : "Connect Search Console"}
        </Button>
      </div>
    </Card>
  );
}

function SyncProgressBar({ sync }: { sync: ReturnType<typeof useSearchSync> }) {
  const p = sync.progress;
  const done = (p?.phase === "inspect" ? p.pagesInspected : p?.daysDone) ?? 0;
  const total = (p?.phase === "inspect" ? p.pagesTotal : p?.daysTotal) ?? 0;
  const label =
    p?.phase === "inspect"
      ? `Checking index status — ${done} of ${total || "…"} pages`
      : total
        ? `Importing search data — day ${done} of ${total}${p?.day ? ` (${p.day})` : ""}`
        : "Importing search data…";
  return (
    <div className="flex items-center gap-3">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-panel2">
        <div
          className={`h-full rounded-full bg-accent transition-[width] duration-500 ${total ? "" : "animate-pulse"}`}
          style={{ width: total ? `${Math.max(2, (done / total) * 100)}%` : "100%" }}
        />
      </div>
      <span className="shrink-0 text-xs text-sub">{label}</span>
      <button
        className="shrink-0 cursor-pointer text-xs text-sub underline-offset-2 hover:text-ink hover:underline disabled:opacity-50"
        onClick={() => void sync.stop()}
        disabled={sync.stopping}
      >
        {sync.stopping ? "Stopping…" : "Stop"}
      </button>
    </div>
  );
}

function PropertyPicker({
  candidates,
  onPicked,
}: {
  candidates: GscProperty[];
  onPicked: (property: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <Card>
      <p className="text-sm font-medium text-ink">Which property is authoritative?</p>
      <p className="mt-1 text-sm text-sub">
        Search Console has more than one property for this site. Domain and URL-prefix
        properties report different numbers — pick the one to trust.
      </p>
      <div className="mt-3 flex flex-col gap-2">
        {candidates.map((c) => (
          <button
            key={c.siteUrl}
            disabled={busy}
            onClick={() => {
              setBusy(true);
              onPicked(c.siteUrl);
            }}
            className="flex items-center justify-between rounded-lg border border-edge2 px-3 py-2 text-left text-sm text-ink transition-colors hover:bg-panel2 disabled:opacity-50"
          >
            <span>{c.siteUrl}</span>
            <Badge>{c.permissionLevel}</Badge>
          </button>
        ))}
      </div>
    </Card>
  );
}

function StrikingDistance() {
  const { data } = useApi<{ rows: QueryRow[]; total: number }>(
    "/api/v1/site/search-data/queries?view=striking&limit=8",
  );
  if (!data || data.rows.length === 0) return null;
  return (
    <Card className="border-accent/40">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-lg text-ink">
          Striking distance — {data.total} quer{data.total === 1 ? "y" : "ies"} just outside the
          top ten
        </h2>
        <span className="text-xs text-faint">28-day averages</span>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-sub">
            <th className="pb-2 pr-3 font-medium">Query</th>
            <th className="pb-2 pr-3 font-medium">Page</th>
            <th className="pb-2 pr-3 font-medium">Pos</th>
            <th className="pb-2 pr-3 font-medium">Impressions</th>
            <th className="pb-2 font-medium">Inlinks</th>
          </tr>
        </thead>
        <tbody>
          {data.rows.map((r) => (
            <tr key={r.query} className="border-t border-edge">
              <td className="py-2 pr-3 text-ink">{r.query}</td>
              <td className="py-2 pr-3 text-sub">{r.page ? shortPath(r.page) : "—"}</td>
              <td className="py-2 pr-3 tabular-nums">{num(r.position, 1)}</td>
              <td className="py-2 pr-3 tabular-nums text-sub">{num(r.impressions)}</td>
              <td className="py-2 tabular-nums">
                {r.inlinks === null ? (
                  "—"
                ) : r.inlinks <= 2 ? (
                  <Badge tone="warn">{r.inlinks} — needs links</Badge>
                ) : (
                  r.inlinks
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-3 text-xs text-faint">
        A page sitting just outside the top ten with two internal links needs something entirely
        different from one sitting there with forty — the Structure view has the link insertions.
      </p>
    </Card>
  );
}
