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
  dstPageId: ID;
  dstUrl: string;
  region: LinkRegion;
  rel?: string;
  anchor?: string;
  count: number;
  followable: boolean;
  dstCanonical: boolean;
}

export interface SiteExternalLink {
  url: string;
  region: LinkRegion;
  rel?: string;
  anchor?: string;
  count: number;
  followable: boolean;
}

export interface SitePageLinks {
  inbound: SitePageLink[];
  outbound: SitePageLink[];
  external: SiteExternalLink[];
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

export const SUGGESTION_STATES = [
  "draft",
  "screening_rejected",
  "screening_approved",
  "review_approved",
  "review_rejected",
  "user_rejected",
] as const;

export type SuggestionState = (typeof SUGGESTION_STATES)[number];

export interface SuggestionSummary {
  draft: number;
  screeningRejected: number;
  screeningApproved: number;
  reviewApproved: number;
  reviewRejected: number;
  userRejected: number;
}

export const LINK_SUGGESTION_ACTIONS = ["create", "delete"] as const;

export type LinkSuggestionAction = (typeof LINK_SUGGESTION_ACTIONS)[number];

export interface LinkSuggestion extends BaseEntity, SiteScoped {
  jobId: string;
  fromPageId: string;
  fromChunkId?: string | null;
  toPageId: string;
  action: LinkSuggestionAction;
  state: SuggestionState;
  suggestion: string;
  searchScore?: number | null;
  confidence?: number | null;
  score?: number | null;
  fromUrl?: string | null;
  toUrl?: string | null;
  fromChunkHeading?: string | null;
  fromChunkOrdinal?: number | null;
  fromChunkText?: string | null;
  anchor?: string | null;
}

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
  state: SuggestionState;
  suggestion: string;
  searchScore?: number | null;
  confidence?: number | null;
  score?: number | null;
  coveringUrl?: string | null;
  members: PillarMember[];
}

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
  sitemapUrls: string[];
  startedAt?: string;
  finishedAt?: string;
  heartbeatAt?: string;
  discovered: number;
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
  pausedAt?: string | null;
  deletesAt?: string | null;
  markets: string[];
  language?: string | null;
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
  level: "warn";
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
  slug?: string | null;
  targetKeyword?: string | null;
  wordCount: number;
  checks: PieceCheck[];
  mediaSource: MediaSource;
  mediaUrl?: string | null;
}

export interface ContentPiece extends ContentPieceSlim, PieceMedia {
  h1: string;
  metaDescription: string;
  bodyMarkdown: string;
  createdBy: "agent" | "user";
  sourcePageId?: string | null;
}

export const REPORT_DESKS = ["analytics", "seo", "technical-seo"] as const;

export type ReportDesk = (typeof REPORT_DESKS)[number];

export interface Report extends BaseEntity, SiteScoped {
  desk: ReportDesk;
  title: string;
  html: string;
  createdBy: "agent" | "user";
}

export type ReportSummary = Omit<Report, "html"> & { htmlBytes: number };

export interface AnalyticsChat {
  id: string;
  siteId: string;
  title: string;
  sdkSessionId?: string;
  createdAt: string;
  updatedAt: string;
}

export type AnalyticsChatSummary = Pick<AnalyticsChat, "id" | "title" | "updatedAt">;

export interface AnalyticsChatMessage {
  id: string;
  role: "user" | "assistant";
  text: string;
  createdAt: string;
}

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
}

export interface SocialListeningQuery extends BaseEntity, SiteScoped {
  text: string;
  enabled: boolean;
  source: "user" | "suggested";
  keywords: string[];
  embedded: boolean;
  found: number;
  kept: number;
}

export type SocialListeningRunStatus = "running" | "done" | "stopped" | "error";

export interface SocialListeningPlatformStats {
  status?: "running" | "done" | "error";
  keywords?: number;
  fromVendor?: number;
  fromDatabase?: number;
  candidates?: number;
  failedKeywords?: string[];
  costMicros?: number;
  error?: string;
}

export interface SocialListeningPlatformEstimate {
  platform: string;
  keywords: number;
  vendorKeywords: number;
  maxCostMicros: number | null;
}

export interface SocialListeningEstimate {
  platforms: SocialListeningPlatformEstimate[];
}

export interface SocialListeningRun extends BaseEntity, SiteScoped {
  status: SocialListeningRunStatus;
  startedAt: string;
  finishedAt: string | null;
  fetchedCount: number;
  matchedCount: number;
  keptCount: number;
  platformStats: Record<string, SocialListeningPlatformStats>;
  error: string | null;
}

export type SocialListeningReviewStatus = "to_reply" | "drafted" | "replied" | "skipped" | "rejected";
export type SocialListeningPostStatus = SocialListeningReviewStatus | "candidate" | "matched";

