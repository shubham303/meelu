"use client";

import {
  AlertTriangle,
  FileText,
  Network,
  ShieldCheck,
} from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import {
  Badge,
  Card,
  EmptyState,
  PageHeader,
  type BadgeTone,
} from "@/components/ui";
import { useApi, useCurrentSite } from "@/lib/use-api";
import { formatRelative } from "@/lib/utils";
import { CrawlButton, CrawlNotes } from "./crawl-button";
import { CrawlProgress } from "./crawl-progress";
import { SiteRecordSection } from "./record-section";
import { SectionCard } from "@/components/section-card";
import { SiteAskButton } from "./site-ask";
import { useCrawl } from "./tracked";
import type { SiteDiscovery, SiteProfile, SiteIssueSummary } from "@/lib/types";
import * as chips from "@/features/prompt-chips/site";

interface Stats {
  pages: number;
  ok: number;
  errored: number;
  gone: number;
  shallow: number;
  notInSitemap: number;
  sitemapMissing: number;
  notFound: number;
  blocked: number;
  serverError: number;
  unreachable: number;
  orphans: number;
  byKind: { kind: string; n: number }[];
  byStage: { stage: string; n: number }[];
  chunks: { total: number; embedded: number; failed: number };
  lastCrawledAt: string | null;
  sitemapUrlCount: number | null;
}

export default function SiteDeskPage() {
  const siteId = useCurrentSite();

  const { data: site, refresh: reloadSite } = useApi<SiteProfile | null>("/api/v1/site");
  const { data: stats, refresh: reloadStats } = useApi<Stats>("/api/v1/site/pages/stats");

  const reload = () => {
    reloadStats();
    reloadSite();
  };

  const crawl = useCrawl(siteId, reload);

  const live = stats ? stats.pages - stats.gone : 0;
  const sitemapListed = stats?.sitemapUrlCount ?? 0;
  const sitemapRead = stats ? Math.min(sitemapListed, sitemapListed - stats.sitemapMissing) : 0;

  return (
    <PageEnter>
      <PageHeader
        title="Site"
        description={
          stats?.lastCrawledAt
            ? `${site?.domain ?? ""} · ${live} pages · crawled ${formatRelative(stats.lastCrawledAt)}`
            : `${site?.domain ?? ""} · nothing has been read yet`
        }
        actions={
          <div className="flex items-center gap-2">
            <CrawlButton crawl={crawl} />
            <SiteAskButton
              title="Ask — Site"
              hint={`Ask something about ${site?.domain || "this website"}, or say what you want done.`}
              suggestions={chips.desk()}
              onRan={reload}
            />
          </div>
        }
      />

      <div className="space-y-4">
        <CrawlProgress crawl={crawl} />
        <CrawlNotes crawl={crawl} />

        {stats && !stats.pages && (
          <EmptyState
            icon={FileText}
            title="This website has not been read yet"
            hint={
              "Crawling reads every page your sitemap lists and makes the site searchable. " +
              "It runs in the Meelu app, from your own machine — no agent and no model spend."
            }
            action={<CrawlButton crawl={crawl} />}
          />
        )}

        {!!stats?.pages && (
          <>
            {stats.sitemapMissing > 0 && (
              <Card className="flex gap-2 border-amber-500/40 bg-amber-500/5 p-3 text-sm">
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
                <span>
                  {stats.sitemapMissing} URL{stats.sitemapMissing === 1 ? "" : "s"} the sitemap lists
                  returned 404 or 410. A sitemap should only list pages that serve — search engines
                  treat dead entries as a quality signal against the whole file.
                </span>
              </Card>
            )}

            <Stagger className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <Stat
                label="Sitemap coverage"
                value={sitemapListed ? `${Math.round((sitemapRead / sitemapListed) * 100)}%` : "—"}
                hint={
                  sitemapListed
                    ? `${sitemapRead} of ${sitemapListed} listed pages read`
                    : "no sitemap read yet"
                }
                tone={sitemapListed && sitemapRead < sitemapListed ? "warn" : "good"}
              />
              <Stat
                label="Broken"
                value={stats.gone}
                hint={
                  [
                    stats.blocked && `${stats.blocked} blocked`,
                    stats.serverError && `${stats.serverError} server errors`,
                    stats.unreachable && `${stats.unreachable} unreachable`,
                  ]
                    .filter(Boolean)
                    .join(" · ") || "404 or 410 from the site"
                }
                tone={stats.gone > 0 ? "warn" : "good"}
              />
              <Stat
                label="Not in sitemap"
                value={stats.notInSitemap}
                hint="found by following links"
                tone={stats.notInSitemap > 0 ? "warn" : "good"}
              />
              <Stat
                label="Orphans"
                value={stats.orphans}
                hint="in the sitemap, nothing links to them"
                tone={stats.orphans > 0 ? "warn" : "good"}
              />
            </Stagger>
          </>
        )}

        <Sections pages={live} />

        <SiteRecordSection />
      </div>
    </PageEnter>
  );
}

function Sections({ pages }: { pages: number }) {
  const { data: summary } = useApi<SiteIssueSummary>("/api/v1/site/technical-seo/summary");
  const { data: discovery } = useApi<SiteDiscovery>("/api/v1/site/pages/discovery");
  const blocked = (discovery?.orphans ?? 0) + (discovery?.unreachable ?? 0) + (discovery?.deep ?? 0);
  const open = (summary?.site.open ?? 0) + (summary?.pages.open ?? 0);
  const rejected = (summary?.site.rejected ?? 0) + (summary?.pages.rejected ?? 0);

  return (
    <Stagger className="space-y-2">
      <SectionCard
        href="/dashboard/site/pages"
        icon={FileText}
        title="Pages"
        blurb="Every page the crawl has read, and what the passages inside them say."
      >
        {pages > 0 && <Badge tone="neutral">{pages} pages</Badge>}
      </SectionCard>

      <SectionCard
        href="/dashboard/site/structure"
        icon={Network}
        title="Internal links"
        blurb="How pages are reached from the home page — orphans, unreachable pages, and pages buried too deep."
      >
        {discovery && discovery.live > 0 && (
          <Badge tone={blocked > 0 ? "warn" : "good"}>
            {blocked > 0 ? `${blocked} hard to reach` : "all reachable"}
          </Badge>
        )}
      </SectionCard>

      <SectionCard
        href="/dashboard/site/technical-seo"
        icon={ShieldCheck}
        title="Technical SEO"
        blurb="Every check that can be answered from the pages already read."
      >
        {summary && <Badge tone={open > 0 ? "warn" : "good"}>{open} open</Badge>}
        {rejected > 0 && <Badge tone="neutral">{rejected} turned down</Badge>}
      </SectionCard>

    </Stagger>
  );
}

function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: BadgeTone;
}) {
  return (
    <Card className="space-y-1 stagger-item">
      <div className="text-xs uppercase tracking-wide text-sub">{label}</div>
      <div className="text-2xl font-semibold">{value}</div>
      {hint && (
        <div className="text-xs text-sub">{tone ? <Badge tone={tone}>{hint}</Badge> : hint}</div>
      )}
    </Card>
  );
}
