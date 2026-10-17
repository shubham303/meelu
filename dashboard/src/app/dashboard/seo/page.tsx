"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { ChevronLeft, ChevronRight, Layers, Trash2 } from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import {
  Badge,
  Button,
  Card,
  ConfirmDelete,
  EmptyState,
  IconButton,
  Input,
  PageHeader,
  Spinner,
  StatCard,
} from "@/components/ui";
import { useIsApp } from "@/lib/use-app-mode";
import { api, useApi, usePagedApi, type Pagination } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import type { SiteProfile } from "@/lib/types";
import * as chips from "@/features/prompt-chips/seo";
import { SiteAskButton } from "../site/site-ask";
import { useAgentTasks } from "../agent-tasks";
import { marketLabel } from "./market";
import { SEO_ASK, TaskCards } from "./task-cards";
import { YourPrompts } from "@/features/user-prompts/your-prompts";
import type {
  BacklinkOpportunity,
  Competitor,
  KeywordCluster,
  TrackedOverview,
} from "./types";
import { WinnabilityBar, position } from "./winnability";
import { ImportanceBadge, IntentBadge } from "./signals";

type Filter = "all" | "scored" | "unscored" | "ranked";

const FILTERS: Array<{ key: Filter; label: string; query: string }> = [
  { key: "all", label: "All", query: "" },
  { key: "scored", label: "Scored", query: "&scored=true" },
  { key: "unscored", label: "Not scored", query: "&scored=false" },
  { key: "ranked", label: "We rank", query: "&ranked=true" },
];

const PAGE_SIZE = 25;

interface SearchSummary {
  hasData: boolean;
  lastDay?: string;
  current?: { clicks: number; impressions: number };
  previous?: { clicks: number };
  active?: { id: string } | null;
}

interface TrafficSummary {
  hasData: boolean;
  lastDay: string | null;
  totals: { current: { sessions: number } };
  organic: { current: { sessions: number } };
  active?: { id: string } | null;
}

function clickChange(search: SearchSummary | null): string {
  const now = search?.current?.clicks ?? 0;
  const before = search?.previous?.clicks ?? 0;
  if (!before) return "no earlier window to compare";
  const change = Math.round(((now - before) / before) * 100);
  return `${change >= 0 ? "up" : "down"} ${Math.abs(change)}% on the previous 28 days`;
}

