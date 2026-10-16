"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowLeft, ExternalLink, Network, Unlink, Waypoints, Layers } from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Badge, Card, EmptyState, Spinner, PageHeader, Tabs } from "@demo/components/ui";
import { useApi } from "@demo/lib/use-api";
import { cn } from "@demo/lib/utils";
import { SiteAskButton } from "../site-ask";
import { YourPrompts } from "@demo/features/user-prompts/your-prompts";
import type { SiteDiscovery, SiteDiscoveryPage, SuggestionSummary } from "@demo/lib/types";
import * as chips from "@demo/features/prompt-chips/site";
import { LinkSuggestions } from "./link-suggestions";
import { LinkStrategies } from "./link-strategies";
import { PillarSuggestions } from "./pillar-suggestions";

type ListKey = "orphans" | "unreachable" | "deep";
type SectionKey = "reachability" | "links" | "pillars";

export default function SiteStructurePage() {
  const { data, loading, error } = useApi<SiteDiscovery>("/api/v1/site/pages/discovery");
  const { data: linkSummary, refresh: refreshLinkSummary } = useApi<SuggestionSummary>(
    "/api/v1/site/structure/link-suggestions/summary",
  );
  const { data: pillarSummary, refresh: refreshPillarSummary } = useApi<SuggestionSummary>(
    "/api/v1/site/structure/pillar-suggestions/summary",
  );
  const [picked, setPicked] = useState<SectionKey | null>(null);
  const [list, setList] = useState<ListKey>("orphans");

  const problems = data ? data.orphans + data.unreachable + data.deep : 0;
  const section: SectionKey = picked ?? (problems > 0 ? "reachability" : "links");

  const openList = (key: ListKey) => {
    setList(key);
    setPicked("reachability");
  };

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
            hint="Pick a link strategy or write your own. The agent runs it through the link pipeline and the results land in the suggestions."
            suggestions={chips.structure()}
            promptSurface="structure"
          />
        }
      />

      {loading && !data && (
        <div className="flex justify-center py-14">
          <Spinner />
        </div>
      )}
      {error && <p className="text-sm text-bad">{error}</p>}
      {data && data.live > 0 && <Health data={data} onPick={openList} />}
      {data && (
        <div className="mt-6">
          <Tabs
            active={section}
            onChange={(k) => setPicked(k as SectionKey)}
            tabs={[
              { key: "reachability", label: "Reachability", count: problems },
              {
                key: "links",
                label: "Link suggestions",
                count: linkSummary?.reviewApproved,
              },
              {
                key: "pillars",
                label: "Pillar pages",
                count: pillarSummary?.reviewApproved,
              },
            ]}
          />
          {section === "reachability" &&
            (data.live === 0 ? (
              <EmptyState
                icon={Network}
                title="Nothing crawled yet"
                hint="Run a crawl from the Site desk. Link structure is computed as the crawl finishes."
              />
            ) : (
              <ProblemPages data={data} list={list} onList={setList} />
            ))}
          {section === "links" && (
            <>
              <LinkStrategies title="Find links" strategies={chips.linkStrategies()} />
              <YourPrompts
                surface="structure"
                endpoint="/api/agent/ask-site"
                titlePrefix="Structure"
                suggestions={chips.structure()}
              />
              <LinkSuggestions summary={linkSummary} refreshSummary={refreshLinkSummary} />
            </>
          )}
          {section === "pillars" && (
            <>
              <LinkStrategies title="Find pillar pages" strategies={chips.pillarStrategies()} />
              <YourPrompts
                surface="structure"
                endpoint="/api/agent/ask-site"
                titlePrefix="Structure"
                suggestions={chips.structure()}
              />
              <PillarSuggestions summary={pillarSummary} refreshSummary={refreshPillarSummary} />
            </>
          )}
        </div>
      )}
    </PageEnter>
  );
}

