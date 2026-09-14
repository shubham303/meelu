# The render job renders at a desktop viewport only — mobile-specific rendering, layout and speed issues are invisible

- **Recorded:** 2026-09-14
- **Severity:** dx
- **Area:** app, schema, mcp-server, dashboard
- **Files:** `app/src/main/render/page.js:8`, `app/src/main/render/page.js:84`, `app/src/main/render/index.js`, `api/src/render_jobs/models/site_page_render.py:17`, `api/src/render_jobs/models/site_render_job.py`, `api/src/render_jobs/schemas/__init__.py:14`, `api/src/render_jobs/repository.py`, `api/src/technical_seo/rules/render.py:3`, `api/src/technical_seo/service.py`, `dashboard/src/app/dashboard/site/technical-seo/page.tsx:469`

## Issue

This is a feature, not a defect. The JS render pass shipped on 2026-09-14
renders every page once, in a hidden 1366x900 window with a desktop Chrome or
Googlebot user agent. Google indexes mobile-first, so what its mobile crawler
sees is what ranks, and it is not what we measure:

- Content, navigation and links that are hidden or collapsed at phone width
  (hamburger menus with no anchors in the DOM, "read more" truncation, tabs
  and accordions rendered only on tap, separate mobile templates behind a UA
  switch) are counted as present because the desktop render shows them.
- Mobile-only speed problems are invisible. LCP, CLS and TBT are far worse on
  a throttled phone-class CPU and a narrow viewport; a page that passes at
  desktop can fail every mobile threshold.
- Sites that serve different HTML to mobile user agents (dynamic serving, or
  an `m.` host) are never fetched with a mobile UA, so a mobile variant that is
  missing a canonical, has a different title, or is noindexed is never seen.
- Tap-target size, viewport meta correctness in practice (the crawl only
  checks the tag exists at `api/src/technical_seo/rules/page.py:635`),
  horizontal overflow, text below 12px and intrusive interstitials are all
  mobile-usability signals that only a mobile render can measure.

Cost of leaving it: the rendering findings describe a device Google no longer
indexes from, and the "site is fine after JS" verdict can be wrong for every
phone visitor.

## Evidence

- `app/src/main/render/page.js:84-85`: `width: 1366, height: 900`, no
  `deviceScaleFactor`, no touch emulation, no CPU or network throttling.
- `app/src/main/render/page.js:8-14`: the three user agents (`googlebot`,
  `generic`, `ai_bot`) are all desktop strings; there is no Googlebot
  smartphone UA.
- `api/src/render_jobs/models/site_page_render.py:20`: `page_id` is unique, so
  the table can hold exactly one render per page — a mobile render would
  overwrite the desktop one.
- `api/src/technical_seo/rules/render.py`: every rule reads the single alias
  `r`; nothing distinguishes device.

## Suggested fix

Keep the shape the user settled for rendering: mobile findings are technical
SEO issues with `is_rendering_issue = true`, in the same two issue tables. No
new desk, no new issue table, no new MCP tool. Only the render data and the
render job learn about devices.

**1. Schema (`api/src/render_jobs`)**

- Add `device` (`desktop` | `mobile`, text, not null, default `desktop`) to
  `site_page_renders` and change the unique index from `(page_id)` to
  `(page_id, device)`. Update `upsert_render` in `repository.py` to conflict on
  both columns, and `get_render` / `delete_render` / `render_counts` to take
  the device.
- Add `device` to `site_render_jobs` (a job renders one device; the UI can
  queue two). Carry it through `RenderJobOpenRequest`, `RenderJobRecord`,
  `RenderJobStatusRecord`, and `claim_render` so the app knows what to emulate.
- Add the mobile-only measurements to `site_page_renders`, nullable so desktop
  rows leave them empty: `viewport_overflow_px` (document scrollWidth minus
  viewport width), `small_text_ratio` (share of text nodes below 12px
  computed), `small_tap_targets` (count of links/buttons under 48x48 CSS px
  with a neighbour closer than 8px), `interstitial_detected` (bool: a fixed or
  sticky element covering more than ~30% of the viewport at load),
  `hidden_word_count` (words in the DOM not visible at the mobile viewport),
  `hidden_internal_links` (anchors not visible at the mobile viewport).
- Consider `desktop_title_differs` etc. as SQL over the two rows rather than
  columns — a self-join of `site_page_renders` on `page_id` covers it.

**2. App renderer (`app/src/main/render/page.js`)**

- Add a `mobile` device profile: 412x915 viewport, `deviceScaleFactor` 2.625,
  mobile Chrome / Googlebot smartphone user agent
  (`Mozilla/5.0 (Linux; Android 6.0.1; Nexus 5X Build/MMB29P) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/W.X.Y.Z Mobile Safari/537.36 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)`),
  `Emulation.setDeviceMetricsOverride` with `mobile: true`,
  `Emulation.setTouchEmulationEnabled`, and
  `Emulation.setCPUThrottlingRate` (4x) plus
  `Network.emulateNetworkConditions` (a "Slow 4G" profile) so the lab timings
  approximate a phone rather than a laptop.
