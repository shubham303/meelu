export type ID = string;

export interface BaseEntity {
  id: ID;
  createdAt: string;
  updatedAt: string;
}

export interface SiteScoped {
  siteId: ID;
}

export interface UserProfile {
  id: ID;
  createdAt: string;
  updatedAt: string;
  fullName: string;
  role?: string;
  company?: string;
  timezone?: string;
  signature?: string;
  bio?: string;
  writingVoice?: string;
  linkedinUrl?: string;
  xUrl?: string;
  websiteUrl?: string;
}

export type SiteShallowReason =
  | "thin"
  | "legal"
  | "pagination"
  | "redirect"
  | "gone"
  | "blocked"
  | "server-error"
  | "unreachable"
  | "not-html";

export type LinkRegion =
  | "body"
  | "breadcrumb"
  | "nav"
  | "header"
  | "footer"
  | "aside"
  | "pagination";

export interface SitePage extends BaseEntity, SiteScoped {
  url: string;
  status?: number;
  contentHash?: string;
  etag?: string;
  lastModified?: string;
  lastCrawledAt?: string;
  inlinks: number;
  title?: string;
  titlePixels?: number;
  metaDescription?: string;
  h1: string[];
  headings: { level: number; text: string; ordinal: number }[];
  bodyText?: string;
  canonical?: string;
  robotsDirectives?: string;
  xRobotsTag?: string;
  blockedByRobots: boolean;
  viewportMeta?: string | null;
  nosnippetCount?: number;
  socialMetaCount: number;
  socialMeta?: Record<string, string>;
  hasGoogleAnalytics?: boolean | null;
  author?: string;
  schemaTypes: string[];
  schemaNodes: { type: string; keys: number; props: string[] }[];
  lang?: string;
  hreflang: Record<string, string>;
  pageType?: SitePageType | null;
  format?: string;
  inSitemap: boolean;
  depth?: number;
  redirectTo?: string;
  redirectFinal?: string;
  redirectHops?: number;
  fetchError?: string;
  contentType?: string;
  images: { src: string; alt?: string; width?: number; height?: number; bytes?: number; type?: string }[];
  publishedAt?: string;
  modifiedAt?: string;
  wordCount?: number;
  mixedContent: boolean;
  contentChangedAt?: string;
  indexState?: SiteIndexState;
  coverageState?: string;
  googleCanonical?: string;
  indexCheckedAt?: string;
  similarity?: number;
  match?: { text: string; headingPath?: string };
  linkScore?: number;
  chunkedFromHash?: string;
  embedState?: string;
  embedError?: string;
  shallow: boolean;
  shallowReason?: SiteShallowReason;
  stage?: PageStage;
  outLinkCount: number;
  externalLinkCount: number;
  isLeaf?: boolean;
}

export interface SitePageLink {
  id: ID;
  srcPageId: ID;
  srcUrl?: string;
  dstPageId?: ID | null;
  dstUrl: string;
  external: boolean;
  region: LinkRegion;
  rel?: string;
  anchor?: string;
  count: number;
  followable: boolean;
  dstCanonical: boolean;
}

export interface SitePageLinks {
  inbound: SitePageLink[];
  outbound: SitePageLink[];
}

export interface SiteDiscoveryPage {
  id: ID;
  url: string;
  title?: string;
  pageType?: SitePageType | null;
  inlinks: number;
  depth?: number;
  inSitemap: boolean;
}

export interface SiteDiscovery {
  live: number;
  homeFound: boolean;
  orphans: number;
  unreachable: number;
  deep: number;
  deepFrom: number;
  byDepth: { depth?: number; n: number }[];
  orphanPages: SiteDiscoveryPage[];
  unreachablePages: SiteDiscoveryPage[];
  deepPages: SiteDiscoveryPage[];
}

export type PageStage = "pending" | "blocked" | "failed" | "skipped" | "crawled" | "indexed";

export interface SiteChunk extends BaseEntity, SiteScoped {
  pageId: ID;
  ordinal: number;
  headingPath?: string;
  text: string;
  embedModel?: string;
  embedAttempts: number;
  embedError?: string;
  fromHash?: string;
}

export const NOTE_KINDS = ["note", "feedback"] as const;

export type NoteKind = (typeof NOTE_KINDS)[number];

export interface Note extends BaseEntity, SiteScoped {
  note: string;
  kind: NoteKind;
}

