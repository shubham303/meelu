"use client";

import { useState, type ReactNode } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Button, Card, Textarea } from "@demo/components/ui";
import { api } from "@demo/lib/use-api";
import { cn } from "@demo/lib/utils";
import type { LeadBrief, LeadSource } from "@demo/lib/types";
import { chipLabel, DEFAULT_SOURCES, MAX_BRIEFS, SOURCE_OPTIONS } from "./lib";

export const NEW_BRIEF = "new";

function SourceChips({ sources }: { sources: LeadSource[] }) {
  return (
    <span className="flex flex-wrap gap-1.5">
      {sources.map((s) => (
        <span key={s} className="rounded-full bg-accent-soft px-2 py-0.5 text-[12px] text-accent">
          {chipLabel(s)}
        </span>
      ))}
    </span>
  );
}

function BriefEditor({
  brief,
  onSaved,
  onDeleted,
  onCancel,
}: {
  brief: LeadBrief | null;
  onSaved: (id: string) => Promise<void>;
  onDeleted: () => Promise<void>;
  onCancel: () => void;
}) {
  const [text, setText] = useState(brief?.text ?? "");
  const [sources, setSources] = useState<LeadSource[]>(brief?.sources ?? DEFAULT_SOURCES);
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = (id: LeadSource) =>
    setSources((prev) => (prev.includes(id) ? prev.filter((s) => s !== id) : [...prev, id]));

  const save = async () => {
    const clean = text.trim();
    if (!clean) {
      setError("Describe who you are looking for.");
      return;
    }
    if (sources.length === 0) {
      setError("Pick at least one place to look.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const saved = brief
        ? await api<LeadBrief>(`/api/v1/find-leads/briefs/${brief.id}`, {
            method: "PATCH",
            body: { text: clean, sources },
          })
        : await api<LeadBrief>("/api/v1/find-leads/briefs", { method: "POST", body: { text: clean, sources } });
      await onSaved(saved.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "The brief did not save.");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!brief) {
      onCancel();
      return;
    }
    if (!confirming) {
      setConfirming(true);
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await api(`/api/v1/find-leads/briefs/${brief.id}`, { method: "DELETE" });
      await onDeleted();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The brief was not deleted.");
      setBusy(false);
    }
  };

  return (
    <div className="space-y-3.5 px-3.5 pt-1 pb-3.5">
      <label className="block space-y-1.5">
        <span className="block text-[13px] font-semibold text-ink">Who are they?</span>
        <Textarea
          rows={2}
          autoFocus={!brief}
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="e.g. Owners of small online stores who say their Google traffic dropped"
          className="min-h-0 bg-white leading-relaxed"
        />
      </label>
      <fieldset className="space-y-2">
        <legend className="mb-2 text-[13px] font-semibold text-ink">Where to look</legend>
        <div className="grid gap-2 sm:grid-cols-3">
          {SOURCE_OPTIONS.map((s) => {
            const on = sources.includes(s.id);
            return (
              <label
                key={s.id}
                className={cn(
                  "flex cursor-pointer gap-2.5 rounded-xl border px-3 py-2.5",
                  on ? "border-accent/40 bg-accent-soft" : "border-edge",
                )}
              >
                <input
                  type="checkbox"
                  checked={on}
                  onChange={() => toggle(s.id)}
                  className="mt-0.5 h-4 w-4 shrink-0 accent-accent"
                />
                <span className="space-y-0.5">
                  <span className="block text-[13.5px] font-semibold text-ink">{s.label}</span>
                  <span className="block text-[12.5px] leading-snug text-sub">{s.hint}</span>
                </span>
              </label>
            );
          })}
        </div>
      </fieldset>
      {error && <p className="text-[13px] text-bad">{error}</p>}
      <div className="flex flex-wrap justify-between gap-2">
        <Button variant="ghost" size="sm" className="text-bad hover:text-bad" disabled={busy} onClick={() => void remove()}>
          {!brief ? "Cancel" : confirming ? "Delete this brief?" : "Delete"}
        </Button>
        <Button size="sm" disabled={busy} onClick={() => void save()}>
          {busy ? "Saving…" : "Save and collapse"}
        </Button>
      </div>
    </div>
  );
}

export function BriefsPanel({
  briefs,
  openId,
  setOpenId,
  refresh,
  runLine,
}: {
  briefs: LeadBrief[];
  openId: string | null;
  setOpenId: (id: string | null) => void;
  refresh: () => Promise<void>;
  runLine: ReactNode;
}) {
  const [panelOpen, setPanelOpen] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const on = briefs.filter((b) => b.enabled).length;
  const full = briefs.length >= MAX_BRIEFS;

  const shown = panelOpen || openId !== null;

  const togglePanel = () => {
    if (shown) {
      setOpenId(null);
      setPanelOpen(false);
    } else {
      setPanelOpen(true);
    }
  };

  const setEnabled = async (brief: LeadBrief, enabled: boolean) => {
    setError(null);
    try {
      await api(`/api/v1/find-leads/briefs/${brief.id}`, { method: "PATCH", body: { enabled } });
    } catch (e) {
      setError(e instanceof Error ? e.message : "The change did not save.");
    }
    await refresh();
  };

  const rows: Array<LeadBrief | null> = openId === NEW_BRIEF ? [...briefs, null] : briefs;

  return (
    <Card className="space-y-1 px-2 py-1.5">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <button
          type="button"
          aria-expanded={shown}
          onClick={togglePanel}
          className="flex min-h-11 flex-1 cursor-pointer items-center gap-2.5 rounded-lg px-2.5 text-left"
        >
          <ChevronRight size={16} className={cn("text-ink transition-transform", shown && "rotate-90")} />
          <span className="text-sm font-semibold text-ink">Who you&apos;re looking for</span>
          <span className="text-[13px] text-sub">
            {briefs.length} of {MAX_BRIEFS} briefs · {on} on
          </span>
        </button>
        <Button
          variant="outline"
          size="sm"
          className="mr-1.5"
          disabled={full || openId === NEW_BRIEF}
          title={full ? `A website can have at most ${MAX_BRIEFS} briefs.` : undefined}
          onClick={() => setOpenId(NEW_BRIEF)}
        >
          + Add brief
        </Button>
      </div>

      {shown && (
        <div className="space-y-2 px-2.5 pb-3">
          {rows.map((brief) => {
            const id = brief?.id ?? NEW_BRIEF;
            const expanded = openId === id;
            return (
              <div
                key={id}
                className={cn("rounded-xl border", expanded ? "border-accent/40 bg-white" : "border-edge")}
              >
                <div className="flex items-center gap-3 py-1.5 pr-2 pl-3">
                  {brief ? (
                    <input
                      type="checkbox"
                      aria-label="Use this brief"
                      checked={brief.enabled}
                      onChange={(e) => void setEnabled(brief, e.target.checked)}
                      className="h-[18px] w-[18px] shrink-0 cursor-pointer accent-accent"
                    />
                  ) : (
                    <span className="h-[18px] w-[18px] shrink-0" />
                  )}
                  <button
                    type="button"
                    aria-expanded={expanded}
                    onClick={() => setOpenId(expanded ? null : id)}
                    className="flex min-h-10 min-w-0 flex-1 cursor-pointer items-center justify-between gap-3 text-left"
                  >
                    <span
                      className={cn(
                        "min-w-0 truncate text-sm",
                        brief?.enabled === false ? "text-sub" : "text-ink",
                      )}
                    >
                      {brief?.text || "New brief"}
                    </span>
                    <span className="flex shrink-0 items-center gap-2">
                      {brief && !expanded && (
                        <>
                          {brief.kept > 0 && (
                            <span className="text-[12px] tabular-nums text-sub">{brief.kept} kept</span>
                          )}
                          <SourceChips sources={brief.sources} />
                        </>
                      )}
                      <ChevronDown
                        size={16}
                        className={cn("text-sub transition-transform", expanded && "rotate-180")}
                      />
                    </span>
                  </button>
                </div>
                {expanded && (
                  <BriefEditor
                    key={id}
                    brief={brief}
                    onCancel={() => setOpenId(null)}
                    onSaved={async () => {
                      setOpenId(null);
                      await refresh();
                    }}
                    onDeleted={async () => {
                      setOpenId(null);
                      await refresh();
                    }}
                  />
                )}
              </div>
            );
          })}
          {error && <p className="text-[13px] text-bad">{error}</p>}
          {runLine && <p className="px-0.5 pt-1 text-[13px] text-sub">{runLine}</p>}
        </div>
      )}
    </Card>
  );
}