- Extend `METRICS_SCRIPT` (or add a second in-page script) to measure the
  mobile-only fields above with `getBoundingClientRect`, `getComputedStyle`
  and `document.documentElement.scrollWidth`. Hidden content is anything with
  `display: none`, zero-size rects, or `visibility: hidden` at the mobile
  viewport that the desktop render counts as visible.
- `app/src/main/render/index.js` passes `plan.job.device` into `renderPage`
  and includes `device` in every `/site/page-renders` post.
- The window is reused across pages (`WINDOW_REUSE`); the emulation override
  has to be re-applied per page or the window recreated when the device
  changes.

**3. Rules (`api/src/technical_seo/rules/render.py`)**

- Alias the mobile row separately in `audit_repository.PAGES`:
  `left join site_page_renders r on r.page_id = site_pages.id and r.device = 'desktop'`
  `left join site_page_renders m on m.page_id = site_pages.id and m.device = 'mobile'`.
  Existing rules keep reading `r`. New mobile rules read `m`, guarded by a
  `MOBILE_RENDERED` predicate mirroring `RENDERED` at `render.py:3`.
- New page rules, all `rendering=True`: `mobile-hidden-content` (hidden words
  are a large share of the rendered words), `mobile-hidden-links` (internal
  links not reachable at phone width), `mobile-title-differs`,
  `mobile-canonical-differs`, `mobile-noindex-differs` (self-join r vs m),
  `mobile-viewport-overflow`, `mobile-small-text`, `mobile-small-tap-targets`,
  `mobile-interstitial`, and mobile thresholds for `slow-largest-paint`,
  `layout-shift` and `main-thread-blocked` as separate kinds
  (`mobile-slow-largest-paint` …) so a page can carry both verdicts.
- Register every kind in `api/src/technical_seo/constants.py` and the
  dashboard `SITE_ISSUE_KINDS` in `dashboard/src/lib/types.ts`; update the
  rule-count assertions in `tests/unit/technical_seo/test_rules.py` and
  `tests/integration/technical_seo/test_audit.py`.
- A site rule `mobile-differs-from-desktop` when a majority of pages rendered
  on both devices differ in title, canonical or noindex.

**4. Dashboard**

- `RenderPanel` in `dashboard/src/app/dashboard/site/technical-seo/page.tsx`
  gains a device choice next to the scope select (Desktop / Mobile / Both;
  "Both" queues two jobs back to back through `useRender`). The status line
  shows rendered counts per device.
- No new tab: mobile findings sit in the existing Rendering view because they
  carry the same flag. A small "mobile" badge on the issue card, driven by the
  kind prefix, is enough to tell them apart.

**5. Agent surface**

- Nothing new. Extend the technical-seo guide in
  `api/src/agent_scope/guides.py` with one sentence: `site_page_renders` has
  one row per (page, device), compare the two rows to see what changes on a
  phone.

Open decisions to settle with the user before writing the schema:

1. One job per device (recommended, keeps the job record simple) versus one
   job that renders both devices per page.
2. Whether the mobile render should use the Googlebot smartphone UA by default
   (matches what ranks) or a plain mobile Chrome UA (fewer bot-protection
   surprises); the existing `user_agent_profile` column can carry either.
3. Throttling levels for the lab timings; without throttling the mobile
   numbers are not comparable to Core Web Vitals field data.

## Risks / knock-on effects

- Schema change on two tables → Alembic revision under `api/alembic/versions`,
  and `tests/integration/technical_seo/test_render_audit.py` seeds
  `site_page_renders` directly and must set `device`.
- Every existing rule and test assumes a single render per page; the join
  alias change in `audit_repository.py` touches all 77 page rules' query even
  though only the `PAGES` string changes.
- Doubling the render volume doubles a job that is already the slowest thing
  the app runs; the sample scope becomes the sensible default for both.
- CPU throttling in an offscreen window slows the app's own main process if the
  renderer shares it — verify it only affects the render window's renderer
  process.
- Mobile user agents trip bot protection more often; the `x-meelu-crawl` token
  path already used in `page.js` must stay on for same-site requests.

## Verification

- `cd api && uv run alembic upgrade head && uv run pytest tests/unit/technical_seo tests/integration/render_jobs tests/integration/technical_seo/test_render_audit.py -q`
- New integration test: seed a page with a desktop render that shows 40 links
  and a mobile render with 30 hidden ones → `mobile-hidden-links` fires with
  `isRenderingIssue: true`; a page with only a desktop row raises no mobile
  kind.
- `cd dashboard && npx tsc --noEmit && npx eslint src/app/dashboard/site/technical-seo`
- `cd app && npm test`, then render a known responsive site with a hamburger
  menu in the app: the mobile row's `hidden_internal_links` is greater than 0
  and the desktop row's is 0.
