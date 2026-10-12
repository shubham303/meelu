"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowLeft, BarChart3, Loader2 } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Badge, Button, Card, EmptyState, PageHeader, Spinner } from "@demo/components/ui";
import { api, useApi, useCurrentSite } from "@demo/lib/use-api";
import { SiteAskButton } from "../site-ask";
import * as chips from "@demo/features/prompt-chips/site";
import { LineChart, type ChartSeries } from "../search/line-chart";
import { useGaConnected, useTrafficSync, type GaAccount } from "./sync";

interface Totals {
  users: number;
  newUsers: number;
  sessions: number;
  engagedSessions: number;
  pageViews: number;
  engagementSeconds: number;
  keyEvents: number;
  revenue: number;
}

interface ChannelTotals {
  sessions: number;
  engagedSessions: number;
  keyEvents: number;
  revenue: number;
}

interface RollupRow {
  key: string[];
  sessions: number;
  prevSessions: number;
  users: number;
  engagedSessions: number;
  keyEvents: number;
  revenue: number;
}

interface Overview {
  connected: boolean;
  property: string | null;
  hasData: boolean;
  days: number;
  firstDay: string | null;
  lastDay: string | null;
  totals: { current: Totals; previous: Totals };
  organic: { current: ChannelTotals; previous: ChannelTotals };
  channels: RollupRow[];
  active?: { id: string } | null;
}

interface SeriesPoint {
  day: string;
  users: number;
  sessions: number;
  engagedSessions: number;
  pageViews: number;
  keyEvents: number;
  revenue: number;
  organicSessions: number;
}

interface LandingRow {
  landingPage: string;
  title: string | null;
  sessions: number;
  prevSessions: number;
  engagedSessions: number;
  keyEvents: number;
  revenue: number;
}

interface ContentRow {
  pagePath: string;
  views: number;
  prevViews: number;
  users: number;
  engagementSeconds: number;
  keyEvents: number;
}

type MetricKey = "sessions" | "users" | "keyEvents" | "revenue";

const RANGES = [28, 90, 180];
const PAGE_SIZE = 20;
const ORGANIC_COLOR = "#1baf7a";

const METRICS: Record<MetricKey, { name: string; color: string; fmt: (v: number) => string }> = {
  sessions: { name: "Sessions", color: "#2563eb", fmt: (v) => compact(v) },
  users: { name: "Users", color: "#eb6834", fmt: (v) => compact(v) },
  keyEvents: { name: "Key events", color: "#d97706", fmt: (v) => compact(v) },
  revenue: { name: "Revenue", color: "#d55181", fmt: (v) => money(v) },
};

const BREAKDOWNS = [
  { by: "source", label: "Sources", column: "Source / medium", unit: "Sessions" },
  { by: "event", label: "Events", column: "Event", unit: "Count" },
  { by: "country", label: "Countries", column: "Country", unit: "Sessions" },
  { by: "device", label: "Devices", column: "Device", unit: "Sessions" },
  { by: "os", label: "Systems", column: "Operating system", unit: "Sessions" },
  { by: "browser", label: "Browsers", column: "Browser", unit: "Sessions" },
] as const;

type BreakdownKey = (typeof BREAKDOWNS)[number]["by"];