export interface NoteHit extends Note {
  score: number;
  similarity?: number | null;
}

export const SITE_ISSUE_STATES = ["open", "rejected"] as const;

export type SiteIssueState = (typeof SITE_ISSUE_STATES)[number];

export const SITE_ISSUE_SEVERITIES = ["p0", "p1", "p2", "p3"] as const;

export type SiteIssueSeverity = (typeof SITE_ISSUE_SEVERITIES)[number];

export const SITE_ISSUE_KINDS = [
  "robots-missing",
  "robots-unreadable",
  "robots-blocks-assets",
  "robots-no-sitemap",
  "sitemap-missing",
  "sitemap-not-at-standard-url",
  "llms-missing",
  "llms-not-plain-text",
  "robots-blocked-but-linked",
  "noindex-but-linked",
  "sitemap-dead-page",
  "sitemap-redirect",
  "missing-from-sitemap",
  "server-error",
  "soft-404",
  "missing-title",
  "duplicate-title",
  "title-too-long",
  "title-too-short",
  "missing-meta-description",
  "duplicate-meta-description",
  "meta-description-length",
  "missing-h1",
  "multiple-h1",
  "heading-hierarchy-skip",
  "orphan-page",
  "orphan-page-unlisted",
  "deep-page",
  "broken-internal-link",
  "internal-link-to-redirect",
  "external-links-dense",
  "facet-trap",
  "internal-nofollow",
  "missing-breadcrumbs",
  "nav-gap",
  "canonical-mismatch",
  "missing-canonical",
  "canonical-to-dead-page",
  "canonical-to-redirect",
  "canonical-to-noindex",
  "redirect-chain",
  "thin-content",
  "stale-content",
  "date-inflation",
  "image-missing-alt",
  "image-missing-dimensions",
  "image-oversized",
  "image-legacy-format",
  "missing-lang",
  "missing-viewport",
  "hreflang-no-self-reference",
  "hreflang-not-reciprocal",
  "hreflang-invalid-code",
  "hreflang-no-x-default",
  "no-structured-data",
  "home-missing-organization",
  "home-missing-contact-link",
  "home-missing-terms-link",
  "home-missing-social-links",
  "home-missing-google-analytics",
  "schema-article-incomplete",
  "schema-product-incomplete",
  "schema-faq-incomplete",
  "schema-howto-incomplete",
  "schema-breadcrumb-incomplete",
  "schema-organization-incomplete",
  "schema-localbusiness-incomplete",
  "restrictive-snippet",
  "mixed-content",
  "url-hygiene",
  "url-too-long",
  "url-dated",
  "url-stop-words",
  "googlebot-blocked",
  "ai-search-crawler-blocked",
  "ai-user-fetch-blocked",
  "ai-training-blocked",
  "ai-permissions-inconsistent",
  "ai-crawler-blocked-at-edge",
  "http-not-redirected",
  "host-variant-duplicate",
  "host-variant-distinct",
  "host-variant-elsewhere",
  "host-path-not-redirected",
  "trailing-slash-duplicate",
  "case-variant-duplicate",
  "host-variant-canonicalised",
  "host-variant-redirect-chain",
  "js-only-content",
  "js-only-title",
  "js-only-canonical",
  "js-only-h1",
  "js-only-schema",
  "js-only-links",
  "robots-changed-by-js",
  "canonical-changed-by-js",
  "client-side-redirect",
  "render-blocked-assets",
  "render-console-errors",
  "render-failed-requests",
  "heavy-javascript",
  "too-many-requests",
  "third-party-bloat",
  "js-dependent-site",
  "mobile-js-only-content",
  "mobile-hidden-content",
  "mobile-hidden-links",
  "mobile-viewport-overflow",
  "mobile-small-tap-targets",
  "mobile-title-differs",
  "mobile-canonical-differs",
  "mobile-noindex-differs",
  "mobile-differs-from-desktop",
  "soft-404-after-render",
  "mobile-soft-404-after-render",
  "rendered-body-empty",
  "mobile-rendered-body-empty",
  "render-exception-with-thin-content",
  "mobile-render-exception-with-thin-content",
  "content-lost-after-render",
  "mobile-content-lost-after-render",
  "links-lost-after-render",
  "mobile-links-lost-after-render",
  "uncrawlable-anchors-after-render",
  "mobile-uncrawlable-anchors-after-render",
  "old-ajax-crawling-scheme",
  "mobile-old-ajax-crawling-scheme",
  "dangling-fragment-links",
  "mobile-dangling-fragment-links",
  "url-changed-by-history-api",
  "mobile-url-changed-by-history-api",
  "interaction-gated-content",
  "mobile-interaction-gated-content",
  "images-without-src-after-render",
  "mobile-images-without-src-after-render",
  "shadow-dom-content-unslotted",
  "mobile-shadow-dom-content-unslotted",
  "service-worker-registered",
  "mobile-service-worker-registered",
  "failed-data-request",
  "mobile-failed-data-request",
  "failed-first-party-script",
  "mobile-failed-first-party-script",
  "cors-blocked-request",
  "mobile-cors-blocked-request",
  "network-never-idle",
  "mobile-network-never-idle",
  "websocket-transport-used",
  "mobile-websocket-transport-used",
  "mixed-content-active",
  "mobile-mixed-content-active",
  "mixed-content-passive",
  "mobile-mixed-content-passive",
  "document-over-2mb",
  "mobile-document-over-2mb",
  "resource-over-2mb",
  "mobile-resource-over-2mb",
  "rendered-html-over-2mb",
  "mobile-rendered-html-over-2mb",
  "mobile-status-differs-from-desktop",
  "mobile-final-url-differs-from-desktop",
  "viewport-meta-missing",
  "viewport-meta-restrictive",
  "mobile-intrusive-overlay",
  "intrusive-overlay",
  "mobile-illegible-text",
  "mobile-word-count-drop",
  "mobile-description-differs-from-desktop",
  "mobile-h1-differs-from-desktop",
  "mobile-schema-differs-from-desktop",
  "mobile-image-alt-differs",
  "schema-changed-by-js",
  "mobile-schema-changed-by-js",
  "schema-duplicated-after-render",
  "mobile-schema-duplicated-after-render",
  "schema-invalid-after-render",
  "mobile-schema-invalid-after-render",
  "canonical-conflict-after-render",
  "mobile-canonical-conflict-after-render",
  "canonical-repeated-after-render",
  "mobile-canonical-repeated-after-render",
  "canonical-invalid-after-render",
  "mobile-canonical-invalid-after-render",
  "robots-directives-conflict-after-render",
  "mobile-robots-directives-conflict-after-render",
  "nofollow-changed-by-js",
  "mobile-nofollow-changed-by-js",
  "title-modified-by-js",
  "mobile-title-modified-by-js",
  "meta-description-modified-by-js",
  "mobile-meta-description-modified-by-js",
  "h1-modified-by-js",
  "mobile-h1-modified-by-js",
  "meta-description-only-after-js",
  "mobile-meta-description-only-after-js",
  "title-duplicated-after-render",
  "mobile-title-duplicated-after-render",
  "description-duplicated-after-render",
  "mobile-description-duplicated-after-render",
  "hreflang-changed-by-js",
  "mobile-hreflang-changed-by-js",
  "hreflang-invalid-after-render",
  "mobile-hreflang-invalid-after-render",
  "unrendered-template-tokens",
  "mobile-unrendered-template-tokens",
  "unrendered-template-tokens-body",
  "mobile-unrendered-template-tokens-body",
  "js-injected-images-missing-alt",
  "mobile-js-injected-images-missing-alt",
  "external-links-injected-by-js",
  "mobile-external-links-injected-by-js",
  "plugin-content-after-render",
  "mobile-plugin-content-after-render",
  "viewport-meta-changed-by-js",
  "mobile-viewport-meta-changed-by-js",
  "data-nosnippet-changed-by-js",
  "mobile-data-nosnippet-changed-by-js",
  "og-tags-only-after-js",
  "mobile-og-tags-only-after-js",
] as const;