export default function SeoPage() {
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const query = FILTERS.find((f) => f.key === filter)?.query ?? "";
  const term = search.trim()
    ? `&search=${encodeURIComponent(search.trim())}`
    : "";

  const { data: site } = useApi<SiteProfile>("/api/v1/site");
  const clusters = usePagedApi<KeywordCluster>(
    `/api/v1/site/seo/clusters?page=${page}&page_size=${PAGE_SIZE}${query}${term}`,
  );
  const { data: all } = usePagedApi<KeywordCluster>(
    "/api/v1/site/seo/clusters?page_size=1",
  );
  const { data: unscored } = usePagedApi<KeywordCluster>(
    "/api/v1/site/seo/clusters?page_size=1&scored=false",
  );
  const { data: best } = usePagedApi<KeywordCluster>(
    "/api/v1/site/seo/clusters?page_size=1&scored=true",
  );
  const { data: searchData } = useApi<SearchSummary>(
    "/api/v1/site/search-data",
  );
  const { data: traffic } = useApi<TrafficSummary>("/api/v1/site/traffic");
  const { data: tracked } = useApi<TrackedOverview>("/api/v1/site/seo/tracked");
  const { data: competitors } = useApi<Competitor[]>(
    "/api/v1/site/seo/competitors",
  );
  const { data: opportunities } = usePagedApi<BacklinkOpportunity>(
    "/api/v1/site/seo/backlink-opportunities?page_size=1",
  );

  const lastPage = Math.max(1, clusters.data?.pagination.total_pages ?? 1);
  if (clusters.data && page > lastPage) setPage(lastPage);

  const total = all?.pagination.total ?? 0;
  const waiting = unscored?.pagination.total ?? 0;
  const top = best?.data[0];
  const reload = () => void clusters.refresh();

  return (
    <PageEnter>
      <PageHeader
        title="SEO"
        description="What to target next, ranked by how winnable it is and how many people search it."
        actions={
          <div className="flex items-center gap-2">
            <Badge tone="neutral" className="px-3 py-1 text-xs">
              Market · {marketLabel(site?.markets, site?.language)}
            </Badge>
            <SiteAskButton
              title="Ask — SEO"
              hint="Ask about clusters, search performance, competitors or tracked keywords."
              suggestions={chips.desk()}
              endpoint={SEO_ASK}
              promptSurface="seo"
              onRan={reload}
            />
          </div>
        }
      />

      <TaskCards title="Start a task" chips={chips.desk()} onRan={reload} />
      <YourPrompts
        surface="seo"
        endpoint={SEO_ASK}
        titlePrefix="SEO"
        suggestions={chips.desk()}
        onRan={reload}
      />

      <Stagger className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Clusters"
          value={total}
          hint={
            total
              ? `${total - waiting} scored · ${waiting} waiting`
              : "none built yet"
          }
        />
        <Link
          href={top ? `/dashboard/seo/clusters/${top.id}` : "#clusters"}
          className="block"
        >
          <StatCard
            label="Best odds"
            value={
              top?.winnability !== undefined ? Math.round(top.winnability) : "—"
            }
            hint={top?.mainKeyword ?? "nothing scored yet"}
          />
        </Link>
        <Link href="/dashboard/seo/search" className="block">
          <StatCard
            label="Search clicks · 28d"
            value={(searchData?.current?.clicks ?? 0).toLocaleString()}
            hint={
              searchData?.hasData
                ? clickChange(searchData)
                : "Search Console not synced"
            }
          />
        </Link>
        <Link href="/dashboard/seo/tracked" className="block">
          <StatCard
            label="Tracked keywords"
            value={tracked?.stats.tracked ?? 0}
            hint={
              tracked ? `${tracked.stats.moved} moved since last month` : "—"
            }
          />
        </Link>
      </Stagger>

      <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <SourceCard
          href="/dashboard/seo/search"
          title="Search performance"
          active={Boolean(searchData?.active)}
          lastDay={searchData?.hasData ? searchData.lastDay : undefined}
          line={
            searchData?.hasData
              ? `${(searchData.current?.clicks ?? 0).toLocaleString()} clicks · ${(searchData.current?.impressions ?? 0).toLocaleString()} impressions in the last 28 days`
              : "Connect Search Console to see the queries Google sends."
          }
        />
        <SourceCard
          href="/dashboard/seo/traffic"
          title="Traffic"
          active={Boolean(traffic?.active)}
          lastDay={
            traffic?.hasData ? (traffic.lastDay ?? undefined) : undefined
          }
          line={
            traffic?.hasData
              ? `${traffic.totals.current.sessions.toLocaleString()} sessions · ${organicShare(traffic)}% from organic search`
              : "Connect Analytics to see what visitors do."
          }
        />
        <Link href="/dashboard/seo/competitors" className="block h-full">
          <Card className="flex h-full flex-col gap-2.5 transition-colors hover:border-edge2">
            <span className="flex items-center justify-between">
              <span className="text-sm font-medium text-ink">
                Competitors
              </span>
              <span className="text-xs text-sub">
                {competitors?.length ?? 0} saved
              </span>
            </span>
            {competitors?.length ? (
              <span className="flex flex-wrap gap-1.5">
                {competitors.slice(0, 8).map((c) => (
                  <span
                    key={c.id}
                    className="rounded-full border border-edge bg-bg px-2.5 py-0.5 text-xs text-ink"
                  >
                    {c.domain}
                    {c.domainRank !== undefined && (
                      <span className="text-faint"> · {c.domainRank}</span>
                    )}
                  </span>
                ))}
              </span>
            ) : (
              <span className="text-xs text-sub">None saved yet.</span>
            )}
          </Card>
        </Link>
        <Link href="/dashboard/seo/backlinks" className="block h-full">
          <Card className="flex h-full flex-col gap-1.5 transition-colors hover:border-edge2">
            <span className="flex items-center justify-between">
              <span className="text-sm font-medium text-ink">
                Backlink opportunities
              </span>
              <span className="font-display text-xl text-ink">
                {opportunities?.pagination.total ?? 0}
              </span>
            </span>
            <span className="text-xs text-sub">
              Genuine sites linking to your competitors but not to you.
            </span>
          </Card>
        </Link>
      </div>

      <section id="clusters" className="min-w-0">
        <Card className="overflow-hidden p-0">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-edge px-4 py-4">
            <h2 className="font-display text-lg text-ink">
              Keyword clusters
            </h2>
            <div className="flex flex-wrap items-center gap-2">
              <label className="sr-only" htmlFor="cluster-search">
                Search clusters
              </label>
              <Input
                id="cluster-search"
                type="search"
                className="w-56"
                placeholder="Search a topic or phrase"
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
              />
              {FILTERS.map((f) => (
                <button
                  key={f.key}
                  type="button"
                  onClick={() => {
                    setFilter(f.key);
                    setPage(1);
                  }}
                  className={cn(
                    "rounded-full border px-3 py-1.5 text-xs transition-colors",
                    filter === f.key
                      ? "border-accent bg-accent text-white"
                      : "border-edge bg-panel text-ink hover:bg-panel2",
                  )}
                >
                  {f.label}
                </button>
              ))}
            </div>
          </div>
          <ClusterTable
            loading={clusters.loading && !clusters.data}
            error={clusters.error}
            rows={clusters.data?.data ?? []}
            empty={total === 0}
            onRan={reload}
          />
          {clusters.data && (
            <ClusterPager
              pagination={clusters.data.pagination}
              onPage={setPage}
            />
          )}
          {waiting > 0 && <ScoreFooter waiting={waiting} onRan={reload} />}
        </Card>
      </section>
    </PageEnter>
  );
}

