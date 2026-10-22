export type SearchIntent =
  | "informational"
  | "navigational"
  | "commercial"
  | "transactional";

export type ClusterImportance = "hot" | "warm" | "cold";

export interface KeywordCluster {
  id: string;
  mainKeyword: string;
  keywords: string[];
  coreKeyword?: string;
  seeds: string[];
  locationCode: number;
  languageCode: string;
  country?: string;
  volume: number;
  intent?: SearchIntent;
  importance?: ClusterImportance;
  isRanked: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Competitor {
  id: string;
  domain: string;
  domainRank?: number;
  backlinksFetchedAt?: string;
  createdAt: string;
  backlinks: number;
}

export interface CompetitorsChange {
  added: string[];
  removed: string[];
  unchanged: string[];
  competitors: string[];
}

export interface BacklinkOpportunity {
  domain: string;
  linksTo: string[];
  domainRank?: number;
  domainSpamScore?: number;
  backlinkSpamScore?: number;
  dofollow: boolean;
  exampleUrl: string;
  exampleAnchor?: string;
}

export interface TrackedKeyword {
  keyword: string;
  position?: number;
  previousPosition?: number;
  change?: number;
  url?: string;
  history: Array<number | null>;
  volume?: number;
  demand?: "rising" | "steady" | "falling" | "seasonal";
}

export interface TrackedOverview {
  locationCode: number;
  languageCode: string;
  markets: Array<{
    locationCode: number;
    languageCode: string;
    country?: string;
  }>;
  months: string[];
  stats: { tracked: number; topTen: number; moved: number; notRanking: number };
  keywords: TrackedKeyword[];
}
