# Striking distance: the reachability ranking

Date: 2026-09-29. Status: stages 1–6 are implemented as the reach tool
(`api/src/seo/reach`), including the snapshot pre-check, `bulk_pages_summary`
strengths and live-vs-snapshot noise handling. The evidence view, the app crawl
of target pages and the LLM comparison step are still to build.

## 1. The question

For each search query where one of our pages already ranks, how far up can that
page realistically climb if we improve it?

Position alone misleads. A page at #7 under six strong, established pages is
stuck. A page at #20 under small blogs and thin pages can climb far. The
algorithm measures how hard each page above us is to pass, then walks up the
results page.

It predicts **positions**, not clicks. CTR prediction was considered and dropped:
per-query CTR varies too much, new sites have no curve, and even DataForSEO's own
curve varies 7–30% at position 1.

## 2. Principles

- **One formula for every result.** No special cases by site type (no "if Reddit
  then …", no forum or stale-page bonuses). Special cases become unmanageable.
- **Google's order beats our guess.** Our strength number is based on links.
  When the SERP order contradicts it, the order wins (see smoothing).
- **Better content can beat a stronger page, but only up to a point.** That point
  is the MARGIN constant.
- **Content signals are evidence, not weights.** No LLM content analysis.
  Word count, headings and dates are shown to the human, not fed to the formula,
  until our own data proves they predict rank.
- **Meelu suggests, the human decides.** Every number is shown with the data
  behind it.

## 3. Data sources

| Data | Source | Stored in | Cost (verified 2026-09-29) | Notes |
|---|---|---|---|---|
| Our query × page × device × day: clicks, impressions, position | GSC via the app | `site_search_daily` | free | device added 2026-09-29; values desktop / mobile / tablet |
| Keyword volume, KD, intent, core keyword, top-10 averages | Labs keyword_overview / ideas | `seo_keywords` | ~$0.012 per request + per keyword | `avg_backlinks_info` is means only; no min/max/median anywhere |
| Past SERPs with per-result `page_rank`, `main_domain_rank`, referring domains, `rank_changes` | Labs `historical_serps` | not yet (to add to `seo_serps`) | ~$0.00012 per snapshot | ~1 snapshot per 2 months; none for long-tail; may be a promo price |
| Live SERP | SERP API organic live advanced | `seo_serps` | $0.002 per 10 results; async AI Overview +$0.002 only when async | noisy between calls; desktop vs mobile differ a lot |
| Page and domain strength | Backlinks `bulk_pages_summary` (planned) / `bulk_ranks` (current) | `seo_pages`, `seo_domains` | $0.024 per request + $0.000036 per target, ≤1000 targets | pages summary returns page rank **and** main domain rank plus referring main domains, first_seen |
| Domain traffic | Labs bulk_traffic_estimation | `seo_domains` | ~$0.012 per request | organic etv and keyword count |
| Our actual Google rank per query | Labs ranked_keywords on our domain | not yet | ~$0.013 per 10 rows | Google rank + date + trend + `is_lost` |
| Competitor page content | app crawl | `seo_pages` content columns | free | DataForSEO OnPage was blocked by Forbes and served Zoho in German |

## 4. Pipeline

```
1 Candidates     GSC: query × page × device
2 Pre-check      latest historical snapshot → full math on the actual top list
3 Shortlist      top N by P(page 1) / P(top 3); demand shown alongside
4 Live SERP      current order for the shortlist, device from GSC
5 Strength       S per result, one strength source per query
6 Math           smooth → pass → reach → outputs
7 Evidence       numbers and content side by side for the human
```

### Stage 1: candidates (SQL, free)

From `site_search_daily` over a window ending 3 days before today (GSC lag):

- position per query × page = `sum(position·impressions) / sum(impressions)`
- keep 4 ≤ position ≤ 20 and impressions ≥ floor
- drop brand queries
- drop queries where another of our pages holds a real share of impressions
  (that is cannibalization, a different strategy)
- drop pages that are not indexable or are utility / legal pages
- **device** = the device with the most impressions for that query; our starting
  position `r` is the position on that device

Where available, our domain's ranked keywords give Google's actual rank with a
date. When it disagrees with the GSC average, prefer the newer, exact value, and
skip queries marked `is_lost`.

### Stage 2: pre-check (≈ free)

For each candidate, fetch the latest `historical_serps` snapshot (`date_from` set
so only the newest comes back). It lists every result with `page_rank` and
`main_domain_rank`, so we run the **same math as stage 6** on the actual list
instead of on averages.

Example, "best crm for small business": the top-10 average page rank is 161, but
the real list is 151, 265, 162, 183, 157, 240, **38**, 233, **52**, 131. The
average hides two weak pages at #7 and #9.

Rules:
- **Be optimistic.** A query wrongly kept costs one cheap live SERP; a query
  wrongly dropped is never seen again.
- **No snapshot (long tail) → keep**, marked "unchecked".
- `page_rank = 0` means "not in the vendor's link index", not "weak". It makes S
  low, which is acceptable here because smoothing and the live SERP correct it.

### Stage 3: shortlist

Take the top N by P(page 1) or P(top 3) from stage 2, plus unchecked queries in
order of GSC impressions, up to a hard per-run SERP cap. Show demand (volume or
impressions) beside each; do not multiply it in.

### Stage 4: live SERP

- device from stage 1
- depth: our position rounded up to the next 10, plus 10, capped at 30 (depth 20
  returns only 18–19 organic results)
- load the async AI Overview so citations are not silently empty
- use organic `rank_group` for positions, never `rank_absolute`
- forum blocks carry `domain: google.com`; parse the domain from `url`

### Stage 5: strength

```
S = w · page_rank + (1 − w) · domain_rank        w = 0.85
```

Both ranks are 0–1000. Our own page and domain go through the same lookup.

Use **one strength source per query**: the endpoints disagree slightly on the
same day (Forbes page 175 in bulk_ranks vs 167 in pages summary).

### Stage 6: the math

**6a. Smooth S down the list.** Where a page sits above a stronger one, Google has
already judged it stronger for this query. Make S non-increasing from #1 down
with pool-adjacent-violators:

```
blocks = [[S_1], [S_2], …, [S_{r−1}]]
while some block has mean < the mean of the block after it:
    merge the two blocks into one (its value = the mean of all its members)
S'_i = mean of the block that i belongs to
```

A Reddit post with few links above Forbes gets raised; Forbes sitting low gets
lowered. One outlier no longer blocks everything above it.

**6b. Pass chance for each result above us.**

```
pass_i = 1 / (1 + exp((S'_i − S_us − MARGIN) / SCALE))      MARGIN = 50, SCALE = 50
```

| gap S'_i − S_us | pass |
|---|---|
| −50 | 0.88 |
| 0 | 0.73 |
| 50 | 0.50 |
| 100 | 0.27 |
| 200 | 0.05 |

**6c. Reach.** We climb one result at a time, nearest first, and stop at the
first one we fail to pass. The passes are treated as independent.

```
R(r) = 1
R(k) = pass_k · R(k+1)                     k = r−1 … 1
P(end at k) = R(k) · (1 − pass_{k−1})      with pass_0 = 0
```

**6d. Outputs.**

| Output | Formula |
|---|---|
| Likely position | highest k with R(k) ≥ 0.5 |
| Expected position | Σ k · P(end at k) |
| Expected climb | r − expected position |
| P(page 1) | R(10) when r > 10 |
| P(top 3) | R(3) |

Sort by P(top 3) or P(page 1), not by raw climb: #20 → #15 is five places but
still page 2.

### Stage 7: evidence for the human

Per suggestion, for every result above us:
- S, the gap, the pass chance, and whether smoothing changed S
- page rank and site rank shown separately, labelled by quadrant:

| | weak pages | strong pages |
|---|---|---|
| big sites | beatable with a strong dedicated page | hard |
| small sites | easiest | niche specialists, hard-ish |

- referring root domains, ours vs theirs; `first_seen`
- publish/update date from the SERP `timestamp` or the page's JSON-LD
- app-crawled content side by side: main word count, H2/H3 lists, the subtopics
  their headings cover and ours don't, schema types
- forum post counts, AI Overview citations, `rank_changes` (new / up / down)
- our own rank history across snapshots

None of these change the score.

## 5. Worked example

We are at #6 with S_us = 74. The pages above:

| Pos | S | smoothed S' | pass |
|---|---|---|---|
| 1 | 120 | 177 | 0.26 |
| 2 | 110 | 177 | 0.26 |
| 3 | 300 | 177 | 0.26 |
| 4 | 100 | 100 | 0.62 |
| 5 | 90 | 90 | 0.66 |

| k | R(k) | P(end at k) |
|---|---|---|
| 6 | 1.00 | 0.34 |
| 5 | 0.66 | 0.25 |
| 4 | 0.41 | 0.30 |
| 3 | 0.11 | 0.08 |
| 2 | 0.03 | 0.02 |
| 1 | 0.007 | 0.007 |

Likely position #5; expected position 4.8; P(top 3) = 11%. Without smoothing,
the 300 at #3 would give R(3) = 0.01.

Real strengths with w = 0.85: Forbes page 175 / site 646 → S = 246; Fayedigital
page 4 / site 243 → S = 40. Against a site with page 20 / domain 200 (S = 47),
Forbes has a pass chance of 0.05 and Fayedigital 0.76.

## 6. Constants

| Constant | Value | Meaning | How to calibrate |
|---|---|---|---|
| w | 0.85 | page vs site weight | DataForSEO's own KD uses 0.9 page / 0.1 domain; fit on stored SERPs |
| MARGIN | 50 | authority deficit content can make up | outcome loop |
| SCALE | 50 | how fast pass chance falls with the gap | outcome loop |
| position band | 4–20 | candidate range | outcome loop |
| impression floor | tbd | minimum evidence | — |
| SERP cap per run | tbd | spend ceiling | — |

All constants live in one constants module, never inline.

## 7. Calibration

1. **From stored SERPs (no waiting).** For every pair of results in the same SERP,
   check whether the one with higher S sits higher. Pick the w that maximises
   agreement. The same data shows how often links disagree with Google's order.
2. **From outcomes (slow).** Measure implemented suggestions in GSC at 4, 8 and 12
   weeks against the predicted positions. Tune MARGIN and SCALE.
3. **Content terms, only if proven.** Regress (actual − predicted position) on a
   content signal across many query × page pairs. Add a term only if it shows a
   real effect.

## 8. Known limits

- S is links only. It does not see content, clicks or Google's taste for sites
  such as Reddit. Smoothing and the evidence cover part of this.
- One live SERP is a noisy snapshot: two calls a minute apart shared 1 of ~8
  domains; desktop and mobile shared 1 of 19 domains (possibly a proxy artefact).
- Historical snapshots come about every 2 months; some keyword data dates from
  2024; long-tail queries have no keyword data and no snapshots.
- Pass chances are assumed independent, and other pages are assumed to stay put.
- Our page rank changes only when links change, so content improvements show up
  through MARGIN, not S.

## 9. Decisions taken (2026-09-29)

1. **Pre-check from `historical_serps`.** Up to `precheck_limit` (default 100)
   eligible queries get the latest snapshot (looked back 120 days). The math runs
   on the snapshot's per-result ranks with our GSC position. Queries whose
   expected climb is under 0.5 places are skipped (`precheck_blocked`). The
   shortlist is: passing queries by expected climb, then queries with no snapshot
   by impressions, cut at `max_queries`. Snapshots are stored in `seo_serps` with
   `source = "history"` and their real `captured_at`, and are never used to
   answer a live SERP request.
2. **`bulk_pages_summary` replaces `bulk_ranks`** everywhere (one source). It takes
   domains and pages; the facade batches ≤1000 targets and ≤100 distinct domains
   per request. `seo_domains` and `seo_pages` gained `referring_main_domains`,
   `referring_main_domains_nofollow`, `spam_score`, `first_seen`; `seo_pages` also
   `main_domain_rank`.
3. **Noise.** For desktop queries with a snapshot, `serp_agreement` = overlap of the
   live and snapshot top-10 domains ÷ the shorter list. The pass curve widens for
   every result: `scale = 50 × (1 + (1 − agreement))`. Mobile queries are not
   compared (snapshots are desktop only) and keep scale 50. Both values are saved
   on the row.

Still open: movement terms (evidence only for now), the impression floor (20)
and SERP cap (25 per run) are first guesses.

## 10. Implementation map

Built:
- `api/src/seo/keywords`: `seo_keywords`, table-first lookup, tools
- `api/src/seo/competitors`: `seo_domains`, `seo_pages`, `seo_serps`, strength and
  SERP lookups, app content and app SERP ingest, daily purge
- `site_search_daily.device`; the app's GSC sync requests the `device` dimension
- `api/src/seo/reach`: the ranking tool
  - `reachability.py`: strength, smoothing, pass chance, climb (pure, unit-tested
    against the worked example)
  - `candidates.py`: stage 1 filters (band, impression floor, brand terms,
    cannibalised queries, device with most impressions)
  - `service.py`: SERPs for the top candidates by impressions (capped per run),
    one batched strength lookup for the whole run, saves the results
  - tables `seo_reach_queries` (one row per query: positions, strengths, likely
    and expected position, P(page 1), P(top 3), target count) and
    `seo_reach_targets` (one row per result above us: ranks, S, S', pass, reach,
    `is_target`)
  - REST `/api/v1/seo/reach/runs`, `/queries`, `/queries/{id}`; agent tool
    `seo_rank_reach` (desk `seo`, writes)

To build:
- our domain's ranked keywords as a second position source
- indexability / page-type filter in stage 1
- app crawl of `is_target` pages, and the generic LLM comparison tool
  (our page vs pages to beat → structured suggestion; body trimmed between
  paragraphs and sections, never whole sections dropped)
