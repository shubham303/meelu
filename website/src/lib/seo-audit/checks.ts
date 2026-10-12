import type { Check, Page } from "./types";
import { pathOf, slugOf } from "./url";

export type CheckContext = {
  origin: string;
  pages: Page[];
  byUrl: Map<string, Page>;
  /** False when the page cap was hit, which makes link-graph checks unreliable. */
  complete: boolean;
  hasSitemap: boolean;
  titleCounts: Map<string, number>;
  descriptionCounts: Map<string, number>;
};

export type PageCheck = Check & {
  /** Skipped unless the whole site was crawled — partial crawls fake orphans. */
  needsCompleteCrawl?: boolean;
  needsSitemap?: boolean;
  test: (page: Page, ctx: CheckContext) => string | null;
};

const STOP_WORDS =
  /(^|[/-])(a|an|and|the|for|to|of|in|on|at|is|it|by|with|from|that|are|was|be|or)([/-]|$)/gi;

export const noindex = (page: Page): boolean =>
  /noindex/i.test(page.robotsDirectives ?? "") || /noindex/i.test(page.xRobotsTag ?? "");

export const isOk = (page: Page): boolean => page.state === "ok" && page.status === 200;

export const isIndexable = (page: Page): boolean =>
  isOk(page) && !page.blockedByRobots && !noindex(page);

const isLinked = (page: Page): boolean => page.inSitemap || page.inlinks > 0;

const truncate = (text: string, n = 90): string =>
  text.length > n ? `${text.slice(0, n - 1)}…` : text;

const HREFLANG_CODE = /^[a-z]{2,3}(-[a-z]{4})?(-([a-z]{2}|[0-9]{3}))?$/i;

const SOFT_404_TITLE = /(not found|404|no longer available|page unavailable)/i;
const SOFT_404_BODY =
  /(page you are looking for|page cannot be found|page does not exist|page you requested)/i;

function schemaNodeMissing(
  page: Page,
  types: string[],
  required: string[][],
): string | null {
  for (const node of page.schemaNodes) {
    if (!types.includes(node.type.toLowerCase())) continue;
    if (node.keys === 0) continue;
    const missing = required
      .filter((group) => !group.some((prop) => node.props.includes(prop)))
      .map((group) => group.join(" or "));
    if (missing.length > 0) {
      return `${node.type} markup is missing ${missing.join(", ")}`;
    }
  }
  return null;
}

