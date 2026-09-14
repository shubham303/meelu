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
        where=f"{RENDERED} and r.final_url is not null and r.final_url <> site_pages.url",
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
