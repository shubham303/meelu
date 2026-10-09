from src.technical_seo.rules.types import PageRule

CRAWLED = "site_pages.status = 200 and not site_pages.shallow"

WANTED = """site_pages.status = 200 and not site_pages.blocked_by_robots
  and coalesce(site_pages.robots_directives, '') not ilike '%noindex%'
  and coalesce(site_pages.x_robots_tag, '') not ilike '%noindex%'"""

INDEXABLE = f"{WANTED} and not site_pages.shallow"

HAS_HREFLANG = "site_pages.hreflang <> '{}'::jsonb"

HREFLANG_LEAD = """site_pages.url <= coalesce(
  (select min(v.value) from jsonb_each_text(site_pages.hreflang) v where v.key <> 'x-default'),
  site_pages.url)"""

CLUSTER_MEMBER = """site_pages m
   where m.site_id = site_pages.site_id
     and (m.url = site_pages.url
       or m.url in (select v.value from jsonb_each_text(site_pages.hreflang) v where v.key <> 'x-default'))"""

PATH = "regexp_replace(site_pages.url, '^https?://[^/]+', '')"

IS_HOME = f"{PATH} in ('', '/')"

SLUG = f"split_part({PATH}, '?', 1)"

STOP_WORD_RE = (
    "(^|[/-])(a|an|and|the|for|to|of|in|on|at|is|it|by|with|from|that|are|was|be|or)([/-]|$)"
)


def schema_node(types: list[str], missing: str) -> str:
    listed = ", ".join(f"'{t}'" for t in types)
    return f"""exists (
      select 1 from jsonb_array_elements(site_pages.schema_nodes) n
       where lower(n->>'type') in ({listed})
         and (n->>'keys')::int > 0
         and ({missing})
    )"""


def without(*props: str) -> str:
    listed = ",".join(f'"{prop}"' for prop in props)
    return f"not (n->'props' @> '[{listed}]'::jsonb)"


def home_links_none(pattern: str) -> str:
    return f"""site_pages.status = 200 and {IS_HOME}
      and not exists (
        select 1 from site_page_links e
         where e.src_page_id = site_pages.id and e.dst_url ~* '{pattern}'
      )"""


def home_external_links_none(pattern: str) -> str:
    return f"""site_pages.status = 200 and {IS_HOME}
      and not exists (
        select 1 from jsonb_array_elements(site_pages.external_links) x
         where x->>'url' ~* '{pattern}'
      )"""


BODY_EXTERNAL_LINKS = """(select coalesce(sum((x->>'count')::int), 0)
  from jsonb_array_elements(site_pages.external_links) x where x->>'region' = 'body')"""

CONTACT_LINK = r"(^|/)contact(-us)?(/|\.|\?|$)"

TERMS_LINK = (
    r"(^|/)(terms|tos|terms-(of-|and-)?(service|use|conditions)|conditions|legal)(/|\.|\?|$)"
)

SOCIAL_LINK = (
    r"^https?://([a-z0-9-]+\.)?(facebook|instagram|linkedin|twitter|x|youtube|tiktok|pinterest|"
    r"threads|github)\.com/[^/?#]|^https?://(www\.)?bsky\.app/[^/?#]"
)


