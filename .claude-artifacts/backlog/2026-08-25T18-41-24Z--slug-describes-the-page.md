# Slug checks are mechanical; nothing asks whether the slug describes the page

- **Recorded:** 2026-08-25
- **Severity:** cleanup
- **Area:** dashboard
- **Files:** `dashboard/src/features/domain/site/issues-repository.ts:714` (`url-hygiene`, `url-too-long`, `url-dated`, `url-stop-words`)

## Issue

Four rules now cover SEO-friendly URLs: `url-hygiene` (capitals, underscores,
tracking parameters), `url-too-long` (path over 100 characters), `url-dated`
(a year-and-month baked into the path) and `url-stop-words` (two or more
function words in the slug).

All four are shape checks. None of them can tell that `/p/sku-40021` says
nothing about the page, that `/blog/post-2` is a CMS default nobody renamed, or
that a slug describes something the page no longer covers after a rewrite. That
is the half of the Ahrefs advice — "use a short, descriptive URL" — that the
audit does not reach, and it needs a model that has read the page.

The cost of leaving it is small: this is polish, and changing a live URL costs a
redirect, which is usually a worse trade than a vague slug. It is worth having
for pages that are not published yet.

## Evidence

The three new rules test only the string:

```sql
length(${slug}) > 100
${slug} ~ '/(19|20)[0-9]{2}[/-](0[1-9]|1[0-2])([/-]|$)'
regexp_count(${slug}, ${STOP_WORD_RE}, 1, 'i') >= 2
```

Nothing in `PAGE_RULES` joins a slug against `title`, `h1` or `bodyText`.

## Suggested fix

Do not add an issue kind. Two better homes:

1. **A cheap deterministic near-miss**, if one is wanted: flag pages whose slug
   shares no word with the title or any H1 — `title`, `h1` and the slug are all
   on the row, so it is a pure SQL rule. It is crude (it will fire on
   deliberately short brand slugs) but it is honest about what it measures, and
   it is the only part of this that can be deterministic.
2. **The judgement itself belongs in the content desk prompt**, applied at the
   point a page is being drafted rather than audited — that is when the URL is
   still free to change. Recommending a slug for an existing page should come
   with the redirect cost stated, which the `url-stop-words` issue text already
   does.

Unsure about: whether (1) earns its noise. Try the query against the live
database first and look at what it catches before committing to a kind.

## Risks / knock-on effects

A new kind needs adding to `SITE_ISSUE_KINDS` in **both**
`dashboard/src/lib/types.ts` and `mcp-server/src/domains/sites/types.ts`; the
lists must stay byte-identical. No schema change.

## Verification

- `cd dashboard && npx tsc --noEmit`
- `cd mcp-server && npx tsc --noEmit`
- Run the candidate `where` against the live database and read the URLs it
  matches before keeping it.
