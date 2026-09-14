# PRD — Site Structure (internal link structure fix)

This is a feature of the Site desk. The technical design is in
`site-structure-rfc.md`. This document replaces the draft
`internal-linking-agent-prd-1.pdf`. Three reviews shaped this version: an
SEO expert review with web research, a technical review against the
codebase, and an adversarial product review.

## 1. Why fix internal links at all

Internal links are the one structural tool that a site owner controls
fully, for free, at any time. The feature exists to produce four outcomes.
They are listed from most certain to least certain:

1. Indexation and discovery. A page that Google cannot reach earns
   nothing. Orphan pages (pages with no incoming links), deep pages, and
   broken link chains block discovery. Fixes here are deterministic and
   always correct. Google's own staff call discovery the main job of
   internal links.
2. Funnel routing. A visitor who reads about a problem must find the page
   that solves it one click away. Links from informational pages to money
   pages (pages that earn revenue) turn blog traffic into business value.
   This works even if rankings never move.
3. Authority routing. Link equity earned by informational pages flows to
   pages that convert. This effect is real but modest. Google has said in
   public that links now count less as a ranking signal. We present
   ranking movement as a bonus, not a promise.
4. Topical clarity. Coherent clusters tell Google which page owns which
   topic. A cluster is a group of pages on one subject. Good clusters also
   stop our own suggestions from making pages compete with each other.

Every building block and strategy recipe must serve one of these four
outcomes. "Increase the total number of internal links" is not a goal.

### Design rules

Strategies are prompts, not code. The strategies are endless. Examples:
analyze the link structure around money pages, rescue orphan pages, and
trim pages with too many outgoing links. We do not code them. The code
ships building blocks: precomputed data, retrieval tools, check tools, a
loop harness for per-item LLM work, and one suggestion queue. The agent
combines these from a prompt. A new strategy costs a guide recipe, not a
release.

Cheap comes before expensive. The order is: rules, then SQL and
statistics, then classical machine learning, then small local models, then
the LLM. The LLM only judges a short list. It never searches the whole
site. It answers two questions: is this link natural, and which existing
phrase is the anchor.

Similarity is not relatedness. A dog-care article that never mentions food
will never sit near a dog-food product page in embedding space. Yet that
link is the most valuable kind. Content similarity is one signal among
several. The main signals for links from informational pages to money
pages are intent signals. These are the keywords of the target page
searched against source paragraphs, and shared queries in Search Console
data.

Whole-page embeddings are the wrong unit. A link needs a placement, which
means a paragraph. Matching is asymmetric. We embed a short intent summary
of the target page and search it against source-page chunks. A chunk is
one embedded passage of a page. This gives relevance and the exact
insertion point together.

The graph must be the canonical graph. We compute defects and authority
only over followable links to canonical, indexable pages. Parameter URLs,
facet URLs, redirect targets, noindexed pages, and nofollow links are
excluded or flagged. They are never counted in silence. To count them is
the most common way that this math goes wrong, above all on ecommerce
sites.

Suggestions are a queue, not a report. The backlog is persistent. Each
source page has a fixed link budget. Rejections are remembered. Review is
grouped. One note on tone: Google has said that there is no penalty for
over-optimized internal links. We gate on naturalness for precision and
user trust, not to avoid a penalty. The real costs of bad links are
ignored links, diluted equity, and a user who stops trusting the tool.

## 2. Goals

1. Detect structural defects and show them in one Structure view. The
   defects are: orphan pages, pages missing from the sitemap, broken
   internal links, links to redirects, deep pages that matter, missing
   breadcrumbs, and parameter or facet URL traps. Depth flags apply to
   money pages and valuable pages only, not to the whole catalog.
2. Classify the role of every page as money, informational, utility, or
   leaf. A rule cascade does most of the work. The user confirms money
   pages once, and confirmed labels are locked. An archetype preset
   (ecommerce, blog, SaaS, or local) sets role priors, budgets, and which
   defect classes are loud.