export interface SocialListeningPost extends BaseEntity, SiteScoped {
  postId: string;
  url: string;
  platform: string;
  externalId: string | null;
  title: string | null;
  text: string | null;
  authorHandle: string | null;
  authorName: string | null;
  postedAt: string | null;
  engagement: { score?: number | null; comments?: number | null; views?: number | null };
  context: { subreddit?: string | null; tags?: string[] | null };
  status: SocialListeningPostStatus;
  similarity: number | null;
  keepReason: string | null;
  suggestedAngle: string | null;
  replyText: string | null;
  repliedAt: string | null;
  queryId: string | null;
  runId: string | null;
}

export interface SocialListeningSummary {
  toReply: number;
  drafted: number;
  replied: number;
  skipped: number;
  rejected: number;
  done: number;
  unprocessed: number;
  lastRun: SocialListeningRun | null;
}

export type LeadSource = "posts" | "linkedin" | "web";
export type LeadBriefSource = "user" | "suggested";

export interface LeadBriefPlan {
  keywords?: string[];
  linkedin?: { query: string; titles: string[]; locations: string[] };
}

export interface LeadBrief extends BaseEntity, SiteScoped {
  text: string;
  enabled: boolean;
  source: LeadBriefSource;
  sources: LeadSource[];
  plan: LeadBriefPlan;
  found: number;
  kept: number;
}

export type LeadRunStatus = "running" | "done" | "stopped" | "error";

export interface LeadSourceStats {
  status?: "running" | "done" | "error";
  candidates?: number;
  skipped?: number;
  fromVendor?: number;
  fromStore?: number;
  people?: number;
  error?: string;
}

export interface LeadRun extends BaseEntity, SiteScoped {
  status: LeadRunStatus;
  startedAt: string;
  finishedAt: string | null;
  foundCount: number;
  shortlistedCount: number;
  keptCount: number;
  sourceStats: Record<string, LeadSourceStats>;
  error: string | null;
}

export type LeadReviewStatus = "new" | "contacted" | "discarded";
export type LeadStatus = LeadReviewStatus | "candidate" | "shortlisted";

export interface LeadEvidence {
  url: string;
  quote: string;
  at?: string | null;
}

export interface Lead extends BaseEntity, SiteScoped {
  briefId: string | null;
  runId: string | null;
  source: LeadSource;
  platform: string;
  name: string | null;
  handle: string | null;
  headline: string | null;
  profileUrl: string | null;
  email: string | null;
  emailSourceUrl: string | null;
  website: string | null;
  snippet: string | null;
  evidence: LeadEvidence[];
  reason: string | null;
  angle: string | null;
  status: LeadStatus;
  contactedAt: string | null;
  discardedAt: string | null;
}

export interface LeadSummary {
  new: number;
  contacted: number;
  discarded: number;
  unprocessed: number;
  lastRun: LeadRun | null;
}

export type GeoIntent = "informational" | "commercial" | "transactional" | "navigational";
export type GeoVerdict = "no_page" | "partial" | "low_rank" | "covered";
export type GeoPointStatus = "answers" | "partly" | "missing";
export type GeoPlatform = "chat_gpt" | "claude" | "ai_overview";

export interface GeoPoint {
  point: string;
  status: GeoPointStatus;
  evidence?: string;
}

export interface GeoPage {
  pageId: ID;
  url: string;
  title?: string;
  coverage: number;
  points: GeoPoint[];
}

export interface GeoAiAnswer {
  platform: GeoPlatform;
  shown: boolean;
  text: string;
  citations: { url: string; title?: string }[];
  citedUs: boolean;
  covers: string[];
  misses: string[];
  error?: string;
}

export type GeoCheckStage = "pages" | "question" | "judge" | "compare";

export interface GeoCheckProgress {
  stage?: GeoCheckStage;
  pagesFound?: number;
  points?: number;
  pagesJudged: number;
  answersFetched: number;
}

export interface GeoCheck extends BaseEntity, SiteScoped {
  queryId: ID;
  status: "running" | "done" | "error" | "stopped";
  progress: GeoCheckProgress;
  startedAt: string;
  finishedAt?: string;
  error?: string;
  intent?: GeoIntent;
  requiredPoints: string[];
  verdict?: GeoVerdict;
  pageId?: ID;
  pageUrl?: string;
  position?: number;
  pages: GeoPage[];
  aiAnswers: GeoAiAnswer[];
  pageAdds: string[];
  suggestion?: string;
  model?: string;
}

export interface GeoQuery extends BaseEntity, SiteScoped {
  text: string;
  source: "user" | "suggested";
  enabled: boolean;
  latestCheck?: GeoCheck;
}

export interface GeoSummary {
  queries: number;
  unchecked: number;
  running: number;
  noPage: number;
  partial: number;
  lowRank: number;
  covered: number;
  cited: number;
  lastCheckedAt?: string;
}
