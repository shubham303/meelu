---
name: backlog-add
description: Record a code issue and its suggested fix as one timestamped file in `.claude-artifacts/backlog/`, so it can be picked up later by backlog-fix. Use when the user says "add to backlog", "backlog this", "log this issue", "note this for later", "add this issue in backlog", or describes a problem they do not want fixed right now.
---

# Add an issue to the code-fix backlog

One issue, one file, in `.claude-artifacts/backlog/`. The file is the entire
handover: `backlog-fix` will read it in a **fresh session with none of this
conversation's context**, so anything you leave implicit is lost.

## Rules

- **One file per issue.** Two unrelated problems are two files, never one with
  two headings. `backlog-fix` resolves exactly one file per run.
- **Never fix the code here.** This skill only records. If the user wants it
  fixed now, say so and fix it instead of writing a file.
- **Name real paths.** `src/lib/store.ts:461` is actionable; "the store layer"
  is not. Verify each path exists before writing it down — a stale path sends
  the next session hunting.
- **Write the suggested fix as a proposal, not a promise.** The next session
  must re-check it against the code as it stands, so record *why* you think it
  is right, not just *what* to type.

## Procedure

### 1. Gather the issue

Take it from what the user said. If they pointed at code, read that code now and
confirm the problem is real before recording it — a backlog full of issues that
turn out not to exist is worse than an empty one.

Ask only if the issue is genuinely ambiguous (you cannot tell which file or
which behaviour is wrong). Otherwise record it and move on.

### 2. Build the filename

```bash
date -u +%Y-%m-%dT%H-%M-%SZ
```

Filename: `<timestamp>--<slug>.md` in `.claude-artifacts/backlog/`, where
`<slug>` is 3–6 kebab-case words naming the issue.

```
.claude-artifacts/backlog/2026-08-19T10-42-05Z--profile-dead-base-columns.md
```

The timestamp leads so plain filename sort is chronological order — that is how
`backlog-fix` finds the oldest. The slug is there so the folder is readable at a
glance.

### 3. Write the file

Use this template. Drop a section only when it genuinely does not apply.

```markdown
# <One-line title — the problem, not the fix>

- **Recorded:** <YYYY-MM-DD>
- **Severity:** blocker | bug | correctness | cleanup | perf | dx
- **Area:** <dashboard | mcp-server | app | schema | infra>
- **Files:** `path/to/file.ts:123`, `path/to/other.ts`

## Issue

What is wrong, in plain terms. Include the concrete failure: what input or
state produces what wrong output. If it is a cleanup rather than a defect, say
what the cost of leaving it is.

## Evidence

How you know. A quoted line, a grep result, a build error, a schema diff.
Enough that the next session can confirm it in under a minute.

## Suggested fix

The change you would make, concretely enough to act on — which file, which
function, what shape the result should take. Note anything you are unsure
about.

## Risks / knock-on effects

What else touches this. Callers that would need updating, tests that would
change, whether it needs a schema regen. Write "none known" rather than
omitting the section.

## Verification

How the next session proves it worked — the exact command where possible:

- `cd dashboard && npx tsc --noEmit`
- `cd mcp-server && npm run build`
- ...or the manual check, if there is no automated one.
```

### 4. Confirm

Tell the user the filename you wrote and give a one-line summary of what was
recorded. Do not restate the whole file back at them.

## Project notes

- If the issue touches `dashboard/src/lib/schema.ts`, say so explicitly in
  **Risks** — fixing it means regenerating the baseline migration and rebuilding
  the database. See the Migrations section of the root `CLAUDE.md`.
- Nothing is in production. Never record a fix that adds a compatibility shim,
  a `legacy_*` fallback, or a deprecation window; record the outright change.