export const SITE_ISSUE_TYPES = ["static", "desktop", "mobile"] as const;

export type SiteIssueType = (typeof SITE_ISSUE_TYPES)[number];

export type SiteIssueKind = (typeof SITE_ISSUE_KINDS)[number];

export interface SiteIssue extends BaseEntity, SiteScoped {
  kind: SiteIssueKind;
  issue: string;
  severity: SiteIssueSeverity;
  state: SiteIssueState;
  issueType: SiteIssueType;
}

export interface SitePageIssue extends SiteIssue {
  pageId: string;
  matchedPages: number;
  url?: string;
}

export const LINK_SUGGESTION_STATES = [
  "draft",
  "ready",
  "llm_rejected",
  "user_rejected",
  "done",
  "stale",
] as const;

export type LinkSuggestionState = (typeof LINK_SUGGESTION_STATES)[number];

export const LINK_SUGGESTION_ACTIONS = ["create", "delete", "edit"] as const;

export type LinkSuggestionAction = (typeof LINK_SUGGESTION_ACTIONS)[number];

export interface LinkSuggestion extends BaseEntity, SiteScoped {
  jobId: string;
  fromPageId: string;
  fromChunkId?: string | null;
  toPageId: string;
  action: LinkSuggestionAction;
  state: LinkSuggestionState;
  suggestion: string;
  searchScore?: number | null;
  confidence?: number | null;
  score?: number | null;
  fromUrl?: string | null;
  toUrl?: string | null;
  fromChunkHeading?: string | null;
  fromChunkOrdinal?: number | null;
}