function organicShare(traffic: TrafficSummary): number {
  const all = traffic.totals.current.sessions;
  return all ? Math.round((traffic.organic.current.sessions / all) * 100) : 0;
}

function SourceCard({
  href,
  title,
  active,
  lastDay,
  line,
}: {
  href: string;
  title: string;
  active: boolean;
  lastDay?: string;
  line: string;
}) {
  return (
    <Link href={href} className="block h-full">
      <Card className="flex h-full flex-col gap-1.5 transition-colors hover:border-edge2">
        <span className="flex flex-wrap items-center justify-between gap-x-2 gap-y-1">
          <span className="text-sm font-medium whitespace-nowrap text-ink">
            {title}
          </span>
          {active && <Badge tone="accent">syncing</Badge>}
          {!active && lastDay && (
            <Badge tone="good">data through {lastDay}</Badge>
          )}
          {!active && !lastDay && <Badge tone="neutral">not synced</Badge>}
        </span>
        <span className="text-xs text-sub">{line}</span>
      </Card>
    </Link>
  );
}

function ClusterTable({
  loading,
  error,
  rows,
  empty,
  onRan,
}: {
  loading: boolean;
  error: string | null;
  rows: KeywordCluster[];
  empty: boolean;
  onRan: () => void;
}) {
  const router = useRouter();
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  const [deleting, setDeleting] = useState<KeywordCluster | null>(null);

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }
  if (error) return <p className="px-4 py-6 text-sm text-bad">{error}</p>;
  if (empty) {
    return (
      <div className="p-4">
        <EmptyState
          icon={Layers}
          title="No keyword clusters yet"
          hint="Ask Meelu to build clusters for a topic. It drops noise and off-topic searches, then groups what is left by what searchers want."
        />
      </div>
    );
  }
  if (!rows.length)
    return (
      <p className="px-4 py-8 text-center text-sm text-sub">
        No cluster matches.
      </p>
    );

  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[840px] border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-sub">
            <th className="px-4 py-2.5 font-medium">Main keyword</th>
            <th className="px-3 py-2.5 font-medium">Importance</th>
            <th className="px-3 py-2.5 font-medium">Intent</th>
            <th className="px-3 py-2.5 font-medium">Winnability</th>
            <th className="px-3 py-2.5 text-right font-medium">
              Searches / mo
            </th>
            <th className="px-3 py-2.5 font-medium">Likely spot</th>
            <th className="px-3 py-2.5 font-medium">We rank</th>
            <th className="px-4 py-2.5">
              <span className="sr-only">Actions</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((c) => (
            <tr
              key={c.id}
              onClick={() => router.push(`/dashboard/seo/clusters/${c.id}`)}
              className="cursor-pointer border-t border-edge transition-colors hover:bg-panel2/60"
            >
              <td className="px-4 py-3">
                <Link
                  href={`/dashboard/seo/clusters/${c.id}`}
                  onClick={(e) => e.stopPropagation()}
                  className="font-medium text-ink hover:text-accent"
                >
                  {c.mainKeyword}
                </Link>
                <span className="block text-xs text-faint">
                  {c.keywords.length} keywords
                  {c.coreKeyword ? ` · ${c.coreKeyword}` : ""}
                </span>
              </td>
              <td className="px-3 py-3">
                <ImportanceBadge importance={c.importance} />
              </td>
              <td className="px-3 py-3">
                <IntentBadge intent={c.intent} />
              </td>
              <td className="px-3 py-3">
                <WinnabilityBar
                  score={c.winnability}
                  poisoned={c.serpVerdict === "poisoned"}
                />
              </td>
              <td className="px-3 py-3 text-right tabular-nums">
                {c.volume.toLocaleString()}
              </td>
              <td className="px-3 py-3 text-sub">
                {position(c.likelyPosition)}
              </td>
              <td className="px-3 py-3 text-sub">
                {c.ourPosition ? position(c.ourPosition) : c.isRanked ? "yes" : "—"}
                {c.competitors.length > 0 && (
                  <span className="block text-xs text-faint">
                    {c.competitors.length} competitor{c.competitors.length === 1 ? "" : "s"}
                  </span>
                )}
              </td>
              <td className="px-4 py-3">
                <span className="flex items-center justify-end gap-1.5">
                  {isApp && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        const plan = chips.cluster(c.mainKeyword)[0];
                        launchTask({
                          title: `SEO — ${plan.label}`,
                          endpoint: SEO_ASK,
                          emptyHint: plan.blurb ?? plan.label,
                          suggestions: chips.cluster(c.mainKeyword),
                          draft: {},
                          autoStart: plan.prompt,
                          onCreated: onRan,
                        });
                      }}
                    >
                      Plan a page
                    </Button>
                  )}
                  <IconButton
                    aria-label="Delete cluster"
                    title="Delete cluster"
                    className="hover:text-bad"
                    onClick={(e) => {
                      e.stopPropagation();
                      setDeleting(c);
                    }}
                  >
                    <Trash2 size={13} />
                  </IconButton>
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <ConfirmDelete
        open={deleting !== null}
        onClose={() => setDeleting(null)}
        what={`the cluster "${deleting?.mainKeyword ?? ""}"`}
        onConfirm={async () => {
          if (!deleting) return;
          await api(`/api/v1/site/seo/clusters/${deleting.id}`, {
            method: "DELETE",
          });
          setDeleting(null);
          onRan();
        }}
      />
    </div>
  );
}

