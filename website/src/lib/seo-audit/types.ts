export type Severity = "critical" | "high" | "medium" | "low";

export type Category =
  | "crawlability"
  | "indexability"
  | "metadata"
  | "content"
  | "links"
  | "structured-data"
  | "international"
  | "mobile"
  | "urls"
  | "ai-crawlers";

export type PageState = "ok" | "redirect" | "error" | "blocked" | "not-html";

export type LinkRef = { url: string; anchor: string; rel: string | null };

export type ImageRef = {
  src: string;
  alt?: string;
  width?: number;
  height?: number;
  loading?: string;
};

export type SchemaNode = { type: string; keys: number; props: string[] };

export type Heading = { level: number; text: string };

/** Everything the checks need about one URL, read straight from the response. */
export type Page = {
  url: string;
  status: number | null;
  state: PageState;
  fetchError: string | null;
  contentType: string | null;
  /** Milliseconds to first byte of the final response. */
  responseMs: number | null;
  bytes: number | null;
  /** Number of redirect hops taken before the final response. */
  redirectHops: number;
  redirectTo: string | null;
  redirectChain: Array<{ from: string; status: number; to: string }>;
  inSitemap: boolean;
  blockedByRobots: boolean;
  /** Clicks from the start URL, when the crawl followed links to get here. */
  depth: number | null;
  inlinks: number;
  kind: PageKind;
  format: string | null;

  title: string | null;
  titlePixels: number | null;
  metaDescription: string | null;
  h1: string[];
  headings: Heading[];
  bodyText: string;
  wordCount: number;
  outLinks: LinkRef[];
  externalLinks: LinkRef[];
  canonical: string | null;
  robotsDirectives: string | null;
  xRobotsTag: string | null;
  hasViewport: boolean;
  lang: string | null;
  hreflang: Record<string, string>;
  schemaTypes: string[];
  schemaNodes: SchemaNode[];
  images: ImageRef[];
  mixedContent: boolean;
  openGraph: boolean;
  twitterCard: boolean;
  favicon: boolean;
  ampHtml: string | null;
  noindexHeaderOnly: boolean;
};

export type PageKind =
  | "home"
  | "article"
  | "product"
  | "pricing"
  | "docs"
  | "category"
  | "legal"
  | "contact"
  | "about"
  | "other";

export type Check = {
  id: string;
  label: string;
  severity: Severity;
  category: Category;
  /** Why it matters, in one or two sentences. */
  why: string;
  /** What to do about it. */
  fix: string;
};

export type Finding = Check & {
  /** Absent for site-wide findings. */
  url?: string;
  /** The evidence read off this page — the title that was too long, and so on. */
  detail: string;
};

export type Robots = {
  fetched: boolean;
  status: number | null;
  body: string | null;
  error: string | null;
  sitemaps: string[];
};

export type AiCrawlerVerdict = {
  operator: string;
  agent: string;
  job: "search" | "fetch" | "training";
  allowed: boolean;
};

export type AuditSummary = {
  /** Rows in the report, including URLs recorded without being fetched. */
  pagesCrawled: number;
  /** Disallowed to Googlebot, so recorded but never requested. */
  pagesBlocked: number;
  pagesOk: number;
  urlsFound: number;
  limitReached: boolean;
  complete: boolean;
  score: number;
  counts: Record<Severity, number>;
  durationMs: number;
};

export type AuditResult = {
  input: string;
  origin: string;
  scope: "site" | "sitemap" | "page";
  startedAt: string;
  summary: AuditSummary;
  findings: Finding[];
  pages: Page[];
  robots: Robots;
  llmsTxtStatus: number | null;
  sitemapsUsed: string[];
  sitemapUrlCount: number;
  sitemapAtRoot: boolean;
  aiCrawlers: AiCrawlerVerdict[];
  notes: string[];
};

export type BlockedCode =
  | "robots-disallow"
  | "bot-protection"
  | "http-refused"
  | "unreachable"
  | "not-html"
  | "no-urls"
  | "invalid-url"
  | "private-address"
  | "rate-limited"
  | "busy"
  | "timeout";

export type AuditError = { code: BlockedCode; message: string; hint?: string };

export type StreamEvent =
  | { type: "phase"; message: string }
  | { type: "progress"; fetched: number; total: number; queued: number }
  | { type: "done"; result: AuditResult; shareUrl?: string | null }
  | { type: "error"; error: AuditError };
