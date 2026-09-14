import re
from urllib.parse import urlsplit

from src.sites.schemas import SiteRecord
from src.technical_seo.rules.types import SiteRule

ASSET_DISALLOW = re.compile(r"^\s*disallow:\s*(\S+)", re.IGNORECASE)
ASSET_PATH = re.compile(
    r"(\.css|\.js|\.jpe?g|\.png|\.gif|\.webp|\.svg|/wp-content|/assets|/static)", re.IGNORECASE
)
SITEMAP_DIRECTIVE = re.compile(r"^\s*sitemap:\s*\S+", re.IGNORECASE | re.MULTILINE)
HTML_DOCUMENT = re.compile(r"^\s*(<!doctype\s+html|<html\b|<\?xml)", re.IGNORECASE)
STANDARD_SITEMAP_PATH = "/sitemap.xml"


def disallows_assets(robots_txt: str) -> bool:
    for line in robots_txt.split("\n"):
        match = ASSET_DISALLOW.match(line)
        path = match.group(1) if match else None
        if path and path != "/" and ASSET_PATH.search(path):
            return True
    return False


def origin_of(site: SiteRecord) -> str:
    host_variants = site.host_variants if isinstance(site.host_variants, dict) else None
    preferred = host_variants.get("preferred") if host_variants else None
    for candidate in (preferred, f"https://{site.domain}"):
        if not candidate:
            continue
        parts = urlsplit(str(candidate))
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}"
    return f"https://{site.domain}"


def well_known_rules(site: SiteRecord) -> list[SiteRule]:
    fetched = site.robots_fetched_at is not None
    status = site.robots_status
    body = site.robots_txt or ""
    crawled = site.last_crawled_at is not None
    llms_fetched = site.llms_fetched_at is not None
    llms_status = site.llms_status
    llms_body = site.llms_txt or ""
    origin = origin_of(site)
    sitemaps = site.sitemap_urls or []
    sitemap_at_root = site.sitemap_at_root is True

    return [
        SiteRule(
            kind="robots-missing",
            severity="p2",
            issue=(
                "This site has no robots.txt — the request for it came back 404. That is not broken on "
                "its own, and a site that wants everything crawled needs no file. It does mean there is "
                "nowhere to point a crawler at the sitemap, and nowhere to keep one out of an admin "
                "path, so it is usually worth adding."
            ),
            holds=fetched and status in (404, 410),
        ),
        SiteRule(
            kind="robots-unreadable",
            severity="p0",
            issue=(
                "robots.txt could not be read — the request for it failed or the server errored. This "
                "is worse than not having one: faced with an unreadable robots.txt Google may stop "
                "crawling the site altogether rather than guess what it was allowed to fetch. Fix the "
                "server, or return a clean 404."
            ),
            holds=fetched and status not in (200, 404, 410),
        ),
        SiteRule(
            kind="robots-blocks-assets",
            llm_check=True,
            severity="p1",
            issue=(
                "robots.txt disallows paths that hold CSS, JavaScript or images. Google renders a page "
                "the way a browser does, so blocking the assets means it sees a broken version of every "
                "page that depends on them — most often judging the page mobile-unfriendly or thin. "
                "Assets should be crawlable even when the pages using them are not."
            ),
            holds=fetched and status == 200 and disallows_assets(body),
        ),
        SiteRule(
            kind="robots-no-sitemap",
            severity="p2",
            issue=(
                "robots.txt names no sitemap. A Sitemap: line is the one place every crawler looks for "
                "the list of pages worth reading, and it is the only route that does not depend on the "
                "crawler guessing a filename or following enough links to find a page. Add a Sitemap: "
                "line pointing at the absolute URL of the sitemap, or the sitemap index if there are "
                "several."
            ),
            holds=fetched and status == 200 and not SITEMAP_DIRECTIVE.search(body),
        ),
        SiteRule(
            kind="sitemap-missing",
            severity="p1",
            issue=(
                "The last crawl found no sitemap URLs at all — robots.txt named none, the usual "
                "locations produced none, and any sitemap given on the Website profile screen came back "
                "empty or unreadable. Without one a crawler discovers pages only by following links, so "
                "anything the navigation does not reach may never be read, and nothing says which URLs "
                "are the ones worth indexing. It also stops the crawl: this desk reads the pages a "
                "sitemap lists, so until there is one there is nothing to audit. Publish a sitemap, then "
                "name it in robots.txt and on the Website profile screen."
            ),
            holds=crawled and not site.sitemap_url_count,
        ),
        SiteRule(
            kind="sitemap-not-at-standard-url",
            severity="p3",
            issue=(
                f"The sitemap this crawl read is {', '.join(sitemaps)}, not {origin}{STANDARD_SITEMAP_PATH}. "
                "No specification requires that path, and a crawler told about the file in robots.txt "
                "finds it wherever it lives — so nothing is broken here. What the root path buys is the "
                "case where nothing tells the crawler anything: it is the first and often only location "
                "guessed by search engines, AI crawlers, link checkers and every tool someone points at "
                "the domain, and it is the address a person types when looking for it by hand. Serve the "
                "sitemap, or a sitemap index naming the real files, at "
                f"{origin}{STANDARD_SITEMAP_PATH} as well — a redirect from there to the current file "
                "is enough — and keep the Sitemap: line in robots.txt either way."
            ),
            holds=crawled and len(sitemaps) > 0 and not sitemap_at_root,
        ),
        SiteRule(
            kind="llms-missing",
            severity="p3",
            issue=(
                "There is no /llms.txt. It is a young convention rather than a standard — no assistant "
                "is known to require it, and a site is not penalised for leaving it out — so this is the "
                "last thing to do, not the first. What it buys is control of the summary: a short "
                "markdown file naming what the site is and linking the pages worth reading gives a model "
                "fetching the domain something written by you instead of whatever it assembles from the "
                "home page. Cheap to add once the pages themselves are in order."
            ),
            holds=llms_fetched and llms_status in (404, 410),
        ),
        SiteRule(
            kind="llms-not-plain-text",
            severity="p3",
            issue=(
                "/llms.txt answers 200 but serves a web page, not markdown — the usual cause is a "
                "single-page app whose server returns the app shell for every unknown path. Anything "
                "fetching it gets HTML where it expected a plain list, which is worse than a clean 404 "
                "because nothing signals the file is absent. Either serve the real file as text, or let "
                "unknown paths 404."
            ),
            holds=llms_fetched and llms_status == 200 and bool(HTML_DOCUMENT.match(llms_body)),
        ),
    ]
