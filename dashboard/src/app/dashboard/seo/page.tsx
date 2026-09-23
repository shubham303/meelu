"use client";

import { useState } from "react";
import { Search as SearchIcon, ArrowRight, Sparkles } from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import {
  Badge,
  Card,
  PageHeader,
  Spinner,
  Tabs,
  type BadgeTone,
} from "@/components/ui";
import { useApi } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import { formatRelative } from "@/lib/utils";
import type { SeoOverview } from "@/lib/types";
import * as chips from "@/features/prompt-chips/seo";
import { SiteAskButton } from "../site/site-ask";
import { useAgentTasks } from "../agent-tasks";
import { PageSuggestions } from "./page-suggestions";
import { Keywords } from "./keywords";

type TabKey = "suggestions" | "keywords";

export default function SeoPage() {
  const [tab, setTab] = useState<TabKey>("suggestions");
  const { data, loading, error, refresh } = useApi<SeoOverview>(
    "/api/v1/seo/overview",
  );
  const ready = data
    ? (data.suggestions.add.ready ?? 0) +
      (data.suggestions.edit.ready ?? 0) +
      (data.suggestions.delete.ready ?? 0)
    : 0;

  return (
    <PageEnter>
      <PageHeader
        title="SEO"
        description="Which page to add, edit or merge. Every suggestion is grounded in Search Console, the keyword table and the search results the agent stored."
        actions={
          <SiteAskButton
            title="SEO"
            hint="Pick a strategy or write your own. The agent runs it through the suggestion pipeline and the results land below."
            suggestions={chips.seo()}
            endpoint="/api/agent/ask-seo"
            onRan={refresh}
          />
        }
      />

      {loading && !data && (
        <div className="flex justify-center py-14">
          <Spinner />
        </div>
      )}
      {error && <p className="text-sm text-bad">{error}</p>}
      {data && (
        <Stagger className="mb-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Stat
            label="Ready"
            value={ready}
            hint="waiting on you"
            tone={ready > 0 ? "accent" : "neutral"}
          />
          <Stat
            label="Keywords"
            value={data.keywords}
            hint={`${data.keywordsWithFacts} with facts`}
            tone="neutral"
          />
          <Stat
            label="Clusters"
            value={data.clusters}
            hint={
              data.state.embeddedAt
                ? `built ${formatRelative(data.state.embeddedAt)}`
                : "not built yet"
            }
            tone={data.state.embeddedAt ? "good" : "warn"}
          />
          <Stat
            label="Competitors"
            value={data.competitorsConfirmed}
            hint="confirmed"
            tone="neutral"
          />
        </Stagger>
      )}

      <Strategies onRan={refresh} />

      <Tabs
        active={tab}
        onChange={(k) => setTab(k as TabKey)}
        tabs={[
          { key: "suggestions", label: "Suggestions", count: ready },
          { key: "keywords", label: "Keywords", count: data?.keywords ?? 0 },
        ]}
      />
      {tab === "suggestions" && <PageSuggestions onChanged={refresh} />}
      {tab === "keywords" && (
        <Keywords state={data?.state ?? null} onChanged={refresh} />
      )}
    </PageEnter>
  );
}

function Strategies({ onRan }: { onRan: () => void }) {
  const isApp = useIsApp();
  const { launchTask } = useAgentTasks();
  if (!isApp) return null;
  const strategies = chips.seo();
  return (
    <div className="mb-8">
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 className="font-display text-lg text-ink">Strategies</h2>
        <span className="text-xs text-faint">
          Pick one. The first spends no vendor credit.
        </span>
      </div>
      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {strategies.map((s) => (
          <button
            key={s.label}
            type="button"
            onClick={() =>
              launchTask({
                title: `SEO — ${s.label}`,
                endpoint: "/api/agent/ask-seo",
                emptyHint: s.blurb ?? s.label,
                suggestions: strategies,
                draft: {},
                autoStart: s.prompt,
                onCreated: onRan,
              })
            }
            className="group flex items-start gap-3 rounded-lg border border-edge bg-panel p-3 text-left transition hover:border-accent/40 hover:bg-accent-soft/40"
          >
            <span className="mt-0.5 rounded-md bg-accent-soft p-1.5 text-accent">
              <Sparkles size={14} />
            </span>
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-1 text-sm font-medium text-ink">
                {s.label}
                <ArrowRight
                  size={12}
                  className="opacity-0 transition group-hover:translate-x-0.5 group-hover:opacity-100"
                />
              </span>
              <span className="mt-0.5 block text-xs text-sub">{s.blurb}</span>
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}

function Stat({
  label,
  value,
  hint,
  tone,
}: {
  label: string;
  value: number;
  hint: string;
  tone: BadgeTone;
}) {
  return (
    <Card className="space-y-1 stagger-item">
      <div className="flex items-center gap-1.5 text-xs uppercase tracking-wide text-sub">
        <SearchIcon size={13} className="text-accent" />
        {label}
      </div>
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-xs">
        <Badge tone={tone}>{hint}</Badge>
      </div>
    </Card>
  );
}
