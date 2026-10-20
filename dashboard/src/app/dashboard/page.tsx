"use client";

import { useState, type FormEvent, type ReactNode } from "react";
import Link from "next/link";
import {
  ArrowRight,
  ArrowUp,
  BarChart3,
  FileText,
  Globe,
  Radar,
  Search,
  UserSearch,
  type LucideIcon,
} from "lucide-react";
import { PageEnter } from "@/components/animate";
import { Card, Spinner } from "@/components/ui";
import { Sparkline } from "@/components/charts";
import { useApi } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import { cn, formatRelative } from "@/lib/utils";
import type { PromptChip } from "@/features/prompt-chips/lib";
import type { SiteProfile } from "@/lib/types";
import { useAgentTasks } from "./agent-tasks";

const OVERVIEW_ASK = "/api/agent/ask-overview";
const WINDOW_DAYS = 28;

interface Stats {
  pages: number;
  lastCrawlAt: string | null;
  contentPieces: number;
  reports: number;
  waiting: {
    structureSuggestions: number;
    conversationsToReply: number;
    leadsToMessage: number;
    issuesOpen: number;
  };
}

interface SearchTotals {
  clicks: number;
  impressions: number;
  ctr: number | null;
  position: number | null;
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
  series: { page: string | null; points: SeriesPoint[] }[];
  current?: SearchTotals;
  previous?: SearchTotals;
}

interface Mover {
  kind: string;
  key: string;
  clicks: number;
  prevClicks: number;
}

interface ChangesResponse {
  hasData: boolean;
  up: Mover[];
  down: Mover[];
}

const CHIPS: (PromptChip & { icon: LucideIcon })[] = [
  {
    icon: Search,
    label: "Find pages that split one query",
    prompt: "Find search queries where two or more of my pages compete, and say what each page adds.",
  },
  {
    icon: BarChart3,
    label: "What changed in Search Console?",
    prompt: "What changed in my Search Console data over the last 28 days compared with the 28 before, and why?",
  },
  {
    icon: FileText,
    label: "Draft a page for a keyword",
    prompt: "Help me pick a keyword worth a new page, then draft it with internal links.",
  },
  {
    icon: Radar,
    label: "Conversations I should join",
    prompt: "Which social conversations waiting on me are most worth answering, and with what angle?",
  },
];

function num(n: number | undefined | null): string {
  return n === undefined || n === null ? "—" : n.toLocaleString();
}

function compact(n: number): string {
  return n >= 10_000 ? `${(n / 1000).toFixed(1)}k` : n.toLocaleString();
}

function pctChange(now: number, before: number): number | null {
  if (!before) return null;
  return Math.round(((now - before) / before) * 100);
}

function pathOf(url: string): string {
  try {
    const u = new URL(url);
    return u.pathname + u.search || "/";
  } catch {
    return url;
  }
}

export default function OverviewPage() {
  const isApp = useIsApp();
  const { data: site, loading: siteLoading } = useApi<SiteProfile | null>("/api/v1/site");
  const { data: stats, loading: statsLoading, error: statsError } = useApi<Stats>(
    site ? "/api/v1/stats" : null,
  );
  const { data: series } = useApi<SeriesResponse>(
    site ? `/api/v1/site/search-data/series?days=${WINDOW_DAYS}` : null,
  );
  const { data: changes } = useApi<ChangesResponse>(
    site ? `/api/v1/site/search-data/changes?days=${WINDOW_DAYS}` : null,
  );

  if (siteLoading || (site && statsLoading)) {
    return (
      <PageEnter>
        <Spinner />
      </PageEnter>
    );
  }

  if (!site) {
    return (
      <PageEnter>
        <div className="mx-auto max-w-xl py-16 text-center">
          <h1 className="font-display text-3xl text-ink">Good to see you</h1>
          <p className="mt-3 text-sm text-sub">
            Add a website from the picker at the top of the sidebar. Meelu reads it straight away, then this page
            shows what is waiting on you.
          </p>
        </div>
      </PageEnter>
    );
  }

  return (
    <PageEnter>
      <div className="mx-auto flex max-w-6xl flex-col gap-8">
        {isApp ? (
          <AskBox siteName={site.name} />
        ) : (
          <header>
            <h1 className="font-display text-3xl text-ink">{site.name}</h1>
            <p className="mt-1 text-sm text-sub">{site.domain}</p>
          </header>
        )}

        {statsError && <p className="text-sm text-bad">{statsError}</p>}

        <SearchKpis series={series} />

        <div className="grid gap-5 lg:grid-cols-[minmax(0,1.6fr)_minmax(0,1fr)]">
          <PagesThatMoved changes={changes} />
          <WaitingOnYou stats={stats} />
        </div>

        <Glance stats={stats} />
      </div>
    </PageEnter>
  );
}