3. Compute blended authority per page. This is internal PageRank over the
   canonical graph, with a teleport vector weighted by impressions. A
   second editorial variant weights each link by its position on the page.
   Body counts more than breadcrumb, breadcrumb more than nav, and nav
   more than footer. The user sees only relative deficit, for example
   "high impressions, few editorial inlinks". We never show an absolute
   score for the user to chase.
4. Ship the building blocks that link strategies are made of. These are: a
   placement retrieval tool (the intent of the target searched against
   source paragraphs), a guarded suggestion-create path with hard
   eligibility and budget checks built in, and an item-loop harness for
   per-item LLM work. The agent combines these from a strategy prompt.
   Query-overlap and cluster-integrity signals arrive as later building
   blocks.
5. Keep the two-step constrained LLM review, executed through the loop
   harness. Step one is a yes-or-no verdict. Step two selects the anchor.
   The anchor must be a verbatim phrase from the source chunk, and the
   server checks this. The prompt carries the existing anchor texts of the
   target, so we never propose the same exact-match anchor across the
   whole site.
6. Maintain a suggestion backlog that the user reviews at a fixed cadence.
   The queue is grouped by target page. The actions are: accept, reject
   with a reason, snooze, and never-link-this-pair. After the user accepts
   a suggestion, the next crawl makes sure that the link appeared. The
   check is a normalized body-region match on the page pair.

## 3. Non-goals

- We do not write or rewrite page content. We do not apply links to the
  live site. The user applies changes in their CMS, and we confirm on
  recrawl.
- External backlinks. Log-file crawl-budget analysis.
- Links into utility pages or authority dead ends.
- Symmetric links between pages that compete for the same queries. True
  cannibalization pairs are excluded from suggestions and reported
  separately. A cannibalization pair is two pages that rank top-10 for the
  same query with the same intent.
- Live SERP scraping as a pipeline stage. Metered spot checks come later.
- Link removal suggestions in version 1. We report them only, because
  removals carry more risk.

## 4. The problems, one at a time

### P0 — The crawler forgets where links live (prerequisite)

Today `outLinks` is `{url, anchor, rel}`. It records no nav, body, or
footer position, no ordinal, and no surrounding sentence. The crawler
discards the raw HTML, so the server can never recover this. Region
detection uses semantic HTML tags plus class, id, and role heuristics,
because many themes have no `<nav>` element. We accept a stated error
rate. Version 1.5 adds detection of widgets that repeat across templates,
for example Related Posts blocks inside `<article>`. This crawler change
comes first.

### P1 — Structure health (deterministic, mostly assembly)

This stage builds a stored canonical edge table, splits editorial links
from template links, runs weighted and blended PageRank, and ships one
Structure screen. It adds defect classes beyond the existing technical-seo
rules: a parameter and facet trap report, an internal nofollow report,
missing breadcrumbs, and pagination as its own link class. We recommend
BreadcrumbList markup because it is one of the cheapest site-wide wins.
Pagination links are neither editorial nor template, and depth is not
computed through them. The deterministic `nav_gap` check finds a spoke
page whose only link to its hub is a template link. It ships here as a
health issue, not through the LLM queue. This stage delivers value on day
one, needs no machine learning, and works with zero history.

### P2 — Page roles

Role gates everything downstream. The rule cascade reads schema.org types,
template markers, URL patterns, and graph signals, tuned by the archetype
preset. It labels most pages with high confidence. On small and medium
sites, the user resolves the ambiguous remainder in the confirm flow. LLM
template labeling is deferred to version 1.5. That method groups ambiguous
pages by URL pattern and DOM shape, labels 2 or 3 examples per template,
and propagates a label only when the examples agree. It earns its cost at
about 10,000 pages, not before. Money-page confirmation is a first-run
step, and user labels stay locked forever.

### P3 — Opportunity building blocks

The agent runs opportunity finding as a strategy. So what ships here are
signal sources and one guarded write path, in this order:

| Ship | Building block | Enables |
|---|---|---|
| v1 | Placement retrieval tool: the target intent summary (title, H1, lead, owned keywords) searched against informational source chunks | The dog-food and dog-care case. The engine for info-to-money strategies |
| v1.1 | Query overlap from Search Console, weighted by impressions, one direction only (lower to higher authority, or info to money). Same-query top-10 overlap is excluded as cannibalization | Relatedness in Google's own model, invisible to embeddings |
| v1.1 | Chunk similarity: source chunk against target summary. Cross-cluster hits are marked bridge links | Contextual siblings |
| v1.5 | Cluster integrity: missing spoke-to-hub, hub-to-spoke, and sibling links from the taxonomy | The highest-precision structural links. Needs the P5 taxonomy |

The precision defense is that eligibility lives in the guarded
suggestion-create path, not in strategy prompts. So no prompt can forget
it. The rules:

- The target role must be money or valuable informational.
- The edge must be absent. This includes accepted suggestions that no
  crawl confirmed yet.
- The source must have budget left.
- A chunk must have at least about 40 words. It must not come from a list
  or a table.
- A chunk that matches many targets is a hub sentence, not many
  placements. So each source chunk has a candidate cap.
- Retrieval requires loose lexical co-occurrence: some token family of the
  target keywords must appear near the chunk. A page that shares zero
  vocabulary with the target fails the human-editor test anyway.

Scoring is a hand-weighted blend, recorded per suggestion. The weights
renormalize over the signals that exist for this site. With no Search
Console connection there are no overlap or deficit terms, and results are
labeled "similarity-only until Search Console is connected".

The link budget is a guardrail, not a KPI. The soft ceiling is about one
contextual link per 125 words, with per-role defaults from the archetype.
The limit is one suggestion per paragraph. The budget counts accepted
suggestions that are still pending. No expert consensus supports any exact
density number, so we do not report budget compliance as a success metric.

### P4 — LLM review and anchor (two constrained steps)

The review runs through the item-loop harness. This is an app-local job
that walks the queued candidates one at a time with zero-tool calls. So it
works with small local models and never enters the context of the main
agent:

1. Verdict. One call per candidate, schema-constrained, yes or no plus one
   reason: "would a careful human editor link to [target purpose] from
   this paragraph?" The prompt includes the existing anchor distribution
   of the target.
2. Anchor selection, for approvals only. The model picks a verbatim
   contiguous phrase from the chunk. The server makes sure that the phrase
   is a substring. This turns anchors from a trust problem into a
   checkable one, and it gives the insertion point for free. If the exact
   anchor already points at a different page anywhere on the site, the
   suggestion is rejected. Partial-match phrasing is preferred.

We log per-model approval rates and schema-failure rates from day one. A
model that approves more than 90% of candidates is rubber-stamping, and
its approvals are flagged as untrusted.

### P5 — Taxonomy (v1.5)

The tree comes from what the site declares, in priority order:
BreadcrumbList, then nav, then URL segments. Pages that the tree cannot
place are assigned to the nearest category centroid by embedding. The
acceptance threshold is calibrated per site from the similarity
distribution, never an absolute cosine value. HDBSCAN runs only to suggest
new categories from the residue. Nodes with low internal similarity, for
example `/sale/`, are flagged virtual. Hubs are detected from editorial
link degree. Centroid assignments are visibly provisional in the UI, with
one-click reassign, and user corrections lock. Taxonomy adjacency enters
scoring only as a small tie-breaker. It never penalizes an info-to-money
candidate from keyword retrieval, because bridge links are the point.
Taxonomy is deferred to version 1.5 because its consumers are version 1.5,
and a Tree screen proves nothing about link value.

### P6 — Backlog, review UI, measurement

The queue is grouped by target page, so the context of one target serves
all of its candidates. The actions are: accept, reject with an enum reason
(wrong target, bad placement, or bad anchor, which are three different
bugs to count), snooze (resurfaces after a chosen period), and
never-link-this-pair (the only permanent rejection). An ordinary rejection
is scoped to the source content hash, so a rewritten page can surface the
edge again. Batch-accept is offered per strategy once its acceptance rate
is high. Those decisions also train the later GBDT scorer.

