"use client";

import { useState } from "react";
import Link from "next/link";
import { ArrowRight, Sparkles, X } from "lucide-react";
import { PageEnter, Stagger } from "@demo/components/animate";
import { Card, IconButton, PageHeader, Spinner, StatCard } from "@demo/components/ui";
import { useApi } from "@demo/lib/use-api";
import { WEBSITE_DESKS } from "@demo/components/desks";
import type { SiteProfile } from "@demo/lib/types";

interface Stats {
  site?: { pages?: number; needsReading?: number };
  pages?: { open?: number; verified?: number; rejected?: number };
  analytics?: { sources?: number; reports?: number };
  content?: { drafts?: number; blocked?: number };
}

function num(n: number | undefined): string {
  return n === undefined || n === null ? "—" : n.toLocaleString();
}

function count(n: number | undefined, one: string, many = `${one}s`): string {
  if (n === undefined) return `— ${many}`;
  return `${n.toLocaleString()} ${n === 1 ? one : many}`;
}

export default function OverviewPage() {
  const [bannerDismissed, setBannerDismissed] = useState(false);

  const { data: stats, loading: statsLoading, error: statsError } = useApi<Stats>("/api/v1/stats");
  const { data: site, loading: siteLoading } = useApi<SiteProfile | null>("/api/v1/site");

  if (statsLoading || siteLoading) {
    return (
      <PageEnter>
        <Spinner />
      </PageEnter>
    );
  }

  const content = stats?.content ?? {};
  const pages = stats?.pages ?? {};

  const waiting = [
    {
      label: "Pieces in draft",
      value: content.drafts,
      hint: content.blocked ? `${content.blocked} blocked by channel limits` : undefined,
    },
    {
      label: "Page issues open",
      value: pages.open,
    },
  ];

  const line: Record<string, string> = {
    site: `${count(stats?.site?.pages, "page")} · ${num(stats?.site?.needsReading)} need reading`,
    pages: `${num(pages.open)} open · ${num(pages.verified)} verified fixed`,
    content: `${num(content.drafts)} in draft · ${num(content.blocked)} blocked`,
    analytics: `${count(stats?.analytics?.sources, "source")} · ${num(stats?.analytics?.reports)} saved`,
  };

  const desks = WEBSITE_DESKS.filter((d) => d.id !== "overview");

  return (
    <PageEnter>
      <PageHeader
        title={site?.name || "Good to see you"}
        description={
          site?.domain
            ? site.domain
            : "Add a website from the picker at the top of the sidebar."
        }
      />

      {statsError && <p className="text-sm text-bad mb-4">{statsError}</p>}

      {!site && !bannerDismissed && (
        <div className="relative rounded-2xl border border-accent/30 bg-accent-soft p-5 mb-6">
          <div className="flex items-start gap-3 pr-8">
            <Sparkles size={18} className="text-accent mt-0.5 shrink-0" />
            <div>
              <p className="text-sm font-medium text-ink">
                Let&apos;s get your coworker up to speed.
              </p>
              <p className="text-sm text-sub mt-1">
                Add a website from the switcher above — Meelu reads it straight away. Then{" "}
                <Link href="/demo/dashboard/settings" className="text-accent hover:underline">
                  fill in your profile and connect the MCP server
                </Link>{" "}
                so your coworker can start working as you.
              </p>
            </div>
          </div>
          <IconButton
            className="absolute top-3 right-3"
            aria-label="Dismiss"
            onClick={() => setBannerDismissed(true)}
          >
            <X size={14} />
          </IconButton>
        </div>
      )}

      <div className="flex items-baseline gap-2 mb-3">
        <h2 className="font-display text-lg text-ink">Waiting on you</h2>
        <span className="text-xs text-faint">nothing here was decided by an agent</span>
      </div>
      <Stagger className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {waiting.map((stat) => (
          <StatCard
            key={stat.label}
            label={stat.label}
            value={num(stat.value)}
            hint={stat.hint}
          />
        ))}
      </Stagger>

      <h2 className="font-display text-lg text-ink mb-3">Desks</h2>
      <Stagger className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3 mb-6">
        {desks.map((desk) => {
          const Icon = desk.icon;
          return (
            <Link key={desk.href} href={desk.href} className="stagger-item group block">
              <Card className="h-full hover:border-edge2 transition-colors">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2.5 min-w-0">
                    <Icon size={16} className="text-accent shrink-0" />
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-ink">{desk.label}</p>
                      <p className="text-xs text-sub mt-0.5 truncate">{line[desk.id] ?? desk.blurb}</p>
                    </div>
                  </div>
                  <ArrowRight
                    size={14}
                    className="text-faint group-hover:text-accent transition-colors shrink-0"
                  />
                </div>
              </Card>
            </Link>
          );
        })}
      </Stagger>

    </PageEnter>
  );
}