function AskBox({ siteName }: { siteName: string }) {
  const { launchTask } = useAgentTasks();
  const [text, setText] = useState("");

  const ask = (prompt: string, label: string) =>
    launchTask({
      title: `Overview — ${label.length > 60 ? `${label.slice(0, 57)}…` : label}`,
      endpoint: OVERVIEW_ASK,
      emptyHint: "Ask about your pages, search data, content or conversations.",
      suggestions: CHIPS,
      draft: {},
      autoStart: prompt,
    });

  const submit = (e: FormEvent) => {
    e.preventDefault();
    const prompt = text.trim();
    if (!prompt) return;
    ask(prompt, prompt);
    setText("");
  };

  return (
    <section aria-labelledby="overview-ask" className="flex flex-col items-center gap-4 pt-4 text-center">
      <h1 id="overview-ask" className="font-display text-3xl leading-tight text-ink sm:text-4xl">
        What should we look at on {siteName}?
      </h1>
      <form
        onSubmit={submit}
        className="flex w-full max-w-3xl flex-col gap-2 rounded-2xl border border-edge2 bg-panel px-4 pt-3 pb-2.5 text-left shadow-sm focus-within:border-accent/50"
      >
        <label htmlFor="overview-prompt" className="sr-only">
          Ask your coworker
        </label>
        <textarea
          id="overview-prompt"
          rows={2}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) submit(e);
          }}
          placeholder="Ask about your pages, search data or conversations…"
          className="resize-none bg-transparent text-base text-ink outline-none placeholder:text-faint"
        />
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs text-sub">Meelu suggests; you approve every change.</span>
          <button
            type="submit"
            aria-label="Start task"
            disabled={!text.trim()}
            className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent text-white transition hover:bg-accent-hi disabled:opacity-40"
          >
            <ArrowUp size={18} />
          </button>
        </div>
      </form>
      <div className="flex max-w-4xl flex-wrap justify-center gap-2">
        {CHIPS.map((chip) => {
          const Icon = chip.icon;
          return (
            <button
              key={chip.label}
              type="button"
              onClick={() => ask(chip.prompt, chip.label)}
              className="inline-flex min-h-10 items-center gap-2 rounded-full border border-edge bg-panel px-3.5 text-sm text-ink transition hover:border-accent/40 hover:bg-accent-soft"
            >
              <Icon size={14} className="text-accent" />
              {chip.label}
            </button>
          );
        })}
      </div>
    </section>
  );
}

function SectionTitle({ children, aside }: { children: ReactNode; aside?: ReactNode }) {
  return (
    <div className="mb-3 flex flex-wrap items-baseline justify-between gap-2">
      <h2 className="font-display text-lg text-ink">{children}</h2>
      {aside && <span className="text-xs text-sub">{aside}</span>}
    </div>
  );
}

function SearchKpis({ series }: { series: SeriesResponse | null }) {
  if (series && !series.hasData) {
    return (
      <Card className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-medium text-ink">No Search Console data yet</p>
          <p className="mt-0.5 text-sm text-sub">Connect Search Console to see clicks, impressions and pages that moved.</p>
        </div>
        <Link href="/dashboard/seo" className="inline-flex items-center gap-1.5 text-sm font-medium text-accent">
          Open SEO <ArrowRight size={14} />
        </Link>
      </Card>
    );
  }

  const points = series?.series[0]?.points ?? [];
  const now = series?.current;
  const before = series?.previous;
  const ctrNow = now?.ctr ?? null;
  const ctrBefore = before?.ctr ?? null;
  const posNow = now?.position ?? null;
  const posBefore = before?.position ?? null;

  const tiles = [
    {
      label: "Clicks",
      value: now ? compact(now.clicks) : "—",
      delta: now && before ? pctChange(now.clicks, before.clicks) : null,
      unit: "%",
      better: "up" as const,
      spark: points.map((p) => p.clicks),
    },
    {
      label: "Impressions",
      value: now ? compact(now.impressions) : "—",
      delta: now && before ? pctChange(now.impressions, before.impressions) : null,
      unit: "%",
      better: "up" as const,
      spark: points.map((p) => p.impressions),
    },
    {
      label: "CTR",
      value: ctrNow === null ? "—" : `${(ctrNow * 100).toFixed(1)}%`,
      delta: ctrNow !== null && ctrBefore !== null ? Number(((ctrNow - ctrBefore) * 100).toFixed(1)) : null,
      unit: " pt",
      better: "up" as const,
      spark: points.map((p) => p.ctr ?? 0),
    },
    {
      label: "Average position",
      value: posNow === null ? "—" : posNow.toFixed(1),
      delta: posNow !== null && posBefore !== null ? Number((posNow - posBefore).toFixed(1)) : null,
      unit: "",
      better: "down" as const,
      spark: points.filter((p) => p.position !== null).map((p) => -(p.position as number)),
    },
  ];

  return (
    <section aria-label="Search, last 28 days">
      <SectionTitle aside="vs the 28 days before · Search Console">Search, last {WINDOW_DAYS} days</SectionTitle>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {tiles.map((t) => {
          const good = t.delta !== null && t.delta !== 0 && (t.better === "up" ? t.delta > 0 : t.delta < 0);
          return (
            <Card key={t.label} className="flex flex-col gap-2 p-4">
              <span className="text-sm text-sub">{t.label}</span>
              <div className="flex items-baseline gap-2">
                <span className="text-2xl font-medium tracking-tight text-ink">{t.value}</span>
                {t.delta !== null && (
                  <span className={cn("text-sm font-medium", t.delta === 0 ? "text-sub" : good ? "text-good" : "text-warn")}>
                    {t.delta > 0 ? "+" : t.delta < 0 ? "−" : "±"}
                    {Math.abs(t.delta)}
                    {t.unit}
                  </span>
                )}
              </div>
              <div className="overflow-hidden">
                <Sparkline data={t.spark} width={200} height={36} stroke="var(--color-accent)" />
              </div>
            </Card>
          );
        })}
      </div>
    </section>
  );
}