function compact(v: number): string {
  if (v >= 1_000_000) return `${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 10_000) return `${(v / 1000).toFixed(1)}K`;
  return Math.round(v).toLocaleString("en-US");
}

function money(v: number): string {
  if (v >= 10_000) return compact(v);
  return v.toLocaleString("en-US", { maximumFractionDigits: 2 });
}

function num(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined) return "—";
  return n.toLocaleString(undefined, { maximumFractionDigits: digits });
}

function pct(part: number, whole: number): string {
  return whole > 0 ? `${((part / whole) * 100).toFixed(0)}%` : "—";
}

function delta(cur: number, prev: number): { text: string; good: boolean } | null {
  if (prev <= 0) return null;
  const d = ((cur - prev) / prev) * 100;
  return { text: `${d >= 0 ? "▲" : "▼"} ${Math.abs(d).toFixed(0)}%`, good: d >= 0 };
}

export default function TrafficPage() {
  const siteId = useCurrentSite();
  const [range, setRange] = useState(90);
  const {
    data: overview,
    error: overviewError,
    refresh,
  } = useApi<Overview>(`/api/v1/site/traffic?days=${range}`);
  const sync = useTrafficSync(siteId, refresh, overview?.active?.id ?? null);
  const ga = useGaConnected();

  const [metric, setMetric] = useState<MetricKey>("sessions");

  const { data: series } = useApi<{ points: SeriesPoint[] }>(
    overview?.hasData ? `/api/v1/site/traffic/series?days=${range}` : null,
  );

  return (
    <PageEnter>
      <Link
        href="/demo/dashboard/site"
        className="mb-3 inline-flex items-center gap-1.5 text-sm text-sub hover:text-ink"
      >
        <ArrowLeft size={14} /> Site
      </Link>
      <PageHeader
        title="Traffic"
        description={
          overview?.hasData
            ? `Everything Google Analytics measured — sessions, channels, pages, events, kept since ${overview.firstDay}. Data through ${overview.lastDay}.`
            : "Everything Google Analytics measures, kept here. Connect Analytics and the desk imports 16 months of it."
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
              title="Ask — Traffic"
              hint="Ask about the measured traffic — where it comes from, what converts, what changed."
              suggestions={chips.traffic()}
              onRan={refresh}
            />
          </div>
        }
      />

      <div className="space-y-4">
        {ga.connected === false && (
          <ConnectGaCard onConnect={sync.connectGa4} onConnected={ga.markConnected} />
        )}
        {sync.running && <SyncProgressBar sync={sync} />}
        {sync.error && !sync.candidates && (
          <Card className="border-bad/40 bg-bad/5 p-3 text-sm">{sync.error}</Card>
        )}
        {sync.candidates && (
          <PropertyPicker
            candidates={sync.candidates}
            onPicked={async (property) => {
              await api("/api/v1/site/traffic/property", {
                method: "PUT",
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
            icon={BarChart3}
            title="No traffic data yet"
            hint={
              sync.canSync
                ? "The first sync imports 16 months of Analytics data — sessions, channels, landing pages, events, countries and devices, day by day. It runs from this machine and costs nothing."
                : "Syncing runs in the Meelu app, where the Analytics connection lives. Open the app to import 16 months of data."
            }
            action={
              sync.canSync ? (
                <Button onClick={() => void sync.start()}>Import 16 months of traffic data</Button>
              ) : undefined
            }
          />
        )}

        {overview?.hasData && (
          <>
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="inline-flex overflow-hidden rounded-lg border border-edge2 bg-panel">
                {RANGES.map((d, i) => (
                  <button
                    key={d}
                    type="button"
                    aria-pressed={range === d}
                    onClick={() => setRange(d)}
                    className={`cursor-pointer px-3 py-1.5 text-[13px] transition-colors ${
                      range === d
                        ? "bg-accent-soft font-medium text-accent"
                        : "text-sub hover:bg-panel2"
                    } ${i > 0 ? "border-l border-edge" : ""}`}
                  >
                    {d} days
                  </button>
                ))}
              </div>
              <span className="text-xs text-faint">
                Organic Search: {compact(overview.organic.current.sessions)} of{" "}
                {compact(overview.totals.current.sessions)} sessions (
                {pct(overview.organic.current.sessions, overview.totals.current.sessions)})
              </span>
            </div>

            <MetricTiles metric={metric} onMetric={setMetric} range={range} overview={overview} />
            <ChartCard metric={metric} points={series?.points ?? null} loading={!series} />
            <ChannelsCard rows={overview.channels} totalSessions={overview.totals.current.sessions} range={range} />
            <LandingPagesTable range={range} channels={overview.channels.map((c) => c.key[0])} />
            <ContentPagesTable range={range} />
            <BreakdownCard range={range} />

            <p className="text-xs text-faint">
              Property {overview.property} — chosen by you. Numbers are Google Analytics daily
              rollups; key events are what GA4 used to call conversions.
            </p>
          </>
        )}
      </div>
    </PageEnter>
  );
}

function MetricTiles({
  metric,
  onMetric,
  range,
  overview,
}: {
  metric: MetricKey;
  onMetric: (m: MetricKey) => void;
  range: number;
  overview: Overview;
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {(Object.keys(METRICS) as MetricKey[]).map((key) => {
        const mt = METRICS[key];
        const cur = overview.totals.current[key];
        const prev = overview.totals.previous[key];
        const d = delta(cur, prev);
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
            style={
              active ? { borderColor: mt.color, boxShadow: `inset 0 3px 0 ${mt.color}` } : undefined
            }
          >
            <p className="flex items-center gap-2 text-xs uppercase tracking-wide text-sub">
              <span className="h-2.5 w-2.5 rounded-sm" style={{ background: mt.color }} />
              {mt.name}
            </p>
            <p className="mt-1.5 font-display text-2xl text-ink">{mt.fmt(cur)}</p>
            <p className={`mt-0.5 text-xs ${d === null ? "text-faint" : d.good ? "text-good" : "text-bad"}`}>
              {d === null ? "no prior data" : `${d.text} vs previous ${range}d`}
            </p>
          </button>
        );
      })}
    </div>
  );
}

function ChartCard({
  metric,
  points,
  loading,
}: {
  metric: MetricKey;
  points: SeriesPoint[] | null;
  loading: boolean;
}) {
  const mt = METRICS[metric];
  const chartSeries: ChartSeries[] = useMemo(() => {
    if (!points?.length) return [];
    const all: ChartSeries = {
      name: mt.name,
      color: mt.color,
      values: points.map((p) => p[metric]),
    };
    if (metric !== "sessions") return [all];
    return [
      all,
      {
        name: "Organic Search",
        color: ORGANIC_COLOR,
        values: points.map((p) => p.organicSessions),
      },
    ];
  }, [points, metric, mt]);

  return (
    <Card>
      <div className="mb-2 flex items-baseline justify-between gap-3">
        <h2 className="font-display text-lg text-ink">
          {mt.name}
          {metric === "sessions" && <span className="text-sub"> · all vs Organic Search</span>}
        </h2>
        <span className="text-xs text-faint">per day</span>
      </div>
      {loading && <Spinner />}
      {!loading && chartSeries.length > 0 && (
        <LineChart
          labels={points?.map((p) => p.day) ?? []}
          series={chartSeries}
          format={mt.fmt}
          invert={false}
        />
      )}
      {!loading && chartSeries.length === 0 && (
        <p className="py-8 text-center text-sm text-sub">No data in this window.</p>
      )}
    </Card>
  );
}

function ChannelsCard({
  rows,
  totalSessions,
  range,
}: {
  rows: RollupRow[];
  totalSessions: number;
  range: number;
}) {
  if (rows.length === 0) return null;
  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-lg text-ink">Channels · last {range} days</h2>
        <span className="text-xs text-faint">where sessions come from</span>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-xs uppercase tracking-wide text-sub">
              <th className="pb-2 pr-3 font-medium">Channel</th>
              <th className="pb-2 pr-3 text-right font-medium">Sessions</th>
              <th className="pb-2 pr-3 text-right font-medium">Δ</th>
              <th className="pb-2 pr-3 text-right font-medium">Share</th>
              <th className="pb-2 pr-3 text-right font-medium">Engaged</th>
              <th className="pb-2 pr-3 text-right font-medium">Key events</th>
              <th className="pb-2 text-right font-medium">Revenue</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const d = delta(r.sessions, r.prevSessions);
              return (
                <tr key={r.key.join("/")} className="border-t border-edge">
                  <td className="py-2 pr-3 text-ink">{r.key[0]}</td>
                  <td className="py-2 pr-3 text-right tabular-nums">{num(r.sessions)}</td>
                  <td
                    className={`py-2 pr-3 text-right text-xs ${d === null ? "text-faint" : d.good ? "text-good" : "text-bad"}`}
                  >
                    {d?.text ?? "—"}
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums text-sub">
                    {pct(r.sessions, totalSessions)}
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums text-sub">
                    {pct(r.engagedSessions, r.sessions)}
                  </td>
                  <td className="py-2 pr-3 text-right tabular-nums">{num(r.keyEvents)}</td>
                  <td className="py-2 text-right tabular-nums text-sub">{money(r.revenue)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

type LandingSort = "sessions" | "keyEvents" | "revenue" | "delta";

function LandingPagesTable({ range, channels }: { range: number; channels: string[] }) {
  const [sort, setSort] = useState<LandingSort>("sessions");
  const [channel, setChannel] = useState("");
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim());
      setOffset(0);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { data } = useApi<{ pages: LandingRow[]; total: number }>(
    `/api/v1/site/traffic/pages?days=${range}&sort=${sort}&limit=${PAGE_SIZE}&offset=${offset}` +
      (channel ? `&channel=${encodeURIComponent(channel)}` : "") +
      (search ? `&search=${encodeURIComponent(search)}` : ""),
  );

  const header = (label: string, key: LandingSort) => (
    <th className="pb-2 pr-3 text-right font-medium">
      <button
        type="button"
        onClick={() => {
          setSort(key);
          setOffset(0);
        }}
        className={`cursor-pointer whitespace-nowrap uppercase tracking-wide hover:text-accent ${sort === key ? "text-ink" : ""}`}
      >
        {label}
        {sort === key ? " ▼" : ""}
      </button>
    </th>
  );

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-lg text-ink">Landing pages · last {range} days</h2>
        <div className="flex items-center gap-2">
          <select
            value={channel}
            onChange={(e) => {
              setChannel(e.target.value);
              setOffset(0);
            }}
            aria-label="Filter by channel"
            className="rounded-lg border border-edge2 bg-panel px-2 py-1.5 text-[13px] text-ink focus:border-accent focus:outline-none"
          >
            <option value="">All channels</option>
            {channels.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <input
            type="search"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            placeholder="Filter pages…"
            aria-label="Filter landing pages"
            className="rounded-lg border border-edge2 bg-panel px-3 py-1.5 text-[13px] text-ink placeholder:text-faint focus:border-accent focus:outline-none"
          />
        </div>
      </div>
      {!data && <Spinner />}
      {data && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-sub">
                  <th className="pb-2 pr-3 text-left font-medium uppercase tracking-wide">
                    Landing page
                  </th>
                  {header("Sessions", "sessions")}
                  {header("Δ", "delta")}
                  <th className="pb-2 pr-3 text-right font-medium uppercase tracking-wide">
                    Engaged
                  </th>
                  {header("Key events", "keyEvents")}
                  {header("Revenue", "revenue")}
                </tr>
              </thead>
              <tbody>
                {data.pages.map((r) => {
                  const d = delta(r.sessions, r.prevSessions);
                  return (
                    <tr key={r.landingPage} className="border-t border-edge hover:bg-panel2/50">
                      <td
                        className="max-w-72 truncate py-2 pr-3 text-ink"
                        title={r.title ?? r.landingPage}
                      >
                        {r.landingPage}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{num(r.sessions)}</td>
                      <td
                        className={`py-2 pr-3 text-right text-xs ${d === null ? "text-faint" : d.good ? "text-good" : "text-bad"}`}
                      >
                        {d?.text ?? "—"}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums text-sub">
                        {pct(r.engagedSessions, r.sessions)}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{num(r.keyEvents)}</td>
                      <td className="py-2 text-right tabular-nums text-sub">{money(r.revenue)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <Pager
            offset={offset}
            shown={data.pages.length}
            total={data.total}
            unit="landing pages"
            onPrev={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            onNext={() => setOffset(offset + PAGE_SIZE)}
          />
        </>
      )}
    </Card>
  );
}

type ContentSort = "views" | "users" | "keyEvents" | "delta";

function ContentPagesTable({ range }: { range: number }) {
  const [sort, setSort] = useState<ContentSort>("views");
  const [offset, setOffset] = useState(0);
  const [searchInput, setSearchInput] = useState("");
  const [search, setSearch] = useState("");

  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim());
      setOffset(0);
    }, 300);
    return () => clearTimeout(t);
  }, [searchInput]);

  const { data } = useApi<{ pages: ContentRow[]; total: number }>(
    `/api/v1/site/traffic/content?days=${range}&sort=${sort}&limit=${PAGE_SIZE}&offset=${offset}` +
      (search ? `&search=${encodeURIComponent(search)}` : ""),
  );

  const header = (label: string, key: ContentSort) => (
    <th className="pb-2 pr-3 text-right font-medium">
      <button
        type="button"
        onClick={() => {
          setSort(key);
          setOffset(0);
        }}
        className={`cursor-pointer whitespace-nowrap uppercase tracking-wide hover:text-accent ${sort === key ? "text-ink" : ""}`}
      >
        {label}
        {sort === key ? " ▼" : ""}
      </button>
    </th>
  );

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-lg text-ink">Pages viewed · last {range} days</h2>
        <input
          type="search"
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Filter pages…"
          aria-label="Filter viewed pages"
          className="rounded-lg border border-edge2 bg-panel px-3 py-1.5 text-[13px] text-ink placeholder:text-faint focus:border-accent focus:outline-none"
        />
      </div>
      {!data && <Spinner />}
      {data && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-xs text-sub">
                  <th className="pb-2 pr-3 text-left font-medium uppercase tracking-wide">Page</th>
                  {header("Views", "views")}
                  {header("Δ", "delta")}
                  {header("Users", "users")}
                  <th className="pb-2 pr-3 text-right font-medium uppercase tracking-wide">
                    Avg. time
                  </th>
                  {header("Key events", "keyEvents")}
                </tr>
              </thead>
              <tbody>
                {data.pages.map((r) => {
                  const d = delta(r.views, r.prevViews);
                  const secs = r.users > 0 ? r.engagementSeconds / r.users : 0;
                  return (
                    <tr key={r.pagePath} className="border-t border-edge hover:bg-panel2/50">
                      <td className="max-w-72 truncate py-2 pr-3 text-ink" title={r.pagePath}>
                        {r.pagePath}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{num(r.views)}</td>
                      <td
                        className={`py-2 pr-3 text-right text-xs ${d === null ? "text-faint" : d.good ? "text-good" : "text-bad"}`}
                      >
                        {d?.text ?? "—"}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums text-sub">{num(r.users)}</td>
                      <td className="py-2 pr-3 text-right tabular-nums text-sub">
                        {secs > 0 ? `${Math.round(secs)}s` : "—"}
                      </td>
                      <td className="py-2 text-right tabular-nums">{num(r.keyEvents)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <Pager
            offset={offset}
            shown={data.pages.length}
            total={data.total}
            unit="pages"
            onPrev={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            onNext={() => setOffset(offset + PAGE_SIZE)}
          />
        </>
      )}
    </Card>
  );
}

function BreakdownCard({ range }: { range: number }) {
  const [by, setBy] = useState<BreakdownKey>("source");
  const [offset, setOffset] = useState(0);
  const meta = BREAKDOWNS.find((b) => b.by === by) ?? BREAKDOWNS[0];

  const { data } = useApi<{ rows: RollupRow[]; total: number }>(
    `/api/v1/site/traffic/breakdown?by=${by}&days=${range}&limit=${PAGE_SIZE}&offset=${offset}`,
  );

  return (
    <Card>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-lg text-ink">Breakdown · last {range} days</h2>
        <div className="inline-flex overflow-hidden rounded-lg border border-edge2 bg-panel">
          {BREAKDOWNS.map((b, i) => (
            <button
              key={b.by}
              type="button"
              aria-pressed={by === b.by}
              onClick={() => {
                setBy(b.by);
                setOffset(0);
              }}
              className={`cursor-pointer px-3 py-1.5 text-[13px] transition-colors ${
                by === b.by ? "bg-accent-soft font-medium text-accent" : "text-sub hover:bg-panel2"
              } ${i > 0 ? "border-l border-edge" : ""}`}
            >
              {b.label}
            </button>
          ))}
        </div>
      </div>
      {!data && <Spinner />}
      {data && (
        <>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-sub">
                  <th className="pb-2 pr-3 font-medium">{meta.column}</th>
                  <th className="pb-2 pr-3 text-right font-medium">{meta.unit}</th>
                  <th className="pb-2 pr-3 text-right font-medium">Δ</th>
                  <th className="pb-2 pr-3 text-right font-medium">Users</th>
                  <th className="pb-2 pr-3 text-right font-medium">Key events</th>
                  <th className="pb-2 text-right font-medium">Revenue</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.map((r) => {
                  const d = delta(r.sessions, r.prevSessions);
                  return (
                    <tr key={r.key.join("/")} className="border-t border-edge">
                      <td className="max-w-72 truncate py-2 pr-3 text-ink" title={r.key.join(" / ")}>
                        {r.key.join(" / ")}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums">{num(r.sessions)}</td>
                      <td
                        className={`py-2 pr-3 text-right text-xs ${d === null ? "text-faint" : d.good ? "text-good" : "text-bad"}`}
                      >
                        {d?.text ?? "—"}
                      </td>
                      <td className="py-2 pr-3 text-right tabular-nums text-sub">{num(r.users)}</td>
                      <td className="py-2 pr-3 text-right tabular-nums">{num(r.keyEvents)}</td>
                      <td className="py-2 text-right tabular-nums text-sub">{money(r.revenue)}</td>
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
            unit={meta.label.toLowerCase()}
            onPrev={() => setOffset(Math.max(0, offset - PAGE_SIZE))}
            onNext={() => setOffset(offset + PAGE_SIZE)}
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
  onPrev,
  onNext,
}: {
  offset: number;
  shown: number;
  total: number;
  unit: string;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <div className="mt-3 flex items-center justify-between gap-3 border-t border-edge pt-2.5">
      <span className="text-xs text-faint">
        {total === 0 ? "Nothing to show." : `${offset + 1}–${offset + shown} of ${total} ${unit}`}
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

function ConnectGaCard({
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
          <p className="text-sm font-medium text-ink">Google Analytics is not connected</p>
          <p className="mt-0.5 text-sm text-sub">
            Syncing traffic data needs a Google account with access to this site&apos;s Analytics
            property. The connection stays on this device.
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
          {busy ? "Connecting…" : "Connect Google Analytics"}
        </Button>
      </div>
    </Card>
  );
}

function SyncProgressBar({ sync }: { sync: ReturnType<typeof useTrafficSync> }) {
  const p = sync.progress;
  const done = p?.daysDone ?? 0;
  const total = p?.daysTotal ?? 0;
  const label = total
    ? `Importing traffic data — day ${done} of ${total}${p?.day ? ` (${p.day})` : ""}`
    : "Importing traffic data…";
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
  candidates: GaAccount[];
  onPicked: (property: string) => void;
}) {
  const [busy, setBusy] = useState(false);
  return (
    <Card>
      <p className="text-sm font-medium text-ink">Which Analytics property measures this site?</p>
      <p className="mt-1 text-sm text-sub">
        Analytics does not say which website a property reports on, so it cannot be matched
        automatically — pick the one to trust.
      </p>
      <div className="mt-3 flex flex-col gap-2">
        {candidates.flatMap((account) =>
          account.properties.map((p) => (
            <button
              key={p.property}
              disabled={busy}
              onClick={() => {
                setBusy(true);
                onPicked(p.property);
              }}
              className="flex items-center justify-between rounded-lg border border-edge2 px-3 py-2 text-left text-sm text-ink transition-colors hover:bg-panel2 disabled:opacity-50"
            >
              <span>
                {p.name || p.property}
                <span className="ml-2 text-xs text-faint">{account.name}</span>
              </span>
              <Badge>{p.propertyId}</Badge>
            </button>
          )),
        )}
        {candidates.every((a) => a.properties.length === 0) && (
          <p className="text-sm text-sub">
            This Google account has no Analytics properties. Connect an account that can read the
            site&apos;s property.
          </p>
        )}
      </div>
    </Card>
  );
}
