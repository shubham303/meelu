# Content piece editor — redesign

Route: `/dashboard/content/[id]`. Built 2026-09-12 on top of the
`content_pieces` / `content_piece_issues` tables. Web renders the document
and the rail; the app adds the agent, the selection composer, proposals and
the local checks. Mockups: `content-editor-design/` (canvas artifact).

## What was wrong

- A raw CodeMirror box with a `Write in markdown…` placeholder inside a card,
  inside a page with a duplicate title above it. It read as a settings form.
- The agent was a fixed-position chat drawer bolted on the right. Turns were
  plain text; a rewrite silently replaced the whole document and offered a
  single "undo the last change" link. No diff, no per-change accept/reject.
- Selection actions (rephrase, shorter…) lived in a floating menu that had no
  visual relationship to the chat, so two disconnected AI surfaces competed.
- Slug, description, status, publish target and publish itself were buried in
  a "Details" modal. The piece's most important facts were invisible while
  writing.
- Header actions (`Details`, `Agent`, `Save`) were generic; "Save" as a manual
  button on a text editor is 2010.

## Principles

1. The document is the page. No card, no border, no placeholder box — a
   centered column of prose (~68ch) on the panel background, title as an
   editable H1, body as a rich text editor that stores markdown.
2. Every AI change is a proposal, never a replacement. It shows as an inline
   diff (deleted spans struck in red, inserted spans in green) with
   Accept / Reject per hunk and Accept all / Reject all at the top. Nothing
   overwrites the draft until accepted.
3. One AI surface, not two. Selecting text opens a small inline composer
   anchored to the selection (with the quick actions as chips); the side panel
   is the same conversation, just wider. Both write proposals into the
   document.
4. Autosave. Debounced PATCH 800ms after the last keystroke; a quiet
   "Saved · just now" / "Saving…" indicator next to the title. No Save button.
5. Metadata is a rail, not a modal. Slug, description, status and published
   URL live in the right rail. There is no publish flow: a copy icon in the
   top bar copies the piece as a markdown file with frontmatter.
6. Checks are a panel. `Checks` in the top bar swaps the rail for a list of
   issues from local text tools (readability today; more later). Selecting one
   highlights its passage; `Edit` puts the cursor there, `Fix with agent`
   produces a single inline proposal without opening the chat. Issues with no
   passage are shown as findings only.
7. Images and GIFs go through the existing media upload (paste, drop, or the
   button under the document) and are stored as `![alt](/api/v1/content/media/{id})`.

## Layout

See the canvas: Writing (rail), Checks (issue selected), Agent (proposals).

## Components

| File | Role |
|---|---|
| `content/page.tsx` | List with status tabs, search, `New piece`, app-only brief that seeds the editor's chat. |
| `content/[id]/page.tsx` | Loads the piece, owns autosave, the panel switch (rail / checks / agent), proposals and check runs. |
| `content/[id]/document.tsx` | Tiptap editor (`@tiptap/markdown` in and out), image upload, selection bubble with formatting + agent chips. |
| `content/[id]/issue-highlights.ts` | ProseMirror plugin decorating flagged passages; `findText` maps anchor text to doc positions. |
| `content/[id]/diff.ts` + `proposal-review.tsx` | Line-level hunks with word-level colouring; Keep / Discard per hunk, Keep all / Discard all. |
| `content/[id]/checks-panel.tsx` | Issue list grouped by tool. |
| `content/[id]/agent-panel.tsx` | Conversation; replies with a markdown fence become proposals. |
| `content/[id]/rail.tsx` | Slug, description, status, published URL, delete. |
| `content/[id]/use-agent.ts` | `content-draft` turns: whole-piece questions/instructions (session kept) and passage rewrites. |
| `content/[id]/use-autosave.ts` | Debounced PATCH with saved/saving/error state. |

Checks run in the app: `app/packages/readability/` (ported from the
meelu-website tool, plain ESM) behind `app/src/main/text-checks/`, exposed as
`checkContent({ text, tools })` on the preload bridge. The renderer posts each
tool's issues to `POST /content/pieces/{id}/issues`, which replaces that
tool's previous run.

## Data contract

`GET/POST /content/pieces`, `GET/PATCH/DELETE /content/pieces/{id}`,
`GET /content/pieces/{id}/markdown`, `GET/POST /content/pieces/{id}/issues`,
`PATCH /content/pieces/{id}/issues/{issueId}`. Proposals and chat turns are
not stored; only what the user keeps lands in `body_markdown`.

## Web vs app

Web gets the document, autosave, the rail and read-only checks. Selection
composer, agent panel, proposals and running checks are gated on
`useIsApp()`, matching the rule that agent affordances never ship to the web.
