---
name: backlog-fix
description: Take the oldest issue from `.claude-artifacts/backlog/`, re-verify it, make the code change, prove it works, then delete the file. Use when the user says "backlog fix", "fix the backlog", "work the backlog", "pick up the next issue", or "resolve the oldest issue".
---

# Resolve the oldest backlog issue

Issues are recorded by `backlog-add` as timestamped files in
`.claude-artifacts/backlog/`. This skill works **one** of them — the oldest —
end to end, and deletes it only once the change is made and verified.

## Rules

- **Oldest first, one per run.** Filenames start with a UTC timestamp, so plain
  sort is chronological. Do not batch, and do not skip ahead to an easier one,
  unless the user names a specific issue.
- **Re-verify before fixing.** The file may be days old and the code has moved.
  Confirm the problem still exists before changing anything.
- **The recorded fix is a proposal, not an instruction.** It was written without
  the code in front of it. If it is wrong or now unnecessary, say so and do the
  right thing instead.
- **Delete the file only when the work is genuinely done and verified.** A file
  still on disk means unfinished work. `.claude-artifacts/` is git-tracked, so
  the deletion keeps its history — nothing is lost.
- **Do not commit** unless the user asks.

## Procedure

### 1. Find the work

```bash
find .claude-artifacts/backlog -name '*.md' | sort | head -1
```

Use `find`, not a `*.md` glob: this repo's shell is zsh, where an unmatched
glob is a shell-level error raised *before* any redirection, so `ls
…/*.md 2>/dev/null` fails noisily on an empty backlog instead of returning
nothing. `find` prints nothing and exits clean.

If nothing is listed, say the backlog is empty and stop. Do not go looking for
work elsewhere.

To see the whole queue, oldest first:

```bash
find .claude-artifacts/backlog -name '*.md' | sort
```

If the user named a specific issue instead ("do the schema one"), match it
against the filenames and use that file.

Say which issue you picked before starting.

### 2. Read it

Read the whole file. Then read every file it names under **Files**, plus
whatever those lead to. Understand the problem in the code, not just in the
description.

### 3. Re-verify

Confirm the issue is still real, using the **Evidence** section as your starting
point.

Three possible outcomes:

- **Still broken** → continue to step 4.
- **Already fixed** — someone resolved it in the meantime. Delete the file, tell
  the user it was already resolved and what you found. Stop.
- **Not actually a problem** — the record was wrong. Do **not** delete silently.
  Tell the user why you disagree and ask whether to drop it.

### 4. Make the change

Follow the **Suggested fix**, adjusted for what the code actually looks like
now. Where you depart from it, say so in your final report and why.

Match the surrounding code — this repo carries dense explanatory comments above
non-obvious declarations, and a fix that removes or contradicts one leaves the
next reader worse off. Update those comments as part of the change.

Fix the whole issue as recorded. If it turns out to be larger than described —
it needs a schema change nobody anticipated, or it spreads across a subsystem —
stop, leave the file in place, and report what you found. Half a fix with the
file deleted is the one outcome to avoid.

### 5. Verify

Run the commands in the file's **Verification** section. If it names none, use
whatever fits what you touched:

```bash
cd dashboard   && npx tsc --noEmit    # dashboard typecheck
cd dashboard   && npm run build       # full Next build
cd mcp-server  && npm run build       # tsc + boundary/endpoint checks
```

If the dashboard typecheck reports missing modules under `.next/types/`, those
are stale generated route validators — `rm -rf .next/types .next/dev/types` and
re-run.

Report failures honestly with their output. Do not delete the file while
anything is failing.

### 6. Delete the file

```bash
rm .claude-artifacts/backlog/<the-file-you-worked>.md
```

### 7. Report

- Which issue you resolved.
- What you changed, by file.
- Anywhere you departed from the suggested fix, and why.
- What you ran to verify, and the result.
- How many issues remain in the backlog.

## Project notes

- **Schema changes.** If the fix touches `dashboard/src/lib/schema.ts`, it is
  not done until the baseline is regenerated and the database rebuilt:

  ```bash
  cd dashboard && rm -f drizzle/*.sql && rm -rf drizzle/meta
  npx drizzle-kit generate --name baseline
  ```

  Then re-add the two hand-written statements the generator cannot produce —
  `CREATE EXTENSION IF NOT EXISTS vector;` at the top and the guarded pg_search
  / BM25 `DO` block at the foot — and rebuild:

  ```bash
  docker compose -f docker-compose.yml -f docker-compose.dbport.yml down -v
  docker compose -f docker-compose.yml -f docker-compose.dbport.yml up -d postgres
  cd dashboard && node scripts/migrate.mjs
  ```

  Diff the rebuilt schema against what you expected before calling it done — a
  regen silently drops any index that lives only in old hand-written SQL.

- **Nothing is in production.** No backward-compatible code, no shims, no
  deprecation windows. When something is cut, delete it — the table, the routes,
  the service, the MCP domain, and the comments that reference it.

- **Deleting a table means deleting its code.** Remove the Drizzle table, the
  types, the feature directory, the API routes, the MCP domain, the agent scopes
  and toolset entries, and every comment that names it. Grep for the snake_case
  table name *and* the camelCase export before declaring it gone.
