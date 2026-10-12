"use client";

import { useMemo, useState, type FormEvent } from "react";
import {
  MessageSquareWarning,
  NotebookPen,
  Pencil,
  Search as SearchIcon,
  Trash2,
  X,
} from "lucide-react";
import { PageEnter, Stagger } from "@demo/components/animate";
import {
  Badge,
  Button,
  ConfirmDelete,
  EmptyState,
  IconButton,
  PageHeader,
  Spinner,
  Textarea,
} from "@demo/components/ui";
import { api, useApi } from "@demo/lib/use-api";
import { cn, formatRelative } from "@demo/lib/utils";
import { NOTE_KINDS, type Note, type NoteHit, type NoteKind } from "@demo/lib/types";

const KIND_LABEL: Record<NoteKind, string> = {
  note: "Rule",
  feedback: "Correction",
};

const KIND_HINT: Record<NoteKind, string> = {
  note: "How you want things done",
  feedback: "Something it got wrong once",
};

interface SearchResult {
  hits: NoteHit[];
  mode: string;
  note?: string;
}

type KindFilter = "all" | NoteKind;

export default function NotesPage() {
  const {
    data,
    loading,
    error,
    refresh: reload,
  } = useApi<Note[]>("/api/v1/notes?page_size=100");
  const notes = useMemo(() => data ?? [], [data]);

  const [query, setQuery] = useState("");
  const [searched, setSearched] = useState<SearchResult | null>(null);
  const [filter, setFilter] = useState<KindFilter>("all");
  const [problem, setProblem] = useState<string | null>(null);

  const [editing, setEditing] = useState<Note | null>(null);
  const [deleting, setDeleting] = useState<Note | null>(null);

  const refresh = async () => {
    setSearched(null);
    setQuery("");
    await reload();
  };

  async function runSearch(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    if (!q) {
      setSearched(null);
      return;
    }
    try {
      setSearched(await api<SearchResult>(`/api/v1/notes?q=${encodeURIComponent(q)}&limit=25`));
      setProblem(null);
    } catch (err) {
      setProblem(err instanceof Error ? err.message : "Could not search the notes.");
    }
  }

  const pool: Note[] = searched ? searched.hits : notes;
  const shown = filter === "all" ? pool : pool.filter((n) => n.kind === filter);
  const countOf = (k: KindFilter) =>
    k === "all" ? pool.length : pool.filter((n) => n.kind === k).length;

  return (
    <PageEnter>
      <PageHeader
        title="Notes"
        description="Everything you have told your coworker once, so you never say it twice. It reads these before every task — a rule here outranks whatever it was about to do."
      />

      <div className="mx-auto max-w-3xl space-y-6">
        <Composer onSaved={refresh} />

        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <div className="flex items-center gap-1 rounded-lg border border-edge bg-panel p-0.5">
              {(["all", ...NOTE_KINDS] as KindFilter[]).map((k) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => setFilter(k)}
                  className={cn(
                    "rounded-md px-2.5 py-1 text-xs transition-colors",
                    filter === k
                      ? "bg-accent-soft text-accent font-medium"
                      : "text-sub hover:text-ink",
                  )}
                >
                  {k === "all" ? "All" : `${KIND_LABEL[k]}s`}
                  <span className="ml-1.5 tabular-nums text-faint">{countOf(k)}</span>
                </button>
              ))}
            </div>

            <form onSubmit={runSearch} className="flex min-w-0 flex-1 items-center gap-2">
              <div className="relative min-w-0 flex-1">
                <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Search by meaning or by words…"
                  className="w-full rounded-lg border border-edge bg-panel py-1.5 pl-9 pr-8 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none"
                />
                {searched && (
                  <button
                    type="button"
                    aria-label="Clear search"
                    onClick={() => void refresh()}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-faint transition-colors hover:text-ink"
                  >
                    <X size={14} />
                  </button>
                )}
              </div>
            </form>
          </div>

          {(problem || error) && <p className="text-sm text-bad">{problem ?? error}</p>}
          {searched?.note && <p className="text-xs text-faint">{searched.note}</p>}

          {loading ? (
            <Spinner className="py-8" />
          ) : shown.length === 0 ? (
            <EmptyState
              icon={searched ? SearchIcon : NotebookPen}
              title={
                searched
                  ? "No note matches that"
                  : filter === "all"
                    ? "Nothing written down yet"
                    : `No ${KIND_LABEL[filter as NoteKind].toLowerCase()}s yet`
              }
              hint={
                searched
                  ? "Try fewer, plainer words, or clear the search to see everything."
                  : "The next time you correct your coworker, or explain how you want something done, write it here — it reads these before every task."
              }
            />
          ) : (
            <Stagger className="space-y-2">
              {shown.map((n) => (
                <div
                  key={n.id}
                  className={cn(
                    "stagger-item group rounded-xl border bg-panel transition-colors",
                    editing?.id === n.id ? "border-accent/40" : "border-edge hover:border-edge2",
                  )}
                >
                  {editing?.id === n.id ? (
                    <div className="p-4">
                      <NoteEditor
                        note={n}
                        onClose={() => setEditing(null)}
                        onSaved={async () => {
                          setEditing(null);
                          await refresh();
                        }}
                      />
                    </div>
                  ) : (
                    <div className="flex items-start gap-3 p-4">
                      <span
                        className={cn(
                          "mt-1 shrink-0",
                          n.kind === "feedback" ? "text-warn" : "text-accent",
                        )}
                      >
                        {n.kind === "feedback" ? (
                          <MessageSquareWarning size={15} />
                        ) : (
                          <NotebookPen size={15} />
                        )}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="whitespace-pre-wrap text-sm leading-relaxed text-ink">
                          {n.note}
                        </p>
                        <div className="mt-2 flex flex-wrap items-center gap-2">
                          <Badge tone={n.kind === "feedback" ? "warn" : "accent"}>
                            {KIND_LABEL[n.kind]}
                          </Badge>
                          <span className="text-xs text-faint">{formatRelative(n.updatedAt)}</span>
                        </div>
                      </div>
                      <div className="flex shrink-0 items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
                        <IconButton aria-label="Edit note" onClick={() => setEditing(n)}>
                          <Pencil size={14} />
                        </IconButton>
                        <IconButton aria-label="Delete note" onClick={() => setDeleting(n)}>
                          <Trash2 size={14} />
                        </IconButton>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </Stagger>
          )}
        </div>
      </div>

      <ConfirmDelete
        open={!!deleting}
        onClose={() => setDeleting(null)}
        what="this note"
        onConfirm={async () => {
          if (!deleting) return;
          await api(`/api/v1/notes/${deleting.id}`, { method: "DELETE" });
          setDeleting(null);
          await refresh();
        }}
      />
    </PageEnter>
  );
}

function KindToggle({
  value,
  onChange,
}: {
  value: NoteKind;
  onChange: (k: NoteKind) => void;
}) {
  return (
    <div className="flex items-center gap-1 rounded-lg border border-edge bg-panel2 p-0.5">
      {NOTE_KINDS.map((k) => (
        <button
          key={k}
          type="button"
          onClick={() => onChange(k)}
          title={KIND_HINT[k]}
          className={cn(
            "rounded-md px-2.5 py-1 text-xs transition-colors",
            value === k ? "bg-panel text-ink font-medium shadow-sm" : "text-sub hover:text-ink",
          )}
        >
          {KIND_LABEL[k]}
        </button>
      ))}
    </div>
  );
}

function Composer({ onSaved }: { onSaved: () => void | Promise<void> }) {
  const [note, setNote] = useState("");
  const [kind, setKind] = useState<NoteKind>("note");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!note.trim()) return;
    setBusy(true);
    setError(null);
    try {
      await api("/api/v1/notes", { method: "POST", body: { note: note.trim(), kind } });
      setNote("");
      setKind("note");
      await onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form
      onSubmit={submit}
      className="rounded-xl border border-edge bg-panel p-4 focus-within:border-accent/50 transition-colors"
    >
      <Textarea
        value={note}
        onChange={(e) => setNote(e.target.value)}
        rows={2}
        placeholder='e.g. "Never open a page with a rhetorical question" or "We do not sell to agencies — stop suggesting agency keywords"'
        className="border-0 bg-transparent p-0 focus:ring-0"
      />
      <div className="mt-3 flex flex-wrap items-center justify-between gap-2 border-t border-edge pt-3">
        <KindToggle value={kind} onChange={setKind} />
        <div className="flex items-center gap-3">
          <span className="hidden text-xs text-faint sm:block">
            Worth keeping if it will still be true next month.
          </span>
          <Button type="submit" size="sm" disabled={busy || !note.trim()}>
            {busy ? "Saving…" : "Save note"}
          </Button>
        </div>
      </div>
      {error && <p className="mt-2 text-xs text-bad">{error}</p>}
    </form>
  );
}

function NoteEditor({
  note,
  onClose,
  onSaved,
}: {
  note: Note;
  onClose: () => void;
  onSaved: () => void | Promise<void>;
}) {
  const [text, setText] = useState(note.note);
  const [kind, setKind] = useState<NoteKind>(note.kind);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const changed = text.trim() !== note.note || kind !== note.kind;

  async function save() {
    if (!text.trim() || !changed) return;
    setBusy(true);
    setError(null);
    try {
      await api(`/api/v1/notes/${note.id}`, {
        method: "PUT",
        body: { note: text.trim(), kind },
      });
      await onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save that.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-3">
      <Textarea autoFocus value={text} onChange={(e) => setText(e.target.value)} rows={3} />
      <div className="flex flex-wrap items-center justify-between gap-2">
        <KindToggle value={kind} onChange={setKind} />
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button size="sm" onClick={() => void save()} disabled={busy || !text.trim() || !changed}>
            {busy ? "Saving…" : "Save"}
          </Button>
        </div>
      </div>
      {error && <p className="text-xs text-bad">{error}</p>}
    </div>
  );
}
