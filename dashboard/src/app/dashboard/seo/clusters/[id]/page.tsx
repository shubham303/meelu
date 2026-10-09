"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import {
  Badge,
  Button,
  Card,
  ConfirmDelete,
  PageHeader,
  Spinner,
  StatCard,
} from "@/components/ui";
import { api, useApi } from "@/lib/use-api";
import { cn, formatRelative } from "@/lib/utils";
import * as chips from "@/features/prompt-chips/seo";
import { SiteAskButton } from "../../../site/site-ask";
import { countryName } from "../../market";
import { SEO_ASK, TaskCards } from "../../task-cards";
import type { ClimbResult, KeywordCluster } from "../../types";
import { percent, position } from "../../winnability";

const FIT: Record<
  string,
  { label: string; tone: "neutral" | "warn" | "good" }
> = {
  "1": { label: "fits intent", tone: "neutral" },
  "0.5": { label: "partly fits", tone: "warn" },
  "0": { label: "misses intent", tone: "good" },
};

function passTone(chance: number): string {
  if (chance >= 0.6) return "bg-good";
  if (chance >= 0.35) return "bg-warn";
  return "bg-bad";
}

export default function ClusterDetailPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const {
    data: cluster,
    loading,
    error,
    refresh,
  } = useApi<KeywordCluster>(`/api/v1/site/seo/clusters/${id}`);
  const [busy, setBusy] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [confirming, setConfirming] = useState(false);

  async function run(key: string, action: () => Promise<string>) {
    setBusy(key);
    setStatus(null);
    try {
      setStatus(await action());
    } catch (e) {
      setStatus(e instanceof Error ? e.message : "Something went wrong");
    } finally {
      setBusy(null);
    }
  }

  if (loading && !cluster) {
    return (
      <div className="flex justify-center py-16">
        <Spinner />
      </div>
    );
  }
  if (error || !cluster)
    return <p className="text-sm text-bad">{error ?? "Not found"}</p>;

  const scored = cluster.metricsAt !== undefined;
  const members = cluster.keywords.filter((k) => k !== cluster.mainKeyword);

  return (
    <PageEnter>
      <Link
        href="/dashboard/seo"
        className="mb-3 inline-flex items-center gap-1.5 text-sm text-sub hover:text-ink"
      >
        <ArrowLeft size={14} /> SEO
      </Link>
      <PageHeader
        title={cluster.mainKeyword}
        description={[
          `${cluster.keywords.length} keywords`,
          `${cluster.volume.toLocaleString()} searches a month`,
          `${countryName(cluster.country)}, ${cluster.languageCode}`,
          scored
            ? `scored ${formatRelative(cluster.metricsAt)}`
            : "not scored yet",
        ].join(" · ")}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              disabled={busy !== null}
              onClick={() =>
                void run("track", async () => {
                  await api("/api/v1/site/seo/tracked/rankings", {
                    method: "POST",
                    body: { keywords: [cluster.mainKeyword] },
                  });
                  return "Tracking started. Rankings land on the Tracked keywords page.";
                })
              }
            >
              Track its ranking
            </Button>
            <Button
              variant="outline"
              disabled={busy !== null}
              onClick={() =>
                void run("score", async () => {
                  await api(`/api/v1/site/seo/clusters/${cluster.id}/metrics`, {
                    method: "POST",
                  });
                  await refresh();
                  return "Scored.";
                })
              }
            >
              {scored ? "Rescore" : "Score"}
            </Button>
            <SiteAskButton
              title={`Ask — ${cluster.mainKeyword}`}
              hint="Ask about this cluster: what page would win it, and why."
              suggestions={chips.cluster(cluster.mainKeyword)}
              endpoint={SEO_ASK}
              onRan={() => void refresh()}
            />
          </div>
        }
      />
      {status && (
        <p className="-mt-3 mb-4 text-sm text-sub">
          {busy ? "Working…" : status}
        </p>
      )}

      <TaskCards
        title="Start a task on this cluster"
        chips={chips.cluster(cluster.mainKeyword)}
        onRan={() => void refresh()}
      />

      <Stagger className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          label="Winnability"
          value={
            cluster.winnability !== undefined
              ? Math.round(cluster.winnability)
              : "—"
          }
          hint="out of 100"
        />
        <StatCard
          label="Likely spot"
          value={position(cluster.likelyPosition)}
          hint="where a good page probably lands"
        />
        <StatCard
          label="Top 3 chance"
          value={percent(cluster.pTopThree)}
          hint="P(top three)"
        />
        <StatCard
          label="Page one chance"
          value={percent(cluster.pPageOne)}
          hint="P(page one)"
        />
        <StatCard
          label="Searches / mo"
          value={cluster.volume.toLocaleString()}
          hint="main keyword, clickstream"
        />
      </Stagger>

      <div className="flex flex-wrap items-start gap-5">
        <Card className="min-w-0 flex-[999_1_640px] overflow-hidden p-0">
          <div className="border-b border-edge px-4 py-4">
            <h2 className="font-display text-lg text-ink">The climb</h2>
            <p className="mt-0.5 text-xs text-sub">
              {cluster.ourPosition
                ? `Your page ranks #${cluster.ourPosition} with a strength of ${cluster.ourStrength ?? 0}. Each result above it, and the chance of passing it.`
                : `A new page starts below the top 10 with your domain's strength (${cluster.ourStrength ?? 0}). Each result above it, and the chance of passing it.`}
            </p>
          </div>
          {scored ? (
            <Climb results={cluster.climb} />
          ) : (
            <p className="px-4 py-8 text-center text-sm text-sub">
              Score this cluster to see the results above you.
            </p>
          )}
          <p className="border-t border-edge px-4 py-3 text-xs text-sub">
            A result that misses the search intent is easy to pass however
            strong its links. Strengths above a stronger result are smoothed,
            because Google already ranked them higher.
          </p>
        </Card>

        <aside className="flex min-w-0 flex-[1_1_300px] flex-col gap-3.5">
          <Card className="flex flex-col gap-2.5">
            <span className="text-sm font-medium text-ink">
              Keywords in this cluster
            </span>
            <span className="text-xs text-sub">
              Google answers these with the same pages. One page targets them
              all, led by the main keyword.
            </span>
            <span className="flex flex-wrap gap-1.5">
              <Badge tone="accent">{cluster.mainKeyword} · main</Badge>
              {members.map((k) => (
                <Badge key={k}>{k}</Badge>
              ))}
            </span>
          </Card>
          <Card className="flex flex-col gap-2.5">
            <span className="flex items-center justify-between">
              <span className="text-sm font-medium text-ink">Competitors ranking here</span>
              <Badge tone={cluster.isRanked ? "good" : "neutral"}>
                {cluster.isRanked ? "you rank" : "you don't rank"}
              </Badge>
            </span>
            {cluster.competitors.length ? (
              <span className="flex flex-wrap gap-1.5">
                {cluster.competitors.map((d) => (
                  <Badge key={d}>{d}</Badge>
                ))}
              </span>
            ) : (
              <span className="text-xs text-sub">None of your saved competitors ranks for it.</span>
            )}
          </Card>
          <Card className="flex flex-col gap-1.5 text-xs text-sub">
            <span className="text-sm font-medium text-ink">
              Where it came from
            </span>
            <span>Seeds: {cluster.seeds.join(", ") || "—"}</span>
            <span>
              Core keyword: {cluster.coreKeyword ?? cluster.mainKeyword}
            </span>
            <span>
              {cluster.ourUrl ? (
                <>
                  Your ranking page:{" "}
                  <a
                    href={cluster.ourUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-accent"
                  >
                    {cluster.ourUrl}
                  </a>
                </>
              ) : (
                "None of your pages ranks in the top 30 yet."
              )}
            </span>
          </Card>
          <Button
            variant="danger"
            className="self-start"
            onClick={() => setConfirming(true)}
          >
            Delete cluster
          </Button>
        </aside>
      </div>

      <ConfirmDelete
        open={confirming}
        onClose={() => setConfirming(false)}
        what={`the cluster "${cluster.mainKeyword}"`}
        onConfirm={async () => {
          await api(`/api/v1/site/seo/clusters/${cluster.id}`, {
            method: "DELETE",
          });
          router.push("/dashboard/seo");
        }}
      />
    </PageEnter>
  );
}

