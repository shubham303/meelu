"use client";

import Link from "next/link";
import { useState } from "react";
import { ArrowLeft, LineChart } from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import {
  Badge,
  type BadgeTone,
  Card,
  EmptyState,
  Input,
  PageHeader,
  Select,
  Spinner,
  StatCard,
} from "@/components/ui";
import { useApi } from "@/lib/use-api";
import { cn, formatDate } from "@/lib/utils";
import * as chips from "@/features/prompt-chips/seo";
import { SiteAskButton } from "../../site/site-ask";
import { countryName } from "../market";
import { SEO_ASK, TaskCards } from "../task-cards";
import type { TrackedKeyword, TrackedOverview } from "../types";

type Filter = "all" | "up" | "down";

const DEMAND_TONE: Record<string, BadgeTone> = {
  rising: "good",
  steady: "neutral",
  falling: "bad",
  seasonal: "warn",
};

export default function TrackedPage() {
  const [market, setMarket] = useState<number | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [search, setSearch] = useState("");
  const { data, loading, error, refresh } = useApi<TrackedOverview>(
    `/api/v1/site/seo/tracked${market ? `?locationCode=${market}` : ""}`,
  );
  const reload = () => void refresh();

  const term = search.trim().toLowerCase();
  const rows = (data?.keywords ?? []).filter(
    (k) =>
      (!term || k.keyword.includes(term)) &&
      (filter === "all" ||
        (filter === "up" ? (k.change ?? 0) > 0 : (k.change ?? 0) < 0)),
  );

  return (
    <PageEnter>
      <Link
        href="/dashboard/seo"
        className="mb-3 inline-flex items-center gap-1.5 text-sm text-sub hover:text-ink"
      >
        <ArrowLeft size={14} /> SEO
      </Link>
      <PageHeader
        title="Tracked keywords"
        description="Where you rank, and how demand moves, for the keywords Meelu tracks. Each one keeps twelve months of history from the day it was first tracked."
        actions={
          <SiteAskButton
            title="Ask — Tracked keywords"
            hint="Ask what moved, why, and when demand peaks."
            suggestions={chips.tracked()}
            endpoint={SEO_ASK}
            onRan={reload}
          />
        }
      />
      <TaskCards title="Start a task" chips={chips.tracked()} onRan={reload} />

      {loading && !data && (
        <div className="flex justify-center py-12">
          <Spinner />
        </div>
      )}
      {error && <p className="text-sm text-bad">{error}</p>}

      {data && (
        <>
          <Stagger className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Tracked"
              value={data.stats.tracked}
              hint={`in ${countryName(currentCountry(data))}`}
            />
            <StatCard
              label="In the top 10"
              value={data.stats.topTen}
              hint="on the last run"
            />
            <StatCard
              label="Moved"
              value={data.stats.moved}
              hint="since the run before"
            />
            <StatCard
              label="Not ranking yet"
              value={data.stats.notRanking}
              hint="outside the top 30"
            />
          </Stagger>

          <Card className="overflow-hidden p-0">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-edge px-4 py-4">
              <h2 className="font-display text-lg text-ink">Keywords</h2>
              <div className="flex flex-wrap items-center gap-2">
                <label htmlFor="market" className="text-xs text-sub">
                  Market
                </label>
                <Select
                  id="market"
                  className="w-48"
                  value={data.locationCode}
                  onChange={(e) => setMarket(Number(e.target.value))}
                >
                  {data.markets.map((m) => (
                    <option
                      key={`${m.locationCode}-${m.languageCode}`}
                      value={m.locationCode}
                    >
                      {countryName(m.country)}
                    </option>
                  ))}
                </Select>
                <label className="sr-only" htmlFor="find">
                  Find a keyword
                </label>
                <Input
                  id="find"
                  type="search"
                  className="w-48"
                  placeholder="Find a keyword"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                />
                {(["all", "up", "down"] as const).map((f) => (
                  <button
                    key={f}
                    type="button"
                    onClick={() => setFilter(f)}
                    className={cn(
                      "rounded-full border px-3 py-1.5 text-xs transition-colors",
                      filter === f
                        ? "border-accent bg-accent text-white"
                        : "border-edge bg-panel text-ink hover:bg-panel2",
                    )}
                  >
                    {f === "all"
                      ? "All"
                      : f === "up"
                        ? "Going up"
                        : "Going down"}
                  </button>
                ))}
              </div>
            </div>
            {data.keywords.length === 0 ? (
              <div className="p-4">
                <EmptyState
                  icon={LineChart}
                  title="Nothing tracked in this market yet"
                  hint="Ask Meelu to track the main keywords of the clusters you plan to target."
                />
              </div>
            ) : (
              <TrackedTable rows={rows} months={data.months} />
            )}
            <p className="border-t border-edge px-4 py-3 text-xs text-sub">
              Positions are Google&apos;s top 30 on desktop, recorded on each
              tracking run. A grey bar is a month with no position in the top
              30.
            </p>
          </Card>
        </>
      )}
    </PageEnter>
  );
}

