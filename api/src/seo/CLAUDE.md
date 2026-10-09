# SEO desk (rebuild) — what we are building

Source: `docs/SEO Decision Strategies for an Add Edit Page Agent.pdf` (2026-09-27).
The PDF says **what** the desk decides and **which evidence** it needs. It does
not say how to build it. We build it step by step, following the "Adding a new
feature" order in the root `CLAUDE.md`. This file is the scope. Update it as
decisions are made.

## How we build it: strategies are prompts, code is building blocks

The PDF is a reference, not a spec. We will change it as we learn. We build
one strategy at a time, the same way `site_structure` was built:

- **A strategy is a prompt.** "Striking distance", "cannibalization", "content
  gap" live in the desk's prompt as steps for the agent. There is no
  `striking_distance.py` that encodes the strategy.
- **The code is building blocks** that any strategy can combine. The agent
  selects candidates with SQL into a workspace table. A generator turns the
  table into draft suggestions and does the work SQL cannot do (vendor
  calls, SERP overlap, frozen evidence). Then screen → review → rank decide what the
  user sees.
- **A building block is added only when a strategy needs it.** The playbooks,
  router and analyses below describe where we might go. Build none of them
  ahead of the strategy that uses them.

`api/src/seo_deprecated` is the old desk, unwired and kept only to read. Never
import from it or copy its shapes.

Other modules are fixed only once this desk is ready, not while it is built.
Left broken or stopgapped until then: the dashboard SEO screen (calls removed
routes and ask-seo), the Content desk (loads only the Site desk for keywords
instead of `seo`), the app's `review.js` (old SEO review pipeline removed),
and the api/agent/embed-worker images (need a rebuild).

## The one decision

The desk answers one question, over and over:

> For a given pocket of search demand, which of the user's URLs should own it,
> and what change gets it there?

There are three possible answers:

- **edit**: an existing page should own the demand. Change that page.
- **add**: no page owns the demand, and one should. Write a brief for a new page.
- **consolidate**: two or more pages split the demand. Pick an owner and say
  what happens to the others (merge, redirect, differentiate, de-optimize,
  canonical, delete/noindex).

A **technical flag** is a fourth outcome. It means the problem is not the
content (for example, the page is not indexed or its canonical is wrong). The
desk names the flag and points to the Technical SEO desk. It does not fix it.

Meelu suggests and the human decides (root `CLAUDE.md`). Every answer above is
a suggestion with evidence. The desk never edits, retitles, merges, redirects
or deletes anything. "Merge into X and 301" is text the user reads, not an
action the desk takes.

## Why the rebuild: the desk does not own the inputs

The old desk copied other domains' data into its own tables (GSC rows per
keyword and page, page facts, SERP results). Those copies went stale, doubled
the schema and meant two places to change when a source changed.

**Rule: `seo` stores only what it produces.** It reads everything else from
the domain that owns it, through that domain's service or repository, at the
time it needs it.

| Input | Owner (read from here, never copy) |
|---|---|
| GSC query × page × day (clicks, impressions, position) | `site_search` — `site_search_daily` |
| Index state, Google-selected canonical, last crawl | `site_search` — `site_page_index_status` |
| GA4 sessions, key events, revenue per landing page | `site_traffic` — `site_traffic_landing_daily`, `site_traffic_pages_daily` |
| URL inventory, title, H1, headings, body, schema, word count, dates, indexability | `site_pages` — `site_pages` |
| Page chunks and embeddings (e5-small, 384) | `site_pages` — `site_chunks` |
| Page type | `site_pages` — `site_page_llm_extraction` |
| Internal-link graph, inlinks, link score | `site_pages` — `site_page_links`, `site_pages.link_score` |
| Site domain, country, summary | `sites` |
| Market data (volume, difficulty, intent, SERPs, competitors, trends, AI mentions) | `providers/seo_data` facade (cached in `provider_cache`, charged in credits) |
| Internal-link suggestions | `site_structure` — the desk hands off to it, it does not compute links |

The facade already caches vendor responses. Do not add a second vendor cache
in `seo`.

What `seo` does own (to be confirmed at the schema step):

- **Query clusters** and their member queries/keywords. This is derived data,
  but it is expensive (SERP calls) and every playbook needs it.
- **The cluster-to-URL map**: which page owns, partly covers or competes for
  each cluster.
- **Suggestions**, each with an **evidence snapshot**: the GSC numbers and the
  SERP the desk saw when it made the suggestion. The facade cache expires, so
  the snapshot is frozen on the suggestion. Later we measure whether the
  suggestion worked against it.