export type LinkSuggestionSummary = Record<LinkSuggestionState, number>;

export const PILLAR_SUGGESTION_ACTIONS = ["create", "expand"] as const;

export type PillarSuggestionAction = (typeof PILLAR_SUGGESTION_ACTIONS)[number];

export interface PillarMember {
  id: string;
  url: string;
  title?: string | null;
}

export interface PillarSuggestion extends BaseEntity, SiteScoped {
  jobId: string;
  action: PillarSuggestionAction;
  topic: string;
  memberPageIds: string[];
  coveringPageId?: string | null;
  state: LinkSuggestionState;
  suggestion: string;
  searchScore?: number | null;
  confidence?: number | null;
  score?: number | null;
  coveringUrl?: string | null;
  members: PillarMember[];
}

export type PillarSuggestionSummary = Record<LinkSuggestionState, number>;

export type SiteIssueScope = "site" | "pages";

export interface SiteIssueGroup {
  scope: SiteIssueScope;
  kind: SiteIssueKind;
  issue: string;
  severity: SiteIssueSeverity;
  pages: number;
  matched: number;
  examples: string[];
  state: SiteIssueState;
  reason?: string | null;
  issueType: SiteIssueType;
}

export interface SiteIssueExportRow {
  kind: SiteIssueKind;
  scope: SiteIssueScope;
  severity: SiteIssueSeverity;
  state: SiteIssueState;
  url: string;
  issue: string;
}

export interface SiteIssueSummary {
  site: { open: number; rejected: number };
  pages: { open: number; rejected: number };
  openSiteIssues: {
    kind: SiteIssueKind;
    issue: string;
    severity: SiteIssueSeverity;
    issueType: SiteIssueType;
  }[];
  openPageIssues: SiteIssueGroup[];
}

export type SiteRenderScope = "sample" | "all";

export type SiteRenderUserAgent = "googlebot" | "generic" | "ai_bot";

export type SiteRenderDevice = "desktop" | "mobile";

export interface SiteRenderJobStatus {
  siteId: string;
  jobId?: string | null;
  device: SiteRenderDevice;
  state: string;
  active: boolean;
  trigger?: string | null;
  scope?: SiteRenderScope | null;
  userAgentProfile?: SiteRenderUserAgent | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  total?: number;
  rendered?: number;
  failed?: number;
  error?: string | null;
  stopReason?: string | null;
  renderedPages: number;
  eligiblePages: number;
  pendingPages: number;
  lastRenderedAt?: string | null;
}

export type SiteCrawlJobStatus =
  | "queued"
  | "running"
  | "cancelling"
  | "cancelled"
  | "completed"
  | "failed";

export type SiteIndexState =
  | "indexed"
  | "crawled-not-indexed"
  | "discovered"
  | "excluded"
  | "blocked"
  | "unknown";

export type SiteSearchSyncStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface SiteSearchSync extends BaseEntity, SiteScoped {
  status: SiteSearchSyncStatus;
  trigger: string;
  property?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  heartbeatAt?: string | null;
  daysTotal: number;
  daysDone: number;
  rowsStored: number;
  pagesInspected: number;
  firstDay?: string | null;
  lastDay?: string | null;
  error?: string | null;
  notes: unknown[];
}

