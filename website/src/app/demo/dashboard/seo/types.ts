export interface ClimbResult {
  position: number;
  url: string;
  domain: string;
  title?: string | null;
  pageRank?: number | null;
  domainRank?: number | null;
  strength: number;
  smoothedStrength: number;
  intentFit: number;
  passChance: number;
}

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
  winnability?: number;
  pTopThree?: number;
  pPageOne?: number;
  likelyPosition?: number;
  ourPosition?: number;
  ourUrl?: string;
  ourStrength?: number;
  intentFit?: number;
  isRanked: boolean;
  competitors: string[];
  climb: ClimbResult[];
  metricsAt?: string;
  createdAt: string;
  updatedAt: string;
}

export interface SiteSeoLists {
  siteId: string;
  competitors: string[];
  backlinkOpportunities: string[];
}

export type SeoListName = "competitors" | "backlink_opportunities";

export interface SeoListChange {
  list: SeoListName;
  added: string[];
  removed: string[];
  unchanged: string[];
  items: string[];
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
  lastTracked?: string;
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
