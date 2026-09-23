from dataclasses import dataclass

from src.technical_seo.rules.types import PageRule, SiteRule

RENDERED = "r.rendered_at is not null and r.render_error is null and site_pages.status = 200"

RAW_WORDS = "coalesce(site_pages.word_count, 0)"

RAW_LINKS = "jsonb_array_length(site_pages.out_links)"

RAW_NOINDEX = "(coalesce(site_pages.robots_directives, '') ilike '%noindex%')"

RENDERED_NOINDEX = "(coalesce(r.robots_directives, '') ilike '%noindex%')"

JS_ONLY_CONTENT = f"{RENDERED} and r.word_count >= 100 and {RAW_WORDS} < r.word_count * 0.3"

MOBILE_RENDERED = "m.rendered_at is not null and m.render_error is null and site_pages.status = 200"

BOTH_RENDERED = f"{RENDERED} and {MOBILE_RENDERED}"

MOBILE_NOINDEX = "(coalesce(m.robots_directives, '') ilike '%noindex%')"

MOBILE_DIFFERS = (
    f"{BOTH_RENDERED} and (r.title is distinct from m.title"
    " or r.canonical is distinct from m.canonical"
    f" or {RENDERED_NOINDEX} is distinct from {MOBILE_NOINDEX})"
)

MIN_RENDERED_FOR_SITE_VERDICT = 5

JS_DEPENDENT_SHARE = 0.5

MOBILE_DIFFERS_SHARE = 0.5


@dataclass(frozen=True)
class RenderCounts:
    rendered: int
    js_dependent: int
    both_rendered: int
    mobile_differs: int


