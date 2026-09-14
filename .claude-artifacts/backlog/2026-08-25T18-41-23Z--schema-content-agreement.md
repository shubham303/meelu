# Structured data is checked for required properties, never against the page it describes

- **Recorded:** 2026-08-25
- **Severity:** correctness
- **Area:** dashboard
- **Files:** `dashboard/src/features/domain/site/issues-repository.ts:470` (`no-structured-data` through `schema-localbusiness-incomplete`), `app/src/main/crawler/extract.js:213` (`schemaNodes`), `dashboard/src/lib/schema/site.ts` (`schemaNodes` column)

## Issue

The audit now records, per JSON-LD node, its `@type`, how many properties were
declared and which of them were non-empty (`site_pages.schema_nodes`), and
checks required-property presence for Article, Product, FAQPage, HowTo,
BreadcrumbList, Organization and LocalBusiness. That catches markup that cannot
produce a rich result at all.

It cannot catch the failure Google actually acts on: markup that is complete and
disagrees with the page. An `FAQPage` whose questions appear nowhere in the
visible text, a `Product` whose `offers.price` is stale against the price on the
page, an `AggregateRating` with no reviews behind it, an `Article` whose
`author` names someone with no byline on the page — all of these pass every
check here and are exactly what a manual action for structured-data spam is
issued for.

The cost of leaving it is that the audit's schema findings read as a full
verdict on structured data when they are only a shape check.

## Evidence

`schemaNodes` deliberately keeps property **names** and drops values, in
`app/src/main/crawler/extract.js`:

```js
function ldProps(node) {
  const declared = Object.entries(node).filter(([key]) => !key.startsWith("@"));
  return {
    keys: declared.length,
    props: declared.filter(([, value]) => stated(value)).map(([key]) => key),
  };
}
```

So no rule downstream can compare a marked-up value with anything, by
construction. The rules only ever ask `n->'props' @> '["..."]'::jsonb`.

## Suggested fix

Belongs to the agent, not to the audit. `bodyText` and `schemaTypes` are already
on the page row and the page-read tool already returns them, so an agent asked
"does the structured data on this page match what the page says" has what it
needs — except the schema *values*, which are currently flattened into
`schemaText` for embedding and then discarded.

Concretely:

1. Decide whether the page-read tool should return the raw JSON-LD blocks
   alongside `schemaTypes`. Today it does not, so the agent cannot see the
   marked-up price to compare it. That probably means one more column
   (`schema_raw jsonb`, capped) or re-parsing on read — check the size cost
   before adding a column, JSON-LD blobs on ecommerce templates are large.
2. Put the actual comparison in the Pages desk prompt as a capability the agent
   performs on request, not as an issue kind. A model-scored issue kind would
   break the "the checks are deterministic and cost no model time" and
   "re-running is safe" contract stated in
   `mcp-server/src/domains/sites/issues.ts:41`.

Unsure about: whether storing raw JSON-LD is worth it versus having the agent
re-fetch the page when it wants to check. Re-fetching is one request and always
current, which may be the better trade.

## Risks / knock-on effects

Adding a column means a new migration on top of `0030_dizzy_sinister_six.sql`
(the one that added `schema_nodes`), plus adding the field to `CRAWL_COLUMNS` in
`dashboard/src/features/domain/site/pages-repository.ts` and to the `SitePage`
type — the crawler writes rows wholesale, so a column missing from
`CRAWL_COLUMNS` is silently dropped. No baseline regeneration needed.

## Verification

- `cd dashboard && npx tsc --noEmit && npm test`
- `cd mcp-server && npx tsc --noEmit`
- If a column is added: `npm run db:generate` then `DATABASE_URL=... npm run db:migrate`, and confirm `\d site_pages` shows it.
