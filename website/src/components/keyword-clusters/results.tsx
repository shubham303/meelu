"use client";

import { useMemo, useState } from "react";
import { ChevronDown, Download, FileSpreadsheet, Search } from "lucide-react";
import { FLAG_LABEL, clusterFileStem, clustersCsv, droppedCsv } from "@/lib/keyword-clusters/csv";
import type {
  ClusterFlag,
  ClusterFlagKind,
  ClusterRunResult,
  KeywordCluster,
  SearchIntent,
} from "@/lib/keyword-clusters/types";

function download(name: string, body: string) {
  const blob = new Blob([`﻿${body}`], { type: "text/csv;charset=utf-8;" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

const number = (n: number | null | undefined) => (n === null || n === undefined ? "–" : n.toLocaleString("en-US"));
const money = (n: number | null | undefined) => (n === null || n === undefined ? "–" : `$${n.toFixed(2)}`);

const FLAG_TONE: Record<ClusterFlagKind, string> = {
  "serp-overlaps-other-intent": "border-accent/25 bg-accent/5 text-accent",
  "serp-splits-cluster": "border-warn/25 bg-warn/5 text-warn",
  "serp-overlaps-other-cluster": "border-edge2 bg-panel2 text-sub",
  "merged-volume": "border-warn/25 bg-warn/5 text-warn",
  "not-split": "border-edge2 bg-panel2 text-sub",
};

const INTENT_TONE: Record<SearchIntent, string> = {
  informational: "border-accent/25 bg-accent/10 text-accent",
  commercial: "border-warn/25 bg-warn/10 text-warn",
  transactional: "border-good/25 bg-good/10 text-good",
  navigational: "border-edge2 bg-panel2 text-sub",
};

const DROP_LABEL = {
  "low-volume": "Below min. Ads volume",
  "low-clickstream": "Below min. real searches",
  irrelevant: "Off-topic for its seed",
  "over-cap": "Over the keyword cap",
} as const;

type View = "all" | "flagged" | "serp";

export function ClusterResults({ result, onReset }: { result: ClusterRunResult; onReset: () => void }) {
  const [view, setView] = useState<View>("all");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<string | null>(result.clusters[0]?.id ?? null);
  const stem = clusterFileStem(result);
  const { caps } = result;
  const realVolume = caps.clickstreamChecked;

  const flagged = result.clusters.filter((c) => c.flags.length > 0).length;
  const checked = result.clusters.filter((c) => c.serpChecked).length;
  const disagreements = result.clusters.filter((c) =>
    c.flags.some((f) => f.kind === "serp-overlaps-other-intent" || f.kind === "serp-splits-cluster"),
  ).length;

  const rows = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return result.clusters.filter((c) => {
      if (view === "flagged" && c.flags.length === 0) return false;
      if (view === "serp" && !c.serpChecked) return false;
      if (!needle) return true;
      return (
        c.label.toLowerCase().includes(needle) ||
        c.keywords.some((k) => k.keyword.includes(needle))
      );
    });
  }, [result.clusters, view, query]);

  const byId = useMemo(() => new Map(result.clusters.map((c) => [c.id, c])), [result.clusters]);
  const serpOf = useMemo(() => new Map(result.serps.map((s) => [s.keyword, s.urls])), [result.serps]);

  return (
    <div className="mt-8">
      <section className="rounded-2xl border border-edge bg-panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="text-center">
              <p className="font-display text-5xl leading-none text-ink">{result.clusters.length}</p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-faint">
                Page clusters
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-ink">{result.input.seeds.join(", ")}</p>
              <p className="mt-1 text-sm text-sub">
                {caps.keywordsKept} keywords · {result.locationName} ·{" "}
                {result.input.languageCode.toUpperCase()} · {(result.durationMs / 1000).toFixed(0)}s
              </p>
              <p className="mt-1 text-xs text-sub">
                {disagreements} where Google&rsquo;s results and the intent split disagree ·{" "}
                {checked} checked against the SERP
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => download(`${stem}.csv`, clustersCsv(result))}
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
            >
              <Download size={14} />
              Clusters CSV
            </button>
            <button
              type="button"
              onClick={() => download(`${stem}-removed.csv`, droppedCsv(result))}
              disabled={result.dropped.length === 0}
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink transition-colors hover:bg-panel2 disabled:cursor-not-allowed disabled:text-faint"
            >
              <FileSpreadsheet size={14} />
              Removed keywords CSV
            </button>
            <button
              type="button"
              onClick={onReset}
              className="rounded-lg px-3 py-2 text-sm text-sub transition-colors hover:bg-panel2 hover:text-ink"
            >
              New run
            </button>
          </div>
        </div>

        <p className="mt-5 rounded-xl border border-edge bg-bg/60 p-3 text-xs leading-relaxed text-sub">
          These are suggestions, not decisions. Each cluster is a page the data supports. The flags
          show where the evidence pulls different ways, so you can judge them yourself.
          {realVolume
            ? " Clusters are ranked by clickstream volume, the searches people actually typed for each exact phrase."
            : " Clickstream volume was not available, so clusters are ranked by Google Ads volume."}
        </p>

        <CapsPanel result={result} />
      </section>

      <div className="mt-6 flex flex-wrap items-center gap-2">
        {(
          [
            ["all", `All (${result.clusters.length})`],
            ["flagged", `Flagged (${flagged})`],
            ["serp", `SERP checked (${checked})`],
          ] as const
        ).map(([key, label]) => (
          <button
            key={key}
            type="button"
            onClick={() => setView(key)}
            className={`rounded-full border px-3 py-1.5 text-xs transition-colors ${
              view === key
                ? "border-accent bg-accent/10 text-accent"
                : "border-edge2 bg-panel text-sub hover:bg-panel2"
            }`}
          >
            {label}
          </button>
        ))}
        <label className="relative ml-auto w-full sm:w-64">
          <span className="sr-only">Filter clusters</span>
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-faint" />
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter by keyword"
            className="h-9 w-full rounded-lg border border-edge2 bg-panel pl-8 pr-3 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none"
          />
        </label>
      </div>

      <ol className="mt-4 flex flex-col gap-3">
        {rows.map((cluster) => (
          <ClusterCard
            key={cluster.id}
            cluster={cluster}
            open={open === cluster.id}
            onToggle={() => setOpen(open === cluster.id ? null : cluster.id)}
            byId={byId}
            serpOf={serpOf}
            onJump={(id) => {
              setView("all");
              setQuery("");
              setOpen(id);
              window.setTimeout(() => document.getElementById(`cluster-${id}`)?.scrollIntoView({ behavior: "smooth", block: "start" }), 50);
            }}
          />
        ))}
        {rows.length === 0 && (
          <li className="rounded-2xl border border-edge bg-panel p-5 text-sm text-sub">
            No cluster matches that filter.
          </li>
        )}
      </ol>

      {result.dropped.length > 0 && <DroppedList result={result} />}

      {result.notes.length > 0 && (
        <ul className="mt-6 space-y-1.5 text-xs text-faint">
          {result.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      )}

      <p className="mt-4 text-xs text-faint">
        {Math.max(0, result.dailyRuns.limit - result.dailyRuns.used)} of {result.dailyRuns.limit} runs
        left today across everyone. The count resets at midnight UTC.
      </p>
    </div>
  );
}

function CapsPanel({ result }: { result: ClusterRunResult }) {
  const { caps } = result;
  const items: Array<{ label: string; value: string; capped: boolean }> = [
    {
      label: "Seeds",
      value: `${caps.seedsUsed} of ${caps.seedsGiven} used (max ${caps.maxSeeds})`,
      capped: caps.seedsGiven > caps.seedsUsed,
    },
    {
      label: "Keywords found",
      value: `${caps.keywordsFound}, ${caps.keywordsKept} clustered (max ${caps.maxKeywords})`,
      capped: caps.droppedOverCap > 0,
    },
    {
      label: "Removed",
      value: `${caps.droppedLowVolume + caps.droppedLowClickstream} low volume · ${caps.droppedIrrelevant} off-topic · ${caps.droppedOverCap} over cap`,
      capped: false,
    },
    {
      label: "Intent split",
      value: `${caps.groupsSplit} core groups split${caps.groupsNotSplit > 0 ? `, ${caps.groupsNotSplit} not (max ${caps.maxSplitGroups})` : ""}`,
      capped: caps.groupsNotSplit > 0,
    },
    {
      label: "SERP checks",
      value: `${caps.serpCalls} of ${caps.maxSerpCalls} Google top-10 lookups`,
      capped: result.clusters.some((c) => !c.serpChecked),
    },
  ];
  return (
    <dl className="mt-4 grid gap-2 text-xs sm:grid-cols-2 lg:grid-cols-3">
      {items.map((item) => (
        <div key={item.label} className="rounded-lg border border-edge bg-bg/40 px-3 py-2">
          <dt className="font-mono text-[10px] uppercase tracking-widest text-faint">
            {item.label}
            {item.capped && <span className="ml-1.5 text-warn">capped</span>}
          </dt>
          <dd className="mt-0.5 text-sub">{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}

function FlagItem({
  flag,
  byId,
  onJump,
}: {
  flag: ClusterFlag;
  byId: Map<string, KeywordCluster>;
  onJump: (id: string) => void;
}) {
  const other = flag.otherClusterId ? byId.get(flag.otherClusterId) : undefined;
  return (
    <li className={`rounded-lg border px-3 py-2 text-xs leading-relaxed ${FLAG_TONE[flag.kind]}`}>
      <span className="font-medium">{FLAG_LABEL[flag.kind]}.</span>{" "}
      <span className="text-ink/80">{flag.message}</span>
      {other && (
        <button
          type="button"
          onClick={() => onJump(other.id)}
          className="ml-1.5 underline decoration-dotted underline-offset-2 hover:text-ink"
        >
          Go to &ldquo;{other.label}&rdquo;
        </button>
      )}
    </li>
  );
}

function ClusterCard({
  cluster,
  open,
  onToggle,
  byId,
  serpOf,
  onJump,
}: {
  cluster: KeywordCluster;
  open: boolean;
  onToggle: () => void;
  byId: Map<string, KeywordCluster>;
  serpOf: Map<string, string[]>;
  onJump: (id: string) => void;
}) {
  const headUrls = serpOf.get(cluster.headKeyword);
  return (
    <li id={`cluster-${cluster.id}`} className="scroll-mt-24 rounded-2xl border border-edge bg-panel">
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex w-full flex-wrap items-start justify-between gap-4 p-5 text-left"
      >
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-[11px] text-faint">{cluster.id}</span>
            <h3 className="text-base font-medium text-ink">{cluster.label}</h3>
            {cluster.searchIntent && (
              <span
                className={`rounded-full border px-2 py-0.5 font-mono text-[10px] ${INTENT_TONE[cluster.searchIntent]}`}
              >
                {cluster.searchIntent}
              </span>
            )}
            {cluster.flags.length > 0 && (
              <span className="rounded-full border border-warn/25 bg-warn/5 px-2 py-0.5 font-mono text-[10px] text-warn">
                {cluster.flags.length} flag{cluster.flags.length === 1 ? "" : "s"}
              </span>
            )}
          </div>
          {cluster.intent && <p className="mt-1 text-sm text-sub">{cluster.intent}</p>}
          <p className="mt-1.5 truncate text-xs text-faint">
            {cluster.keywords.map((k) => k.keyword).join(" · ")}
          </p>
        </div>
        <div className="flex shrink-0 items-start gap-5 text-right">
          <Stat label="Real searches" value={number(cluster.clickstreamVolume)} />
          <Stat label="Ads volume" value={number(cluster.adsVolume)} />
          <Stat label="CPC" value={money(cluster.cpc)} />
          <ChevronDown
            size={16}
            className={`mt-1 text-faint transition-transform ${open ? "rotate-180" : ""}`}
          />
        </div>
      </button>

      {open && (
        <div className="border-t border-edge px-5 pb-5 pt-4">
          {cluster.flags.length > 0 && (
            <ul className="mb-4 flex flex-col gap-2">
              {cluster.flags.map((flag, i) => (
                <FlagItem key={`${flag.kind}-${i}`} flag={flag} byId={byId} onJump={onJump} />
              ))}
            </ul>
          )}

          <div className="overflow-x-auto">
            <table className="w-full min-w-[520px] text-left text-sm">
              <thead>
                <tr className="font-mono text-[10px] uppercase tracking-widest text-faint">
                  <th className="pb-2 font-normal">Keyword</th>
                  <th className="pb-2 text-right font-normal">Real searches</th>
                  <th className="pb-2 text-right font-normal">Ads volume</th>
                  <th className="pb-2 text-right font-normal">CPC</th>
                  <th className="pb-2 pl-3 font-normal">Intent</th>
                </tr>
              </thead>
              <tbody>
                {cluster.keywords.map((k) => (
                  <tr key={k.keyword} className="border-t border-edge/70 align-top">
                    <td className="py-2 pr-3 text-ink">
                      {k.keyword}
                      {k.keyword === cluster.headKeyword && (
                        <span className="ml-1.5 font-mono text-[10px] text-faint">head</span>
                      )}
                      {k.sharedVolumeWith.length > 0 && (
                        <p className="mt-0.5 text-[11px] text-warn">
                          Ads volume shared with {k.sharedVolumeWith.slice(0, 3).join(", ")}
                          {k.sharedVolumeWith.length > 3 ? ` +${k.sharedVolumeWith.length - 3}` : ""}
                        </p>
                      )}
                    </td>
                    <td className="py-2 text-right tabular-nums text-ink">{number(k.clickstreamVolume)}</td>
                    <td className={`py-2 text-right tabular-nums ${k.sharedVolumeWith.length > 0 ? "text-warn" : "text-sub"}`}>
                      {number(k.adsVolume)}
                    </td>
                    <td className="py-2 text-right tabular-nums text-sub">{money(k.cpc)}</td>
                    <td className="py-2 pl-3 text-xs text-sub">{k.searchIntent ?? "–"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {cluster.serpPairs.length > 0 && (
            <div className="mt-4">
              <p className="font-mono text-[10px] uppercase tracking-widest text-faint">
                SERP overlap (shared organic top-10 URLs)
              </p>
              <ul className="mt-2 flex flex-col gap-1 text-xs text-sub">
                {cluster.serpPairs.map((pair) => (
                  <li key={`${pair.a}-${pair.b}`} className="flex flex-wrap gap-x-2">
                    <span className="tabular-nums text-ink">
                      {pair.shared}/{pair.compared}
                    </span>
                    <span>
                      &ldquo;{pair.a}&rdquo; vs &ldquo;{pair.b}&rdquo;
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {headUrls && (
            <details className="mt-4">
              <summary className="cursor-pointer text-xs text-accent hover:text-accent-hi">
                Google top 10 for &ldquo;{cluster.headKeyword}&rdquo;
              </summary>
              <ol className="mt-2 list-decimal space-y-1 pl-5 text-xs text-sub">
                {headUrls.map((url) => (
                  <li key={url} className="break-all">
                    <a href={url} target="_blank" rel="noopener noreferrer nofollow" className="hover:text-accent">
                      {url.replace(/^https?:\/\//, "").replace(/\?.*$/, "")}
                    </a>
                  </li>
                ))}
              </ol>
            </details>
          )}
          {!cluster.serpChecked && (
            <p className="mt-4 text-xs text-faint">
              Not checked against Google&rsquo;s results in this run: the SERP budget went to
              higher-volume clusters and split groups first.
            </p>
          )}
        </div>
      )}
    </li>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-sm tabular-nums text-ink">{value}</p>
      <p className="font-mono text-[9px] uppercase tracking-widest text-faint">{label}</p>
    </div>
  );
}

function DroppedList({ result }: { result: ClusterRunResult }) {
  return (
    <details className="mt-6 rounded-2xl border border-edge bg-panel p-5">
      <summary className="cursor-pointer text-sm font-medium text-ink">
        Removed keywords ({result.dropped.length})
      </summary>
      <p className="mt-2 text-xs text-sub">
        Kept here so you can put back anything the filters got wrong.
      </p>
      <div className="mt-3 max-h-80 overflow-auto">
        <table className="w-full min-w-[420px] text-left text-xs">
          <thead>
            <tr className="font-mono text-[10px] uppercase tracking-widest text-faint">
              <th className="pb-2 font-normal">Keyword</th>
              <th className="pb-2 text-right font-normal">Ads volume</th>
              <th className="pb-2 pl-3 font-normal">Why</th>
            </tr>
          </thead>
          <tbody>
            {result.dropped.map((d) => (
              <tr key={`${d.keyword}-${d.reason}`} className="border-t border-edge/70">
                <td className="py-1.5 pr-3 text-ink">{d.keyword}</td>
                <td className="py-1.5 text-right tabular-nums text-sub">{number(d.adsVolume)}</td>
                <td className="py-1.5 pl-3 text-sub">
                  {DROP_LABEL[d.reason]}
                  {d.reason === "low-clickstream" && d.clickstreamVolume !== undefined
                    ? ` (${number(d.clickstreamVolume)})`
                    : ""}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