RENDER_PAGE_RULES: list[PageRule] = [
    PageRule(
        kind="js-only-content",
        severity="p1",
        issue_type="desktop",
        issue=(
            "Almost all of this page's text exists only after JavaScript runs. The raw HTML the "
            "server sends carries a fraction of the words the rendered page shows, so any crawler "
            "that does not execute scripts — every AI crawler, and Google on its first pass — sees "
            "an empty shell. Server-render or pre-render the page so the content is in the "
            "response itself."
        ),
        where=JS_ONLY_CONTENT,
    ),
    PageRule(
        kind="js-only-title",
        severity="p1",
        issue_type="desktop",
        issue=(
            "The title tag is written by JavaScript; the raw HTML has none. Non-rendering crawlers "
            "index the page without a title, and even Google shows the bare URL until its render "
            "queue catches up. Put the title in the server response."
        ),
        where=f"{RENDERED} and site_pages.title is null and r.title is not null",
    ),
    PageRule(
        kind="js-only-canonical",
        severity="p2",
        issue_type="desktop",
        issue=(
            "The canonical link only appears after JavaScript runs. A canonical that is not in "
            "the raw HTML is ignored by crawlers that do not render, and Google treats a canonical "
            "injected by script as a weak hint at best. Emit it server-side."
        ),
        where=f"{RENDERED} and site_pages.canonical is null and r.canonical is not null",
    ),
    PageRule(
        kind="js-only-h1",
        severity="p2",
        issue_type="desktop",
        issue=(
            "The H1 is added by JavaScript; the server response has no heading at all. Crawlers "
            "that skip rendering see a page with no stated topic. Render the heading on the server."
        ),
        where=f"{RENDERED} and site_pages.h1 = '{{}}'::text[] and r.h1 <> '{{}}'::text[]",
    ),
    PageRule(
        kind="js-only-schema",
        severity="p2",
        issue_type="desktop",
        issue=(
            "Structured data is injected by JavaScript and is absent from the raw HTML. Rich "
            "results depend on Google's render pass picking it up, and AI crawlers never see it. "
            "Inline the JSON-LD in the server response."
        ),
        where=(
            f"{RENDERED} and site_pages.schema_types = '{{}}'::text[]"
            " and r.schema_types <> '{}'::text[]"
        ),
    ),
    PageRule(
        kind="js-only-links",
        severity="p1",
        issue_type="desktop",
        issue=(
            "Many of this page's internal links exist only after JavaScript runs — navigation, "
            "related items or pagination rendered client-side. Crawlers that do not execute "
            "scripts cannot follow them, so the pages behind them look orphaned and link equity "
            "never reaches them. Render the links as plain anchors in the HTML."
        ),
        where=f"{RENDERED} and r.internal_links >= {RAW_LINKS} + 5 and r.internal_links > {RAW_LINKS} * 2",
    ),
    PageRule(
        kind="robots-changed-by-js",
        severity="p0",
        issue_type="desktop",
        issue=(
            "JavaScript changes the page's indexing directive: the raw HTML and the rendered page "
            "disagree on noindex. Google reads the directive before rendering, and a script that "
            "adds noindex later can drop the page from the index while one that removes it is "
            "ignored. Decide once, in the server response."
        ),
        where=f"{RENDERED} and {RAW_NOINDEX} is distinct from {RENDERED_NOINDEX}",
    ),
    PageRule(
        kind="canonical-changed-by-js",
        severity="p1",
        issue_type="desktop",
        issue=(
            "The canonical URL the server sends is not the one the page ends up with after "
            "JavaScript runs. Two different signals for the same page make Google pick either, and "
            "consolidation becomes unpredictable. Make the server-side canonical the only one."
        ),
        where=(
            f"{RENDERED} and site_pages.canonical is not null and r.canonical is not null"
            " and site_pages.canonical <> r.canonical"
        ),
    ),
    PageRule(
        kind="client-side-redirect",
        severity="p1",
        issue_type="desktop",
        issue=(
            "The server answers 200 but JavaScript then moves the visitor to another URL. "
            "Non-rendering crawlers index the shell at the original address and never see the "
            "destination; Google treats the script redirect as a weaker signal than a real one. "
            "Send an HTTP 301 instead."
        ),
        where=f"{RENDERED} and r.final_url is not null and r.final_url <> site_pages.url and r.main_frame_navigations > 0",
    ),
    PageRule(
        kind="render-blocked-assets",
        severity="p1",
        issue_type="desktop",
        issue=(
            "Rendering this page needs scripts or styles that robots.txt disallows for Googlebot. "
            "Google renders with whatever it is allowed to fetch, so the page it evaluates is "
            "broken or empty even though a browser shows it fine. Allow the asset paths in "
            "robots.txt."
        ),
        where=f"{RENDERED} and r.blocked_assets > 0",
    ),
    PageRule(
        kind="render-console-errors",
        severity="p2",
        issue_type="desktop",
        issue=(
            "JavaScript threw errors while this page rendered. An uncaught exception can stop the "
            "rest of the script, leaving content, links or structured data unrendered for the "
            "crawler even when the page looks fine after a manual reload. Fix the errors in the "
            "recorded samples."
        ),
        where=f"{RENDERED} and r.console_errors > 0",
    ),
    PageRule(
        kind="render-failed-requests",
        severity="p2",
        issue_type="desktop",
        issue=(
            "Sub-resources failed to load while this page rendered — scripts, styles, data calls "
            "or images answered with an error or never came back. Whatever depended on them is "
            "missing from the rendered page. The failed URLs are recorded with the render."
        ),
        where=f"{RENDERED} and r.failed_requests > 0",
    ),
    PageRule(
        kind="heavy-javascript",
        severity="p3",
        issue_type="desktop",
        issue=(
            "This page loads more than 1.5 MB of JavaScript. That much script costs seconds on a "
            "phone before anything is interactive, and a render budget on every crawler that "
            "executes it. Audit the bundles for unused code and third-party tags."
        ),
        where=f"{RENDERED} and r.js_bytes > 1500000",
    ),
    PageRule(
        kind="too-many-requests",
        severity="p3",
        issue_type="desktop",
        issue=(
            "Rendering this page made more than 150 network requests. Each one is a round trip "
            "the browser waits on, and most are tracking pixels, fonts and widgets the content "
            "does not need. Consolidate assets and cut the tags that earn nothing."
        ),
        where=f"{RENDERED} and r.request_count > 150",
    ),
    PageRule(
        kind="third-party-bloat",
        severity="p3",
        issue_type="desktop",
        issue=(
            "This page pulls resources from more than ten third-party hosts. Every extra origin "
            "is a DNS lookup, a connection and a script you do not control, and together they are "
            "usually the largest share of load time. The hosts are recorded with the render; "
            "keep the ones that pay for themselves."
        ),
        where=f"{RENDERED} and coalesce(array_length(r.third_party_hosts, 1), 0) > 10",
    ),
    PageRule(
        kind="mobile-js-only-content",
        severity="p1",
        issue_type="mobile",
        issue=(
            "On a phone this page's text exists only after JavaScript runs. The raw HTML carries "
            "a fraction of the words the rendered mobile page shows, and Google indexes from its "
            "mobile crawler, so what ranks is an empty shell until the render queue catches up. "
            "Server-render or pre-render the page so the content is in the response itself."
        ),
        where=f"{MOBILE_RENDERED} and m.word_count >= 100 and {RAW_WORDS} < m.word_count * 0.3",
    ),
    PageRule(
        kind="mobile-hidden-content",
        severity="p1",
        issue_type="mobile",
        issue=(
            "A large share of this page's text is not visible at phone width — collapsed behind "
            "tabs, accordions or 'read more' controls, or hidden by a mobile layout. Google "
            "indexes the mobile page and gives hidden text less weight, so the copy that earns "
            "the ranking on desktop is discounted on the device that decides it. Show the content "
            "by default on mobile."
        ),
        where=(
            f"{MOBILE_RENDERED} and m.hidden_word_count >= 100"
            " and m.hidden_word_count >= m.word_count * 0.3"
        ),
    ),
    PageRule(
        kind="mobile-hidden-links",
        severity="p1",
        issue_type="mobile",
        issue=(
            "Internal links that are plain anchors on desktop are unreachable at phone width — "
            "typically a navigation that collapses into a menu whose entries are not in the DOM "
            "until tapped. Google's mobile crawler cannot follow what is not there, so the pages "
            "behind those links lose their internal links. Keep the anchors in the HTML at every "
            "width and hide them with CSS if you must."
        ),
        where=(
            f"{MOBILE_RENDERED} and m.hidden_internal_links >= 5"
            " and m.hidden_internal_links * 4 >= m.internal_links"
        ),
    ),
    PageRule(
        kind="mobile-viewport-overflow",
        severity="p2",
        issue_type="mobile",
        issue=(
            "The page is wider than a phone screen and scrolls sideways. Something — a table, an "
            "image, a fixed-width block — does not fit the viewport, so text and controls sit off "
            "screen and Google's mobile usability signal counts against the page. Constrain the "
            "offending element to the viewport width."
        ),
        where=f"{MOBILE_RENDERED} and m.viewport_overflow_px > 20",
    ),
    PageRule(
        kind="mobile-small-tap-targets",
        severity="p3",
        issue_type="mobile",
        issue=(
            "Several links or buttons on this page are smaller than 48 CSS pixels and sit closer "
            "than 8 pixels to a neighbour, so a thumb lands on the wrong one. It is a mobile "
            "usability signal and a real annoyance for visitors. Give tap targets room."
        ),
        where=f"{MOBILE_RENDERED} and m.small_tap_targets >= 5",
    ),
    PageRule(
        kind="mobile-title-differs",
        severity="p2",
        issue_type="mobile",
        issue=(
            "The title this page shows on a phone is not the one it shows on desktop. Google "
            "indexes the mobile version, so the desktop title you wrote is not the one that "
            "ranks or appears in results. Serve one title on every device."
        ),
        where=f"{BOTH_RENDERED} and r.title is distinct from m.title",
    ),
    PageRule(
        kind="mobile-canonical-differs",
        severity="p1",
        issue_type="mobile",
        issue=(
            "The canonical URL differs between the mobile and desktop renders of this page. "
            "Google reads the mobile one, so consolidation goes wherever the mobile template "
            "points, which is rarely what the desktop template intends. Emit the same canonical "
            "on both."
        ),
        where=f"{BOTH_RENDERED} and r.canonical is distinct from m.canonical",
    ),
    PageRule(
        kind="mobile-noindex-differs",
        severity="p0",
        issue_type="mobile",
        issue=(
            "The mobile and desktop renders of this page disagree on noindex. Google indexes "
            "from the mobile page, so a noindex only on mobile drops the page from the index "
            "while desktop looks fine, and a noindex only on desktop does nothing. Set the "
            "directive once, identically, on both."
        ),
        where=f"{BOTH_RENDERED} and {RENDERED_NOINDEX} is distinct from {MOBILE_NOINDEX}",
    ),
]