export type SiteTrafficSyncStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface SiteTrafficSync extends BaseEntity, SiteScoped {
  status: SiteTrafficSyncStatus;
  trigger: string;
  property?: string | null;
  startedAt?: string | null;
  finishedAt?: string | null;
  heartbeatAt?: string | null;
  daysTotal: number;
  daysDone: number;
  rowsStored: number;
  firstDay?: string | null;
  lastDay?: string | null;
  error?: string | null;
  notes: unknown[];
}

export interface SiteCrawlJob extends BaseEntity, SiteScoped {
  status: SiteCrawlJobStatus;
  trigger: string;
  freshBefore?: string;
  cutoffDays?: number;
  sitemapUrls: string[];
  startedAt?: string;
  finishedAt?: string;
  heartbeatAt?: string;
  discovered: number;
  skipped: number;
  fetched: number;
  queued: number;
  newPages: number;
  changed: number;
  unchanged: number;
  failed: number;
  pagesStored: number;
  passagesStored: number;
  complete: boolean;
  error?: string;
  stopReason?: string;
  notes: string[];
}

export type SitePageType =
  | "money"
  | "hub"
  | "informational"
  | "support"
  | "company"
  | "legal"
  | "utility";

export interface SitePageLlmExtraction extends BaseEntity, SiteScoped {
  pageId: string;
  pageType: SitePageType | null;
  confidence?: number;
  extractedFromHash?: string;
  model?: string;
  error?: string;
  extractedAt: string;
}

export interface SiteSocialLink {
  platform: string;
  url: string;
  handle?: string;
}

export type SiteStatus = "active" | "disabled";

export interface SiteProfile extends BaseEntity {
  domain: string;
  name: string;
  status: SiteStatus;
  country?: string;
  repoUrl?: string;
  summary?: string;
  socialLinks: SiteSocialLink[];
  sitemapUrls: string[];
  sitemapUrlCount?: number;
  sitemapAtRoot?: boolean | null;
  robotsTxt?: string | null;
  robotsStatus?: number | null;
  robotsFetchedAt?: string | null;
  llmsTxt?: string | null;
  llmsStatus?: number | null;
  llmsFetchedAt?: string | null;
  crawlerAccess?: CrawlerAccess | null;
  hostVariants?: HostVariants | null;
  lastCrawledAt?: string | null;
  gscProperty?: string | null;
  gaProperty?: string | null;
}

export type CrawlerEdgeVerdict = "allowed" | "blocked" | "unknown";

export interface CrawlerEdgeProbe {
  agent: string;
  status: number | null;
  bytes: number | null;
  verdict: CrawlerEdgeVerdict;
  reason?: string;
}

export interface CrawlerAccess {
  checkedAt: string;
  url: string;
  baseline: { status: number | null; bytes: number | null };
  agents: CrawlerEdgeProbe[];
}

export type HostVariantKind = "scheme" | "host" | "host-path" | "trailing-slash" | "case";

export type HostVariantVerdict =
  | "duplicate"
  | "canonicalised"
  | "redirects"
  | "elsewhere"
  | "absent"
  | "distinct"
  | "unknown";

export interface HostVariantProbe {
  kind: HostVariantKind;
  url: string;
  target: string;
  verdict: HostVariantVerdict;
  status: number | null;
  hops: number;
  finalUrl: string | null;
  canonical: string | null;
}

export interface HostVariants {
  checkedAt: string;
  preferred: string;
  sample: string | null;
  variants: HostVariantProbe[];
}

export interface SiteChannel extends BaseEntity, SiteScoped {
  channelKey: string;
  enabled: boolean;
  rules: string[];
  label: string;
  composeUrl: string;
  characterLimit: number;
  requiresMedia: boolean;
  maxLinks: number | null;
  maxHashtags: number | null;
  maxMedia: number;
}

export type PieceStatus = "draft" | "blocked";

export type MediaSource = "none" | "upload" | "unsplash";

export interface PostMedia extends BaseEntity {
  contentType: string;
  byteSize: number;
  width?: number | null;
  height?: number | null;
  originalName?: string | null;
}

export interface PieceCheck {
  code: string;
  level: "block" | "warn";
  message: string;
}

export interface PieceMedia {
  mediaSource: MediaSource;
  mediaUrl?: string | null;
  mediaAlt?: string | null;
  mediaWidth?: number | null;
  mediaHeight?: number | null;
  mediaCreditName?: string | null;
  mediaCreditUrl?: string | null;
  mediaUploadId?: ID | null;
}