function Climb({ results }: { results: ClimbResult[] }) {
  const top = results.filter((c) => c.position <= 10);
  if (!top.length) {
    return (
      <p className="px-4 py-8 text-center text-sm text-sub">
        Nothing ranks above you here.
      </p>
    );
  }
  return (
    <div className="overflow-x-auto">
      <table className="w-full min-w-[760px] border-collapse text-sm">
        <thead>
          <tr className="text-left text-xs uppercase tracking-wide text-sub">
            <th className="px-4 py-2.5 font-medium">#</th>
            <th className="px-3 py-2.5 font-medium">Result</th>
            <th className="px-3 py-2.5 text-right font-medium">Page rank</th>
            <th className="px-3 py-2.5 text-right font-medium">Domain rank</th>
            <th className="px-3 py-2.5 font-medium">Intent</th>
            <th className="px-4 py-2.5 font-medium">Chance to pass</th>
          </tr>
        </thead>
        <tbody>
          {top.map((c) => {
            const fit = FIT[String(c.intentFit)] ?? FIT["1"];
            return (
              <tr key={c.position} className="border-t border-edge">
                <td className="px-4 py-2.5 tabular-nums text-faint">
                  {c.position}
                </td>
                <td className="max-w-80 px-3 py-2.5">
                  <a
                    href={c.url}
                    target="_blank"
                    rel="noreferrer"
                    className="block truncate font-medium text-ink hover:text-accent"
                  >
                    {c.title ?? c.url}
                  </a>
                  <span className="block text-xs text-faint">{c.domain}</span>
                </td>
                <td className="px-3 py-2.5 text-right tabular-nums">
                  {c.pageRank ?? 0}
                </td>
                <td className="px-3 py-2.5 text-right tabular-nums">
                  {c.domainRank ?? 0}
                </td>
                <td className="px-3 py-2.5">
                  <Badge tone={fit.tone}>{fit.label}</Badge>
                </td>
                <td className="px-4 py-2.5">
                  <span className="flex items-center gap-2">
                    <span className="h-2 w-28 overflow-hidden rounded-full bg-panel2">
                      <span
                        className={cn(
                          "block h-2 rounded-full",
                          passTone(c.passChance),
                        )}
                        style={{ width: `${Math.round(c.passChance * 100)}%` }}
                      />
                    </span>
                    <span className="tabular-nums text-sub">
                      {Math.round(c.passChance * 100)}%
                    </span>
                  </span>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
