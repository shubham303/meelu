"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ExternalLink, Network, Unlink, Waypoints, Layers } from "lucide-react";
import { PageEnter, Stagger } from "@demo/components/animate";
import { Badge, Card, EmptyState, Spinner, PageHeader, Tabs, type BadgeTone } from "@demo/components/ui";
import { useApi } from "@demo/lib/use-api";
import { cn } from "@demo/lib/utils";
import { SiteAskButton } from "../site-ask";
import type { SiteDiscovery, SiteDiscoveryPage } from "@demo/lib/types";
import * as chips from "@demo/features/prompt-chips/site";
import { LinkSuggestions } from "./link-suggestions";
import { LinkStrategies } from "./link-strategies";
import { PillarSuggestions } from "./pillar-suggestions";

type ListKey = "orphans" | "unreachable" | "deep";

export default function SiteStructurePage() {
  const { data, loading, error } = useApi<SiteDiscovery>("/api/v1/site/pages/discovery");

  return (
    <PageEnter>
      <Link
        href="/demo/dashboard/site"
        className="mb-3 inline-flex items-center gap-1 text-xs text-sub hover:text-ink"
      >
        <ArrowLeft size={12} /> Site
      </Link>
      <PageHeader
        title="Structure"
        description="How pages are reached from the home page. A page Google cannot reach through a link earns nothing."
        actions={
          <SiteAskButton
            title="Find links — Structure"
            hint="Pick a link strategy or write your own. The agent runs it through the link pipeline and the results land in the suggestions below."
            suggestions={chips.structure()}
          />
        }
      />

      {loading && !data && (
        <div className="flex justify-center py-14">
          <Spinner />
        </div>
      )}
      {error && <p className="text-sm text-bad">{error}</p>}
      {data && data.live === 0 && (
        <EmptyState
          icon={Network}
          title="Nothing crawled yet"
          hint="Run a crawl from the Site desk. Link structure is computed as the crawl finishes."
        />
      )}
      {data && data.live > 0 && <Discovery data={data} />}
      {data && (
        <div className="mt-8">
          <LinkStrategies />
          <LinkSuggestions />
          <PillarSuggestions />
        </div>
      )}
    </PageEnter>
  );
}

function Discovery({ data }: { data: SiteDiscovery }) {
  const [list, setList] = useState<ListKey>("orphans");

  const lists: Record<ListKey, { pages: SiteDiscoveryPage[]; total: number; empty: string }> = {
    orphans: {
      pages: data.orphanPages,
      total: data.orphans,
      empty: "Every live page has at least one internal link pointing at it.",
    },
    unreachable: {
      pages: data.unreachablePages,
      total: data.unreachable,
      empty: "Every linked page can be reached from the home page.",
    },
    deep: {
      pages: data.deepPages,
      total: data.deep,
      empty: `No live page sits ${data.deepFrom} or more clicks from the home page.`,
    },
  };
  const current = lists[list];

  return (
    <div className="space-y-5">
      {!data.homeFound && (
        <Card className="border-warn/40 bg-warn/5 text-sm text-ink">
          The crawl did not read a home page at the root of this site, so click depth could not be
          measured. Every linked page shows as unreachable until it does.
        </Card>
      )}

      <Stagger className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        <Stat
          icon={Unlink}
          label="Orphans"
          value={data.orphans}
          hint="nothing links to them"
          tone={data.orphans > 0 ? "warn" : "good"}
        />
        <Stat
          icon={Waypoints}
          label="Unreachable"
          value={data.unreachable}
          hint="linked only from pages that are themselves unreachable"
          tone={data.unreachable > 0 ? "warn" : "good"}
        />
        <Stat
          icon={Layers}
          label={`${data.deepFrom}+ clicks deep`}
          value={data.deep}
          hint="too far from the home page"
          tone={data.deep > 0 ? "warn" : "good"}
        />
      </Stagger>

      <DepthBars data={data} />

      <div>
        <Tabs
          active={list}
          onChange={(k) => setList(k as ListKey)}
          tabs={[
            { key: "orphans", label: "Orphans", count: data.orphans },
            { key: "unreachable", label: "Unreachable", count: data.unreachable },
            { key: "deep", label: `${data.deepFrom}+ clicks deep`, count: data.deep },
          ]}
        />
        {current.pages.length === 0 ? (
          <p className="text-sm text-sub">{current.empty}</p>
        ) : (
          <PageList pages={current.pages} total={current.total} />
        )}
      </div>
    </div>
  );
}

