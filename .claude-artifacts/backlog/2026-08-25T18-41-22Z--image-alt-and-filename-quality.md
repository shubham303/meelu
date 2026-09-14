# The audit checks that alt text exists, never that it says anything

- **Recorded:** 2026-08-25
- **Severity:** correctness
- **Area:** dashboard
- **Files:** `dashboard/src/features/domain/site/issues-repository.ts:653` (`image-missing-alt`), `app/src/main/crawler/extract.js:268` (image extraction)

## Issue

`image-missing-alt` fires only when the `alt` attribute is absent entirely. A
page where every image carries `alt="image"`, `alt="photo"`, `alt="logo"` or the
filename repeated back passes the check cleanly, and so does a page whose images
are all named `IMG_8590.jpg` or `Screenshot 2024-05-02 at 14.31.png`. Both are
things the Ahrefs on-page guide calls out and both are invisible to the audit as
it stands: the first needs someone to compare the alt text against what the
image actually shows, the second is partly mechanical but still needs judgement
about whether a filename is descriptive of the page it sits on.

The cost of leaving it is that the audit reports a clean bill on image
accessibility for sites whose alt text is boilerplate, which is the common case
rather than the rare one.

## Evidence

The rule body, in full:

```sql
where: sql`${crawled} and exists (
    select 1 from jsonb_array_elements(${p.images}) im where im->>'alt' is null
  )`
```

`im->>'alt' is null` is the whole test. And `extract.js` stores `alt` verbatim
with no inspection:

```js
const alt = $(el).attr("alt");
images.push({ src, ...(alt === undefined ? {} : { alt: alt.trim() }) });
```

## Suggested fix

This is not a SQL rule — deciding whether "a person at a laptop" describes the
image needs a model that can see the page and the image. Two halves worth
separating:

1. **Mechanical half, could be a rule now.** Flag alt text that is obviously
   placeholder: equal to the filename, equal to the page title, one of a small
   stop-list (`image`, `photo`, `picture`, `logo`, `icon`, `img`, `banner`), or
   matching `^(img|dsc|screenshot|photo)[-_ ]?\d+` on the *filename* side. That
   is a new `PageRule` next to `image-missing-alt`, same shape, no new columns —
   `src` and `alt` are both already in the `images` jsonb.

2. **Judgement half, belongs to the agent, not the audit.** Anything beyond the
   stop-list should be a prompt-level capability on the Pages desk, not a
   deterministic issue kind: the agent reads the page, looks at the images it
   lists, and says which alt text is uninformative. Do not add an issue kind
   whose truth depends on a model — the audit is documented to the agent as
   deterministic and re-runnable, and a model-scored kind would break the
   "re-running is safe and is the point" promise in
   `mcp-server/src/domains/sites/issues.ts:41`.

Unsure about: whether the stop-list half generates enough signal to be worth a
separate kind, or whether it should widen `image-missing-alt` itself. Widening
it changes what an already-rejected `image-missing-alt` means for users who
turned it down, which argues for a separate kind.

## Risks / knock-on effects

A new kind needs adding to `SITE_ISSUE_KINDS` in **both**
`dashboard/src/lib/types.ts` and `mcp-server/src/domains/sites/types.ts` — the
two lists must stay identical, there is no shared source. No schema change: the
`images` jsonb already carries `src` and `alt`.

## Verification

- `cd dashboard && npx tsc --noEmit`
- `cd mcp-server && npx tsc --noEmit`
- `diff <(sed -n '/export const SITE_ISSUE_KINDS/,/as const/p' dashboard/src/lib/types.ts) <(sed -n '/export const SITE_ISSUE_KINDS/,/as const/p' mcp-server/src/domains/sites/types.ts)` must be empty
- Run the new rule's `where` against the live database and confirm it matches
  pages you can eyeball as genuinely bad, not every page with a logo.
