# Meelu — Design System & Frontend Conventions

Meelu is a reading-first tool: light white-and-blue theme, low-glare off-white ground,
white panels, slate ink (never pure black), one restrained blue accent, generous whitespace,
serif display headlines (Fraunces) over a clean sans body (Geist). Every screen animates in
with GSAP — subtle, fast, never bouncy. Keep accents sparse: color marks meaning (status,
actions), never decoration — bright spots compete with reading.

## Tokens (defined in `src/app/globals.css` via Tailwind v4 `@theme`)

Use ONLY these semantic classes for color:

| Class | Role |
|---|---|
| `bg-bg` | app background (warm cream #f8f5eb — slight yellow tint for reading comfort) |
| `bg-panel` / `bg-panel2` | warm-white cards / light raised surfaces |
| `border-edge` / `border-edge2` | hairline borders |
| `text-ink` | primary text (slate #1f2d3d, not black) |
| `text-sub` | secondary text |
| `text-faint` | tertiary/placeholder |
| `bg-accent` / `text-accent` / `border-accent` | blue #2563eb (hover = accent-hi, darker) |
| `text-good` / `text-warn` / `text-bad` | success / warning / danger (dark, light-bg-safe) |
| `font-display` | Fraunces (headings, stats) |

Radii: cards `rounded-2xl`, buttons/inputs `rounded-lg`, pills `rounded-full`.
Hairlines everywhere: `border border-edge`. Shadows: avoid; use borders + subtle bg shifts.

## Shared components — `src/components/ui.tsx` (READ THE FILE for exact props)

`Button` (variants: primary | outline | ghost | danger; sizes sm | md), `IconButton`,
`Card`, `PageHeader` (title, description, actions), `StatCard` (label, value, change?, spark?),
`Badge` (tone: neutral | accent | good | warn | bad), `Input`, `Textarea`, `Select`, `Field`
(label + control wrapper), `Modal` (right-side sheet, GSAP slide-in from the right — ALL popups
use this), `Drawer` (right-side detail panel: ~half viewport, drag-resize on the left edge,
drag past minimum to dismiss), `EmptyState` (icon, title, hint, action), `Tabs`,
`Table`/`THead`/`TRow`/`TCell`, `Spinner`, `ConfirmDelete`.

House interaction pattern: clicking a list item opens a `Drawer` with the full detail
(keep the selected item in state while the drawer animates closed; stopPropagation on
inline action buttons inside clickable cards; sync the selected item after `refresh()`).
Create/edit forms open in `Modal`, which slides in from the right by design.

Charts — `src/components/charts.tsx`: `Sparkline`, `Bars`, `Donut` (pure SVG, token colors).

Animation — `src/components/animate.tsx` (GSAP + @gsap/react):
- `<PageEnter>` — wrap every page's content once; fades/slides the page in.
- `<Stagger>` — parent whose children with class `stagger-item` animate in with stagger.
- `<AnimatedNumber value={n} />` — counts up on mount.
- `<Reveal delay={0.1}>` — single-element fade-up.
- For custom animations import `gsap` + `useGSAP` from this file's re-exports; landing page
  may use `ScrollTrigger` (already registered in `animate.tsx`).

## Data fetching — `src/lib/use-api.ts`

- `const { data, loading, error, refresh } = useApi<T>("/api/v1/...")` — GET on mount.
- `await api("/api/v1/...", { method: "POST", body: {...} })` — mutations; throws `Error(message)` on non-2xx. Always `refresh()` after a successful mutation; surface errors with a small inline `<p className="text-bad">`.

## Page conventions

- All dashboard pages are client components (`"use client"`) rendered inside the sidebar shell
  (`src/app/dashboard/layout.tsx` — already handles auth + chrome; do NOT re-add nav).
- Page skeleton:
  ```tsx
  <PageEnter>
    <PageHeader title="..." description="..." actions={<Button .../>} />
    ...content (Stagger of Cards, Tables, etc.)
  </PageEnter>
  ```
- Loading: centered `<Spinner />`. Empty: `<EmptyState />` explaining that the MCP coworker
  fills this screen, with a manual-create action too.
- Every entity list supports create (Modal form), edit (Modal), delete (ConfirmDelete).
- Dates: `formatRelative()` / `formatDate()` from `src/lib/utils.ts`.
- Status fields render as `Badge` with a sensible tone mapping.
- Do not install new dependencies. Do not edit shared files (`src/components/*`, `src/lib/*`,
  `src/app/globals.css`, `src/app/layout.tsx`) — if you need a section-specific component,
  create it inside your own page directory.

## The agent guide catalog

Each agent has a guide page at `/dashboard/guide/[key]`. The page is rendered entirely from a pure data module — no DB, no
React, icons named as strings and resolved in the page directory:

| Catalog | Describes | Page |
|---|---|---|
| `src/lib/agents.ts` | agents that exist — prompts, rules, limits | `/dashboard/guide/[key]` |

It is a file rather than a table because nothing in it is per-user, and it wants a diff and a
git history. There is deliberately no coming-soon catalog: the app lists agents that work.

**Changing an agent's behaviour means changing its guide entry in the same commit.** A guide
that describes last quarter's behaviour is worse than no guide, and the prompts in it are meant
to be copied verbatim into Claude — one that no longer works reads as the product being broken.
The load-bearing field is `prompts`: the dashboard has no intelligence, so what a user most
needs from these pages is what to *say*, not what the screen they are standing on looks like.

## Voice

UI copy speaks of the AI as "your coworker": "Your coworker found 12 pages with missing meta descriptions",
"Ask your coworker in Claude — results land here." Landing page: confident, craft-warm,
no corporate fluff.
