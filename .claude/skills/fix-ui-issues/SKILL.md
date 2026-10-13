---
name: fix-ui-issues
description: Fix UI feedback captured by the dev annotation overlay. Reads each timestamped pair in `.annotations/` (screenshot + markdown), applies the requested fixes, then deletes the pair. Use when the user says "fix ui issues", "check the annotations", "apply my feedback", or "apply the annotations".
---

# Fix UI issues from annotations

The Electron dev annotation overlay (`app/dev/annotator/`) writes UI feedback to
`.annotations/` at the repo root: a screenshot with the markup baked in plus a
markdown file describing each numbered badge.

## Rules

- **Never read or delete `latest.md` / `latest.png`** — they are stable aliases
  for the newest timestamped pair, not separate work items. Acting on them
  double-processes an issue. Leave them on disk untouched.
- Work only on timestamped pairs, e.g. `2026-08-13T03-54-44Z.md` +
  `2026-08-13T03-54-44Z.png`.
- Delete a pair **only after** its fixes are actually applied. A pair still on
  disk means unfinished work.
- Run until no timestamped pairs remain.

## Procedure

1. List the work:

   ```bash
   ls .annotations/*.md 2>/dev/null | grep -v '/latest\.md$'
   ```

   If nothing is listed, say there is no pending UI feedback and stop.

2. Process pairs **oldest first** (filenames sort chronologically). For each:

   a. Read the `.md` file. Note the `Route:` and viewport — the route tells you
      which view/page the feedback is about.

   b. Read the sibling `.png` with the Read tool. This is required, not
      optional: the markdown's "Points at" selector for a *drawn* mark is
      inferred, and **the screenshot is the tiebreaker**.

   c. Match each numbered badge in the screenshot to the same-numbered section
      in the markdown.
      - **Pin** sections carry an exact selector, component name, tag/text and
        bounding box — trust them.
      - **Drawn mark** sections carry geometry plus an *inferred* "Points at"
        selector — a strong hint; confirm against the screenshot.
      - **Free-floating notes** have no selector — locate them by position in
        the screenshot.
      The typed comment under a mark **is the request**; the mark is only a
      pointer.

   d. Locate the real source. Start from the route and the component name, and
      search the app/dashboard UI code for the element's text or classes.
      Remember the split in `CLAUDE.md`: app and web share UI code, so a fix
      usually lands in the shared dashboard component — but anything agentic
      stays app-gated. Never add an agent affordance to the web.

   e. Apply the fix. Make the smallest change that satisfies the comment and
      matches surrounding code style. If a comment is ambiguous, implement the
      most reasonable reading and say what you assumed in the final summary.

   f. Verify what can be verified cheaply — typecheck/lint/build for the package
      you touched (e.g. `npm run check`).

   g. Delete the pair, and only that pair:

      ```bash
      rm .annotations/<stamp>.md .annotations/<stamp>.png
      ```

3. Repeat step 1 — new annotations can land while you work. Loop until the
   listing is empty.

4. Report: for each annotation, the request, the file(s) changed, and any
   assumption made. Call out anything you could **not** fix — leave that pair on
   disk rather than deleting it, and say so explicitly.

## Do not

- Do not delete a pair you skipped or only partially fixed.
- Do not delete or rewrite `latest.md` / `latest.png`.
- Do not commit or push unless the user asks.