def render_site_rules(counts: RenderCounts) -> list[SiteRule]:
    js_share = counts.js_dependent / counts.rendered if counts.rendered else 0.0
    mobile_share = counts.mobile_differs / counts.both_rendered if counts.both_rendered else 0.0
    return [
        SiteRule(
            kind="js-dependent-site",
            severity="p0",
            issue_type="desktop",
            issue=(
                f"{counts.js_dependent} of the {counts.rendered} pages rendered so far show their "
                "content only after JavaScript runs. AI crawlers — GPTBot, ClaudeBot, "
                "PerplexityBot and the rest — never execute scripts, so to them this website is a "
                "set of empty shells, and Google indexes it late and partially. This is the single "
                "biggest visibility problem the site has. Server-render or pre-render the "
                "templates so the content is in the HTML response."
            ),
            holds=(
                counts.rendered >= MIN_RENDERED_FOR_SITE_VERDICT and js_share >= JS_DEPENDENT_SHARE
            ),
        ),
        SiteRule(
            kind="mobile-differs-from-desktop",
            severity="p1",
            issue_type="mobile",
            issue=(
                f"{counts.mobile_differs} of the {counts.both_rendered} pages rendered on both "
                "devices show a different title, canonical or indexing directive on a phone. "
                "Google indexes the mobile version, so the site it ranks is not the site you see "
                "on desktop: titles you wrote are replaced, canonicals point elsewhere, pages drop "
                "out. This is usually a separate mobile template or a user-agent switch. Serve "
                "the same head on every device."
            ),
            holds=(
                counts.both_rendered >= MIN_RENDERED_FOR_SITE_VERDICT
                and mobile_share >= MOBILE_DIFFERS_SHARE
            ),
        ),
    ]


def measured(alias: str) -> str:
    return f"{alias}.rendered_at is not null and {alias}.render_error is null and site_pages.status = 200 and {alias}.settle_reason is not null"


SOFT_404_RE = (
    r"\m(404|not found|page (doesn''t|does not|cannot be) (exist|found)|no longer available|oops)\M"
)

POSITIVE_ROBOTS_RE = r"\m(index|follow|all)\M"

NEGATIVE_ROBOTS_RE = r"\m(noindex|nofollow|none)\M"

NOFOLLOW_RE = r"\m(nofollow|none)\M"

ORIGIN_ROOT_RE = r"^https?://[^/]+/?$"

HTTP_RE = r"^https?://"

VIEWPORT_MISSING = "(m.viewport_meta is null or m.viewport_meta not ilike '%width=%')"

VIEWPORT_RESTRICTIVE = (
    r"(m.viewport_meta ~* 'user-scalable\s*=\s*(no|0)\M'"
    r" or coalesce(nullif(substring(m.viewport_meta from 'maximum-scale\s*=\s*([0-9.]+)'), '')::real, 1) < 1"
    r" or coalesce(nullif(substring(m.viewport_meta from 'initial-scale\s*=\s*([0-9.]+)'), '')::real, 1) < 1)"
)


def norm(expr: str) -> str:
    return f"regexp_replace(lower(trim({expr})), '\\s+', ' ', 'g')"


def lost_links(alias: str) -> str:
    return (
        "(select count(*) from jsonb_array_elements(site_pages.out_links) l"
        f" where not (l->>'url' = any({alias}.internal_link_urls)))"
    )


