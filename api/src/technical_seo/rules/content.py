from src.technical_seo.rules.types import PageRule

OPTIMISABLE = """site_pages.status = 200 and not site_pages.shallow and not site_pages.blocked_by_robots
  and coalesce(site_pages.robots_directives, '') not ilike '%noindex%'
  and coalesce(site_pages.x_robots_tag, '') not ilike '%noindex%'
  and site_pages.kind in ('article', 'product', 'pricing', 'docs')"""

CONTENT_PAGE_RULES: list[PageRule] = [
    PageRule(
        kind="stale-content",
        severity="p2",
        issue=(
            "Nothing in the text of this page has changed in over a year. That is measured rather than "
            "declared — the crawl keeps a fingerprint of what each page says and compares it visit to "
            "visit, so this is the date the content really last moved, not the date the page claims. "
            "Freshness weighs unusually heavily in AI answers: the large majority of pages cited for "
            "commercial and evaluation questions had genuinely been updated within the last year. "
            "Prices, statistics, versions and product claims are exactly what gets extracted, so a page "
            "left this long is quietly being quoted with stale specifics, or passed over for something "
            "newer. Revisit what it says rather than reissuing it."
        ),
        where=f"""{OPTIMISABLE} and site_pages.content_changed_at is not null
      and site_pages.content_changed_at < now() - interval '12 months'""",
    ),
    PageRule(
        kind="date-inflation",
        severity="p2",
        issue=(
            "This page says it was modified more recently than its text actually changed. The declared "
            "date has moved forward while the content behind it has not — the crawl compares the page's "
            "own words between visits, so the gap is measured, not inferred. It is usually a CMS "
            "stamping a new date on every deploy rather than anyone deciding to say the page is fresh. "
            "Search engines discount a date that moves without the page moving with it, and it costs the "
            "one signal a reader has for judging whether what they are reading is current. Either update "
            "the content the date is claiming, or let the date reflect when it last really changed."
        ),
        where="""site_pages.status = 200 and not site_pages.shallow
      and site_pages.content_changed_at is not null and site_pages.modified_at is not null
      and site_pages.last_crawled_at is not null
      and site_pages.content_changed_at < site_pages.last_crawled_at
      and site_pages.modified_at > site_pages.content_changed_at + interval '7 days'""",
    ),
]