function currentCountry(data: TrackedOverview): string | undefined {
  return data.markets.find((m) => m.locationCode === data.locationCode)
    ?.country;
}

function TrackedTable({
  rows,
  months,
}: {
  rows: TrackedKeyword[];
  months: string[];
}) {
  if (!rows.length)
    return (
      <p className="px-4 py-8 text-center text-sm text-sub">
        No keyword matches.
      </p>
    );
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[900px] border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-sub">
            <th className="px-4 py-2.5 font-medium">Keyword</th>
            <th className="px-3 py-2.5 font-medium">You rank</th>
            <th className="px-3 py-2.5 font-medium">Change</th>
            <th className="px-3 py-2.5 font-medium">12-month position</th>
            <th className="px-3 py-2.5 text-right font-medium">
              Searches / mo
            </th>
            <th className="px-4 py-2.5 font-medium">Demand</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((k) => (
            <tr key={k.keyword} className="border-t border-edge">
              <td className="px-4 py-3">
                <span className="block font-medium text-ink">{k.keyword}</span>
                <span className="block max-w-72 truncate text-xs text-faint">
                  {k.url ?? "—"}
                </span>
              </td>
              <td className="px-3 py-3 font-display text-lg text-ink">
                {k.position ? (
                  `#${k.position}`
                ) : (
                  <span className="font-sans text-xs text-faint">
                    not in top 30
                  </span>
                )}
              </td>
              <td className="px-3 py-3">
                <Change value={k.change} />
              </td>
              <td className="px-3 py-3">
                <History history={k.history} months={months} />
              </td>
              <td className="px-3 py-3 text-right tabular-nums">
                {k.volume?.toLocaleString() ?? "—"}
              </td>
              <td className="px-4 py-3">
                {k.demand ? (
                  <Badge tone={DEMAND_TONE[k.demand]}>{k.demand}</Badge>
                ) : (
                  <span className="text-xs text-faint">—</span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Change({ value }: { value: number | undefined }) {
  if (!value) return <span className="text-xs text-faint">—</span>;
  return (
    <span
      className={cn(
        "text-xs font-medium",
        value > 0 ? "text-good" : "text-bad",
      )}
    >
      {value > 0 ? "▲" : "▼"} {Math.abs(value)}
    </span>
  );
}

function History({
  history,
  months,
}: {
  history: Array<number | null>;
  months: string[];
}) {
  return (
    <div
      className="flex h-8 items-end gap-[3px]"
      aria-label="Position over the last twelve months"
    >
      {history.map((p, i) => (
        <span
          key={months[i]}
          title={`${formatDate(months[i])}: ${p ? `#${p}` : "not in the top 30"}`}
          className={cn(
            "w-2 rounded-sm",
            p ? (p <= 10 ? "bg-good" : "bg-accent") : "bg-edge2",
          )}
          style={{ height: p ? Math.round(((31 - p) / 30) * 30 + 2) : 3 }}
        />
      ))}
    </div>
  );
}