function Health({ data, onPick }: { data: SiteDiscovery; onPick: (key: ListKey) => void }) {
  return (
    <div className="space-y-3">
      {!data.homeFound && (
        <Card className="border-warn/40 bg-warn/5 text-sm text-ink">
          The crawl did not read a home page at the root of this site, so click depth could not be
          measured. Every linked page shows as unreachable until it does.
        </Card>
      )}
      <Card className="grid gap-5 p-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:gap-6">
        <div className="grid grid-cols-3 gap-2">
          <Stat
            icon={Unlink}
            label="Orphans"
            value={data.orphans}
            hint="nothing links to them"
            onClick={() => onPick("orphans")}
          />
          <Stat
            icon={Waypoints}
            label="Unreachable"
            value={data.unreachable}
            hint="linked only from pages that are themselves unreachable"
            onClick={() => onPick("unreachable")}
          />
          <Stat
            icon={Layers}
            label={`${data.deepFrom}+ clicks deep`}
            value={data.deep}
            hint="too far from the home page"
            onClick={() => onPick("deep")}
          />
        </div>
        <DepthBars data={data} />
      </Card>
    </div>
  );
}

function ProblemPages({
  data,
  list,
  onList,
}: {
  data: SiteDiscovery;
  list: ListKey;
  onList: (key: ListKey) => void;
}) {
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
  const keys: Array<{ key: ListKey; label: string }> = [
    { key: "orphans", label: "Orphans" },
    { key: "unreachable", label: "Unreachable" },
    { key: "deep", label: `${data.deepFrom}+ clicks deep` },
  ];

  return (
    <div>
      <div className="mb-3 inline-flex rounded-lg border border-edge bg-panel p-0.5">
        {keys.map((k) => (
          <button
            key={k.key}
            type="button"
            onClick={() => onList(k.key)}
            className={cn(
              "cursor-pointer rounded-md px-2.5 py-1 text-xs transition-colors",
              list === k.key ? "bg-accent-soft text-accent" : "text-sub hover:text-ink",
            )}
          >
            {k.label}
            <span className="ml-1.5 text-faint">{lists[k.key].total}</span>
          </button>
        ))}
      </div>
      {current.pages.length === 0 ? (
        <p className="text-sm text-sub">{current.empty}</p>
      ) : (
        <PageList pages={current.pages} total={current.total} />
      )}
    </div>
  );
}

function DepthBars({ data }: { data: SiteDiscovery }) {
  const rows = data.byDepth.filter((b) => b.depth !== undefined && b.depth !== null);
  if (rows.length === 0) return null;
  const max = Math.max(...rows.map((b) => b.n), 1);
  return (
    <div>
      <div className="mb-2 flex items-center justify-between gap-3">
        <h2 className="text-xs uppercase tracking-wide text-sub">Clicks from home</h2>
        <span className="text-xs text-faint">{data.live} live pages</span>
      </div>
      <div className="space-y-1">
        {rows.map((b) => {
          const deep = (b.depth ?? 0) >= data.deepFrom;
          return (
            <div key={b.depth} className="flex items-center gap-3 text-xs">
              <span className="w-5 shrink-0 text-right tabular-nums text-sub">{b.depth}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-panel2">
                <div
                  className={cn("h-full rounded-full", deep ? "bg-warn" : "bg-accent")}
                  style={{ width: `${Math.max((b.n / max) * 100, 1)}%` }}
                />
              </div>
              <span className="w-10 shrink-0 tabular-nums text-sub">{b.n}</span>
            </div>
          );
        })}
        {data.unreachable + data.orphans > 0 && (
          <div className="flex items-center gap-3 text-xs">
            <span className="w-5 shrink-0 text-right text-faint">—</span>
            <div className="flex-1 text-faint">not reachable from home</div>
            <span className="w-10 shrink-0 tabular-nums text-sub">
              {data.unreachable + data.orphans}
            </span>
          </div>
        )}
      </div>
    </div>
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
            {p.pageType && <Badge tone="neutral">{p.pageType}</Badge>}
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
  onClick,
}: {
  icon: typeof Unlink;
  label: string;
  value: number;
  hint: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      title={hint}
      onClick={onClick}
      className="cursor-pointer space-y-1 rounded-xl border border-edge p-3 text-left transition-colors hover:border-accent/40 hover:bg-accent-soft/40"
    >
      <div className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-sub">
        <Icon size={13} className="shrink-0 text-accent" />
        <span className="truncate">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-2xl font-semibold">{value}</span>
        <Badge tone={value > 0 ? "warn" : "good"}>{value > 0 ? "fix" : "clear"}</Badge>
      </div>
    </button>
  );
}