function PagesThatMoved({ changes }: { changes: ChangesResponse | null }) {
  const up = (changes?.up ?? []).filter((m) => m.kind === "page").slice(0, 3);
  const down = (changes?.down ?? []).filter((m) => m.kind === "page").slice(0, 3);
  const rows = [...up, ...down];

  return (
    <Card className="flex min-w-0 flex-col gap-3">
      <div className="flex items-baseline justify-between gap-2">
        <h2 className="text-[15px] font-medium text-ink">Pages that moved</h2>
        <Link href="/dashboard/seo/search" className="text-sm text-accent">
          See search data
        </Link>
      </div>
      {rows.length === 0 ? (
        <p className="py-6 text-sm text-sub">
          {changes?.hasData === false ? "Search Console has no data for this site yet." : "No page moved much in the last 28 days."}
        </p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full min-w-[420px] border-collapse text-sm">
            <thead>
              <tr className="text-left text-sub">
                <th scope="col" className="border-b border-edge py-2 font-medium">Page</th>
                <th scope="col" className="border-b border-edge py-2 text-right font-medium">Clicks</th>
                <th scope="col" className="border-b border-edge py-2 text-right font-medium">Change</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((m) => {
                const delta = m.clicks - m.prevClicks;
                return (
                  <tr key={m.key}>
                    <td className="max-w-0 truncate border-b border-panel2 py-2.5 pr-3 font-mono text-xs text-ink" title={m.key}>
                      {pathOf(m.key)}
                    </td>
                    <td className="border-b border-panel2 py-2.5 text-right text-ink">{num(m.clicks)}</td>
                    <td className={cn("border-b border-panel2 py-2.5 text-right font-medium", delta >= 0 ? "text-good" : "text-warn")}>
                      {delta >= 0 ? "+" : "−"}
                      {Math.abs(delta).toLocaleString()}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}

function WaitingOnYou({ stats }: { stats: Stats | null }) {
  const w = stats?.waiting;
  const rows: { icon: LucideIcon; label: string; count: number | undefined; href: string }[] = [
    { icon: Globe, label: "Link and pillar suggestions", count: w?.structureSuggestions, href: "/dashboard/site/structure" },
    { icon: Radar, label: "Conversations to answer", count: w?.conversationsToReply, href: "/dashboard/social-listening" },
    { icon: UserSearch, label: "People to message", count: w?.leadsToMessage, href: "/dashboard/find-leads" },
    { icon: Search, label: "Technical issues open", count: w?.issuesOpen, href: "/dashboard/site/technical-seo" },
  ];
  const total = rows.reduce((sum, r) => sum + (r.count ?? 0), 0);

  return (
    <Card className="flex min-w-0 flex-col gap-1">
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <h2 className="text-[15px] font-medium text-ink">Waiting on you</h2>
        <span className="text-sm text-sub">{num(total)} in all</span>
      </div>
      {rows.map((r) => {
        const Icon = r.icon;
        return (
          <Link
            key={r.label}
            href={r.href}
            className="-mx-2 flex min-h-12 items-center gap-3 rounded-lg px-2 text-sm text-ink transition hover:bg-panel2"
          >
            <Icon size={16} className="shrink-0 text-accent" />
            <span className="flex-1">{r.label}</span>
            <span className="min-w-7 rounded-full bg-panel2 px-2 py-0.5 text-center text-xs font-medium">{num(r.count)}</span>
          </Link>
        );
      })}
      <p className="mt-2 text-xs text-sub">Nothing here was decided by an agent.</p>
    </Card>
  );
}

function Glance({ stats }: { stats: Stats | null }) {
  const items = [
    {
      value: num(stats?.pages),
      label: stats?.lastCrawlAt ? `pages in the last crawl, ${formatRelative(stats.lastCrawlAt)}` : "pages read; no finished crawl yet",
      href: "/dashboard/site/pages",
    },
    { value: num(stats?.contentPieces), label: "pages written on the Content desk", href: "/dashboard/content" },
    { value: num(stats?.reports), label: "reports saved", href: "/dashboard/reports" },
  ];
  return (
    <section aria-label="Site at a glance" className="grid gap-3 sm:grid-cols-3">
      {items.map((g) => (
        <Link
          key={g.label}
          href={g.href}
          className="flex items-center gap-3.5 rounded-2xl border border-dashed border-edge2 px-4 py-3.5 transition hover:border-accent/40"
        >
          <span className="font-display text-2xl text-ink">{g.value}</span>
          <span className="text-sm leading-snug text-sub">{g.label}</span>
        </Link>
      ))}
    </section>
  );
}
