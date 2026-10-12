export type SearchIntent = "informational" | "navigational" | "commercial" | "transactional";

export type ClusterKeyword = {
  keyword: string;
  coreKeyword: string;
  adsVolume: number;
  clickstreamVolume: number | null;
  cpc: number | null;
  searchIntent: SearchIntent | null;
  sharedVolumeWith: string[];
};

export type SerpResult = {
  keyword: string;
  urls: string[];
};

export type SerpPair = {
  a: string;
  b: string;
  shared: number;
  compared: number;
  sharedUrls: string[];
};

export type ClusterFlagKind =
  | "serp-overlaps-other-intent"
  | "serp-splits-cluster"
  | "serp-overlaps-other-cluster"
  | "merged-volume"
  | "not-split";

export type ClusterFlag = {
  kind: ClusterFlagKind;
  message: string;
  otherClusterId?: string;
  pair?: SerpPair;
};

export type KeywordCluster = {
  id: string;
  label: string;
  intent: string;
  searchIntent: SearchIntent | null;
  coreKeyword: string;
  headKeyword: string;
  keywords: ClusterKeyword[];
  adsVolume: number;
  clickstreamVolume: number | null;
  cpc: number | null;
  serpChecked: boolean;
  serpPairs: SerpPair[];
  flags: ClusterFlag[];
};

export type DroppedKeyword = {
  keyword: string;
  adsVolume: number;
  clickstreamVolume?: number;
  reason: "low-volume" | "low-clickstream" | "irrelevant" | "over-cap";
  confidence?: number;
};

export type RunCaps = {
  seedsGiven: number;
  seedsUsed: number;
  maxSeeds: number;
  keywordsFound: number;
  keywordsKept: number;
  maxKeywords: number;
  droppedLowVolume: number;
  droppedLowClickstream: number;
  droppedIrrelevant: number;
  droppedOverCap: number;
  coreGroups: number;
  groupsSplit: number;
  groupsNotSplit: number;
  maxSplitGroups: number;
  serpCalls: number;
  maxSerpCalls: number;
  clickstreamChecked: boolean;
};

export type ClusterRunInput = {
  seeds: string[];
  locationCode: number;
  languageCode: string;
  minVolume: number;
};

export type ClusterRunResult = {
  input: ClusterRunInput;
  locationName: string;
  startedAt: string;
  durationMs: number;
  model: string;
  clusters: KeywordCluster[];
  serps: SerpResult[];
  dropped: DroppedKeyword[];
  caps: RunCaps;
  notes: string[];
  costUsd: { dataforseo: number; openrouter: number };
  dailyRuns: { used: number; limit: number };
};

export type ClusterErrorCode =
  | "invalid-input"
  | "daily-limit"
  | "rate-limited"
  | "busy"
  | "not-configured"
  | "provider-failed"
  | "no-keywords";

export type ClusterError = { code: ClusterErrorCode; message: string; hint?: string };

export type ClusterStreamEvent =
  | { type: "phase"; message: string; step: number; steps: number }
  | { type: "done"; result: ClusterRunResult }
  | { type: "error"; error: ClusterError };
