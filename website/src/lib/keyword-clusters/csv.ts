import { fileStem, toCsv } from "@/lib/csv/parse";
import type { ClusterFlagKind, ClusterRunResult } from "./types";

export const FLAG_LABEL: Record<ClusterFlagKind, string> = {
  "serp-overlaps-other-intent": "Same SERP, different intent",
  "serp-splits-cluster": "SERP splits this cluster",
  "serp-overlaps-other-cluster": "SERP overlaps another cluster",
  "merged-volume": "Ads volume shared with a variant",
  "not-split": "Not split by intent",
};

export function clustersCsv(result: ClusterRunResult): string {
  const rows: unknown[][] = [];
  for (const cluster of result.clusters) {
    const flags = [...new Set(cluster.flags.map((f) => FLAG_LABEL[f.kind]))].join("; ");
    for (const k of cluster.keywords) {
      rows.push([
        cluster.id,
        cluster.label,
        cluster.intent,
        cluster.searchIntent ?? "",
        cluster.coreKeyword,
        k.keyword,
        k.keyword === cluster.headKeyword ? "yes" : "",
        k.adsVolume,
        k.clickstreamVolume ?? "",
        k.cpc ?? "",
        k.searchIntent ?? "",
        k.sharedVolumeWith.join("; "),
        flags,
      ]);
    }
  }
  return toCsv(
    [
      "Cluster",
      "Page topic",
      "Searcher intent",
      "Search intent type",
      "Core keyword",
      "Keyword",
      "Head keyword",
      "Google Ads volume",
      "Clickstream volume",
      "CPC (USD)",
      "Keyword intent type",
      "Ads volume shared with",
      "Flags",
    ],
    rows,
  );
}

export function droppedCsv(result: ClusterRunResult): string {
  return toCsv(
    ["Keyword", "Google Ads volume", "Clickstream volume", "Reason", "Off-topic confidence"],
    result.dropped.map((d) => [
      d.keyword,
      d.adsVolume,
      d.clickstreamVolume ?? "",
      d.reason,
      d.confidence !== undefined ? d.confidence.toFixed(2) : "",
    ]),
  );
}

export function clusterFileStem(result: ClusterRunResult): string {
  return `${fileStem("keyword-clusters", result.input.seeds[0] ?? "keywords")}-${result.startedAt.slice(0, 10)}`;
}