export interface ContentPieceSlim extends BaseEntity, SiteScoped {
  title: string;
  channelKey: string;
  status: PieceStatus;
  wordCount: number;
  checks: PieceCheck[];
  mediaSource: MediaSource;
  mediaUrl?: string | null;
  parentPieceId?: string | null;
}

export interface ContentPiece extends ContentPieceSlim, PieceMedia {
  bodyMarkdown: string;
  createdBy: "agent" | "user";
  sourcePageId?: string | null;
}

export interface AnalyticsSession extends BaseEntity, SiteScoped {
  title: string;
  about: string;
  sessionKey?: string | null;
}

export interface AnalyticsSource extends BaseEntity, SiteScoped {
  sessionId: string;
  name: string;
  filePath?: string | null;
}

export interface AnalyticsReport extends BaseEntity, SiteScoped {
  sessionId?: ID | null;
  title: string;
  html: string;
  createdBy: "agent" | "user";
}

export type AnalyticsReportSummary = Omit<AnalyticsReport, "html"> & { htmlBytes: number };

export interface ApiKey extends BaseEntity {
  name: string;
  preview: string;
  lastUsedAt: string | null;
}

export interface CreatedApiKey extends ApiKey {
  key: string;
}

export interface SocialListeningConfig extends BaseEntity, SiteScoped {
  platforms: string[];
  resultsPerKeyword: number;
  minRelevance: number;
  minSimilarity: number;
  maxAgeDays: number;
  dropDeadPosts: boolean;
  schedule: "daily" | "weekly" | null;
}

export type SocialListeningSource = "user" | "profile" | "suggested";

export interface SocialListeningQuery extends BaseEntity, SiteScoped {
  text: string;
  enabled: boolean;
  source: "user" | "suggested";
  keywords: string[];
  negativeKeywords: string[];
  embedded: boolean;
}

export interface SocialListeningTarget extends BaseEntity, SiteScoped {
  kind: "brand" | "competitor";
  name: string;
  enabled: boolean;
  source: SocialListeningSource;
}

export type SocialListeningRunStatus = "running" | "done" | "stopped" | "error";

export interface SocialListeningRun extends BaseEntity, SiteScoped {
  status: SocialListeningRunStatus;
  startedAt: string;
  finishedAt: string | null;
  fetchedCount: number;
  keptCount: number;
  platformStats: Record<string, { fetched?: number; kept?: number; error?: string }>;
  error: string | null;
}

export type SocialListeningPostKind = "topic" | "brand" | "competitor";
export type SocialListeningInboxStatus = "needs_reply" | "drafted" | "replied" | "skipped";
export type SocialListeningPostStatus =
  | SocialListeningInboxStatus
  | "fetched"
  | "matched"
  | "filtered";
export type SocialListeningClass =
  | "praise"
  | "complaint"
  | "feature_request"
  | "question"
  | "switch_opportunity";

export interface SocialListeningPost extends BaseEntity, SiteScoped {
  url: string;
  platform: string;
  kind: SocialListeningPostKind;
  title: string | null;
  text: string | null;
  authorHandle: string | null;
  authorName: string | null;
  postedAt: string | null;
  engagement: { score?: number | null; comments?: number | null; views?: number | null };
  context: { subreddit?: string | null; tags?: string[] | null };
  matchedTargets: string[];
  intent: string | null;
  sentiment: "positive" | "neutral" | "negative" | null;
  isQuestion: boolean | null;
  classes: SocialListeningClass[];
  relevance: number | null;
  compositeScore: number | null;
  keepReason: string | null;
  suggestedAngle: string | null;
  status: SocialListeningPostStatus;
  similarity: number | null;
  queryId: string | null;
  replyText: string | null;
  repliedAt: string | null;
  runId: string | null;
}

export interface SocialListeningSummary {
  unprocessed: number;
  needsReply: number;
  drafted: number;
  replied: number;
  skipped: number;
  brandMentions: number;
  competitorMentions: number;
  lastRun: SocialListeningRun | null;
  keptByQuery: Array<{ id: string; text: string; kept: number }>;
  mentionClasses: {
    praise: number;
    complaint: number;
    featureRequest: number;
    question: number;
    switchOpportunity: number;
  };
  sentiment: { positive: number; neutral: number; negative: number };
}

export type LeadCampaignStatus = "active" | "paused" | "archived";