def _both(kind: str, severity: str, issue: str, where) -> list[PageRule]:
    return [
        PageRule(
            kind=kind,
            severity=severity,
            issue_type="desktop",
            issue=issue,
            where=f"{measured('r')} and ({where('r')})",
        ),
        PageRule(
            kind=f"mobile-{kind}",
            severity=severity,
            issue_type="mobile",
            issue=f"Measured on the mobile render. {issue}",
            where=f"{measured('m')} and ({where('m')})",
        ),
    ]


def _mobile(kind: str, severity: str, issue: str, where: str, guard: str | None = None) -> PageRule:
    return PageRule(
        kind=kind,
        severity=severity,
        issue_type="mobile",
        issue=issue,
        where=f"{guard or measured('m')} and ({where})",
    )


BOTH_MEASURED = f"{measured('r')} and {measured('m')}"

V2_PAGE_RULES: list[PageRule] = [
    *_both(
        "soft-404-after-render",
        "p0",
        "The server answers 200, but the rendered page says the content is missing — the title or "
        "heading reads like a not-found page and there is almost nothing else on it. Google calls "
        "this a soft 404: the URL stays in the index as an empty page and wastes crawl budget. "
        "Return a real 404 or 410, or redirect to the page that replaced it; a client-side "
        "noindex is the fallback Google documents for single-page apps.",
        lambda a: (
            f"{a}.status = 200 and {a}.soft404_signal and ({a}.visible_word_count < 150 or {a}.internal_links = 0)"
            f" and coalesce({a}.robots_directives, '') not ilike '%noindex%'"
            f" and coalesce(site_pages.title, '') !~* '{SOFT_404_RE}'"
            f" and not exists (select 1 from unnest(site_pages.h1) h where h ~* '{SOFT_404_RE}')"
        ),
    ),
    *_both(
        "rendered-body-empty",
        "p0",
        "After JavaScript has run and the network has gone quiet, this page still shows almost no "
        "text and no heading. Whatever was meant to appear never did — a script failed, a data "
        "call was refused, or the shell waits for something a crawler never does. Google indexes "
        "what it sees, and it sees nothing. Check the recorded exceptions and failed requests.",
        lambda a: f"{a}.status = 200 and {a}.visible_word_count < 30 and {a}.h1 = '{{}}'::text[]",
    ),
    *_both(
        "render-exception-with-thin-content",
        "p0",
        "An uncaught JavaScript exception fired while this page rendered, and the page ended up "
        "with less text than the server sent or fewer than a hundred words. The script that "
        "builds the page died before it finished, so the indexed copy is the broken state. The "
        "first exceptions are recorded with the render; fix them first.",
        lambda a: (
            f"{a}.exception_count >= 1 and ({a}.word_count < coalesce(site_pages.word_count, 0) or {a}.word_count < 100)"
        ),
    ),
    *_both(
        "content-lost-after-render",
        "p1",
        "This page has markedly less text after JavaScript runs than the raw HTML carried. A "
        "script is removing or replacing server content — a hydration mismatch, a consent wall, "
        "or a client-side template that renders less than the server did. Google indexes the "
        "rendered result, so the words the server sent are not the words that rank.",
        lambda a: (
            f"coalesce(site_pages.word_count, 0) - {a}.word_count >= 100 and {a}.word_count < coalesce(site_pages.word_count, 0) * 0.7"
        ),
    ),
    *_both(
        "links-lost-after-render",
        "p1",
        "Internal links present in the raw HTML are gone from the rendered page. JavaScript "
        "rewrote or removed them — a menu rebuilt client-side, a router that swaps anchors for "
        "handlers. Google follows the rendered links, so the pages behind the missing ones lose "
        "the path and the equity the server-side markup promised.",
        lambda a: (
            f"jsonb_array_length(site_pages.out_links) > 0 and ({lost_links(a)} >= 5 or {lost_links(a)} >= jsonb_array_length(site_pages.out_links) * 0.2)"
        ),
    ),
    *_both(
        "uncrawlable-anchors-after-render",
        "p1",
        "The rendered page navigates with elements Google cannot follow: anchors without an href, "
        "javascript: links, elements with a click handler that changes the location, or "
        "role=link on a div. Google only crawls <a href> with a real URL. Give every "
        "navigation an href, and let scripts intercept the click if they must.",
        lambda a: f"{a}.uncrawlable_anchors >= 3 or {a}.uncrawlable_nav_anchors >= 1",
    ),
    *_both(
        "old-ajax-crawling-scheme",
        "p1",
        "This page still uses the retired AJAX crawling scheme — hashbang (#!) URLs or a "
        "meta name=fragment tag. Google stopped supporting it in 2018; those URLs are treated "
        "as fragments of one page and never crawled on their own. Move to real paths served "
        "with the History API.",
        lambda a: f"{a}.hashbang_links >= 1 or {a}.meta_fragment",
    ),
    *_both(
        "dangling-fragment-links",
        "p2",
        "Many links on this page point at fragments of itself that match no element on the "
        "rendered page. They are either single-page-app routes disguised as anchors, which "
        "Google ignores, or leftovers from removed sections. Either way they lead nowhere a "
        "crawler can go.",
        lambda a: f"{a}.dangling_fragment_links >= 5",
    ),
    *_both(
        "url-changed-by-history-api",
        "p1",
        "JavaScript changed the address bar with the History API without navigating: the page "
        "ended at a different URL from the one requested, with no redirect the crawler could "
        "see. Google indexes the requested URL with whatever content it rendered, and the "
        "rewritten URL never gets a signal. Redirect server-side or leave the URL alone.",
        lambda a: (
            f"{a}.final_url is not null and {a}.final_url <> site_pages.url and {a}.main_frame_navigations = 0"
        ),
    ),
    *_both(
        "interaction-gated-content",
        "p2",
        "The rendered page offers a 'load more' control and no pagination links or rel=next. "
        "Google does not click, scroll or tap, so whatever sits behind that button is never "
        "crawled from this page. Add real paginated URLs alongside the button.",
        lambda a: f"{a}.load_more_control and not {a}.pagination_links",
    ),
    *_both(
        "images-without-src-after-render",
        "p1",
        "Images on the rendered page have no usable src — a placeholder, or a data-src the "
        "lazy-loader never swapped in because nothing scrolled. Google sees the placeholder, so "
        "these images are not indexed and their alt text counts for nothing. Use native "
        "loading=lazy with a real src, or make the loader fill src without a scroll event.",
        lambda a: (
            f"{a}.images_without_src_above_fold >= 1 or ({a}.images_without_src > 0 and {a}.images_without_src * 4 >= jsonb_array_length({a}.images) + {a}.images_without_src)"
        ),
    ),
    *_both(
        "shadow-dom-content-unslotted",
        "p2",
        "A large part of this page's text lives inside shadow DOM that is not slotted into the "
        "light DOM. Google flattens shadow trees when it renders, but tools that read "
        "outerHTML — and any crawler that does not — miss it, and our own word count did. "
        "Slot the content or render it in the light DOM.",
        lambda a: f"{a}.shadow_dom_words >= 200",
    ),
    *_both(
        "service-worker-registered",
        "p3",
        "The page registers a service worker. Googlebot does not run service workers and clears "
        "storage between fetches, so anything the worker serves from cache or synthesises is "
        "invisible to it. Harmless as long as the page works without it; recorded so the "
        "difference is known.",
        lambda a: f"{a}.service_worker",
    ),
    *_both(
        "failed-data-request",
        "p1",
        "A same-site data request the page makes while rendering — an XHR or fetch to your own "
        "API — answered with an error or never came back. The content that call was meant to "
        "fill is missing from the indexed page. The failing URLs are recorded with the render.",
        lambda a: f"{a}.failed_data_requests >= 1",
    ),
    *_both(
        "failed-first-party-script",
        "p1",
        "One of the site's own scripts failed to load while rendering. Everything that script "
        "builds is absent from the page Google indexes, and a bundle that 404s usually means a "
        "deploy left stale filenames in the HTML. The URLs are recorded with the render.",
        lambda a: f"{a}.failed_scripts >= 1",
    ),
    *_both(
        "cors-blocked-request",
        "p1",
        "The browser refused a cross-origin request this page depends on because the responding "
        "server sends no Access-Control-Allow-Origin header. The data never arrives, in Google's "
        "renderer as much as in a browser. Fix the CORS headers on the API host.",
        lambda a: f"{a}.cors_errors >= 1",
    ),
    *_both(
        "network-never-idle",
        "p2",
        "The page kept making requests until the render timed out; several were still pending "
        "when the snapshot was taken. Polling, long-lived connections or an endless chain of "
        "fetches make Google's renderer give up at an arbitrary point, so what gets indexed is "
        "whatever had arrived by then. The pending URLs are recorded.",
        lambda a: f"{a}.settle_reason = 'timeout' and {a}.pending_requests >= 3",
    ),
    *_both(
        "websocket-transport-used",
        "p2",
        "The page opens a WebSocket while rendering. Google's renderer does not keep sockets "
        "open, so content delivered that way is never indexed. Serve the initial content over "
        "HTTP and use the socket only for updates.",
        lambda a: f"{a}.websocket_used",
    ),
    *_both(
        "mixed-content-active",
        "p1",
        "This HTTPS page loads a script, stylesheet, data call or frame over plain HTTP. Browsers "
        "block active mixed content outright, so those resources never run — in Google's "
        "renderer too. Serve them over HTTPS.",
        lambda a: f"{a}.mixed_content_active >= 1",
    ),
    *_both(
        "mixed-content-passive",
        "p3",
        "This HTTPS page loads images, media or fonts over plain HTTP. Browsers show a warning "
        "and may block them; some of the page's images are not indexed as a result. Serve them "
        "over HTTPS.",
        lambda a: f"{a}.mixed_content_passive >= 1",
    ),
    *_both(
        "document-over-2mb",
        "p0",
        "The HTML response for this page is larger than 2 MB. Google stops reading a resource at "
        "2 MB and indexes only what it read, so the end of this document — often the content "
        "and the footer links — does not exist as far as search is concerned. Move inline data "
        "and scripts out of the HTML.",
        lambda a: f"{a}.document_bytes > 2097152",
    ),
    *_both(
        "resource-over-2mb",
        "p1",
        "A script or stylesheet this page loads is larger than 2 MB. Google truncates any single "
        "resource at 2 MB, so the bundle runs incomplete and whatever it renders past that point "
        "is missing. Split the bundle. The URL is recorded with the render.",
        lambda a: f"{a}.largest_resource_bytes > 2097152",
    ),
    *_both(
        "rendered-html-over-2mb",
        "p1",
        "The DOM after rendering serialises to more than 2 MB. Google keeps the rendered HTML "
        "within the same limit it applies to fetched resources, so the tail of this page is cut "
        "off in the index. Trim the DOM: paginate long lists and drop hidden duplicates.",
        lambda a: f"{a}.html_bytes > 2097152",
    ),
    _mobile(
        "mobile-status-differs-from-desktop",
        "p0",
        "The same URL answers with a different HTTP status on a phone than on desktop. Google "
        "crawls with the smartphone agent, so the mobile status is the one that counts: a "
        "mobile error takes the page out of the index while desktop looks fine. Serve the same "
        "response to both.",
        "r.status is distinct from m.status",
        guard=BOTH_MEASURED,
    ),
    _mobile(
        "mobile-final-url-differs-from-desktop",
        "p1",
        "On a phone this page ends at a different URL than on desktop — one device redirects and "
        "the other does not, or they redirect to different places. Google indexes the mobile "
        "destination. Make both devices land on the same canonical URL.",
        "r.final_url is distinct from m.final_url",
        guard=BOTH_MEASURED,
    ),
    _mobile(
        "viewport-meta-missing",
        "p1",
        "The rendered page has no usable viewport meta tag — none at all, or one without a "
        "width. Phones then lay the page out at desktop width and shrink it, which Google's "
        "mobile usability checks flag and which makes every tap target tiny. Add "
        '<meta name=viewport content="width=device-width, initial-scale=1">.',
        VIEWPORT_MISSING,
    ),
    _mobile(
        "viewport-meta-restrictive",
        "p2",
        "The viewport tag disables zoom or scales the page below 1. Users who need to enlarge "
        "text cannot, which is an accessibility failure Lighthouse reports, and initial-scale "
        "under 1 makes text illegible on load. Remove user-scalable=no and keep the scales at 1.",
        VIEWPORT_RESTRICTIVE,
    ),
    _mobile(
        "mobile-intrusive-overlay",
        "p1",
        "On a phone an overlay covers at least half the viewport as soon as the page renders — "
        "a consent wall, an app banner, a newsletter modal. Google's intrusive-interstitial "
        "policy demotes pages that hide their content this way on mobile, and the crawler "
        "cannot dismiss it. Show it smaller, later, or not at all on first load.",
        "m.overlay_coverage >= 0.5",
    ),
    PageRule(
        kind="intrusive-overlay",
        severity="p2",
        issue_type="desktop",
        issue=(
            "An overlay covers at least half the desktop viewport as soon as the page renders. "
            "Google's interstitial guidance is written for mobile, but a crawler that cannot "
            "dismiss it still evaluates the page with the overlay in front of the content. Keep "
            "first-load overlays small."
        ),
        where=f"{measured('r')} and r.overlay_coverage >= 0.5",
    ),
    _mobile(
        "mobile-illegible-text",
        "p2",
        "Two fifths or more of the visible text on the phone render is set below 12 px. That is "
        "the threshold Lighthouse's legibility audit used and the size at which readers pinch "
        "to zoom. Raise the base font size for small screens.",
        "m.small_text_ratio >= 0.4 and m.text_chars >= 200",
    ),
    _mobile(
        "mobile-word-count-drop",
        "p1",
        "The phone render shows noticeably fewer visible words than the desktop render. Google "
        "indexes the mobile version, so anything shown only on desktop does not rank. Put the "
        "same content on both; collapsing it behind a tap is fine, dropping it is not.",
        "m.visible_word_count < r.visible_word_count * 0.8 and r.visible_word_count - m.visible_word_count >= 100",
        guard=BOTH_MEASURED,
    ),
    _mobile(
        "mobile-description-differs-from-desktop",
        "p1",
        "The meta description differs between the phone and desktop renders. Google reads the "
        "mobile one, so the snippet you see on desktop is not the one searchers get. Serve the "
        "same description on both.",
        "r.meta_description is distinct from m.meta_description",
        guard=BOTH_MEASURED,
    ),
    _mobile(
        "mobile-h1-differs-from-desktop",
        "p2",
        "The H1 differs between the phone and desktop renders. Google indexes the mobile heading; "
        "a different or missing one on the phone changes what the page is understood to be "
        "about. Use one heading on both.",
        "r.h1 is distinct from m.h1",
        guard=BOTH_MEASURED,
    ),
    _mobile(
        "mobile-schema-differs-from-desktop",
        "p1",
        "The structured data on the phone render is not the structured data on desktop — types "
        "are missing or blocks differ. Google's mobile-first guidance asks for the same "
        "structured data on both; rich results are earned from the mobile copy.",
        "((select array_agg(x order by x) from unnest(r.schema_types) x) is distinct from"
        " (select array_agg(x order by x) from unnest(m.schema_types) x)"
        " or exists (select 1 from unnest(r.schema_hashes) h where not (h = any(m.schema_hashes))))",
        guard=BOTH_MEASURED,
    ),
    _mobile(
        "mobile-image-alt-differs",
        "p3",
        "The same image carries different alt text on the phone render than on desktop, or has "
        "alt text only on desktop. Google indexes images from the mobile page. Keep alt text "
        "identical across devices.",
        "exists (select 1 from jsonb_array_elements(r.images) a join jsonb_array_elements(m.images) b"
        " on a->>'src' = b->>'src' where (a->'alt') is distinct from (b->'alt'))",
        guard=BOTH_MEASURED,
    ),
    *_both(
        "schema-changed-by-js",
        "p1",
        "Structured data the server sent is missing from the rendered page — JavaScript removed "
        "or replaced a JSON-LD block. Google evaluates the rendered structured data, so the "
        "types you can see in the source are not the ones that earn rich results. Leave "
        "server-side JSON-LD alone.",
        lambda a: (
            f"site_pages.schema_types <> '{{}}'::text[] and exists (select 1 from unnest(site_pages.schema_types) t where not (t = any({a}.schema_types)))"
        ),
    ),
    *_both(
        "schema-duplicated-after-render",
        "p2",
        "The rendered page carries the same structured-data node more than once — the server "
        "emitted it and a script emitted it again. Duplicate nodes confuse rich-result "
        "eligibility and make the Search Console report noisy. Emit each node once.",
        lambda a: (
            f"exists (select 1 from unnest({a}.schema_hashes) h group by h having count(*) > 1)"
        ),
    ),
    *_both(
        "schema-invalid-after-render",
        "p1",
        "A JSON-LD block on the rendered page is not valid JSON. Google skips a block it cannot "
        "parse, so whatever it declared is lost. A trailing comma or an unescaped quote is the "
        "usual cause; the offending block is recorded with the render.",
        lambda a: f"{a}.schema_invalid_blocks >= 1",
    ),
    *_both(
        "canonical-conflict-after-render",
        "p0",
        "After rendering, this page declares two or more different canonical URLs. Google "
        "ignores all of them when they conflict and chooses on its own, which can be the wrong "
        "page. One canonical, set once, in the server response.",
        lambda a: f"(select count(distinct c) from unnest({a}.canonical_hrefs) c) >= 2",
    ),
    *_both(
        "canonical-repeated-after-render",
        "p2",
        "The rendered page carries the same canonical link more than once — the server emitted "
        "it and a script added it again. Harmless today, but the moment either copy changes it "
        "becomes a conflict. Emit it once.",
        lambda a: (
            f"{a}.canonical_count >= 2 and (select count(distinct c) from unnest({a}.canonical_hrefs) c) = 1"
        ),
    ),
    *_both(
        "canonical-invalid-after-render",
        "p1",
        "The canonical the rendered page ends up with is not an absolute HTTP URL, or points at "
        "the site root from a page that is not the home page — the kind of value a client-side "
        "router writes before it knows the route. Google ignores an invalid canonical and may "
        "honour a wrong one. Set it server-side.",
        lambda a: (
            f"{a}.canonical is not null and ({a}.canonical !~* '{HTTP_RE}' or ({a}.canonical ~ '{ORIGIN_ROOT_RE}' and site_pages.url !~ '{ORIGIN_ROOT_RE}'))"
            f" and not (site_pages.canonical is not null and (site_pages.canonical !~* '{HTTP_RE}' or (site_pages.canonical ~ '{ORIGIN_ROOT_RE}' and site_pages.url !~ '{ORIGIN_ROOT_RE}')))"
        ),
    ),
    *_both(
        "robots-directives-conflict-after-render",
        "p1",
        "The rendered page carries more than one robots meta tag, or one that says both index "
        "and noindex. Google resolves conflicts by taking the most restrictive directive, so the "
        "page is treated as noindex or nofollow whichever tag you meant. Emit one tag.",
        lambda a: (
            f"coalesce(array_length({a}.robots_meta_contents, 1), 0) >= 2 or exists (select 1 from unnest({a}.robots_meta_contents) c where c ~* '{POSITIVE_ROBOTS_RE}' and c ~* '{NEGATIVE_ROBOTS_RE}')"
        ),
    ),
    *_both(
        "nofollow-changed-by-js",
        "p1",
        "JavaScript changes whether this page's links may be followed: the raw HTML and the "
        "rendered page disagree on nofollow. Google reads the directive it finds after "
        "rendering, so links you meant to pass equity may not, or the reverse. Set it once, "
        "server-side.",
        lambda a: (
            f"(coalesce({a}.robots_directives, '') ~* '{NOFOLLOW_RE}') is distinct from (coalesce(site_pages.robots_directives, '') ~* '{NOFOLLOW_RE}')"
        ),
    ),
    *_both(
        "title-modified-by-js",
        "p1",
        "The server sends one title and JavaScript replaces it with another. Google indexes the "
        "rendered title, so what appears in search is not what the template author wrote, and "
        "crawlers that do not render see a third version. Decide the title server-side.",
        lambda a: (
            f"site_pages.title is not null and {a}.title is not null and {norm('site_pages.title')} <> {norm(f'{a}.title')}"
        ),
    ),
    *_both(
        "meta-description-modified-by-js",
        "p2",
        "JavaScript rewrites the meta description after load. The snippet Google shows comes from "
        "the rendered one, so the description in the source is not the one searchers read. Set "
        "it server-side.",
        lambda a: (
            f"site_pages.meta_description is not null and {a}.meta_description is not null and {norm('site_pages.meta_description')} <> {norm(f'{a}.meta_description')}"
        ),
    ),
    *_both(
        "h1-modified-by-js",
        "p2",
        "The H1 the server sends is replaced by JavaScript. Google reads the rendered heading; a "
        "different one changes what the page is understood to be about. Render the heading "
        "server-side and leave it.",
        lambda a: (
            f"site_pages.h1 <> '{{}}'::text[] and {a}.h1 <> '{{}}'::text[] and site_pages.h1 <> {a}.h1"
        ),
    ),
    *_both(
        "meta-description-only-after-js",
        "p2",
        "The meta description exists only after JavaScript runs. Crawlers that do not render "
        "index the page without one and Google writes its own snippet until its render queue "
        "catches up. Put it in the server response.",
        lambda a: f"site_pages.meta_description is null and {a}.meta_description is not null",
    ),
    *_both(
        "title-duplicated-after-render",
        "p2",
        "The rendered page has more than one title element — the server's and one a script "
        "appended. Google uses the first, but which is first depends on where the script wrote "
        "it. Keep one.",
        lambda a: f"{a}.title_count >= 2",
    ),
    *_both(
        "description-duplicated-after-render",
        "p2",
        "The rendered page has more than one meta description. Google picks one and it is not "
        "always the one you meant. Keep one.",
        lambda a: f"{a}.description_count >= 2",
    ),
    *_both(
        "hreflang-changed-by-js",
        "p2",
        "The hreflang links after rendering are not the ones the server sent — JavaScript added, "
        "removed or rewrote them. Google reads hreflang from the rendered head; a set that "
        "differs from the raw HTML is a set that differs from what other crawlers and the "
        "sitemap declare. Emit hreflang server-side only.",
        lambda a: (
            f"(site_pages.hreflang <> '{{}}'::jsonb or {a}.hreflang <> '{{}}'::jsonb) and {a}.hreflang is distinct from site_pages.hreflang"
        ),
    ),
    *_both(
        "hreflang-invalid-after-render",
        "p2",
        "A rendered hreflang link has a relative href or a language code that is not a valid "
        "ISO 639 tag. Google drops invalid entries and the whole cluster stops resolving. Use "
        "absolute URLs and two- or three-letter language codes, with x-default for the fallback.",
        lambda a: f"{a}.hreflang_invalid >= 1",
    ),
    *_both(
        "unrendered-template-tokens",
        "p1",
        "The rendered title, description or heading still contains template placeholders like "
        "{{name}}. The framework never filled them in, so that is the text Google indexes and "
        "shows. Find the binding that did not resolve.",
        lambda a: f"{a}.template_tokens_head >= 1",
    ),
    *_both(
        "unrendered-template-tokens-body",
        "p2",
        "Visible body text on the rendered page contains several unfilled template placeholders. "
        "Readers and crawlers both see the raw tokens. Find the bindings that did not resolve.",
        lambda a: f"{a}.template_tokens_body >= 3",
    ),
    *_both(
        "js-injected-images-missing-alt",
        "p2",
        "Images that JavaScript adds to the page have no alt attribute. The static check only "
        "sees the server's images, so these slip through; Google indexes rendered images and "
        "has no text for these. Add alt to the injected images.",
        lambda a: (
            f"exists (select 1 from jsonb_array_elements({a}.images) i where (i->'alt') is null and not exists (select 1 from jsonb_array_elements(site_pages.images) ri where ri->>'src' = i->>'src'))"
        ),
    ),
    *_both(
        "external-links-injected-by-js",
        "p3",
        "JavaScript adds links to several external hosts that are not in the raw HTML — widgets, "
        "embeds, tracking wrappers. Google follows rendered links, so these carry the page's "
        "endorsement whether you meant it or not. Review them and add rel=nofollow or "
        "rel=sponsored where appropriate.",
        lambda a: (
            f"(select count(*) from unnest({a}.external_link_hosts) h where not exists (select 1 from jsonb_array_elements(site_pages.external_links) l where substring(l->>'url' from '^https?://([^/]+)') = h)) >= 5"
        ),
    ),
    *_both(
        "plugin-content-after-render",
        "p3",
        "The rendered page embeds Flash, Silverlight or Java content. No modern browser runs "
        "them and Google indexes nothing inside. Replace the plugin content with HTML.",
        lambda a: f"{a}.plugin_content >= 1",
    ),
]

