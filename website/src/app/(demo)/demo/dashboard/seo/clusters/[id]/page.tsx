"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { ArrowLeft } from "lucide-react";
import { PageEnter, Stagger } from "@demo/components/animate";
import {
  Badge,
  Button,
  Card,
  ConfirmDelete,
  PageHeader,
  Spinner,
  StatCard,
} from "@demo/components/ui";
import { api, useApi } from "@demo/lib/use-api";
import * as chips from "@demo/features/prompt-chips/seo";
import { SiteAskButton } from "../../../site/site-ask";
import { countryName } from "../../market";
import { SEO_ASK, TaskCards } from "../../task-cards";
import type { KeywordCluster } from "../../types";
import {
  IMPORTANCE_MEANING,
  INTENT_MEANING,
  ImportanceBadge,
  IntentBadge,
} from "../../signals";

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

  const members = cluster.keywords.filter((k) => k !== cluster.mainKeyword);

  return (
    <PageEnter>
      <Link
        href="/demo/dashboard/seo"
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
        ].join(" · ")}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="outline"
              disabled={busy !== null}
              onClick={() =>
                void run("track", async () => {
                  await api("/api/v1/site/seo/tracked/volumes", {
                    method: "POST",
                    body: { keywords: [cluster.mainKeyword] },
                  });
                  return "Tracked. Its demand and your Search Console position are on the Tracked keywords page.";
                })
              }
            >
              Track this keyword
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

      <Stagger className="mb-6 grid gap-3 sm:grid-cols-3">
        <StatCard
          label="Searches / mo"
          value={cluster.volume.toLocaleString()}
          hint="all keywords, clickstream"
        />
        <StatCard
          label="Keywords"
          value={cluster.keywords.length}
          hint="answered by the same pages"
        />
        <StatCard
          label="Search Console"
          value={cluster.isRanked ? "yes" : "no"}
          hint="whether you get impressions for it"
        />
      </Stagger>

      <div className="flex flex-wrap items-start gap-5">
        <div className="grid w-full gap-3.5 lg:grid-cols-2">
          <Card className="flex flex-col gap-2.5">
            <span className="text-sm font-medium text-ink">Who searches this</span>
            <span className="flex items-center gap-2 text-xs text-sub">
              <ImportanceBadge importance={cluster.importance} />
              {cluster.importance
                ? IMPORTANCE_MEANING[cluster.importance]
                : "not labelled yet"}
            </span>
            <span className="flex items-center gap-2 text-xs text-sub">
              <IntentBadge intent={cluster.intent} />
              {cluster.intent ? INTENT_MEANING[cluster.intent] : "not labelled yet"}
            </span>
          </Card>
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
          <Card className="flex flex-col gap-1.5 text-xs text-sub">
            <span className="text-sm font-medium text-ink">
              Where it came from
            </span>
            <span>Seeds: {cluster.seeds.join(", ") || "—"}</span>
            <span>
              Core keyword: {cluster.coreKeyword ?? cluster.mainKeyword}
            </span>
          </Card>
        </div>
        <Button variant="danger" onClick={() => setConfirming(true)}>
          Delete cluster
        </Button>
      </div>

      <ConfirmDelete
        open={confirming}
        onClose={() => setConfirming(false)}
        what={`the cluster "${cluster.mainKeyword}"`}
        onConfirm={async () => {
          await api(`/api/v1/site/seo/clusters/${cluster.id}`, {
            method: "DELETE",
          });
          router.push("/demo/dashboard/seo");
        }}
      />
    </PageEnter>
  );
}
