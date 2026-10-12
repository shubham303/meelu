import { crawlSite, MAX_PAGES, type CrawlOptions } from "./crawl";
import { fetchUrl } from "./net";
import { aiCrawlerVerdicts } from "./robots";
import { PAGE_CHECKS, isIndexable, isOk, type PageCheck } from "./checks";
import { siteFindings } from "./site-checks";
import { normalise, sameHost } from "./url";
import type {
  AuditError,
  AuditResult,
  Check,
  Finding,
  Page,
  Severity,
} from "./types";

export { MAX_PAGES };

const SEVERITY_WEIGHT: Record<Severity, number> = {
  critical: 10,
  high: 5,
  medium: 2,
  low: 0.5,
};

export type AuditOptions = CrawlOptions;

export type AuditOutcome =
  | { ok: true; result: AuditResult }
  | { ok: false; error: AuditError };

export async function runAudit(
  rawInput: string,
  options: AuditOptions = {},
): Promise<AuditOutcome> {
  const outcome = await crawlSite(rawInput, options);
  if (!outcome.ok) return outcome;

  const {
    origin,
    scope,
    startedAt,
    startTime,
    outOfTime,
    emit,
    maxPages,
    signal,
    pages,
    byUrl,
    seen,
    blockedSeen,
    hitCap,
    robots,
    robotsBody,
    llmsStatus,
    sitemapsUsed,
    sitemapUrlCount,
    sitemapAtRoot,
    notes,
  } = outcome.crawl;

  // Two extra requests that catch the most common duplicate-content fault.
  let httpRedirects: boolean | null = null;
  let hostVariantRedirects: boolean | null = null;
  let hostVariantUrl: string | null = null;
  if (scope !== "page" && !outOfTime()) {
    const host = new URL(origin).hostname;
    const variantHost = host.startsWith("www.") ? host.slice(4) : `www.${host}`;
    const variant = `https://${variantHost}/`;
    hostVariantUrl = variant;
    const [httpRes, variantRes] = await Promise.all([
      fetchUrl(origin.replace(/^https:/, "http:") + "/", { timeoutMs: 8_000, signal }),
      fetchUrl(variant, { timeoutMs: 8_000, signal }),
    ]);
    if (origin.startsWith("https://") && httpRes.status !== undefined) {
      httpRedirects =
        httpRes.chain.length > 0 && (httpRes.finalUrl ?? "").startsWith("https://");
    }
    if (variantRes.status === 200) {
      hostVariantRedirects =
        variantRes.chain.length > 0 && sameHost(variantRes.finalUrl ?? "", origin);
    }
  }

  // The link graph is only worth reading when the whole crawl finished.
  const complete = !hitCap && !signal?.aborted;
  for (const page of pages) {
    if (!isOk(page)) continue;
    const targets = new Set(page.outLinks.map((l) => normalise(l.url)));
    for (const target of targets) {
      const hit = byUrl.get(target);
      if (hit && hit.url !== page.url) hit.inlinks += 1;
    }
  }

  const indexable = pages.filter(isIndexable);
  const titleCounts = new Map<string, number>();
  const descriptionCounts = new Map<string, number>();
  for (const page of indexable) {
    if (page.title) titleCounts.set(page.title, (titleCounts.get(page.title) ?? 0) + 1);
    if (page.metaDescription) {
      descriptionCounts.set(
        page.metaDescription,
        (descriptionCounts.get(page.metaDescription) ?? 0) + 1,
      );
    }
  }

  emit({ type: "phase", message: "Running the checks" });
  const ctx = {
    origin,
    pages,
    byUrl,
    complete,
    hasSitemap: sitemapUrlCount > 0,
    titleCounts,
    descriptionCounts,
  };

  const findings: Finding[] = [];
  for (const check of PAGE_CHECKS) {
    if (check.needsCompleteCrawl && !complete) continue;
    if (check.needsSitemap && sitemapUrlCount === 0) continue;
    for (const page of pages) {
      const detail = check.test(page, ctx);
      if (detail) findings.push({ ...describe(check), url: page.url, detail });
    }
  }

  const aiCrawlers = aiCrawlerVerdicts(robotsBody);
  const siteLevel = siteFindings({
    origin,
    robots,
    llmsStatus: llmsStatus,
    sitemapsUsed,
    sitemapUrlCount,
    sitemapAtRoot,
    aiCrawlers,
    httpRedirects,
    hostVariantRedirects,
    hostVariantUrl,
  }).filter(
    // A one-page audit never looked for a sitemap, so it cannot report on one.
    (finding) =>
      scope !== "page" ||
      !["sitemap-missing", "sitemap-not-at-standard-url"].includes(finding.id),
  );
  findings.push(...siteLevel);

  const order: Severity[] = ["critical", "high", "medium", "low"];
  findings.sort(
    (a, b) =>
      order.indexOf(a.severity) - order.indexOf(b.severity) ||
      a.id.localeCompare(b.id) ||
      (a.url ?? "").localeCompare(b.url ?? ""),
  );

  const counts: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0 };
  let pagePenalty = 0;
  let sitePenalty = 0;
  for (const finding of findings) {
    counts[finding.severity] += 1;
    if (finding.url) pagePenalty += SEVERITY_WEIGHT[finding.severity];
    else sitePenalty += SEVERITY_WEIGHT[finding.severity];
  }
  const pagesCrawled = pages.length;
  // Page faults are averaged over the pages read; site-wide ones are counted once.
  const score = Math.max(
    0,
    Math.min(
      100,
      Math.round(100 - (pagePenalty / Math.max(1, pagesCrawled)) * 8 - sitePenalty * 1.5),
    ),
  );

  if (hitCap && scope !== "page") {
    notes.push(
      `The audit stops at ${maxPages} pages. Checks that need the whole link graph — orphan pages, pages missing from the sitemap, crawl depth — were skipped because a partial crawl invents false ones.`,
    );
  }
  if (blockedSeen.size > 0) {
    notes.push(
      `${blockedSeen.size} URL(s) are disallowed to Googlebot by robots.txt and were recorded without being read.`,
    );
  }

  const result: AuditResult = {
    input: rawInput.trim(),
    origin,
    scope,
    startedAt,
    summary: {
      pagesCrawled,
      pagesBlocked: blockedSeen.size,
      pagesOk: pages.filter(isOk).length,
      urlsFound: seen.size,
      limitReached: hitCap,
      complete,
      score,
      counts,
      durationMs: Date.now() - startTime,
    },
    findings,
    pages,
    robots: { ...robots, body: robots.body ? robots.body.slice(0, 4000) : null },
    llmsTxtStatus: llmsStatus,
    sitemapsUsed,
    sitemapUrlCount,
    sitemapAtRoot,
    aiCrawlers,
    notes,
  };

  emit({ type: "done", result });
  return { ok: true, result };
}