- **Runs**: one playbook run for one prompt (scope, parameters, vendor spend,
  status).
- **Outcomes**: GSC measurements at 4, 8 and 12 weeks for suggestions the user
  marked done.

Anything that is cheap to recompute from the owner tables (a CTR curve, a
striking-distance list, a decay comparison) is computed when needed and not
stored. If it must be kept as evidence, it goes into the suggestion's snapshot.

## Core concepts

### The query cluster is the unit of analysis

Not the keyword, not the page. GSC says how our URLs perform on queries.
DataForSEO says what the market around those queries looks like. Both are
joined onto clusters. Clusters are built by SERP overlap alone.

**The desk does not compute embeddings in most cases.** Two queries close in
embedding space can want different pages ("crm software" vs "crm software
jobs"), and two far apart can want the same one ("cheap flights" vs "low cost
airfare"). Only the SERP says whether Google treats them as one intent. The
cost of clustering is the number of SERPs fetched, not the pairwise
comparison, so an embedding pre-filter saves nothing worth its error.
Embeddings stay a last resort for a question neither GSC nor a SERP can
answer.

### Playbooks

A user prompt routes to one or more playbooks. A playbook is three fixed things:

1. **Evidence recipe**: which data to pull.
2. **Decision rule**: when to add, edit or consolidate.
3. **Output**: suggestions in the shared suggestion shape.

The LLM routes the prompt, fills the parameters and explains the result.
Deterministic code does the math. The LLM never computes a CTR, a position
band or an overlap count.

### The router

It turns a free-form prompt into playbooks plus scope: whole site, a folder,
one URL or one keyword; the market; and the date range. It asks the user only
when the scope is really ambiguous. When the prompt is vague, the default is
edit playbooks (Quick wins), because edits to pages that already rank are
usually the cheapest wins.

### The shared suggestion shape

Every playbook outputs the same fields. That is what lets one screen → review
→ rank pipeline serve all playbooks:

- action type (edit, add, consolidate sub-action, technical flag)
- target URL, or proposed URL + slug for an add
- target cluster
- evidence numbers (the snapshot)
- what to change, specifically (named sections, titles, redirects — never
  "improve content")
- expected impact, with its assumptions
- confidence
- effort

An **add** suggestion is a brief, not an idea: proposed title and slug, primary
and secondary keywords, intent and format, an outline (what the top 10 cover
plus what they miss), the parent hub, the internal links it should receive,
and the evidence for each gate. The Content desk writes the page from it.

## The six shared analyses (the engine)

Build each once. Every playbook calls them.

| Analysis | Output | Built from |
|---|---|---|
| SERP anatomy | Page type of each top-10 result, dominant type, SERP features, AI Overview present and who it cites | SERP advanced + a page-type classifier |
| Intent label | informational / commercial / transactional / navigational per keyword and cluster | Labs search intent, checked against SERP anatomy |
| Clustering | Keyword groups by SERP overlap | SERP snapshots |
| Cluster-to-URL map | Which page owns, partly covers or competes for each cluster | GSC query × page, SERP overlap test |
| Competitor benchmark | Per cluster: topics most top pages cover (consensus), what only one or two cover (differentiators), typical length, media, schema, freshness | Content parsing of top 3–10, People Also Ask |
| Opportunity model | Expected extra clicks at a target position, with confidence | Volume, current position, the site's own CTR curve, SERP features |

The opportunity model must use the site's own CTR curve per position bucket,
split brand / non-brand and AI Overview present / absent. A generic curve
overpromises when an AI Overview is on the SERP.

## The playbooks

| Playbook | Typical prompt | Evidence | Outputs |
|---|---|---|---|
| Quick wins | "What should I optimize this month?" | Striking distance + CTR gap, sized by the opportunity model | edit |
| Page audit | "Improve this page" / "Rank this page for X" | The page's GSC queries, SERP anatomy, competitor benchmark for its main cluster | edit (add if the target needs a different page) |
| Cannibalization | "Are my pages competing?" | Query × page split scoring, owner choice | consolidate, differentiate, delete |
| Content gaps | "What should we write next?" | Topical map + competitor keyword and page gaps, through the edit-vs-add test and the gates | add, some edit |
| Competitor | "How do we beat competitor.com?" | Domain intersection, relevant pages, per-cluster benchmark | add, edit |
| Topic cluster | "Build out our X topic" | Cluster map for one topic: owned, weak, missing | add, edit, consolidate |
| Traffic drop | "Why did /pricing lose traffic?" | Decay diagnosis, SERP now vs then, competitor changes | edit, consolidate, technical flag |
| Refresh plan | "What should we update before Q4?" | Decay + seasonality from trends and historical volume | edit, ordered by date |
| AI visibility | "Why aren't we in AI Overviews?" | AI Overview presence and citations, LLM mentions | edit |

### Edit strategies (inside the edit playbooks)

- **Striking distance**: query × page at average position about 4–20 with
  meaningful impressions. Add or deepen the section that answers the query,
  align headings, hand internal links to the Site desk.
- **CTR gap**: CTR well below what the position should earn on the site's own
  curve. Rewrite title and meta; add structured data for an eligible rich result.
- **Decay**: clicks down more than ~20% against a comparable period, or three
  months of falling impressions, with no seasonal cause. Decay is a symptom.
  Diagnose first:

  | Pattern | Likely cause | Suggestion |
  |---|---|---|
  | Position falls, impressions fall | Competitors improved, or a new page type wins | Competitor gap + intent check, then edit |
  | Position steady, impressions fall | Demand fell | Usually no edit; retarget if demand moved to a new phrasing |
  | Position steady, CTR falls | A SERP feature or AI Overview now sits above | Snippet rewrite, feature capture, AI-citation edits |
  | Clicks move to another of our URLs | Cannibalization | Hand to the cannibalization playbook |
  | Page disappears | Indexing or canonical problem | Technical flag, not a content edit |

- **Intent / format mismatch**: our page type differs from the dominant top-10
  type. Restructure, or suggest a new page if the gap is fundamental.
- **Competitor content gap**: subtopics, entities or questions most top-10
  pages cover and ours lacks. Name the sections, FAQs, tables to add.
- **Query drift**: the page gets impressions for queries it never addresses.
  Add sections, or retitle to the broader head term.
- **SERP feature capture**: featured snippet, PAA or video on the SERP, we rank
  top 5 but don't hold it. Answer-first paragraph, list or table, schema.
- **Freshness**: top results are recent, our page has stale years, stats or
  product names.

### Add: the four tests

An add is justified only when all four hold:

1. **Demand** exists (volume or GSC impressions over the evidence floor).
2. **No existing page owns it.** This is the hardest gate, because failing it
   creates cannibalization. Edit-vs-add test: the nearest existing page is
   the one GSC already shows for the candidate or its cluster, else our
   domain's result in the candidate's SERP; SERP overlap decides. Compare the candidate's top 10 with the
   top 10 of that page's main queries. 3–4 shared URLs (~40%) means same
   intent → edit the existing page instead. Finer bands: 7–10 shared = review
   for merge, 4–6 = same cluster, 2–3 = weak.
3. **The SERP wants a page we don't have** (format / page type).
4. **The SERP is winnable** for this site: keyword difficulty, authority of the
   ranking domains and pages, and whether weak results (forums, thin pages,
   small sites) appear. Plus **business fit**: relevance to what the user sells,
   and GA4 value of similar pages.

Add candidates come from: competitor keyword gap, competitor page gap, topical
map coverage, hub completion, GSC-born demand (real impressions, best URL past
~20 and only mentions the topic), format split, emerging demand, templated
patterns.

### Cannibalization

Two URLs on one query is not cannibalization by itself. It is when they serve
the same intent and split visibility so neither wins.

- **Detect** from GSC query × page over two or more date ranges: several URLs
  with a real share of impressions and none concentrating them; URLs swapping
  positions with a small gap; a click-concentration score per query (HHI);
  high SERP overlap between the pages' own main queries.
- **Exclude**: branded queries, pages Google ranks side by side for different
  intents, a stable pair where one URL clearly dominates, queries with too few
  impressions.
- **Pick the owner** on non-brand clicks and position for the cluster,
  internal link score, GA4 conversions, and how well the page's format matches
  the SERP's winning type. Weigh non-brand data; brand clicks inflate strength.
- **Action for the others**:

  | Situation | Action | Suggestion must include |
  |---|---|---|
  | Same intent, loser has some unique content | Merge into owner, 301 | Sections to move, redirect map, links to repoint, sitemap removal |
  | Same intent, nothing unique, but links or traffic | 301 only | Redirect map, link updates |
  | Different intents, overlap on surface keywords | Differentiate | New title, H1 and focus per page; cross-links |
  | Loser has value elsewhere but competes here | De-optimize | Text to cut or reframe; link to owner |
  | Near-duplicates both needed (variants, filters) | Canonical to owner | Canonical target |
  | Thin, no traffic, no links | Delete (410) or noindex | Evidence of zero value, links to remove |

## Pipeline: draft → screen → review → rank

Same stages as the Site desk's structure suggestions.

**Screen gates** (cheap, deterministic where possible):

- **Relevance**: the cluster matters to the business.
- **Evidence floor**: minimum impressions or volume and data window before a
  suggestion can exist. Lower confidence when the anonymized-query share is high.
- **Duplication**: an add must fail the SERP overlap test against every
  existing page that GSC or the SERP ties to its cluster.
- **Conflict**: no two suggestions target one cluster with different URLs. An
  add and an edit on one cluster are merged, or one is dropped.
- **Protected pages**: pages the user marked off-limits, or pages that convert
  well (GA4), get light edits only. A rewrite for traffic can cost revenue.

**LLM reviewer** checks that the action follows from the cited numbers, the
change is specific, it matches the SERP's winning format, and the expected
impact states its assumptions. Treat claimed uplift from consolidation as a
hypothesis.

**Rank**: expected click gain × page value × confidence ÷ effort. Confidence
drops with thin data, SERP volatility, AI Overview presence and a high
anonymized share.

**Learn**: measure implemented suggestions in GSC at 4, 8 and 12 weeks against
their evidence snapshot, and re-tune the thresholds from the results.

## Facts about the data the code must respect

- **GSC anonymizes queries.** Often half or more of impressions are in the
  anonymized pool, and AI Mode queries almost all are. Page-level totals are
  reliable; query-level coverage is partial.
- **GSC position is an impression-weighted average.** Always compute at
  query × page level, never page level alone.
- **GSC shows only demand we already touch.** A query with zero impressions
  never appears. Add decisions need DataForSEO.
- **GSC data lands 2–3 days late.** Date windows must end before that.
- **Labs is fast, cheap and slightly stale; the live SERP is fresh and costly.**
  Use Labs for breadth and live SERP only on the shortlist we will suggest on.
- **Every threshold is a convention, not a Google rule** (position 4–20, 40%
  overlap, 20% decay). Keep them in one constants module, never inline, so the
  outcome loop can re-tune them.

## Data we do not have yet

The PDF assumes some inputs the codebase does not have. Each needs a decision
before the playbook that depends on it.

| Missing | Needed by | Note |
|---|---|---|
| Labs search intent, bulk keyword difficulty | Intent label, winnability | Facade has keyword overview; check what it returns before adding endpoints |
| Content parsing of competitor pages | Competitor benchmark, content gap, add outlines | New facade capability (OnPage content parsing) |
| Backlinks (referring domains, rank) | Winnability, owner choice | New facade capability; optional for v1 |
| Historical SERPs | SERP volatility, traffic drop | New facade capability; our own evidence snapshots cover part of it over time |
| Domain / page intersection | Competitor playbook | New facade capability |
| Business context: products, ICP, priority categories, brand terms, protected pages | Relevance gate, brand/non-brand split, protected-pages gate | Owner undecided — `sites`, `profile`, or `seo` |
| Change log (what was edited, when, why) | Outcome loop, no re-suggesting | Suggestion state + "marked done" date may be enough |
| Bing Webmaster Tools | Second view on anonymized queries | Out of scope for v1 |
| AI Overviews report (GSC UI only) | AI visibility | No API; manual CSV at most |

Page speed (CrUX / Lighthouse) is only a tie-breaker in edit diagnosis. The
facade has Lighthouse; do not build around it.

## Build order

1. **Cluster-to-URL map and SERP anatomy.** Every playbook depends on them.
2. **Quick wins, page audit, cannibalization.** GSC-heavy, cheapest data,
   clearest wins.
3. **Content gaps, competitor, topic cluster.** Need Labs data and the add gates.
4. **Traffic drop, refresh plan, AI visibility.** Need history and the outcome log.

For each step, follow the root `CLAUDE.md` order: agree scope → tables →
schema review → repository/service/API with integration tests → agree MCP
tools → app changes. Desk rules apply: no tool reads another desk's data;
bulk rows leave as a CSV path, never as tokens; analytical questions about the
data go to the Analytics desk.

## Open questions (settle before the schema step)

1. Are clusters rebuilt per run, or kept per site and refreshed incrementally?
2. Is the cluster-to-URL map stored, or computed per run from clusters, GSC and
   SERP snapshots?
3. Where does business context live, and who edits it (Website profile screen
   or this desk)?
4. What is the evidence floor per playbook (impressions, days of data)?
5. Which market (country, language) per site: `sites.country` only, or per run?
6. Does the router run as the desk's system prompt (the model picks a
   playbook) or as a server step that returns playbook + parameters?
7. What vendor spend ceiling per run, and what happens when credits run out
   mid-run?
