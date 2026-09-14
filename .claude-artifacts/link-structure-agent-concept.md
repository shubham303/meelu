# Link Structure Agent — Concept Notes

Date: 2026-09-07
Status: conceptual discussion, no code reviewed

## What an SEO expert is actually trying to achieve

When someone says "fix the link structure," they are really pursuing four distinct
goals, and it helps to keep them separate because each one generates different
questions:

1. **Discoverability** — every page that should rank must be reachable by
   crawlers, ideally within 3–4 clicks of the homepage. Pages that exist but
   aren't linked (orphans) or are buried 6 clicks deep effectively don't exist
   to Google.

2. **Authority distribution** — internal links are how a site tells Google which
   pages matter. The homepage has the most authority; every link passes some of
   it along. The expert wants the *money pages* (the ones targeting valuable
   keywords or driving conversions) to receive a disproportionate share, and
   doesn't want authority bleeding into tag archives, login pages, and
   boilerplate.

3. **Topical signaling** — links plus their anchor text tell Google what a page
   is *about* and which pages belong *together*. A "pillar and cluster"
   structure (a hub page linking to all its subtopic pages, and them linking
   back) is the expert's target shape. Generic anchors like "read more" waste
   this signal entirely.

4. **Hygiene** — no links to 404s, no chains of redirects, no links pointing at
   pages that are noindexed or canonicalized elsewhere. Each of these silently
   discards the authority the link was supposed to pass.

## The n questions, roughly in order of how deterministic they are

### Tier 1 — pure graph math, answer is a fact

1. Which pages are orphaned (in the sitemap or getting traffic, but zero
   internal inlinks)?
2. Which pages are too deep (click depth > 3–4 from home)?
3. Which internal links are broken (404/410)?
4. Which links point at redirects, especially redirect chains?
5. Which links point at noindexed or canonicalized-away pages?

### Tier 2 — graph math plus one importance signal

6. Which of my *important* pages are under-linked? (Needs a definition of
   "important": Search Console impressions, GA traffic, or simply the user
   declaring priority pages.)
7. Where is authority leaking — which low-value pages (tags, legal, pagination)
   soak up sitewide links?
8. Is my anchor text working — which pages are only ever linked with generic
   anchors, and do any two different pages share the same keyword anchor (a
   cannibalization smell)?

### Tier 3 — needs content understanding and judgment

9. Where are my missed link opportunities — which existing pages *mention* the
   topic of page X but don't link to it?
10. Do my topic clusters actually interlink — does the pillar link to every
    cluster page and vice versa?
11. Which pages compete with each other for the same query, and should linking
    consolidate toward one of them?

## Which few to solve first

The trap to avoid is jumping to tier 3 because it's the impressive one. The
reasoning for a different order:

**Start with tier 1 in full.** These five are computable from the crawl graph
alone, the answer is objectively correct, and — critically — each finding
converts directly into a copy-paste-able fix ("this link on page A points to a
404; change it to B" / "these 12 pages have no inlinks; here are the 3 most
topically related pages to link from"). An SEO consultant charges real money for
exactly this audit, and most of their time goes into assembling it, not into
judgment. Solving *only* tier 1, completely and with fix briefs attached, is
already a product someone would use weekly.

**Then pick exactly one tier-2 question: #6, under-linked important pages.**
This is the first question that connects link structure to *outcomes* — "your
top-converting page has 2 internal links; your privacy policy has 400." It's the
moment the tool stops being a linter and starts being a strategist, and it only
needs one extra input (a traffic signal or a user-declared priority list), not
full content understanding.

**Then #9, mention-without-link, as the first tier-3 feature.** It's the
highest-leverage suggestion in all of internal linking — "your post about
grinder burrs mentions 'burr alignment' four times and never links to your
burr-alignment guide" — and it decomposes cleanly: text search finds candidate
mentions deterministically, and a judgment layer decides which candidates are
genuinely worth a link and with what anchor. The candidates land as *proposals*
for review rather than auto-applied changes, which keeps the tool honest about
not over-automating.

## What deliberately stays out, and why that's fine

Full cluster architecture design (#10, #11) and any "restructure your whole nav"
ambition should wait. Those require understanding the site's keyword strategy,
and a wrong confident answer there is worse than no answer. The expert's own
workflow mirrors this: they fix hygiene first, redistribute authority second,
and only redesign architecture when the basics are clean — so a tool that covers
tiers 1 and part of 2 matches how the work is actually sequenced, not a cut-down
version of it.

The other useful lens: every feature above ends in the same deliverable shape —
a finding, the evidence, and a concrete fix instruction. If each question added
produces that same shape, adding question types over time is additive rather
than a redesign, which is exactly the intended "one by one" growth path.

## Open next step

Map which of these questions the current crawl data can already answer versus
what new signals (Search Console, declared priority pages) each tier would
require.