export const PAGE_CHECKS: PageCheck[] = [
  {
    id: "server-error",
    label: "Server error (5xx)",
    severity: "critical",
    category: "crawlability",
    why: "A 5xx is not an answer, it is a failure. Google retries for a while and then drops the page out of the index entirely.",
    fix: "Check the server logs for this URL. Until it answers, nothing on it can rank.",
    test: (page) =>
      page.status !== null && page.status >= 500 ? `HTTP ${page.status}` : null,
  },
  {
    id: "robots-blocked-but-linked",
    label: "Blocked by robots.txt but still linked",
    severity: "critical",
    category: "crawlability",
    why: "The site points at this URL from the sitemap or from other pages, and robots.txt tells Googlebot not to fetch it. Every one of those links leads nowhere.",
    fix: "Either drop the Disallow rule or stop advertising the URL. Doing both is the mistake.",
    test: (page) =>
      page.blockedByRobots && isLinked(page)
        ? page.inSitemap
          ? "disallowed for Googlebot, yet listed in the sitemap"
          : `disallowed for Googlebot, yet linked from ${page.inlinks} page(s)`
        : null,
  },
  {
    id: "dead-page",
    label: "Page is gone (404 or 410)",
    severity: "high",
    category: "crawlability",
    why: "The sitemap lists it or other pages link to it, and it answers with nothing. Readers hit a dead end and the crawler burns budget on it.",
    fix: "Restore the page, redirect it to the closest live equivalent, or remove the links and sitemap entry pointing at it.",
    test: (page) =>
      page.status === 404 || page.status === 410
        ? `HTTP ${page.status}${page.inSitemap ? ", listed in the sitemap" : ""}`
        : null,
  },
  {
    id: "noindex-but-linked",
    label: "Noindex on a page the site still points at",
    severity: "high",
    category: "indexability",
    why: "The page will be dropped from search results while the site keeps asking for it to be indexed.",
    fix: "Decide which is intended: remove the noindex, or stop linking and listing it.",
    test: (page) => {
      if (!isOk(page) || !noindex(page) || !isLinked(page)) return null;
      const source = /noindex/i.test(page.robotsDirectives ?? "")
        ? "meta robots"
        : "X-Robots-Tag header";
      return `noindex via ${source}${page.inSitemap ? ", listed in the sitemap" : ""}`;
    },
  },
  {
    id: "canonical-mismatch",
    label: "Canonical points somewhere else",
    severity: "high",
    category: "indexability",
    why: "The page is in the sitemap, so the site is asking for it to be indexed, and its canonical tag tells Google to index a different URL instead. One of the two is wrong.",
    fix: "Point the canonical at this page's own URL, or take the page out of the sitemap.",
    test: (page) =>
      isOk(page) && page.inSitemap && page.canonical && page.canonical !== page.url
        ? `canonical → ${truncate(page.canonical, 120)}`
        : null,
  },
  {
    id: "canonical-to-dead-page",
    label: "Canonical points at a dead page",
    severity: "high",
    category: "indexability",
    why: "Google is being told the real version of this content lives at a URL that answers 404, so it has nowhere to send the ranking signals and may drop both.",
    fix: "Point the canonical at a page that exists, or restore the one it names.",
    test: (page, ctx) => {
      if (!isOk(page) || !page.canonical || page.canonical === page.url) return null;
      const target = ctx.byUrl.get(page.canonical);
      return target && target.status !== null && target.status >= 400
        ? `canonical → ${truncate(page.canonical, 100)} (HTTP ${target.status})`
        : null;
    },
  },
  {
    id: "canonical-to-noindex",
    label: "Canonical points at a noindex page",
    severity: "high",
    category: "indexability",
    why: "The page hands its ranking signals to a URL the site has asked Google to keep out of the index, so neither ends up indexed.",
    fix: "Remove the noindex on the target, or canonicalise somewhere that is meant to rank.",
    test: (page, ctx) => {
      if (!isOk(page) || !page.canonical || page.canonical === page.url) return null;
      const target = ctx.byUrl.get(page.canonical);
      return target && noindex(target)
        ? `canonical → ${truncate(page.canonical, 100)}, which is noindex`
        : null;
    },
  },
  {
    id: "canonical-to-redirect",
    label: "Canonical points at a redirect",
    severity: "medium",
    category: "indexability",
    why: "A canonical should name the final address of the content, not a stop on the way to it. The extra hop muddies the signal and Google may pick a different page as canonical.",
    fix: "Point the canonical at the destination URL.",
    test: (page, ctx) => {
      if (!isOk(page) || !page.canonical || page.canonical === page.url) return null;
      const target = ctx.byUrl.get(page.canonical);
      return target && target.status !== null && target.status >= 300 && target.status < 400
        ? `canonical → ${truncate(page.canonical, 100)} (HTTP ${target.status})`
        : null;
    },
  },
  {
    id: "missing-canonical",
    label: "No canonical tag",
    severity: "medium",
    category: "indexability",
    why: "Without one Google decides for itself which URL is the real version of this content, and it can settle on a tracking-parameter or print variant instead.",
    fix: "Add a canonical link pointing at the page's own address. It costs nothing and removes the guesswork.",
    test: (page) => (isIndexable(page) && !page.canonical ? "no rel=canonical" : null),
  },
  {
    id: "redirect-chain",
    label: "Redirect chain",
    severity: "medium",
    category: "crawlability",
    why: "Each hop loses a little signal and slows the crawl.",
    fix: "Point the first URL straight at the final destination.",
    test: (page) =>
      page.redirectHops > 1
        ? `${page.redirectHops} hops → ${truncate(page.redirectTo ?? "", 90)}`
        : null,
  },
  {
    id: "sitemap-redirect",
    label: "Sitemap lists a redirecting URL",
    severity: "medium",
    category: "crawlability",
    needsSitemap: true,
    why: "A sitemap should name the destination directly. Every redirect is an extra hop before Google reaches the real page, and it hints the sitemap was generated from stale URLs.",
    fix: "Replace the entry with the URL it redirects to.",
    test: (page) =>
      page.inSitemap && page.redirectHops > 0
        ? `HTTP ${page.status ?? "3xx"} → ${truncate(page.redirectTo ?? "", 90)}`
        : null,
  },
  {
    id: "missing-from-sitemap",
    label: "Indexable page missing from the sitemap",
    severity: "medium",
    category: "crawlability",
    needsCompleteCrawl: true,
    needsSitemap: true,
    why: "The sitemap is how you tell Google which pages you consider worth indexing. Leaving good pages out slows discovery of anything the crawler does not stumble across.",
    fix: "Add it to the sitemap, or say why it belongs out.",
    test: (page) =>
      isIndexable(page) && !page.inSitemap && page.inlinks > 0
        ? `linked from ${page.inlinks} page(s), not in the sitemap`
        : null,
  },
  {
    id: "orphan-page",
    label: "Orphan page — nothing links to it",
    severity: "medium",
    category: "links",
    needsCompleteCrawl: true,
    why: "An orphan is reachable only by knowing the URL, so it gets no internal link equity and readers never arrive at it by navigating.",
    fix: "Link it from somewhere relevant, or drop it from the sitemap.",
    test: (page) =>
      isOk(page) && page.inSitemap && page.inlinks === 0
        ? "in the sitemap, zero internal links in"
        : null,
  },
  {
    id: "deep-page",
    label: "More than four clicks from the home page",
    severity: "low",
    category: "links",
    needsCompleteCrawl: true,
    why: "Depth is how Google reads importance: the further down a page sits, the less often it is crawled and the less internal signal reaches it.",
    fix: "Link it from a hub or category page nearer the top.",
    test: (page) =>
      isIndexable(page) && page.depth !== null && page.depth > 4
        ? `${page.depth} clicks deep`
        : null,
  },
  {
    id: "broken-internal-link",
    label: "Links to a dead page on this site",
    severity: "medium",
    category: "links",
    why: "Readers hit a dead end, and the crawler burns budget fetching URLs that answer 404.",
    fix: "Fix the link to point at the live page, or remove it.",
    test: (page, ctx) => {
      if (!isOk(page)) return null;
      const broken = page.outLinks
        .map((link) => ctx.byUrl.get(link.url))
        .filter((t) => t && t.status !== null && t.status >= 400);
      if (broken.length === 0) return null;
      return `${broken.length} broken link(s), e.g. ${truncate(broken[0]!.url, 80)} (HTTP ${broken[0]!.status})`;
    },
  },
  {
    id: "internal-link-to-redirect",
    label: "Links to a redirecting page on this site",
    severity: "low",
    category: "links",
    why: "Nothing is visibly broken, but every one of these is an avoidable extra request and a small loss of link signal.",
    fix: "Update the link to the destination URL.",
    test: (page, ctx) => {
      if (!isOk(page)) return null;
      const hops = page.outLinks
        .map((link) => ctx.byUrl.get(link.url))
        .filter((t) => t && t.status !== null && t.status >= 300 && t.status < 400);
      if (hops.length === 0) return null;
      return `${hops.length} link(s) to redirects, e.g. ${truncate(hops[0]!.url, 80)}`;
    },
  },
  {
    id: "mixed-content",
    label: "HTTPS page loading assets over HTTP",
    severity: "medium",
    category: "crawlability",
    why: "Browsers block or downgrade those requests, so the page renders broken for visitors and for Google, which judges what it can actually render.",
    fix: "Change the asset URLs to https.",
    test: (page) =>
      isOk(page) && page.mixedContent ? "an image, script or stylesheet is loaded over http://" : null,
  },
  {
    id: "soft-404",
    label: "Soft 404 — reads like an error page but answers 200",
    severity: "medium",
    category: "crawlability",
    why: "Google calls this a soft 404 and it wastes crawl budget on a URL that has nothing to index.",
    fix: "Return a real 404 or 410, or put actual content there.",
    test: (page) =>
      isOk(page) &&
      page.wordCount < 200 &&
      (SOFT_404_TITLE.test(page.title ?? "") || SOFT_404_BODY.test(page.bodyText))
        ? `${page.wordCount} words, and the page says it was not found`
        : null,
  },
  {
    id: "thin-content",
    label: "Thin content",
    severity: "medium",
    category: "content",
    why: "A short article or product page rarely has enough on it to answer the question that brought someone there, and a site full of them dilutes the pages worth reading.",
    fix: "Expand it, merge it into a fuller page, or drop it.",
    test: (page) =>
      isIndexable(page) &&
      ["article", "product", "docs"].includes(page.kind) &&
      page.wordCount < 250
        ? `${page.wordCount} words on a ${page.kind} page`
        : null,
  },
  {
    id: "missing-title",
    label: "No title tag",
    severity: "high",
    category: "metadata",
    why: "The title is the headline in search results and the strongest on-page signal of what the page is about. Without one Google writes its own from the page text, usually badly.",
    fix: "Write a title that names what this page covers, with the distinctive words first.",
    test: (page) => (isOk(page) && !page.title ? "no <title> element" : null),
  },
  {
    id: "duplicate-title",
    label: "Duplicate title",
    severity: "medium",
    category: "metadata",
    why: "Two pages claiming the same headline look like the same page to Google, which picks one and ignores the other.",
    fix: "Give each page a title that names what only it covers.",
    test: (page, ctx) => {
      if (!isIndexable(page) || !page.title) return null;
      const n = ctx.titleCounts.get(page.title) ?? 0;
      return n > 1 ? `shared with ${n - 1} other page(s): “${truncate(page.title)}”` : null;
    },
  },
  {
    id: "title-too-long",
    label: "Title will be cut off in search results",
    severity: "low",
    category: "metadata",
    why: "What gets trimmed is the end, which is usually where the specific part of the title sits. Google measures the width in pixels, not characters.",
    fix: "Put the words that matter first and shorten the rest.",
    test: (page) =>
      isOk(page) && page.titlePixels !== null && page.titlePixels > 580
        ? `${page.title?.length} characters, about ${page.titlePixels}px wide (results cut off near 580px)`
        : null,
  },
  {
    id: "title-too-short",
    label: "Title far shorter than the space given",
    severity: "low",
    category: "metadata",
    why: "There is room to say what the page covers and who it is for. A two-word title spends none of it and reads as vague next to competitors.",
    fix: "Use the width: name the subject and the angle.",
    test: (page) =>
      isOk(page) && page.title && page.titlePixels !== null && page.titlePixels < 200
        ? `“${page.title}” — about ${page.titlePixels}px of a possible 580px`
        : null,
  },
  {
    id: "missing-meta-description",
    label: "No meta description",
    severity: "medium",
    category: "metadata",
    why: "Google falls back to scraping a snippet out of the body, which reads like an accident in the result list. This does not change ranking, it changes how many people click.",
    fix: "Write one sentence that gives someone a reason to open this page rather than the one above it.",
    test: (page) =>
      isOk(page) && !page.metaDescription ? "no meta description" : null,
  },
  {
    id: "duplicate-meta-description",
    label: "Duplicate meta description",
    severity: "low",
    category: "metadata",
    why: "A description written once and pasted everywhere tells a searcher nothing about which result to open, so Google usually discards it and writes its own.",
    fix: "Write one per page, about that page.",
    test: (page, ctx) => {
      if (!isIndexable(page) || !page.metaDescription) return null;
      const n = ctx.descriptionCounts.get(page.metaDescription) ?? 0;
      return n > 1 ? `shared with ${n - 1} other page(s)` : null;
    },
  },
  {
    id: "meta-description-length",
    label: "Meta description too short or too long",
    severity: "low",
    category: "metadata",
    why: "Around 70 to 160 characters is what shows. Below that it says nothing; above it, it is cut off mid-sentence.",
    fix: "Aim for one complete sentence inside that range.",
    test: (page) => {
      if (!isOk(page) || !page.metaDescription) return null;
      const n = page.metaDescription.length;
      if (n >= 70 && n <= 160) return null;
      return `${n} characters (aim for 70–160)`;
    },
  },
  {
    id: "missing-h1",
    label: "No H1",
    severity: "medium",
    category: "content",
    why: "The page has no top-level heading naming its subject, which leaves both readers and crawlers to infer the topic from the body text.",
    fix: "Add one H1 that names what the page is about.",
    test: (page) => (isOk(page) && page.h1.length === 0 ? "no <h1> element" : null),
  },
  {
    id: "multiple-h1",
    label: "More than one H1",
    severity: "low",
    category: "content",
    why: "The H1 names the one subject of the page, so several of them leaves it ambiguous which is the real heading — usually a template putting a site name or widget title in an H1.",
    fix: "Keep one and demote the rest.",
    test: (page) =>
      isOk(page) && page.h1.length > 1
        ? `${page.h1.length} H1s: ${page.h1.slice(0, 3).map((h) => `“${truncate(h, 40)}”`).join(", ")}`
        : null,
  },
  {
    id: "heading-hierarchy-skip",
    label: "Headings skip a level",
    severity: "low",
    category: "content",
    why: "Headings are the outline of the page, and a jump breaks the structure that screen readers and answer engines use to work out which part answers what.",
    fix: "Step down one level at a time.",
    test: (page) => {
      if (!isOk(page)) return null;
      for (let i = 1; i < page.headings.length; i++) {
        const jump = page.headings[i].level - page.headings[i - 1].level;
        if (jump >= 2) {
          return `H${page.headings[i - 1].level} → H${page.headings[i].level} at “${truncate(page.headings[i].text, 50)}”`;
        }
      }
      return null;
    },
  },
  {
    id: "image-missing-alt",
    label: "Images with no alt attribute",
    severity: "medium",
    category: "content",
    why: "Alt text is what a screen reader announces and what image search reads. A decorative image should still carry an empty alt so it can be skipped deliberately.",
    fix: "Describe what the image shows, or mark it decorative with alt=\"\".",
    test: (page) => {
      if (!isOk(page)) return null;
      const missing = page.images.filter((img) => img.alt === undefined);
      return missing.length > 0
        ? `${missing.length} of ${page.images.length} image(s), e.g. ${truncate(missing[0].src, 70)}`
        : null;
    },
  },
  {
    id: "image-missing-dimensions",
    label: "Images with no width and height",
    severity: "low",
    category: "mobile",
    why: "The browser cannot reserve space for them, so the page jumps as they load and the reader taps the wrong thing.",
    fix: "Set the width and height attributes. That is the whole fix.",
    test: (page) => {
      if (!isOk(page)) return null;
      const missing = page.images.filter((img) => !img.width || !img.height);
      return missing.length > 0
        ? `${missing.length} of ${page.images.length} image(s)`
        : null;
    },
  },
  {
    id: "missing-viewport",
    label: "No viewport meta tag",
    severity: "medium",
    category: "mobile",
    why: "Without it a phone renders the page at desktop width and shrinks it, so the text is unreadable until the reader pinches to zoom. Google indexes what the mobile crawler sees.",
    fix: 'Add <meta name="viewport" content="width=device-width, initial-scale=1">.',
    test: (page) => (isOk(page) && !page.hasViewport ? "no viewport meta tag" : null),
  },
  {
    id: "missing-lang",
    label: "No language on the html tag",
    severity: "low",
    category: "international",
    why: "Screen readers use it to pick a voice and search engines use it to decide who the page is for. Leaving it off means both are guessing from the text.",
    fix: "Set lang on the html element.",
    test: (page) => (isOk(page) && !page.lang ? "<html> has no lang attribute" : null),
  },
  {
    id: "restrictive-snippet",
    label: "Snippets turned off",
    severity: "medium",
    category: "indexability",
    why: "Without a snippet the result is a bare blue link, and the same directive keeps the page out of the answers AI search assembles.",
    fix: "If it was set to protect paid content, keep it deliberately. If nobody remembers setting it, remove it.",
    test: (page) => {
      if (!isOk(page)) return null;
      const directives = `${page.robotsDirectives ?? ""} ${page.xRobotsTag ?? ""}`;
      return /nosnippet|max-snippet:\s*0/i.test(directives)
        ? `robots directives: ${truncate(directives.trim(), 80)}`
        : null;
    },
  },
  {
    id: "no-structured-data",
    label: "Article or product page with no structured data",
    severity: "medium",
    category: "structured-data",
    why: "Schema markup is how you state in machine-readable terms what the page is — the author, the date, the price — and it is what rich results and answer engines read.",
    fix: "Add JSON-LD for the type of page this is.",
    test: (page) =>
      isIndexable(page) &&
      ["article", "product"].includes(page.kind) &&
      page.schemaTypes.length === 0
        ? `${page.kind} page with no JSON-LD`
        : null,
  },
  {
    id: "home-missing-organization",
    label: "Home page has no Organization or WebSite markup",
    severity: "medium",
    category: "structured-data",
    why: "Those are what tie the site to a named entity — the business, its logo, its official profiles. Without them a search engine has only the text to work out who you are.",
    fix: "Add Organization and WebSite JSON-LD to the home page, with sameAs links to the profiles you already own.",
    test: (page) =>
      isOk(page) &&
      page.kind === "home" &&
      !page.schemaTypes.some((t) =>
        ["organization", "website", "localbusiness", "corporation"].includes(t.toLowerCase()),
      )
        ? "no Organization, WebSite or LocalBusiness node"
        : null,
  },
  {
    id: "schema-article-incomplete",
    label: "Article markup missing required properties",
    severity: "medium",
    category: "structured-data",
    why: "Structured data without a headline, an author and a published date is read and then ignored, so the page gets none of the rich result it is marked up for.",
    fix: "Add the missing properties to the JSON-LD node.",
    test: (page) =>
      isIndexable(page)
        ? schemaNodeMissing(
            page,
            ["article", "blogposting", "newsarticle", "techarticle"],
            [["headline"], ["author"], ["datePublished"]],
          )
        : null,
  },
  {
    id: "schema-product-incomplete",
    label: "Product markup missing name, offer or rating",
    severity: "medium",
    category: "structured-data",
    why: "Google needs a name and at least one of an offer, a review or an aggregate rating before a product is eligible for a rich result. Without them the markup is dead weight.",
    fix: "Add the offer with its price, currency and availability — that is the one that earns the result.",
    test: (page) =>
      isIndexable(page)
        ? schemaNodeMissing(
            page,
            ["product"],
            [["name"], ["offers", "review", "aggregateRating"]],
          )
        : null,
  },
  {
    id: "schema-faq-incomplete",
    label: "FAQ markup with no questions",
    severity: "low",
    category: "structured-data",
    why: "An FAQPage carries its content in mainEntity — a list of questions each with an accepted answer. One without them declares a shape and fills none of it.",
    fix: "Populate it from the questions actually on the page, or remove the markup.",
    test: (page) =>
      isIndexable(page)
        ? schemaNodeMissing(page, ["faqpage", "qapage"], [["mainEntity"]])
        : null,
  },
  {
    id: "schema-breadcrumb-incomplete",
    label: "Breadcrumb markup with no items",
    severity: "low",
    category: "structured-data",
    why: "A BreadcrumbList exists to name the trail of pages above this one. An empty one gives search results nothing to show in place of the bare URL.",
    fix: "Fill in itemListElement with the trail the page actually sits in.",
    test: (page) =>
      isIndexable(page)
        ? schemaNodeMissing(page, ["breadcrumblist"], [["itemListElement"]])
        : null,
  },
  {
    id: "schema-organization-incomplete",
    label: "Organization markup with no name or URL",
    severity: "low",
    category: "structured-data",
    why: "Those two are what tie the markup to an entity a search engine can recognise. Without them it describes nobody.",
    fix: "Add the name and the canonical home page URL, and the logo and sameAs profiles while you are there.",
    test: (page) =>
      isIndexable(page)
        ? schemaNodeMissing(
            page,
            ["organization", "corporation", "onlinebusiness", "ngo"],
            [["name"], ["url"]],
          )
        : null,
  },
  {
    id: "schema-localbusiness-incomplete",
    label: "LocalBusiness markup with no address or phone",
    severity: "medium",
    category: "structured-data",
    why: "A local business is identified by where it is and how to reach it. Markup missing those cannot be matched to the business in local results or on a map.",
    fix: "Add the full address as a PostalAddress, with the telephone number.",
    test: (page) =>
      isIndexable(page)
        ? schemaNodeMissing(
            page,
            ["localbusiness", "restaurant", "store", "professionalservice", "medicalbusiness"],
            [["name"], ["address"], ["telephone"]],
          )
        : null,
  },
  {
    id: "missing-open-graph",
    label: "No Open Graph tags",
    severity: "low",
    category: "metadata",
    why: "Shared on Slack, LinkedIn or a group chat, the link shows a bare URL instead of a title, description and image. It costs clicks on every share.",
    fix: "Add og:title, og:description and og:image.",
    test: (page) =>
      isIndexable(page) && !page.openGraph ? "no og: meta tags" : null,
  },
  {
    id: "hreflang-no-self-reference",
    label: "hreflang set does not list itself",
    severity: "high",
    category: "international",
    why: "Every page in an hreflang set has to name every variant including its own URL. A set that breaks that rule is ignored wholesale, and the variants can compete with each other.",
    fix: "Add the self-referencing tag to each page in the set.",
    test: (page) => {
      const codes = Object.entries(page.hreflang).filter(([k]) => k !== "x-default");
      if (codes.length === 0) return null;
      return codes.some(([, href]) => href === page.url)
        ? null
        : `${codes.length} variant(s) listed, none of them this URL`;
    },
  },
  {
    id: "hreflang-invalid-code",
    label: "Invalid hreflang code",
    severity: "high",
    category: "international",
    why: "hreflang takes a two-letter language code, optionally with a country code after it — en-GB, not en-UK, and a country on its own is never valid. An unrecognised code invalidates the whole set.",
    fix: "Correct the code to a valid ISO 639-1 language, optionally with an ISO 3166-1 Alpha-2 region.",
    test: (page) => {
      const bad = Object.keys(page.hreflang).filter(
        (k) => k !== "x-default" && !HREFLANG_CODE.test(k),
      );
      return bad.length > 0 ? `invalid: ${bad.slice(0, 5).join(", ")}` : null;
    },
  },
  {
    id: "hreflang-not-reciprocal",
    label: "hreflang set is not reciprocal",
    severity: "medium",
    category: "international",
    why: "Google only honours hreflang when both sides agree, so a one-way tag is thrown away and the variants are treated as unrelated pages.",
    fix: "Make every page in the set list every other one.",
    test: (page, ctx) => {
      const codes = Object.entries(page.hreflang).filter(([k]) => k !== "x-default");
      if (codes.length === 0) return null;
      for (const [, href] of codes) {
        const target = ctx.byUrl.get(href);
        if (!target || href === page.url) continue;
        if (Object.keys(target.hreflang).length === 0) continue;
        if (!Object.values(target.hreflang).includes(page.url)) {
          return `${truncate(href, 80)} does not point back at this page`;
        }
      }
      return null;
    },
  },
  {
    id: "hreflang-no-x-default",
    label: "hreflang set has no x-default",
    severity: "low",
    category: "international",
    why: "x-default is the fallback Google serves to anyone whose language or country is not in the set. Without it those visitors get whichever variant the algorithm guesses.",
    fix: "Point x-default at the version you would rather a stranger landed on.",
    test: (page) => {
      const codes = Object.keys(page.hreflang);
      return codes.length > 0 && !codes.includes("x-default")
        ? `${codes.length} variant(s), no x-default`
        : null;
    },
  },
  {
    id: "url-hygiene",
    label: "Capitals, underscores or tracking parameters in the URL",
    severity: "low",
    category: "urls",
    why: "Servers treat upper and lower case as different addresses, word separators should be hyphens, and a tracking parameter left in a link creates a second URL for the same page.",
    fix: "Lower-case the path, use hyphens between words, and strip tracking parameters from internal links.",
    test: (page) => {
      const path = pathOf(page.url);
      const faults: string[] = [];
      if (/[A-Z]/.test(path)) faults.push("capitals");
      if (path.includes("_")) faults.push("underscores");
      if (/[?&](utm_|fbclid|gclid|mc_cid|_ga)=/.test(page.url)) faults.push("tracking parameters");
      return faults.length > 0 ? faults.join(", ") : null;
    },
  },
  {
    id: "url-too-long",
    label: "URL path over 100 characters",
    severity: "low",
    category: "urls",
    why: "A long URL is truncated when it is shown, is harder to read in a result, and usually means the path repeats what the folders above it already say.",
    fix: "Shorten the slug to the words that identify the page.",
    test: (page) => {
      const slug = slugOf(page.url);
      return slug.length > 100 ? `${slug.length} characters` : null;
    },
  },
  {
    id: "url-dated",
    label: "Year and month baked into the URL",
    severity: "low",
    category: "urls",
    why: "It dates the page permanently: updating the article cannot update its address, so the URL keeps announcing a year that is no longer true, and moving it later costs a redirect.",
    fix: "Unless the date is the point of the page, leave it out of the path and let the published date live in the markup.",
    test: (page) =>
      /\/(19|20)[0-9]{2}[/-](0[1-9]|1[0-2])([/-]|$)/.test(slugOf(page.url))
        ? "a date appears in the path"
        : null,
  },
  {
    id: "url-stop-words",
    label: "Several stop words in the slug",
    severity: "low",
    category: "urls",
    why: "And, the, for, to, of take up room in a result without telling anyone anything, and the slug reads the same once they are gone.",
    fix: "Worth doing on a page that is not published yet. Changing a live URL costs a redirect, which is a worse trade than leaving the words in.",
    test: (page) => {
      const slug = slugOf(page.url);
      const matches = slug.match(STOP_WORDS);
      return matches && matches.length >= 2
        ? `${matches.length} stop words in ${truncate(slug, 60)}`
        : null;
    },
  },
  {
    id: "slow-response",
    label: "Slow server response",
    severity: "low",
    category: "mobile",
    why: "This is the server's own thinking time, before a single byte of the page arrives. Everything the browser does afterwards is stacked on top of it.",
    fix: "Look at caching or the queries behind this route. Under 600ms is the target.",
    test: (page) =>
      isOk(page) && page.responseMs !== null && page.responseMs > 1500
        ? `${(page.responseMs / 1000).toFixed(1)}s to first byte`
        : null,
  },
];