RAW_COUNTERPART_RULES: list[PageRule] = [
    *_both(
        "viewport-meta-changed-by-js",
        "p2",
        (
            "The viewport meta tag the server sends is not the one the page ends up with after "
            "JavaScript runs — a script rewrites the width or adds a scaling restriction. Google "
            "reads the tag from the rendered page for mobile-first indexing, so the served tag "
            "and the rendered one disagree about how the page should be laid out on a phone. "
            "Emit the final viewport tag from the server and stop rewriting it."
        ),
        lambda a: (
            f"site_pages.viewport_meta is not null and {a}.viewport_meta is not null"
            f" and lower(regexp_replace(site_pages.viewport_meta, '\\s', '', 'g'))"
            f" <> lower(regexp_replace({a}.viewport_meta, '\\s', '', 'g'))"
        ),
    ),
    *_both(
        "data-nosnippet-changed-by-js",
        "p2",
        (
            "JavaScript changes which parts of the page carry data-nosnippet. Google honours the "
            "attribute as it appears in the rendered page, so text the server marked as off-limits "
            "for snippets can end up quoted, or text meant for snippets can be hidden, depending "
            "on whether the render succeeded. Set the attribute in the server response and leave "
            "it alone."
        ),
        lambda a: f"{a}.nosnippet_count <> site_pages.nosnippet_count",
    ),
    *_both(
        "og-tags-only-after-js",
        "p2",
        (
            "Open Graph and Twitter card tags exist only after JavaScript runs; the raw HTML has "
            "none. Social platforms and most link-preview fetchers do not execute scripts, so "
            "shares of this page get no title, image or description. Put the tags in the server "
            "response."
        ),
        lambda a: f"site_pages.social_meta_count = 0 and {a}.social_meta_count > 0",
    ),
]

RENDER_PAGE_RULES.extend(V2_PAGE_RULES)
RENDER_PAGE_RULES.extend(RAW_COUNTERPART_RULES)