/** The rules carry a test function and gating flags the browser has no use for. */
function describe(check: PageCheck): Check {
  return {
    id: check.id,
    label: check.label,
    severity: check.severity,
    category: check.category,
    why: check.why,
    fix: check.fix,
  };
}

const PAGE_FIELDS_FOR_TABLE = [
  "url",
  "status",
  "state",
  "fetchError",
  "responseMs",
  "bytes",
  "redirectHops",
  "redirectTo",
  "inSitemap",
  "blockedByRobots",
  "depth",
  "inlinks",
  "kind",
  "title",
  "titlePixels",
  "metaDescription",
  "wordCount",
  "canonical",
  "robotsDirectives",
  "xRobotsTag",
  "hasViewport",
  "lang",
  "mixedContent",
  "openGraph",
] as const;

export type SlimPage = Pick<Page, (typeof PAGE_FIELDS_FOR_TABLE)[number]> & {
  h1: string[];
  imageCount: number;
  imagesMissingAlt: number;
  outLinkCount: number;
  externalLinkCount: number;
  schemaTypes: string[];
  hreflangCount: number;
};

export type SlimResult = Omit<AuditResult, "pages"> & { pages: SlimPage[] };

/** Body text and full link lists are worth megabytes and no use in the browser. */
export function slimResult(result: AuditResult): SlimResult {
  return {
    ...result,
    pages: result.pages.map((page) => {
      const slim = {} as Record<string, unknown>;
      for (const field of PAGE_FIELDS_FOR_TABLE) slim[field] = page[field];
      return {
        ...slim,
        h1: page.h1,
        imageCount: page.images.length,
        imagesMissingAlt: page.images.filter((img) => img.alt === undefined).length,
        outLinkCount: page.outLinks.length,
        externalLinkCount: page.externalLinks.length,
        schemaTypes: page.schemaTypes,
        hreflangCount: Object.keys(page.hreflang).length,
      } as SlimPage;
    }),
  };
}