function ClusterPager({
  pagination,
  onPage,
}: {
  pagination: Pagination;
  onPage: (page: number) => void;
}) {
  const { page, page_size, total, total_pages, has_prev, has_next } =
    pagination;
  if (total_pages <= 1) return null;
  const first = (page - 1) * page_size + 1;
  const last = Math.min(page * page_size, total);
  return (
    <div className="flex items-center justify-end gap-2 border-t border-edge px-4 py-2.5 text-xs text-sub">
      <span className="tabular-nums">
        {first}–{last} of {total}
      </span>
      <IconButton
        aria-label="Previous page"
        disabled={!has_prev}
        className="disabled:pointer-events-none disabled:opacity-40"
        onClick={() => onPage(page - 1)}
      >
        <ChevronLeft size={14} />
      </IconButton>
      <span className="tabular-nums">
        {page} / {total_pages}
      </span>
      <IconButton
        aria-label="Next page"
        disabled={!has_next}
        className="disabled:pointer-events-none disabled:opacity-40"
        onClick={() => onPage(page + 1)}
      >
        <ChevronRight size={14} />
      </IconButton>
    </div>
  );
}

function ScoreFooter({
  waiting,
  onRan,
}: {
  waiting: number;
  onRan: () => void;
}) {
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  const target = chips.SCORE_CLUSTERS;
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border-t border-edge px-4 py-3 text-xs text-sub">
      <span>
        Ranked by winnability, then monthly searches. {waiting} cluster
        {waiting === 1 ? " is" : "s are"} not scored yet.
      </span>
      {isApp && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() =>
            launchTask({
              title: `SEO — ${target.label}`,
              endpoint: SEO_ASK,
              emptyHint: target.blurb ?? target.label,
              suggestions: chips.desk(),
              draft: {},
              autoStart: target.prompt,
              onCreated: onRan,
            })
          }
        >
          Score them
        </Button>
      )}
    </div>
  );
}