Applied verification: a body-region edge from source to target, after URL
normalization to page identity. A different anchor or paragraph still
counts as applied. A nav or widget edge never does. An accepted suggestion
becomes stale when the source paragraph disappears, or when the edge has
not appeared after 2 crawls.

## 5. Users and surfaces

- Dashboard and App, under Site → Structure: Health (defects, trap
  reports, breadcrumb recommendation), Roles (money-page confirmation),
  Suggestions (the target-grouped queue), and Deficit (impressions against
  editorial inlinks). The Tree tab arrives with version 1.5.
- The agent on the Site desk is the strategy executor. It has: direct SQL
  reads over the new tables, the placement retrieval tool, the guarded
  suggestion-create tool, a tool to start item-loop jobs, a download tool
  that exports edges, suggestions, defects, or deficit data as CSV for the
  Analytics desk, and write tools to review suggestions and lock roles.
  Strategy recipes live in the desk guide, not in code.
- Local jobs in the app: the crawl with extended extraction, and the
  item-loop job runner. The runner executes per-item LLM work: review
  verdicts, anchor picks, issue triage, and page labels.

## 6. Success metrics

Leading metrics, cheap and available from the queue and the loop-job
counters:

- Acceptance rate per strategy and per score decile. This validates the
  score blend.
- LLM approval rate (the rubber-stamp detector) and schema-failure rate.
- Reject-reason distribution. Queue drain rate and time to review, which
  detect fatigue.
- Share of strategy executions that produce at least K approved
  suggestions, which detects starvation.

Targets:

| KPI | Metric |
|---|---|
| Structural health | Orphans, missing-sitemap pages, and broken internal links trend to zero |
| Suggestion precision | At least 60% of llm_approved suggestions accepted by the human. Volume is per strategy, not per run. Strategy runs are agent-driven, so no fixed per-run floor is promised |
| Adoption | Share of accepted suggestions confirmed applied within 2 crawls |
| Money-page routing | Count of applied info-to-money body links. Referral traffic to money pages from linked sources |
| Business, lagging and directional | Search Console clicks and position on money pages 4 to 12 weeks after application, reported with its confounds named |

## 7. Open questions

1. Money-page confirmation: a blocking first-run step, or run on rule
   output with a "confirm to improve" nudge? Recommended: blocking. It is
   one screen, and every downstream number depends on it.
2. Archetype preset: auto-detect from schema and product signals with a
   user override, or ask at setup?
3. Cannibalization report: its own tab under Structure, or a feed into
   `seo_findings` on the SEO desk with a cross-link? Desk isolation makes
   the second option harder.
4. Pages with no Search Console data: show an explicit "too new, no search
   data" state (recommended), so a zero deficit does not read as "fine".

## 8. Phasing

- v0 — P0 crawler extraction. The canonical edge table. Editorial,
  weighted, and blended PageRank. The Health tab with nav_gap, traps, and
  breadcrumbs.
- v1 — Roles by rules plus user confirmation. The target-grouped queue
  with the full state model and the guarded create path. The placement
  retrieval tool. The item-loop job with the two-step LLM review schemas.
  The deficit view. The agent tools, the scope, and the first strategy
  recipes in the guide. One retrieval signal, the whole machinery.
- v1.1 — The query-overlap and chunk-similarity signal sources
  (directional, cannibalization excluded), and any loop schemas that the
  new strategies need.
- v1.5 — Taxonomy, the Tree tab, and the cluster-integrity signal. LLM
  template labeling for roles (a loop schema, not a new job type).
  Template-widget edge detection. A GBDT scorer trained on acceptance
  data. Metered live-SERP spot checks. Removal suggestions.
- Later — Multi-language trees, drift detection, re-score cadence tuning.