function DepthBars({ data }: { data: SiteDiscovery }) {
  const rows = data.byDepth.filter((b) => b.depth !== undefined && b.depth !== null);
  if (rows.length === 0) return null;
  const max = Math.max(...rows.map((b) => b.n), 1);
  return (
    <Card>
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-lg text-ink">Clicks from home</h2>
        <span className="text-xs text-faint">{data.live} live pages</span>
      </div>
      <div className="space-y-1.5">
        {rows.map((b) => {
          const deep = (b.depth ?? 0) >= data.deepFrom;
          return (
            <div key={b.depth} className="flex items-center gap-3 text-xs">
              <span className="w-6 shrink-0 text-right tabular-nums text-sub">{b.depth}</span>
              <div className="h-3 flex-1 overflow-hidden rounded-full bg-panel2">
                <div
                  className={cn("h-full rounded-full", deep ? "bg-warn" : "bg-accent")}
                  style={{ width: `${Math.max((b.n / max) * 100, 1)}%` }}
                />
              </div>
              <span className="w-12 shrink-0 tabular-nums text-sub">{b.n}</span>
            </div>
          );
        })}
        {data.unreachable + data.orphans > 0 && (
          <div className="flex items-center gap-3 text-xs">
            <span className="w-6 shrink-0 text-right text-faint">—</span>
            <div className="flex-1 text-faint">not reachable from home</div>
            <span className="w-12 shrink-0 tabular-nums text-sub">
              {data.unreachable + data.orphans}
            </span>
          </div>
        )}
      </div>
    </Card>
  );
}

function PageList({ pages, total }: { pages: SiteDiscoveryPage[]; total: number }) {
  return (
    <div className="overflow-hidden rounded-2xl border border-edge bg-panel">
      {pages.map((p) => (
        <div
          key={p.id}
          className="flex items-center justify-between gap-3 border-b border-edge px-4 py-2.5 last:border-b-0"
        >
          <div className="min-w-0">
            <div className="flex min-w-0 items-center gap-2">
              <a
                href={p.url}
                target="_blank"
                rel="noreferrer"
                className="truncate text-sm text-ink hover:underline"
              >
                {p.title || p.url}
              </a>
              <ExternalLink size={11} className="shrink-0 text-faint" />
            </div>
            {p.title && <p className="truncate text-xs text-faint">{p.url}</p>}
          </div>
          <div className="flex shrink-0 items-center gap-1.5 text-xs">
            <Badge tone="neutral">{p.kind}</Badge>
            {p.inSitemap ? (
              <Badge tone="neutral">in sitemap</Badge>
            ) : (
              <Badge tone="warn">not in sitemap</Badge>
            )}
            <span className="text-sub">
              {p.inlinks} {p.inlinks === 1 ? "inlink" : "inlinks"}
            </span>
            {p.depth !== undefined && p.depth !== null && (
              <span className="text-sub">· {p.depth} clicks</span>
            )}
          </div>
        </div>
      ))}
      {total > pages.length && (
        <p className="px-4 py-2.5 text-xs text-faint">
          Showing the first {pages.length} of {total}.
        </p>
      )}
    </div>
  );
}

function Stat({
  icon: Icon,
  label,
  value,
  hint,
  tone,
}: {
  icon: typeof Unlink;
  label: string;
  value: number;
  hint: string;
  tone: BadgeTone;
}) {
  return (
    <Card className="space-y-1 stagger-item">
      <div className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-sub">
        <Icon size={13} className="text-accent" />
        {label}
      </div>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs">
        <Badge tone={tone}>{hint}</Badge>
      </div>
    </Card>
  );
}
