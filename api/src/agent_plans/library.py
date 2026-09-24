BUILTIN_PLANS: dict[str, dict[str, str]] = {
    "striking-distance": {
        "question": "Which queries are within striking distance of page one (positions 8-15)?",
        "plan": """\
Striking-distance queries rank just off page one, where a small improvement
moves them into meaningful traffic. Use the last 28 stored days, anchored to
the data (never to today):

WITH win AS (SELECT max(day) AS last FROM site_search_daily WHERE site_id = :site)
SELECT query, sum(clicks) AS clicks, sum(impressions) AS impressions,
       sum(position * impressions) / NULLIF(sum(impressions), 0) AS avg_position,
       (array_agg(page ORDER BY impressions DESC))[1] AS top_page
FROM site_search_daily, win
WHERE site_id = :site AND day > win.last - 28
GROUP BY query
HAVING sum(position * impressions) / NULLIF(sum(impressions), 0) BETWEEN 8 AND 15
   AND sum(impressions) >= 50
ORDER BY sum(impressions) DESC LIMIT 25;

Weight position by impressions — a plain AVG over-counts thin days. Report
impressions alongside position so the user sees which are worth the effort,
and name the page that currently ranks for each query.""",
    },
    "search-trend": {
        "question": "How are clicks and impressions trending over recent weeks or months?",
        "plan": """\
First check coverage — the sync lags Google by days:
SELECT min(day), max(day) FROM site_search_daily WHERE site_id = :site;

Anchor every window to max(day). Weekly series for a trend chart:

SELECT date_trunc('week', day)::date AS week,
       sum(clicks) AS clicks, sum(impressions) AS impressions,
       sum(clicks)::float / NULLIF(sum(impressions), 0) AS ctr
FROM site_search_daily WHERE site_id = :site
GROUP BY 1 ORDER BY 1;

Drop the newest partial week from trend claims. For a headline number,
compare the last 28 stored days against the 28 before them and give both
absolute and percent change. If total impressions are tiny, say the data is
too thin to reason from instead of quoting percentage swings.""",
    },
    "winners-losers": {
        "question": "Which pages gained or lost search traffic compared to the previous period?",
        "plan": """\
Two equal windows anchored to the last stored day, compared per page:

WITH win AS (SELECT max(day) AS last FROM site_search_daily WHERE site_id = :site),
cur AS (SELECT page, sum(clicks) c FROM site_search_daily, win
        WHERE site_id = :site AND day > win.last - 28 GROUP BY page),
prev AS (SELECT page, sum(clicks) c FROM site_search_daily, win
         WHERE site_id = :site AND day > win.last - 56 AND day <= win.last - 28
         GROUP BY page)
SELECT COALESCE(cur.page, prev.page) AS page,
       COALESCE(cur.c, 0) AS current, COALESCE(prev.c, 0) AS previous,
       COALESCE(cur.c, 0) - COALESCE(prev.c, 0) AS delta
FROM cur FULL OUTER JOIN prev USING (page)
ORDER BY delta;

The FULL OUTER JOIN matters: pages that vanished entirely are the biggest
losers and an inner join hides them. Show the top of both ends, and filter
out pages below a few clicks in both windows — noise, not movement.""",
    },
    "crawled-not-indexed": {
        "question": "Which pages has Google crawled but not indexed?",
        "plan": """\
Index state lives per page in site_page_index_status (from URL inspection),
joined to site_pages for the URL:

SELECT p.url, s.index_state, s.coverage_state, s.google_canonical,
       s.index_checked_at
FROM site_page_index_status s JOIN site_pages p ON p.id = s.page_id
WHERE s.site_id = :site AND s.index_state IS DISTINCT FROM 'indexed'
ORDER BY s.index_checked_at DESC NULLS LAST;

Read coverage_state — it says why. Also count pages never inspected at all
(site_pages LEFT JOIN ... WHERE s.id IS NULL): absence of a row is "unknown",
not "fine". A google_canonical differing from the page's own URL means Google
canonicalises it elsewhere — call those out separately. Many crawled-not-
indexed pages together usually signal thin or duplicative content, not a
technical bug.""",
    },
    "page-top-queries": {
        "question": "What are the top search queries for one specific page?",
        "plan": """\
SELECT query, sum(clicks) AS clicks, sum(impressions) AS impressions,
       sum(clicks)::float / NULLIF(sum(impressions), 0) AS ctr,
       sum(position * impressions) / NULLIF(sum(impressions), 0) AS avg_position
FROM site_search_daily
WHERE site_id = :site AND page = :url
  AND day > (SELECT max(day) - 28 FROM site_search_daily WHERE site_id = :site)
GROUP BY query ORDER BY sum(impressions) DESC LIMIT 50;

`page` holds the full URL exactly as Search Console reports it — match it
against site_pages.url; if a straight equality finds nothing, check for
trailing-slash or protocol variants before concluding there is no data.""",
    },
    "ctr-underperformers": {
        "question": "Which pages or queries get impressions but few clicks (low CTR for their position)?",
        "plan": """\
Low CTR only means something relative to position — position 9 always has low
CTR. Compare within position bands:

WITH agg AS (
  SELECT query, (array_agg(page ORDER BY impressions DESC))[1] AS page,
         sum(clicks) c, sum(impressions) i,
         sum(position * impressions) / NULLIF(sum(impressions), 0) AS pos
  FROM site_search_daily
  WHERE site_id = :site
    AND day > (SELECT max(day) - 28 FROM site_search_daily WHERE site_id = :site)
  GROUP BY query HAVING sum(impressions) >= 100)
SELECT *, c::float / NULLIF(i, 0) AS ctr,
       width_bucket(pos, 1, 21, 4) AS pos_band
FROM agg ORDER BY pos_band, ctr ASC;

Within each band, the bottom entries are title/meta-description candidates:
they earn the impression but lose the click. Check their title and
meta_description in site_pages before recommending a rewrite.""",
    },
    "cannibalization": {
        "question": "Are multiple pages competing for the same query (keyword cannibalization)?",
        "plan": """\
SELECT query, count(DISTINCT page) AS pages,
       sum(impressions) AS impressions,
       array_agg(DISTINCT page) AS competing_pages
FROM site_search_daily
WHERE site_id = :site
  AND day > (SELECT max(day) - 28 FROM site_search_daily WHERE site_id = :site)
GROUP BY query
HAVING count(DISTINCT page) > 1 AND sum(impressions) >= 100
ORDER BY sum(impressions) DESC LIMIT 25;

Then, for the worst queries, break down per page to see whether one page
dominates (fine — the others are incidental) or impressions genuinely split
across pages with mid positions (real cannibalization). Recommend
consolidating toward the page that already earns most of the clicks.""",
    },
    "orphan-deep-pages": {
        "question": "Which pages are orphaned (no internal links) or buried too deep?",
        "plan": """\
SELECT url, inlinks, depth, in_sitemap, word_count, status
FROM site_pages
WHERE site_id = :site AND status = 200
  AND (inlinks = 0 OR depth >= 4)
ORDER BY inlinks ASC, depth DESC;

inlinks and depth are facts the crawl wrote down — this is a filter, not a
walk through page text. Split the report: orphans in the sitemap (Google can
find them, users cannot) vs orphans outside it (effectively invisible).
Check site.last_crawled_at first and say when the crawl is old; a page
published after the crawl will look orphaned when it is merely unseen.""",
    },
    "issue-hotspots": {
        "question": "Which pages have the most technical SEO issues, and which issue kinds are worst?",
        "plan": """\
Only the latest audit run counts:

WITH run AS (SELECT id FROM site_audit_runs WHERE site_id = :site
             ORDER BY seq DESC LIMIT 1)
SELECT p.url, count(*) AS issues,
       count(*) FILTER (WHERE i.severity IN ('p0','p1')) AS severe,
       array_agg(DISTINCT i.kind) AS kinds
FROM site_page_issues i JOIN run ON i.run_id = run.id
JOIN site_pages p ON p.id = i.page_id
WHERE i.state = 'open'
GROUP BY p.url ORDER BY severe DESC, issues DESC LIMIT 25;

Swap the GROUP BY to i.kind for the by-kind view. Filter state = 'open' —
rejected issues are the user's standing decisions; check site_issues (site-
level, same run) too, and surface rejection_reason before re-recommending
anything previously turned down.""",
    },
    "page-details": {
        "question": "Fetch everything known about one page: crawl facts, content, issues, index state.",
        "plan": """\
Three lookups, joined by the page id:

SELECT id, url, status, title, meta_description, h1, word_count, depth,
       inlinks, in_sitemap, canonical, robots_directives, blocked_by_robots,
       format, last_crawled_at
FROM site_pages WHERE site_id = :site AND url = :url;

Open issues on it, from the latest audit only:
WITH run AS (SELECT id FROM site_audit_runs WHERE site_id = :site
             ORDER BY seq DESC LIMIT 1)
SELECT i.kind, i.issue, i.severity, i.state, i.rejection_reason
FROM site_page_issues i JOIN run ON i.run_id = run.id
WHERE i.page_id = :page_id ORDER BY i.severity;

Index state (absence of a row means never inspected, not fine):
SELECT index_state, coverage_state, google_canonical, index_checked_at
FROM site_page_index_status WHERE page_id = :page_id;

Read body_text only if the question is about the content itself — it is the
whole page text and large. If the exact URL misses, retry with trailing-slash
and protocol variants before concluding the page was never crawled.""",
    },
    "broken-pages": {
        "question": "Which pages are broken — 4xx/5xx status, fetch errors, or redirects?",
        "plan": """\
SELECT url, status, fetch_error, inlinks, in_sitemap
FROM site_pages
WHERE site_id = :site AND (status >= 400 OR fetch_error IS NOT NULL)
ORDER BY inlinks DESC, status DESC;

Order by inlinks — a 404 that many pages link to outranks an orphaned one.
Redirects are a separate list, not errors:
SELECT url, status, redirect_to, redirect_final, redirect_hops
FROM site_pages WHERE site_id = :site AND status BETWEEN 300 AND 399
ORDER BY redirect_hops DESC;

For "who links to the broken page", the audit already wrote it down: query
site_page_issues on the latest run with kind = 'broken-internal-link' — the
page_id there is the page HOLDING the broken link. A 404 that is also in the
sitemap (in_sitemap = true) is the worst case; lead with those.""",
    },
    "page-inventory": {
        "question": "Filter the page corpus: thin pages, missing titles or descriptions, pages not in the sitemap.",
        "plan": """\
These are all single filters over site_pages — crawl facts, not walks through
content. Always start from live pages: status = 200. Common filters:

- Thin content: word_count < 300 AND kind checks — filter by kind so a
  category or contact page is not judged as an article.
- Missing metadata: title IS NULL OR title = '' / meta_description IS NULL /
  h1 = '{}' (h1 is an array).
- Sitemap gaps: in_sitemap = false AND status = 200 AND
  blocked_by_robots = false — pages Google must discover by crawling.
- Noindexed: robots_directives ILIKE '%noindex%' — check these are meant
  to be excluded before reporting them as problems.

Example:
SELECT url, word_count, kind, in_sitemap FROM site_pages
WHERE site_id = :site AND status = 200 AND word_count < 300
ORDER BY inlinks DESC LIMIT 50;

Report counts first (one GROUP BY), then the worst examples — never page
through the whole corpus in the conversation.""",
    },
    "data-freshness": {
        "question": "How fresh is the data — when did the last crawl, search sync, and audit run?",
        "plan": """\
Check before answering anything time-sensitive; say the dates in the answer.

SELECT domain, last_crawled_at, gsc_property, ga_property
FROM site WHERE id = :site;

SELECT status, finished_at, pages_stored, failed, error
FROM site_crawl_jobs WHERE site_id = :site ORDER BY seq DESC LIMIT 1;

SELECT status, finished_at, last_day, days_done, days_total, error
FROM site_search_syncs WHERE site_id = :site ORDER BY seq DESC LIMIT 1;

SELECT finished_at, rules_run, site_issues_found, page_issues_found
FROM site_audit_runs WHERE site_id = :site ORDER BY seq DESC LIMIT 1;

A running job (status queued/running, finished_at NULL) means numbers are
about to change — say so. last_day on the search sync is where GSC data
actually ends; anchor windows there, never at today.""",
    },
    "traffic-vs-search": {
        "question": "How does a page's analytics traffic compare with its search clicks?",
        "plan": """\
The two sources key pages differently: site_traffic_pages_daily.page_path is
a GA4 path ('/pricing'), site_search_daily.page is a full URL. Join on the
path suffix:

WITH ga AS (SELECT page_path, sum(views) views, sum(users) users
            FROM site_traffic_pages_daily WHERE site_id = :site
              AND day > current_date - 28 GROUP BY page_path),
gsc AS (SELECT page, sum(clicks) clicks FROM site_search_daily
        WHERE site_id = :site
          AND day > (SELECT max(day) - 28 FROM site_search_daily
                     WHERE site_id = :site)
        GROUP BY page)
SELECT ga.page_path, ga.views, ga.users, COALESCE(gsc.clicks, 0) AS search_clicks
FROM ga LEFT JOIN gsc ON gsc.page LIKE '%' || ga.page_path
ORDER BY ga.views DESC LIMIT 50;

The windows differ on purpose: GA data is near-live, GSC lags days — say so
when comparing. Pages with views but no search clicks are carried by other
channels; pages with clicks but few views suggest a tracking gap.""",
    },
}
