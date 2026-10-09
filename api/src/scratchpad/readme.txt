# Task: Implement a Scratchpad service for agent tools

## Context and goal

Some tools return large outputs (long lists, CSV rows, crawled pages, keyword tables). Returning these inline bloats the agent's context, and agents lose track of which items they have processed.

Build a **scratchpad**: a temporary, schemaless work queue. When a tool's output is large, the tool writes it to a scratchpad and returns only a handle, a count and one sample row. The agent then pulls items in batches, processes them (itself or through subagents), and records each item's status, until nothing is left.

Key principles:
- Each row is free-form text (plain string, JSON, anything). An LLM reads it, so there is no schema. The producing tool is responsible for making each row's text self-describing.
- **Only producer tools create scratchpads or add rows. The LLM never creates a scratchpad**; it only reads, claims and updates rows.
- Scratchpads are temporary working memory for one agent run, not stored results. End-user-facing results live in their own structured tables elsewhere.
- Follow the existing **service and repository pattern** in this codebase. All APIs and tools go through the service layer, which goes through the repository layer. Some APIs and tools look like duplicates of each other; that is intended.

## Data model

### `scratchpad`
| column | notes |
|---|---|
| `id` | primary key, generated on create |
| `tool_name` | name of the tool that created it |
| `created_at` | |
| `updated_at` | bumped on every row insert, claim or status change in this scratchpad |

### `scratchpad_row`
| column | notes |
|---|---|
| `scratchpad_id` | foreign key to `scratchpad.id`, **ON DELETE CASCADE** |
| `row_id` | integer sequence **per scratchpad**, starting at 1, in the producer's original order. Appends continue the sequence. |
| `text` | unbounded text; the row content |
| `text_hash` | SHA-256 of `text` exactly as stored |
| `status` | `pending` / `processing` / `done` / `failed` |
| `status_updated_at` | set on every status change |
| `attempt_count` | integer, default 0, incremented each time the row is claimed |
| `priority` | integer set by the producer tool, default 0; higher is processed first |
| `result` | optional text, written by the agent if it chooses |
| `error_reason` | text, required when status is `failed` |

Constraints and indexes:
- Primary key: `(scratchpad_id, row_id)`
- Unique: `(scratchpad_id, text_hash)` — duplicates are prevented within a scratchpad, not across scratchpads
- Index to support claiming: `(scratchpad_id, status, priority DESC, row_id ASC)`
- Index to support the cleanup job: `(status, status_updated_at)`

Every API and tool that takes a `row_id` also takes `scratchpad_id`.

## Status rules

Allowed transitions; reject everything else with a clear, actionable error message:
- `pending → processing` (only through claim / next)
- `processing → done`
- `processing → failed` (requires `error_reason`)
- `processing → pending` (agent releases a row without finishing it)
- `failed → pending` (retry)

Configurable constants:
- `MAX_ATTEMPTS = 3`
- `STUCK_AFTER_MINUTES = 15`
- `TTL_HOURS = 4`
- `ROW_COUNT_THRESHOLD = 50`
- `CHAR_THRESHOLD = 20000`
- `MAX_ROW_CHARS_RETURNED = 4000`
- `MAX_BATCH_SIZE = 50`

## Concurrency

- `next` and `claim` must be atomic. Inside one transaction, take a lock on the scratchpad, for example by selecting the `scratchpad` row with `FOR UPDATE`. Then select the eligible rows, mark them `processing`, increment `attempt_count`, set `status_updated_at`, and commit.
- The lock is **per scratchpad**. Parallel agents working on the same scratchpad queue up behind each other. Agents on different scratchpads never block each other.
- No row may ever be returned to two claimers.

## Service layer

1. **`create_scratchpad(tool_name, items: list[str], priorities: list[int] | None)`**
   - Generate a new ID, insert all rows as `pending`, with `row_id` in input order.
   - Skip duplicates by `text_hash`.
   - Return: `scratchpad_id`, `total_rows`, `duplicates_skipped`, one sample row.

2. **`append_rows(scratchpad_id, items, priorities)`**
   - Insert as `pending`, continuing the `row_id` sequence.
   - Skip rows whose hash already exists in this scratchpad.
   - Return: `added`, `duplicates_skipped`, current metrics.

3. **`delete_scratchpad(scratchpad_id)`**
   - Delete the scratchpad; rows cascade.

4. **`update_status(scratchpad_id, updates: list[{row_id, status, result?, error_reason?}])`**
   - Validate each transition independently.
   - Apply the valid ones and report the invalid ones with reasons, without failing the whole batch.
   - Return: per-row outcome and current metrics.

5. **`get_metrics(scratchpad_id)`**
   - Return counts of `total`, `pending`, `processing`, `done`, `failed`.

