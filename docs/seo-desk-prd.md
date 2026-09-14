# PRD — SEO Desk

This is a greenfield design. It ignores the current `api/src/seo`
implementation on purpose. The technical design is in `seo-desk-rfc.md`.
Three reviews shaped this version: an SEO expert review with web research,
a technical review, and an adversarial product review.

## 1. What we truly want from purchased SEO data

The user does not want SEO data. They want four recurring decisions made
for them. Arithmetic over two sources answers most of each decision. The
first source is their own performance truth: Search Console and Analytics
data, already ingested, free. The second is purchased market truth from
DataForSEO.

1. **What must I write or update next?** This needs demand (volume and
   intent), what already ranks, what we already earn, what it costs to win,
   and what a win is worth.
2. **What is broken or decaying?** This covers striking-distance pages,
   cannibalization, decay, lost SERP features, lost AI-overview citations,
   and the defining pattern of 2025 and later: visibility without clicks.
3. **Who beats me, where, and why?** This covers true SERP competitors,
   keyword gaps, share of voice per topic, and per-SERP link deficits.
4. **Is it working?** This covers the visibility trend, movements that are
   signal and not noise, and completed actions with their measured effect.

The unit of output is an action, not a report. An action names a target,
what to do, the rationale with numbers, the expected result, the effort,
and a confidence grade. The documented churn mode of this product category
is data without prioritization. The queue's credibility is the product.
Five junk actions in week one, and the acceptance metric never recovers.

### Design rules

- **Never buy what Search Console gives free.** Search Console is the fact
  table. We buy from DataForSEO only where Search Console is blind: search
  volume, difficulty and intent, keywords we do not rank for, competitor
  visibility, SERP composition and AI-overview citations, backlinks, and
  deep history.
- **Respect the lossiness of Search Console.** Its "position" is an average
  over query variants, countries, devices, and URLs. Detectors that read it
  apply gates: branded queries are separated (they pollute every
  curve-based signal), high-variance rows are marked low confidence, data
  is filtered to the primary market's country, and new pages are excluded.
- **Purchased data is inventory with a ledger.** Every vendor call is
  budgeted, logged, and cached with per-endpoint lifetimes. The log also
  shows what caching saved. AI-overview capture is priced as its own line,
  because it roughly doubles the cost per SERP. Labs endpoints are cheap
  per task but priced per returned row, so every pull carries an explicit
  row limit, and the estimator models rows. Labs is a database that
  refreshes about monthly. We never diff Labs data at a faster cadence.
  SERP checks are the real cost multiplier: keyword count times frequency
  times market times device. The default is weekly checks, standard queue,
  depth 10, on a curated set. Instead of a permanent daily tier, a
  temporary watch mode runs daily checks on chosen keywords for N days and
  then expires. Adding a market or device shows "this adds about $X per
  month" before the row exists.
- **Signals are arithmetic. Every emission carries confidence. Low
  confidence degrades to silence or `investigate`, never to a scored
  action.** The LLM does only what formulas cannot: business-fit judgment
  against the user's stated context, intent labels at the margins, and the
  one-sentence "so what".
- **CTR curves are calibrated, not copied.** A CTR curve maps a ranking
  position to an expected click-through rate. Published curves are stale.
  The curve is flattening, and position-1 CTR fell by about a third in
  2025. AI-overview effects also vary by intent. Per-site calibration from
  the user's own Search Console data ships in v0. It is cheap SQL over
  data we already have, and every third detector depends on curve(pos).
  Published curves serve only as the cold-start prior.
- **Bulk research leaves as CSV paths** for the Analytics desk. Normalized
  tables store only what the product reads back continuously.
- **The user's knowledge is first-class data.** Desk memory holds
  structured fields: brand terms, product lines, priorities, a competitor
  allow and deny list, fit rules, and freeform overflow. The chat agent
  captures it, and scoring and every mission read it.

## 2. Goals

1. **Keyword intelligence.** Tracked keywords carry monthly volume,
   difficulty, intent, and SERP-feature dimensions, plus an `is_branded`
   flag. The first tracked set is seeded from top-impression Search Console
   queries, confirmed by the user, at zero vendor cost. Clusters come from
   SERP overlap: 4 or more shared top-10 URLs map keywords to the same
   page, and exactly 3 is a review band. Each cluster maps to one page.
   Cannibalization is detected from Search Console data.
2. **The opportunity engine.** A ranked queue from the signal battery in
   §4. Candidates are deduped within and across runs, capped per signal
   type, and filtered for business fit. Every action carries evidence
   numbers and a confidence grade. Expected results are tiers (small,
   medium, large) with ranges in the evidence. We never show bare click
   promises until calibration matures.