export interface LeadCampaign extends BaseEntity, SiteScoped {
  name: string;
  status: LeadCampaignStatus;
  audience: string;
  sources: string[];
  schedule: "daily" | "weekly" | null;
}

export type LeadRunStatus = "running" | "done" | "stopped" | "error";

export interface LeadRun extends BaseEntity, SiteScoped {
  campaignId: ID;
  status: LeadRunStatus;
  startedAt: string;
  finishedAt: string | null;
  found: number;
  qualified: number;
  skippedKnown: number;
  sourceStats: Record<string, { found?: number; qualified?: number; error?: string }>;
  error: string | null;
}

export type LeadStage = "found" | "qualified" | "shortlisted";

export interface Lead extends BaseEntity, SiteScoped {
  campaignId: ID | null;
  runId: ID | null;
  name: string;
  company: string | null;
  role: string | null;
  email: string | null;
  emailVerified: boolean;
  website: string | null;
  source: string | null;
  sourceUrl: string | null;
  channelHandles: Record<string, string>;
  fitScore: number | null;
  fitReason: string | null;
  evidence: Array<{ quote: string; url: string }>;
  stage: LeadStage;
  stageChangedAt: string | null;
  note: string | null;
}

export interface LeadSummary {
  stages: Record<LeadStage, number>;
  lastRun: LeadRun | null;
  campaigns: Array<{
    id: ID;
    name: string;
    status: LeadCampaignStatus;
    qualified: number;
    shortlisted: number;
  }>;
}

export const PAGE_SUGGESTION_STATES = [
  "draft",
  "reviewed",
  "ready",
  "llm_rejected",
  "user_rejected",
  "done",
  "stale",
] as const;

export type PageSuggestionState = (typeof PAGE_SUGGESTION_STATES)[number];

export const PAGE_SUGGESTION_ACTIONS = ["add", "edit", "delete"] as const;

export type PageSuggestionAction = (typeof PAGE_SUGGESTION_ACTIONS)[number];

export interface PageSuggestion extends BaseEntity, SiteScoped {
  jobId: string;
  action: PageSuggestionAction;
  pageId?: string | null;
  topicKey: string;
  clusterId?: string | null;
  pairId?: string | null;
  mergeIntoPageId?: string | null;
  strategies: string[];
  suggestion: string;
  evidence: Record<string, unknown>;
  coverageAtCreation?: number | null;
  impressionsAtCreation?: number | null;
  targetPosition?: number | null;
  state: PageSuggestionState;
  searchScore?: number | null;
  confidence?: number | null;
  score?: number | null;
  verifiedAt?: string | null;
}

export type PageSuggestionSummary = Record<
  PageSuggestionAction,
  Partial<Record<PageSuggestionState, number>>
>;

export interface SeoSiteState {
  id: string;
  siteId: string;
  locationCode: number;
  languageCode: string;
  brandTerms: string[];
  precomputeRequestedAt?: string | null;
  rollupAt?: string | null;
  embeddedAt?: string | null;
  ctrCurve: Record<string, number>;
}

export interface SeoOverview {
  keywords: number;
  keywordsWithFacts: number;
  clusters: number;
  competitorsConfirmed: number;
  suggestions: PageSuggestionSummary;
  state: SeoSiteState;
}

export interface SeoKeyword {
  id: string;
  keyword: string;
  volume?: number | null;
  difficulty?: number | null;
  cpc?: number | null;
  intent?: string | null;
  factsFetchedAt?: string | null;
  firstSource: string;
  seedKeywordId?: string | null;
  clusterId?: string | null;
  branded: boolean;
  ourPosition?: number | null;
  ourUrl?: string | null;
  impressions28D: number;
  clicks28D: number;
  impressionsPrev28D: number;
  clicksPrev28D: number;
  impressionsLy28D?: number | null;
  clicksLy28D?: number | null;
  createdAt: string;
}

export interface SeoPageFacts {
  id: string;
  pageId: string;
  url: string;
  title?: string | null;
  pageType?: string | null;
  live: boolean;
  indexable: boolean;
  impressions28D: number;
  clicks28D: number;
}

export interface SeoCompetitor {
  id: string;
  domain: string;
  brandTerms: string[];
  firstSource: string;
  intersections?: number | null;
  avgPosition?: number | null;
  state: "candidate" | "confirmed" | "ignored";
  fetchedAt?: string | null;
}