6. **`next(scratchpad_id, n=10)`**
   - Atomically claim up to `n` (capped at `MAX_BATCH_SIZE`) `pending` rows, ordered by `priority DESC, row_id ASC`.
   - Return: the claimed rows and current metrics. Truncate each row's text to `MAX_ROW_CHARS_RETURNED`, adding a marker that says how many characters were cut.
   - If nothing is pending but rows are still `processing`, return a message saying so ("other agents are still working; check metrics later"). Do not report completion in this case.
   - If `pending = 0` and `processing = 0`, return an "all items processed" message that includes the done and failed counts.

7. **`claim_rows(scratchpad_id, row_ids)`**
   - Same locking and claiming as `next`, but for specific rows.
   - Only `pending` rows are claimed and returned. **Never return the content of rows that are `processing`.**
   - Report which requested IDs were not claimed and why (already processing, done, failed, or not found).

8. **`get_scratchpad(scratchpad_id)`**
   - Return basic info: `id`, `tool_name`, `created_at`, `updated_at`, plus metrics.

9. **`get_failed(scratchpad_id, offset, limit)`**
   - Return failed rows with `error_reason` and `attempt_count`.

10. **`search(scratchpad_id, query, status=None, offset=0, limit=10)`**
    - Case-insensitive keyword match on `text`, ordered by `priority DESC, row_id ASC`.
    - Read-only: it does not claim. When a status filter is given, apply it. Never return the content of rows in `processing`.
    - Return: matching rows (truncated as above) and the total match count.

11. **`needs_scratchpad(items: list[str]) -> bool`**
    - Return True if `len(items) > ROW_COUNT_THRESHOLD` or the total characters across items exceed `CHAR_THRESHOLD`. Otherwise False, and the tool returns its output inline as usual.

## Producer-tool integration

Any tool that can return a large list calls `needs_scratchpad`. If it returns True, the tool calls `create_scratchpad` and returns to the LLM:
- `scratchpad_id`, total row count and duplicates skipped
- the one sample row
- one line of guidance, for example: "Output stored in scratchpad {id} ({n} items). Use scratchpad_next to process in batches and scratchpad_update_status to record each item's outcome."

Producer tools should write each row as self-describing text. When an item's content is very large (for example full page HTML), the row should hold a reference such as a URL or file path, not the whole blob.

## LLM-facing tools

All tools go through the service layer.

1. **`scratchpad_next(scratchpad_id, n=10)`** → `service.next`
2. **`scratchpad_claim(scratchpad_id, row_ids)`** → `service.claim_rows`
   - Used after `scratchpad_search`, or by the main agent to hand specific rows to a subagent.
3. **`scratchpad_update_status(scratchpad_id, updates: list[{row_id, status, result?, error_reason?}])`** → `service.update_status`
4. **`scratchpad_metrics(scratchpad_id)`** → `service.get_metrics`
5. **`scratchpad_get_failed(scratchpad_id, offset, limit)`** → `service.get_failed`
6. **`scratchpad_search(scratchpad_id, query, status?, offset, limit)`** → `service.search`
7. **`scratchpad_info(scratchpad_id)`** → `service.get_scratchpad`
8. **`scratchpad_delete(scratchpad_id, force=false)`**
   - If `force` is false and any row is not `done`, do not delete. Return an error that gives the metrics and says: "Set force=true only if you are sure these unfinished rows should be discarded."
   - Otherwise delete.

Tool response requirements:
- Every response that changes or reads rows includes current metrics.
- Error messages say what went wrong and what the agent should do next.
- If a scratchpad ID does not exist (for example it expired), say: "Scratchpad {id} not found; it may have expired. Re-run the tool that created it if the data is still needed."

## Cleanup job (runs every 5 minutes)

1. **Stuck rows.** For rows in `processing` with `status_updated_at` older than `STUCK_AFTER_MINUTES`:
   - if `attempt_count < MAX_ATTEMPTS`: set to `pending`
   - otherwise: set to `failed` with `error_reason = "timed out after {MAX_ATTEMPTS} attempts"`
   - **Never delete stuck rows.**
2. **Expired scratchpads.** Delete scratchpads whose `updated_at` is older than `TTL_HOURS`; rows cascade.
3. Log how many rows were reset, failed and deleted on each run.

## Tests

Cover at least:
- Concurrent `next` calls on the same scratchpad never return the same row.
- Calls on different scratchpads don't block each other.
- Priority ordering and the `row_id` tie-break.
- Duplicate skipping on create and append, and that the same text is allowed in different scratchpads.
- All allowed and rejected status transitions, including partial success in batch updates.
- `claim_rows` partial claims, and that `processing` rows are never returned by claim or search.
- The cleanup job resets stuck rows, fails them at the attempt limit, and deletes expired scratchpads.
- `next` distinguishes "still processing" from "all processed".
- `delete` with and without `force`.
- `needs_scratchpad` triggers on both row count and character size.