3. **Competitor intelligence.** True competitors come from SERP overlap on
   our tracked set. Share of voice is computed per cluster, with
   per-competitor deltas. The keyword gap runs only against competitors the
   user confirmed. It is capped per cluster and bounded to known topics.
   The rest stays in CSV for missions. Per-SERP link difficulty compares
   referring main domains and dofollow ratio against the current top 10.
   It is a gate ("links are or are not the bottleneck"), not a precise
   target.
4. **Rank and SERP reality.** Weekly snapshots record position, SERP
   features, AI-overview presence, and the cited domains. A feature or
   citation change must persist across two snapshots before it produces an
   action. Priority keywords get a next-day confirming check. Alerts are
   gated by a volatility index. When the whole ecosystem moves, the user
   gets one informational line. Daily jitter never surfaces.
5. **AI visibility.** AI-overview presence and citation tracking rides
   along on the rank checks, priced honestly in the ledger. A lost citation
   enters the queue as `investigate`. The click impact of being cited is
   treated as a measured hypothesis, not a promised doubling. Tracking of
   brand mentions inside AI chat products is deferred until it can drive
   actions instead of dashboards.
6. **Backlink reality.** Monthly summary plus new-and-lost series for us
   and confirmed competitors. Link-gap lists per opportunity. No domain
   authority as a KPI.
7. **The action queue.** States: proposed, then accepted, rejected with a
   reason, snoozed, done, and measured. Rejection memory is scoped per
   action kind. A target inside an open measurement window, or within the
   signal's lag horizon of about 8 weeks, is not re-emitted. Each signal
   type has a per-run cap.
8. **Honest measurement.** A done action gets a measurement window. The
   effect is computed as difference-in-differences: the target's change
   minus the change of a control set of non-actioned peers. A volatility
   spike inside the window stamps the result. The report leads with
   completed actions and their controlled effect. No Results screen ships
   before this correction exists.
9. **Agentic capability.** The desk agent, and the app-wide chat agent
   scoped to this desk, can answer any question by SQL, export any slice as
   CSV to the Analytics desk, and run missions. A mission is a user
   instruction executed by the agent under an approved budget cap. The cap
   is real: per-endpoint call ceilings and turn bounds enforce it. A
   user-set auto-approve floor (default about $0.25) lets trivial pulls run
   without ceremony. The agent writes back tracked keywords, actions, and
   memory.

## 3. Non-goals

- Content generation (the Content desk). Technical crawling (the Site
  desk). The DataForSEO OnPage, Lighthouse, Content Generation, Merchant,
  and Business Data products.
- Disavow and toxic-link workflows. Domain-authority KPIs.
- Vendor spend outside the approved caps and the auto-approve floor.
- Numeric traffic promises. Uncontrolled before-and-after ROI claims.

## 4. The signal battery (deterministic; every emission carries confidence)

| Signal | Rule, with the review-driven gates | Action |
|---|---|---|
| striking_distance | Search Console 28 days, position 4.9 to 15.1, impressions at or above a site-relative floor, CTR below the calibrated curve times 0.6. Unbranded only. Primary-market country. Dispersion-gated. SERP-feature aware: below-curve because an AI overview or PAA box sits above is not a weak snippet | update |
| ctr_gap | `(curve(target) − curve(now)) × volume` on calibrated curves that condition on intent and AI-overview state. Runs on tracked keywords with snapshot positions | update / links |
| visibility_no_clicks | Impressions up, clicks flat or down, position stable, and an AI overview appeared. The AI-overview-era pattern gets its own detector and produces citable-structure actions. It is never mixed with decay | update (AIO) |
| decay | Clicks down, after position stability is ruled out first (a stable position with falling clicks is serp_shift, not decay). The changepoint test runs on the year-over-year ratio series, because a seasonal decline holds the ratio flat. Pages under 15 months old are skipped and the UI says so. Seasonal amplitude from the purchased monthly volume series suppresses false hits | update (refresh) |
| cannibalization | Two or more URLs, an impression floor for each, no URL above 70% of impressions, positions crossed, and a same-intent check, because Google splitting a query by intent is not cannibalization. Three or more queries showing the split produce `consolidate`. Fewer produce `investigate`. Rejection memory is scoped to the page pair | consolidate / investigate |
| serp_shift | Snapshot diffs that persist across 2 snapshots. The priority tier gets a next-day confirming check. A lost citation produces `investigate` | update / investigate |
| keyword_gap | Confirmed competitors only. The competitor is top-10 and we are absent. Difficulty is at or below the site ceiling and volume is at or above the floor. The keyword must sit inside an existing cluster or a user-named topic. Top N per run | create |
| link_deficit | Our referring main domains against the median of the top 10. A gap of 30 or less produces a links action. A larger gap lowers the expected tier of other actions on the page | links |
| rank_alert | A move of 5 or more positions across 2 or more consecutive snapshots, gated by the volatility index | investigate |

