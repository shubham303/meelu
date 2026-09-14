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

export type SitePageKind =
  | "home"
  | "product"
  | "pricing"
  | "category"
  | "article"
  | "docs"
  | "about"
  | "contact"
  | "legal"
  | "other";

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

export interface SitePage extends BaseEntity, SiteScoped {
  url: string;
  status?: number;
  contentHash?: string;
  etag?: string;
  lastModified?: string;
  lastCrawledAt?: string;
  inlinks: number;
  inboundAnchors: { from: string; anchor: string }[];
  title?: string;
  titlePixels?: number;
  metaDescription?: string;
  h1: string[];
  headings: { level: number; text: string; ordinal: number }[];
  bodyText?: string;
  outLinks: { url: string; anchor: string }[];
  externalLinks: { url: string; anchor: string; rel?: string }[];
  canonical?: string;
  robotsDirectives?: string;
  xRobotsTag?: string;
  blockedByRobots: boolean;
  hasViewport?: boolean;
  author?: string;
  schemaTypes: string[];
  schemaNodes: { type: string; keys: number; props: string[] }[];
  lang?: string;
  hreflang: Record<string, string>;
  kind: SitePageKind;
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
  keywords?: string[];
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
}

export type PageStage = "pending" | "blocked" | "failed" | "skipped" | "crawled" | "indexed";

export interface SiteChunk extends BaseEntity, SiteScoped {
  pageId: ID;
  ordinal: number;
  headingPath?: string;
  text: string;
  embedModel?: string;
  embeddedFromHash?: string;
  embedAttempts: number;
  embedError?: string;
  chunkStrategy?: string;
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
  "mobile-hidden-content",
  "mobile-hidden-links",
  "mobile-viewport-overflow",
  "mobile-small-tap-targets",
  "mobile-title-differs",
  "mobile-canonical-differs",
  "mobile-noindex-differs",
  "mobile-js-only-content",
  "mobile-differs-from-desktop",
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
  llmCheckRequired: boolean;
  llmCheckDoneAt?: string | null;
}

export interface SitePageIssue extends SiteIssue {
  pageId: string;
  matchedPages: number;
  url?: string;
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

export type SiteAnalysisJobStatus = SiteCrawlJobStatus;

export interface SiteAnalysisJob extends BaseEntity, SiteScoped {
  status: SiteAnalysisJobStatus;
  trigger: string;
  startedAt?: string;
  finishedAt?: string;
  heartbeatAt?: string;
  total: number;
  processed: number;
  skippedUnchanged: number;
  skippedSimilar: number;
  failed: number;
  error?: string;
  stopReason?: string;
}

export interface SitePageAnalysisTopic {
  topic: string;
  section: string | null;
}

export interface SitePageAnalysis extends BaseEntity, SiteScoped {
  pageId: string;
  topics: SitePageAnalysisTopic[];
  keywords: string[];
  questionsAnswered: string[];
  analyzedFromHash?: string;
  analyzedText?: string;
  model?: string;
  analyzedAt: string;
}

export interface SiteSocialLink {
  platform: string;
  url: string;
  handle?: string;
}

export interface SiteProfile extends BaseEntity {
  domain: string;
  name: string;
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

export interface OutreachProject extends BaseEntity, SiteScoped {
  name: string;
  goal?: string;
  prompt?: string;
  prospectProfile: string;
  searchCriteria?: string;
  emailTone?: string;
  valueProp?: string;
  cta?: string;
}

export type CampaignStatus = "running" | "done" | "failed";

export interface Campaign extends BaseEntity, SiteScoped {
  projectId: ID;
  requestedCount: number;
  status: CampaignStatus;
  summary?: string;
  finishedAt?: string | null;
}

export type ProspectStatus = "found" | "contacted" | "replied" | "won" | "rejected";

export interface Prospect extends BaseEntity, SiteScoped {
  campaignId: ID;
  name: string;
  company?: string;
  role?: string;
  email?: string;
  website?: string;
  sourceUrl?: string;
  fitReason?: string;
  status: ProspectStatus;
  dedupeKeys?: string[];
}

export type ConversationStatus = "draft" | "sent" | "received";

export interface ConversationMessage extends BaseEntity, SiteScoped {
  prospectId: ID;
  status: ConversationStatus;
  from?: string | null;
  to?: string | null;
  cc?: string | null;
  bcc?: string | null;
  subject: string;
  body: string;
  messageId?: string | null;
  threadRef?: string | null;
}

export interface SiteChannel extends BaseEntity, SiteScoped {
  channelKey: string;
  enabled: boolean;
  rules: string[];
  timezone: string;
  postingWindows: PostingWindow[];
  minGapHours: number;
  label: string;
  composeUrl: string;
  characterLimit: number;
  requiresMedia: boolean;
  maxLinks: number | null;
  maxHashtags: number | null;
  maxMedia: number;
}

export interface PostingWindow {
  days: number[];
  time: string;
}

export type PieceStatus = "draft" | "scheduled" | "posted" | "failed" | "blocked";

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
  scheduledAt: string | null;
  postedAt?: string | null;
  postedUrl?: string | null;
  failure?: string | null;
  mediaSource: MediaSource;
  mediaUrl?: string | null;
  parentPieceId?: string | null;
}

export interface ContentPiece extends ContentPieceSlim, PieceMedia {
  bodyMarkdown: string;
  externalPostId?: string | null;
  createdBy: "agent" | "user" | "system";
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

export interface SocialPublishing extends BaseEntity, SiteScoped {
  profileGroupId: string;
  postsThisMonth: number;
  monthKey: string;
  lastPostAt?: string | null;
}