PAGE_RULES: list[PageRule] = [
    PageRule(
        kind="robots-blocked-but-linked",
        severity="p0",
        issue=(
            "Disallowed in robots.txt for Googlebot, yet the site still points at it — the sitemap "
            "lists it or other pages link to it. Google will not crawl the page, so the sitemap entry "
            "and every one of those links leads nowhere. Either drop the Disallow rule or stop "
            "advertising the URL; doing both is the mistake."
        ),
        where="site_pages.blocked_by_robots and (site_pages.in_sitemap or site_pages.inlinks > 0)",
    ),
    PageRule(
        kind="server-error",
        severity="p0",
        issue=(
            "The server returned a 5xx error for this page. Unlike a 404 this is not an answer, it is "
            "a failure — Google retries for a while and then drops the page. Check the server logs "
            "for this URL before assuming the crawl was at fault."
        ),
        where="site_pages.status >= 500",
    ),
    PageRule(
        kind="noindex-but-linked",
        severity="p1",
        issue=(
            "Marked noindex, yet the site still points at it — the sitemap lists it or other pages "
            "link to it. The page will be dropped from search results while the site keeps asking for "
            "it to be indexed. Decide which is intended: remove the noindex, or stop linking and "
            "listing it."
        ),
        where="""site_pages.status = 200
      and (site_pages.robots_directives ilike '%noindex%' or site_pages.x_robots_tag ilike '%noindex%')
      and (site_pages.in_sitemap or site_pages.inlinks > 0)""",
    ),
    PageRule(
        kind="canonical-mismatch",
        severity="p1",
        issue=(
            "In the sitemap but its canonical tag points at a different URL. The site is asking for "
            "this page to be indexed and telling Google to index something else instead. One of the "
            "two is wrong."
        ),
        where="""site_pages.status = 200 and site_pages.in_sitemap
      and site_pages.canonical is not null and site_pages.canonical <> site_pages.url""",
    ),
    PageRule(
        kind="canonical-to-dead-page",
        severity="p1",
        issue=(
            "Its canonical tag points at a page that is gone. Google is being told the real version "
            "of this content lives at a URL that answers 404, so it has nowhere to send the ranking "
            "signals and may drop both. Point the canonical at a page that exists, or restore the one "
            "it names."
        ),
        where="""site_pages.status = 200 and site_pages.canonical is not null and site_pages.canonical <> site_pages.url
      and exists (
        select 1 from site_pages t
         where t.site_id = site_pages.site_id and t.url = site_pages.canonical and t.status >= 400
      )""",
    ),
    PageRule(
        kind="canonical-to-noindex",
        severity="p1",
        issue=(
            "Its canonical tag points at a page that is marked noindex. That is a contradiction: the "
            "page hands its ranking signals to a URL the site has asked Google to keep out of the "
            "index, so neither ends up indexed. Remove the noindex on the target, or canonicalise "
            "somewhere that is meant to rank."
        ),
        where="""site_pages.status = 200 and site_pages.canonical is not null and site_pages.canonical <> site_pages.url
      and exists (
        select 1 from site_pages t
         where t.site_id = site_pages.site_id and t.url = site_pages.canonical
           and (t.robots_directives ilike '%noindex%' or t.x_robots_tag ilike '%noindex%')
      )""",
    ),
    PageRule(
        kind="hreflang-no-self-reference",
        severity="p1",
        issue=(
            "This set of language variants does not list itself. Every page in an hreflang set has to "
            "name every variant including its own URL, and a set that breaks that rule is ignored "
            "wholesale — the variants stop being connected and can compete with each other in search. "
            "Add the missing self-referencing tag to each page in the set."
        ),
        where=f"""{HAS_HREFLANG} and {HREFLANG_LEAD}
      and exists (
        select 1 from {CLUSTER_MEMBER}
          and not exists (select 1 from jsonb_each_text(m.hreflang) w where w.value = m.url)
      )""",
    ),
    PageRule(
        kind="hreflang-not-reciprocal",
        severity="p1",
        issue=(
            "This set of language variants is not reciprocal — it names a page that does not name it "
            "back. Google only honours hreflang when both sides agree, so a one-way tag is thrown "
            "away and the variants are treated as unrelated pages. Make every page in the set list "
            "every other one."
        ),
        where=f"""{HAS_HREFLANG} and {HREFLANG_LEAD}
      and exists (
        select 1 from {CLUSTER_MEMBER}
          and exists (
            select 1 from jsonb_each_text(m.hreflang) v
              join site_pages t on t.site_id = m.site_id and t.url = v.value
             where v.key <> 'x-default' and t.url <> m.url
               and not exists (select 1 from jsonb_each_text(t.hreflang) w where w.value = m.url)
          )
      )""",
    ),
    PageRule(
        kind="hreflang-invalid-code",
        severity="p1",
        issue=(
            "This set of language variants uses a code that is not valid. hreflang takes a two-letter "
            "language code, optionally with a two-letter country code after it — en-GB, not en-UK, "
            "and a country on its own is never valid. An unrecognised code invalidates the annotation "
            "and the whole set is ignored."
        ),
        where=f"""{HAS_HREFLANG} and {HREFLANG_LEAD}
      and exists (
        select 1 from {CLUSTER_MEMBER}
          and exists (
            select 1 from jsonb_each_text(m.hreflang) v
             where v.key <> 'x-default'
               and v.key !~* '^[a-z]{{2,3}}(-[a-z]{{4}})?(-[a-z]{{2}}|-[0-9]{{3}})?$'
          )
      )""",
    ),
    PageRule(
        kind="hreflang-no-x-default",
        severity="p2",
        issue=(
            "This set of language variants has no x-default. That is the fallback Google serves to "
            "anyone whose language or country is not in the set, and without it those visitors get "
            "whichever variant the algorithm guesses. Point x-default at the version you would rather "
            "a stranger landed on."
        ),
        where=f"""{HAS_HREFLANG} and {HREFLANG_LEAD}
      and exists (
        select 1 from {CLUSTER_MEMBER}
          and m.hreflang <> '{{}}'::jsonb
          and not exists (select 1 from jsonb_each_text(m.hreflang) w where w.key = 'x-default')
      )""",
    ),
    PageRule(
        kind="mixed-content",
        severity="p2",
        issue=(
            "Served over HTTPS but pulls in an image, script or stylesheet over plain HTTP. Browsers "
            "block or downgrade those requests, so the page renders broken for visitors and for "
            "Google, which judges what it can actually render. Change the asset URLs to https."
        ),
        where="site_pages.status = 200 and site_pages.mixed_content and site_pages.url like 'https://%'",
    ),
    PageRule(
        kind="sitemap-dead-page",
        severity="p2",
        issue=(
            "Listed in the sitemap but the page is gone (404 or 410). A sitemap is a list of pages "
            "worth indexing, so a dead URL in it wastes crawl budget and tells Google the sitemap is "
            "not maintained. Remove the entry, or restore the page."
        ),
        where="site_pages.in_sitemap and site_pages.status in (404, 410)",
    ),
    PageRule(
        kind="sitemap-redirect",
        severity="p2",
        issue=(
            "Listed in the sitemap but the URL redirects. The sitemap should name the destination "
            "directly — every redirect is an extra hop before Google reaches the real page, and it "
            "hints the sitemap was generated from stale URLs."
        ),
        where="site_pages.in_sitemap and site_pages.status between 300 and 399",
    ),
    PageRule(
        kind="missing-from-sitemap",
        severity="p2",
        issue=(
            "Indexable and linked from the site, but the sitemap does not list it. The sitemap is how "
            "you tell Google which pages you consider worth indexing, and leaving good pages out of "
            "it slows discovery on anything the crawler does not stumble across. Add it, or say why "
            "it belongs out."
        ),
        where=f"""{INDEXABLE} and not site_pages.in_sitemap and site_pages.inlinks > 0
      and exists (select 1 from site_pages sm where sm.site_id = site_pages.site_id and sm.in_sitemap)""",
    ),
    PageRule(
        kind="redirect-chain",
        severity="p2",
        issue=(
            "Reached through a chain of two or more redirects. Each hop loses a little signal and "
            "slows the crawl; point the first URL straight at the final destination."
        ),
        where="site_pages.redirect_hops > 1",
    ),
    PageRule(
        kind="canonical-to-redirect",
        severity="p2",
        issue=(
            "Its canonical tag points at a URL that redirects somewhere else. A canonical should name "
            "the final address of the content, not a stop on the way to it — the extra hop muddies "
            "the signal and Google may pick a different page as the canonical instead. Point it at "
            "the destination."
        ),
        where="""site_pages.status = 200 and site_pages.canonical is not null and site_pages.canonical <> site_pages.url
      and exists (
        select 1 from site_pages t
         where t.site_id = site_pages.site_id and t.url = site_pages.canonical
           and t.status between 300 and 399
      )""",
    ),
    PageRule(
        kind="missing-canonical",
        severity="p2",
        issue=(
            "No canonical tag. Without one Google decides for itself which URL is the real version of "
            "this content, and it can settle on a tracking-parameter or print variant instead. A "
            "canonical pointing at the page's own address costs nothing and removes the guesswork."
        ),
        where=f"{INDEXABLE} and (site_pages.canonical is null or site_pages.canonical = '')",
    ),
    PageRule(
        kind="broken-internal-link",
        severity="p2",
        issue=(
            "Links to a page on this site that is gone. Readers hit a dead end, and the crawler burns "
            "budget fetching URLs that answer 404. Fix the link to point at the live page, or remove "
            "it."
        ),
        where="""site_pages.status = 200 and exists (
        select 1 from site_page_links e
          join site_pages t on t.id = e.dst_page_id
         where e.src_page_id = site_pages.id and t.status >= 400
      )""",
    ),
    PageRule(
        kind="internal-link-to-redirect",
        severity="p2",
        issue=(
            "Links to a page on this site that redirects. The redirect works, so nothing is visibly "
            "broken, but every one of these is an avoidable extra request and a small loss of link "
            "signal. Update the link to the destination URL."
        ),
        where="""site_pages.status = 200 and exists (
        select 1 from site_page_links e
          join site_pages t on t.id = e.dst_page_id
         where e.src_page_id = site_pages.id and t.status between 300 and 399
      )""",
    ),
    PageRule(
        kind="external-links-dense",
        severity="p3",
        issue=(
            "The body links out to other sites far more often than its length supports: more than "
            "two external links per hundred words, and at least five in all. Readers are pushed off "
            "the page before it has said anything, and search engines read a link-heavy body as a "
            "directory or a paid-link page rather than an article. Keep the references that earn "
            "their place and cut the rest, or write enough around them to carry the count."
        ),
        where=f"""{INDEXABLE} and coalesce(site_pages.word_count, 0) > 0
        and ({BODY_EXTERNAL_LINKS}) >= 5
        and ({BODY_EXTERNAL_LINKS}) * 100.0 / site_pages.word_count > 2""",
    ),
    PageRule(
        kind="orphan-page",
        severity="p2",
        issue=(
            "In the sitemap but nothing on the site links to it. An orphan is reachable only by "
            "knowing the URL, so it gets no internal link equity and readers never arrive at it by "
            "navigating. Link it from somewhere relevant, or drop it from the sitemap."
        ),
        where="site_pages.status = 200 and site_pages.in_sitemap and site_pages.inlinks = 0",
    ),
    PageRule(
        kind="orphan-page-unlisted",
        severity="p2",
        issue=(
            "Nothing links to it and the sitemap does not list it either. The crawl only found this "
            "page because it was already known — Google may never find it at all. Either link it from "
            "a page that belongs above it, or accept that it is not meant to be found and take it "
            "down."
        ),
        where=f"""site_pages.status = 200 and not site_pages.in_sitemap and site_pages.inlinks = 0
      and not ({IS_HOME})""",
    ),
    PageRule(
        kind="deep-page",
        severity="p2",
        issue=(
            "More than four clicks from the home page. Depth is how Google reads importance: the "
            "further down a page sits, the less often it is crawled and the less internal signal "
            "reaches it. Link it from a hub or category page nearer the top."
        ),
        where=f"{INDEXABLE} and site_pages.depth > 4",
    ),
    PageRule(
        kind="soft-404",
        severity="p2",
        issue=(
            "Answers 200 but reads like an error page — almost no content, and wording that says the "
            "page was not found. Google calls this a soft 404 and it wastes crawl budget on a URL "
            "that has nothing to index. Return a real 404 or 410, or put actual content there."
        ),
        where="""site_pages.status = 200 and coalesce(site_pages.word_count, 0) < 200
      and (site_pages.title ilike '%not found%' or site_pages.title ilike '%404%'
        or site_pages.title ilike '%no longer available%'
        or site_pages.body_text ilike '%page you are looking for%'
        or site_pages.body_text ilike '%page cannot be found%'
        or site_pages.body_text ilike '%page does not exist%')""",
    ),
    PageRule(
        kind="thin-content",
        severity="p2",
        issue=(
            "Very little text for the kind of page it is. A short article or product page rarely has "
            "enough on it to answer the question that brought someone there, and a site full of them "
            "dilutes the pages that are worth reading. Expand it, merge it into a fuller page, or "
            "drop it."
        ),
        where=f"""{INDEXABLE} and x.page_type in ('informational', 'money', 'support')
      and coalesce(site_pages.word_count, 0) < 250""",
    ),
    PageRule(
        kind="missing-title",
        severity="p2",
        issue=(
            "No title tag. The title is the headline in search results and the single strongest "
            "on-page signal of what the page is about; without one Google writes its own from the "
            "page text, usually badly."
        ),
        where="site_pages.status = 200 and not site_pages.shallow and (site_pages.title is null or site_pages.title = '')",
    ),
    PageRule(
        kind="duplicate-title",
        severity="p2",
        issue=(
            "Shares its title with another indexable page on this site. Two pages claiming the same "
            "headline look like the same page to Google, which picks one and ignores the other, and "
            "neither reads as the better answer. Give each page a title that names what only it "
            "covers."
        ),
        where=f"""{INDEXABLE} and site_pages.title is not null and site_pages.title <> ''
      and exists (
        select 1 from site_pages t
         where t.site_id = site_pages.site_id and t.id <> site_pages.id
           and t.status = 200 and not t.shallow and t.title = site_pages.title
      )""",
    ),
    PageRule(
        kind="missing-meta-description",
        severity="p2",
        issue=(
            "No meta description. Google falls back to scraping a snippet out of the body, which "
            "reads like an accident in the result list. This does not change ranking, it changes how "
            "many people click."
        ),
        where="""site_pages.status = 200 and not site_pages.shallow
      and (site_pages.meta_description is null or site_pages.meta_description = '')""",
    ),
    PageRule(
        kind="duplicate-meta-description",
        severity="p3",
        issue=(
            "Shares its meta description with another indexable page on this site. A description "
            "written once and pasted everywhere tells a searcher nothing about which result to open, "
            "so Google usually discards it and writes its own. Write one per page, about that page."
        ),
        where=f"""{INDEXABLE} and site_pages.meta_description is not null and site_pages.meta_description <> ''
      and exists (
        select 1 from site_pages t
         where t.site_id = site_pages.site_id and t.id <> site_pages.id
           and t.status = 200 and not t.shallow and t.meta_description = site_pages.meta_description
      )""",
    ),
    PageRule(
        kind="missing-h1",
        severity="p2",
        issue=(
            "No H1. The page has no top-level heading naming its subject, which leaves both readers "
            "and crawlers to infer the topic from the body text."
        ),
        where="site_pages.status = 200 and not site_pages.shallow and coalesce(cardinality(site_pages.h1), 0) = 0",
    ),
    PageRule(
        kind="no-structured-data",
        severity="p2",
        issue=(
            "An article or product page with no structured data at all. Schema markup is how you "
            "state in machine-readable terms what the page is — the author, the date, the price — and "
            "it is what rich results and answer engines read. Add JSON-LD for the type of page this "
            "is."
        ),
        where=f"""{INDEXABLE} and x.page_type in ('informational', 'money')
      and coalesce(cardinality(site_pages.schema_types), 0) = 0""",
    ),
    PageRule(
        kind="home-missing-organization",
        severity="p2",
        issue=(
            "The home page carries no Organization or WebSite markup. Those are what tie the site to "
            "a named entity — the business, its logo, its official profiles — and without them a "
            "search engine has only the text to work out who you are. Add them to the home page, with "
            "sameAs links to the profiles you already own."
        ),
        where=f"""site_pages.status = 200 and {IS_HOME}
      and not exists (
        select 1 from unnest(site_pages.schema_types) t
         where lower(t) in ('organization', 'website', 'localbusiness', 'corporation')
      )""",
    ),
    PageRule(
        kind="home-missing-contact-link",
        severity="p2",
        issue=(
            "The home page does not link to a contact page. A way to reach the business is one of the first things a search engine's quality "
            "raters, and the models trained on their judgements, look for when deciding whether a site "
            "is a real organisation or a page that could belong to anyone. Link a contact page from "
            "the home page — the footer is the usual place."
        ),
        where=home_links_none(CONTACT_LINK),
    ),
    PageRule(
        kind="home-missing-terms-link",
        severity="p3",
        issue=(
            "The home page does not link to terms and conditions. Nothing ranks a site for having "
            "them, but their absence is one of the signals used to judge whether a business stands "
            "behind what it publishes, and any site that takes payment, collects data or offers a "
            "service is expected to state its terms somewhere reachable. Publish a terms page and link "
            "it from the home page footer alongside the privacy policy."
        ),
        where=home_links_none(TERMS_LINK),
    ),
    PageRule(
        kind="home-missing-social-links",
        severity="p3",
        issue=(
            "The home page links to no social media profile — no Facebook, Instagram, LinkedIn, X, "
            "YouTube, TikTok or similar. Profile links are how search engines and AI models confirm "
            "that the site and the accounts belong to the same entity, and they are what the sameAs "
            "property of Organization markup is expected to repeat. Link the profiles the business "
            "actually maintains from the home page; do not add accounts nobody posts to."
        ),
        where=home_external_links_none(SOCIAL_LINK),
    ),
    PageRule(
        kind="home-missing-google-analytics",
        severity="p3",
        issue=(
            "No Google Analytics tag was found on the home page — no gtag.js or Tag Manager script "
            "and no inline measurement snippet. Analytics changes nothing about how the site ranks, "
            "but without it there is no record of what visitors do once they arrive, so every other "
            "fix here is flying blind: you cannot see which pages earn traffic, where people land or "
            "what they leave from. Install the GA4 tag (directly or through Google Tag Manager) on "
            "every page. If analytics is loaded through a consent manager or another product "
            "entirely, this can be ignored."
        ),
        where=f"""site_pages.status = 200 and {IS_HOME}
      and site_pages.has_google_analytics = false""",
    ),
    PageRule(
        kind="schema-article-incomplete",
        severity="p2",
        issue=(
            "The article markup on this page is missing properties Google treats as required — a "
            "headline, an author and a published date. Structured data that does not carry them is "
            "read and then ignored, so the page gets none of the rich result it is marked up for. "
            "This is not about having schema; the schema is there and incomplete."
        ),
        where=f"""{INDEXABLE} and {
            schema_node(
                ["article", "blogposting", "newsarticle", "techarticle"],
                f"{without('headline')} or {without('author')} or {without('datePublished')}",
            )
        }""",
    ),
    PageRule(
        kind="schema-product-incomplete",
        severity="p2",
        issue=(
            "The product markup on this page has no name, or nothing to price or rate it by. Google "
            "needs a name and at least one of an offer, a review or an aggregate rating before a "
            "product is eligible for a rich result — without them the markup is dead weight. Add the "
            "offer with its price and currency and availability, which is the one that earns the "
            "result."
        ),
        where=f"""{INDEXABLE} and {
            schema_node(
                ["product"],
                f"{without('name')} or ({without('offers')} and {without('review')} and {without('aggregateRating')})",
            )
        }""",
    ),
    PageRule(
        kind="schema-faq-incomplete",
        severity="p2",
        issue=(
            "The page declares FAQ markup with no questions inside it. An FAQPage carries its content "
            "in mainEntity — a list of questions each with an accepted answer — and one without them "
            "declares a shape and fills none of it. Either populate it from the questions actually on "
            "the page or remove the markup."
        ),
        where=f"{INDEXABLE} and {schema_node(['faqpage', 'qapage'], without('mainEntity'))}",
    ),
    PageRule(
        kind="schema-howto-incomplete",
        severity="p2",
        issue=(
            "The how-to markup on this page has no steps, or no name. The steps are the whole of it — "
            "a HowTo without them says a procedure exists without saying what it is. List each step "
            "with its own text, in the order the page gives them."
        ),
        where=f"""{INDEXABLE} and {
            schema_node(
                ["howto"],
                f"{without('name')} or {without('step')}",
            )
        }""",
    ),
    PageRule(
        kind="schema-breadcrumb-incomplete",
        severity="p3",
        issue=(
            "The breadcrumb markup on this page lists no items. A BreadcrumbList exists to name the "
            "trail of pages above this one, in itemListElement, and an empty one gives search results "
            "nothing to show in place of the bare URL."
        ),
        where=f"{INDEXABLE} and {schema_node(['breadcrumblist'], without('itemListElement'))}",
    ),
    PageRule(
        kind="schema-organization-incomplete",
        severity="p2",
        issue=(
            "The organisation markup on this page does not name the organisation or give its URL. "
            "Those two are what tie the markup to an entity a search engine can recognise; without "
            "them it describes nobody. Add the name and the canonical home page URL, and the logo and "
            "sameAs profiles while you are there."
        ),
        where=f"""{INDEXABLE} and {
            schema_node(
                ["organization", "corporation", "onlinebusiness", "ngo"],
                f"{without('name')} or {without('url')}",
            )
        }""",
    ),
    PageRule(
        kind="schema-localbusiness-incomplete",
        severity="p2",
        issue=(
            "The local business markup on this page has no name, postal address or telephone number. "
            "A local business is identified by where it is and how to reach it, and markup missing "
            "those cannot be matched to the business in local results or on a map. Add the full "
            "address as a PostalAddress, with the phone number."
        ),
        where=f"""{INDEXABLE} and {
            schema_node(
                ["localbusiness", "restaurant", "store", "professionalservice", "medicalbusiness"],
                f"{without('name')} or {without('address')} or {without('telephone')}",
            )
        }""",
    ),
    PageRule(
        kind="restrictive-snippet",
        severity="p2",
        issue=(
            "Tells search engines not to show a snippet of this page. Without a snippet the result is "
            "a bare blue link, and the same directive keeps the page out of the answers AI search "
            "assembles. If it was set to protect paid content, say so deliberately; if nobody "
            "remembers setting it, remove it."
        ),
        where="""site_pages.status = 200 and not site_pages.shallow
      and (site_pages.robots_directives ilike '%nosnippet%' or site_pages.robots_directives ilike '%max-snippet:0%'
        or site_pages.x_robots_tag ilike '%nosnippet%' or site_pages.x_robots_tag ilike '%max-snippet:0%')""",
    ),
    PageRule(
        kind="missing-viewport",
        severity="p2",
        issue=(
            "No viewport meta tag. Without it a phone renders the page at desktop width and shrinks "
            "it, so the text is unreadable until the reader pinches to zoom. Google indexes what the "
            "mobile crawler sees, so this is judged on every page that lacks the tag."
        ),
        where="site_pages.status = 200 and not site_pages.shallow and site_pages.viewport_meta is null",
    ),
    PageRule(
        kind="title-too-long",
        severity="p3",
        issue=(
            "The title is wide enough that search results will cut it off. What gets trimmed is the "
            "end, which is usually where the specific part of the title sits. Put the words that "
            "matter first and shorten the rest."
        ),
        where=f"{CRAWLED} and site_pages.title_pixels > 580",
    ),
    PageRule(
        kind="title-too-short",
        severity="p3",
        issue=(
            "The title is far shorter than the space search results give it. There is room to say "
            "what the page covers and who it is for; a two-word title spends none of it and reads as "
            "vague next to competitors."
        ),
        where=f"{CRAWLED} and site_pages.title is not null and site_pages.title <> '' and site_pages.title_pixels < 200",
    ),
    PageRule(
        kind="meta-description-length",
        severity="p3",
        issue=(
            "The meta description is either too short to say anything or long enough to be cut off "
            "mid-sentence. Around seventy to a hundred and sixty characters is what shows, so aim for "
            "one complete sentence that gives someone a reason to click."
        ),
        where=f"""{CRAWLED} and site_pages.meta_description is not null and site_pages.meta_description <> ''
      and (length(site_pages.meta_description) < 70 or length(site_pages.meta_description) > 160)""",
    ),
    PageRule(
        kind="multiple-h1",
        severity="p3",
        issue=(
            "More than one H1. The H1 is meant to name the one subject of the page, so several of "
            "them leaves it ambiguous which is the real heading — usually a sign the template puts a "
            "site name or a widget title in an H1. Keep one and demote the rest."
        ),
        where=f"{CRAWLED} and cardinality(site_pages.h1) > 1",
    ),
    PageRule(
        kind="heading-hierarchy-skip",
        severity="p3",
        issue=(
            "The headings skip a level — an H2 followed by an H4, for instance. Headings are the "
            "outline of the page, and a jump breaks the structure that screen readers and answer "
            "engines use to work out which part answers what. Step down one level at a time."
        ),
        where=f"""{CRAWLED} and exists (
        select 1 from (
          select (h.v->>'level')::int as lvl,
                 lag((h.v->>'level')::int) over (order by h.ord) as prev
            from jsonb_array_elements(site_pages.headings) with ordinality as h(v, ord)
        ) x where x.lvl - x.prev >= 2
      )""",
    ),
    PageRule(
        kind="image-missing-alt",
        severity="p3",
        issue=(
            "Has images with no alt attribute at all. Alt text is what a screen reader announces and "
            "what image search reads, and an image that is purely decorative should still carry an "
            "empty alt so it can be skipped deliberately. Describe what the image shows, or mark it "
            "decorative."
        ),
        where=f"""{CRAWLED} and exists (
        select 1 from jsonb_array_elements(site_pages.images) im where im->>'alt' is null
      )""",
    ),
    PageRule(
        kind="image-missing-dimensions",
        severity="p3",
        issue=(
            "Has images with no width and height set. The browser cannot reserve space for them, so "
            "the page jumps as they load, and the reader taps the wrong thing. Setting the two "
            "attributes is the whole fix."
        ),
        where=f"""{CRAWLED} and exists (
        select 1 from jsonb_array_elements(site_pages.images) im
         where im->>'width' is null or im->>'height' is null
      )""",
    ),
    PageRule(
        kind="image-oversized",
        severity="p3",
        issue=(
            "Carries an image heavier than 200 KB. The file size is measured from the server, not "
            "guessed from the markup. On a phone connection a single image that size is most of the "
            "wait before anything is readable, and it is usually the largest element on screen. "
            "Export it at the size it is actually displayed at and compress it."
        ),
        where=f"""{CRAWLED} and exists (
        select 1 from jsonb_array_elements(site_pages.images) im
         where im->>'bytes' is not null and (im->>'bytes')::bigint > 200000
      )""",
    ),
    PageRule(
        kind="image-legacy-format",
        severity="p3",
        issue=(
            "Serves a large image as JPEG, PNG or GIF. WebP and AVIF carry the same picture in a "
            "fraction of the bytes and every browser in use reads them, so the older formats cost "
            "load time for nothing. Convert the heavy ones, or serve modern formats through a "
            "picture element with the old file as the fallback."
        ),
        where=f"""{CRAWLED} and exists (
        select 1 from jsonb_array_elements(site_pages.images) im
         where im->>'type' in ('image/jpeg', 'image/png', 'image/gif')
           and im->>'bytes' is not null and (im->>'bytes')::bigint > 100000
      )""",
    ),
    PageRule(
        kind="missing-lang",
        severity="p3",
        issue=(
            "The html tag declares no language. Screen readers use it to pick a voice and search "
            "engines use it to decide who the page is for; leaving it off means both are guessing "
            "from the text. Set lang on the html element."
        ),
        where="site_pages.status = 200 and not site_pages.shallow and (site_pages.lang is null or site_pages.lang = '')",
    ),
    PageRule(
        kind="url-hygiene",
        severity="p3",
        issue=(
            "The URL has capitals, underscores or tracking parameters in it. Servers treat upper and "
            "lower case as different addresses, word separators should be hyphens, and a tracking "
            "parameter left in a link creates a second URL for the same page. None of this is fatal; "
            "it just makes duplicates easier to create by accident."
        ),
        where=f"""site_pages.status = 200 and ({PATH} ~ '[A-Z]' or {PATH} ~ '_'
      or site_pages.url ~ '[?&](utm_|fbclid|gclid|mc_cid|_ga)=')""",
    ),
    PageRule(
        kind="url-too-long",
        severity="p3",
        issue=(
            "The path is over a hundred characters long. A long URL is harder to read in a result, "
            "gets truncated when it is shown, and survives being copied into a message or a document "
            "less well. It usually means the path repeats what the folders above it already say. "
            "Shorten the slug to the words that identify the page."
        ),
        where=f"site_pages.status = 200 and length({SLUG}) > 100",
    ),
    PageRule(
        kind="url-dated",
        severity="p3",
        issue=(
            "The URL has a year and month baked into the path. That is a CMS default rather than a "
            "decision, and it dates the page permanently: updating the article cannot update its "
            "address, so the URL keeps announcing a year that is no longer true, and moving it later "
            "costs a redirect. Unless the date is the point of the page, leave it out of the path and "
            "let the published date live in the markup."
        ),
        where=f"site_pages.status = 200 and {SLUG} ~ '/(19|20)[0-9]{{2}}[/-](0[1-9]|1[0-2])([/-]|$)'",
    ),
    PageRule(
        kind="url-stop-words",
        severity="p3",
        issue=(
            "The slug carries several function words — and, the, for, to, of. They take up room in a "
            "result without telling anyone anything, and the slug reads the same once they are gone. "
            "This is polish rather than a ranking problem, and it is only worth doing on a page that "
            "is not published yet: changing a live URL costs a redirect, which is a worse trade than "
            "leaving the words in."
        ),
        where=f"""site_pages.status = 200 and not site_pages.shallow
      and regexp_count({SLUG}, '{STOP_WORD_RE}', 1, 'i') >= 2""",
    ),
]