The measurement layer on top: share of voice per cluster on calibrated
curves, the visibility trend, and seasonal timing hints on create-actions
from the monthly volume series.

## 5. The LLM filter and missions

**The filter** runs in the app harness, schema-constrained, on a short
list only. Deterministic dedupe runs before the model: candidates with the
same target merge into one multi-signal action. The model scores business
fit from 0 to 3 with an anchored rubric. A 0 contradicts a stated
exclusion. A 3 matches a stated priority. The model reads only the
structured memory fields: fit rules, product lines, and the deny list.
When memory is empty or thin, the gate is skipped. Actions then ship with
`fit: unscored`, and a first-run prompt asks the user to teach the desk. A
judgment call with no judgment input is noise. Each run has distribution
guards: more than 90% scored 2 or higher, or more than 70% rejected, flags
the run, and the queue falls back to deterministic order.

**Missions.** A user instruction becomes a mission row with a budget cap
from a template: research about $2, competitive about $1, diagnostic about
$0.25. The user approves the cap, or the auto-approve floor covers it.
The desk-scoped harness session is bounded by the cap, by per-endpoint call
ceilings, and by a turn limit. Artifacts (CSVs), a summary, and writes land
on the row. One canned setup mission with a fixed plan and fixed cost ships
early: "tell me about your business, get a keyword universe and a proposed
tracked set". It is the cold-start path for sites without Search Console
history.

## 6. Cold start (explicit, because early users are cold by definition)

- Search Console connected, nothing else: the v0 detectors work on day one.
  Tracked keywords are auto-seeded from top-impression queries. Snapshots
  begin after confirmation. serp_shift and ctr_gap activate at the second
  snapshot, and the UI says so.
- No Search Console: the first-run screen is the setup mission, and the
  Search Console connection is the loudest nudge. Each detector displays
  its minimum data requirement, for example "decay activates after 12
  months of Search Console data". The user never sees an unexplained empty
  queue.
- Empty memory: the fit gate is skipped, and the first actions ship
  unscored.

## 7. Success metrics

Leading: acceptance rate per signal type and per score decile, the share of
accepted actions completed, vendor cost per accepted action, filter
distribution health, alert precision, and queue drain rate.
Outcome: share of voice per priority cluster, the controlled
(difference-in-differences) click delta on actioned pages, and AI-overview
citations on tracked keywords.
Guardrails: spend within caps, zero purchases outside the approval and
auto-approve rules, and no numeric promise before calibration matures.

## 8. Open questions

1. The tracked-keyword ceiling: a default of 300 to 500 with visible cost
   math. Confirm.
2. Brand-term seeding: from the domain name with user confirmation at
   setup, or an LLM proposal from Search Console queries? Recommended:
   both. Propose, then confirm.
3. Does `investigate` output deserve its own lane, or does it share the
   queue? Recommended: the same queue, a distinct visual class, no score.
4. The auto-approve floor default of $0.25: confirm, and decide whether it
   applies to scheduled overage or only to missions. Recommended: missions
   only.

## 9. Phasing (re-cut after review: v0 spends nothing)

- **v0 — zero vendor spend, proves the thesis.** Brand classification.
  Per-site CTR calibration. The striking_distance, decay,
  visibility_no_clicks, and cannibalization detectors over existing Search
  Console tables. Dedupe, the fit filter with the unscored fallback, the
  action queue, the Opportunities screen, desk memory, and chat capture.
  This tests the risky hypotheses (do users accept actions, does the
  filter help) before any billing code exists.
- **v1** — The vendor layer, ledger, budgets, and the credential move.
  Tracked keywords seeded from Search Console, plus monthly dimensions.
  Weekly snapshots with AI-overview capture. The ctr_gap and serp_shift
  detectors with persistence gates. The canned setup mission.
- **v1.1** — Clustering and share of voice. Confirmed competitors and the
  capped keyword gap. Backlinks and link_deficit.
- **v1.5** — General missions with caps, ceilings, and auto-approve. Rank
  alerts and the volatility line. Results with difference-in-differences
  measurement. Watch mode. A recalibration cadence for the curves.
- **Later** — LLM mention tracking, only when it drives actions. The
  multi-market UI. Historical Labs backfills. A GBDT action scorer trained
  on acceptance data.
