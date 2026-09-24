from src.technical_seo.rules.page import INDEXABLE
from src.technical_seo.rules.types import PageRule

FACET_TRAP_MIN_INLINKS = 10

LINK_PAGE_RULES: list[PageRule] = [
    PageRule(
        kind="facet-trap",
        severity="p1",
        issue=(
            "A query-string URL that the site links to heavily, yet it is not the canonical version "
            "of anything — it is noindexed, canonicalised elsewhere, or a redirect. Filter, sort and "
            "pagination parameters like this soak up crawl budget and internal link equity for pages "
            "that will never rank. Link to the canonical page instead, or drop the parameter links "
            "from templates."
        ),
        where=f"""position('?' in site_pages.url) > 0
      and site_pages.inlinks >= {FACET_TRAP_MIN_INLINKS}
      and exists (
        select 1 from site_page_links e
         where e.site_id = site_pages.site_id and e.dst_page_id = site_pages.id
           and not e.dst_canonical
      )""",
    ),
    PageRule(
        kind="internal-nofollow",
        severity="p2",
        issue=(
            "This page marks some of its links to other pages on the same site as nofollow. "
            "Nofollow on an internal link throws away the equity the page would pass and tells "
            "Google the site does not vouch for its own page. Remove the attribute; if the target "
            "should not be indexed, noindex it there instead."
        ),
        where="""site_pages.status = 200
      and exists (
        select 1 from site_page_links e
         where e.site_id = site_pages.site_id and e.src_page_id = site_pages.id
           and not e.followable
      )""",
    ),
    PageRule(
        kind="missing-breadcrumbs",
        severity="p3",
        issue=(
            "Two or more clicks from the home page, with no breadcrumb trail and no BreadcrumbList "
            "markup. Breadcrumbs give every deep page a link back to its section, show the site's "
            "hierarchy in search results in place of the bare URL, and are one of the cheapest "
            "site-wide wins: a breadcrumb component in the template plus BreadcrumbList schema."
        ),
        where=f"""{INDEXABLE} and site_pages.depth >= 2
      and not exists (
        select 1 from site_page_links e
         where e.src_page_id = site_pages.id and e.region = 'breadcrumb'
      )
      and not exists (
        select 1 from unnest(site_pages.schema_types) t where lower(t) = 'breadcrumblist'
      )""",
    ),
    PageRule(
        kind="nav-gap",
        severity="p2",
        issue=(
            "Every link this page gets from the level above it sits in a template region — the "
            "navigation, sidebar or footer — and none in the body of a page. Template links are "
            "shared by every page and pass little equity; a page that is never mentioned in "
            "running text reads as unimportant. Link to it from the body of its hub page, with a "
            "descriptive anchor."
        ),
        where="""site_pages.status = 200 and site_pages.depth >= 2
      and exists (
        select 1 from site_page_links e join site_pages s on s.id = e.src_page_id
         where e.site_id = site_pages.site_id and e.dst_page_id = site_pages.id
           and s.depth = site_pages.depth - 1
      )
      and not exists (
        select 1 from site_page_links e join site_pages s on s.id = e.src_page_id
         where e.site_id = site_pages.site_id and e.dst_page_id = site_pages.id
           and s.depth = site_pages.depth - 1 and e.region = 'body'
      )""",
    ),
]
