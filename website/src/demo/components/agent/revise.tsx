"use client";

import { useEffect, useRef, useState, type ReactElement } from "react";
import { MessageCircleQuestion, Pencil, Undo2 } from "lucide-react";
import { Button } from "@demo/components/ui";
import { useIsApp } from "@demo/lib/use-app-mode";
import { cn } from "@demo/lib/utils";

export type ReviseKind = "email" | "draft" | "post" | "caption" | "reply" | "fix" | "prose";

export type ReviseNudge = "shorter" | "warmer" | "rephrase";

const FORBIDDEN_SELECTOR =
  "[data-finding],[data-measured],[data-measurement],.evidence,.finding,.measured,.metrics";

const FORBIDDEN_KINDS = ["finding", "measurement", "metric", "evidence", "observation"];

export interface ReviseRequest {
  nudge: ReviseNudge | null;
  instruction: string;
  selection: string | null;
  text: string;
  kind: ReviseKind;
}

export type ReviseResponse =
  | string
  | { text: string; note?: string }
  | { answer: string }
  | null
  | undefined;

export interface ReviseProps {
  kind: ReviseKind;
  value: string;
  onChange: (next: string) => void;
  onRevise: (req: ReviseRequest) => Promise<ReviseResponse> | ReviseResponse;
  label?: string;
  className?: string;
  readOnly?: boolean;
}

const NUDGES: Array<{ key: ReviseNudge; label: string; sentence: string }> = [
  { key: "shorter", label: "Shorter", sentence: "Make this shorter without losing the point." },
  { key: "warmer", label: "Warmer", sentence: "Make this warmer — less transactional." },
  { key: "rephrase", label: "Rephrase", sentence: "Say this a different way." },
];

interface Range {
  start: number;
  end: number;
}

export function Revise({
  kind,
  value,
  onChange,
  onRevise,
  label,
  className,
  readOnly,
}: ReviseProps): ReactElement | null {
  const hostRef = useRef<HTMLDivElement>(null);
  const proseRef = useRef<HTMLDivElement>(null);
  const [refused, setRefused] = useState(FORBIDDEN_KINDS.includes(String(kind)));
  const [changed, setChanged] = useState<Range | null>(null);
  const [undo, setUndo] = useState<{ text: string; changed: Range | null } | null>(null);
  const [selection, setSelection] = useState<(Range & { text: string }) | null>(null);
  const [asking, setAsking] = useState(false);
  const [instruction, setInstruction] = useState("");
  const [busy, setBusy] = useState(false);
  const [answer, setAnswer] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);

  const isApp = useIsApp();

  useEffect(() => {
    if (refused) return;
    const el = hostRef.current;
    if (!el) return;
    if (el.closest(FORBIDDEN_SELECTOR)) {
      setRefused(true);
      if (process.env.NODE_ENV !== "production") {
        console.warn(
          "[agent] <Revise> refused to mount inside a finding or a measurement. " +
            "Observations are not revisable — rephrasing one is how a number becomes a claim.",
        );
      }
    }
  }, [refused]);

  useEffect(() => {
    if (refused && FORBIDDEN_KINDS.includes(String(kind)) && process.env.NODE_ENV !== "production") {
      console.warn(
        `[agent] <Revise kind="${kind}"> refused to mount. Findings and measurements are ` +
          "not revisable — see the header of revise.tsx.",
      );
    }
  }, [refused, kind]);

  if (refused) return null;

  function readSelection() {
    const root = proseRef.current;
    const sel = typeof window !== "undefined" ? window.getSelection() : null;
    if (!root || !sel || sel.isCollapsed || sel.rangeCount === 0) return setSelection(null);
    const range = sel.getRangeAt(0);
    if (!root.contains(range.commonAncestorContainer)) return setSelection(null);
    const start = offsetOf(root, range.startContainer, range.startOffset);
    const end = offsetOf(root, range.endContainer, range.endOffset);
    if (start === null || end === null || end <= start) return setSelection(null);
    const text = value.slice(start, end);
    if (!text.trim()) return setSelection(null);
    setSelection({ start, end, text });
  }

  async function apply(req: Omit<ReviseRequest, "text" | "kind">) {
    setBusy(true);
    setError(null);
    setAnswer(null);
    setNote(null);
    try {
      const res = await onRevise({ ...req, text: value, kind });
      const normal =
        typeof res === "string" ? { text: res } : res && typeof res === "object" ? res : null;
      if (!normal) return;

      if ("answer" in normal) {
        setAnswer(normal.answer);
        return;
      }
      const next = normal.text?.trim();
      if (!next) return;

      setUndo({ text: value, changed });
      if (req.selection && selection) {
        const merged = value.slice(0, selection.start) + next + value.slice(selection.end);
        setChanged({ start: selection.start, end: selection.start + next.length });
        onChange(merged);
      } else {
        setChanged({ start: 0, end: next.length });
        onChange(next);
      }
      if (normal.note) setNote(normal.note);
      setSelection(null);
      window.getSelection()?.removeAllRanges();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That did not go through.");
    } finally {
      setBusy(false);
      setAsking(false);
      setInstruction("");
    }
  }

  const segments = splitByRange(value, changed);

  return (
    <div ref={hostRef} className={cn("space-y-2", className)}>
      {label && <p className="text-[11px] font-medium uppercase tracking-wide text-faint">{label}</p>}

      {editing ? (
        <textarea
          autoFocus
          value={value}
          onChange={(e) => {
            setChanged(null);
            onChange(e.target.value);
          }}
          onBlur={() => setEditing(false)}
          rows={Math.min(20, Math.max(4, value.split("\n").length + 1))}
          className="w-full resize-y rounded-lg bg-panel2 border border-edge2 px-3 py-2 text-sm leading-relaxed text-ink focus:outline-none focus:border-accent"
        />
      ) : (
        <div
          ref={proseRef}
          onMouseUp={readSelection}
          onKeyUp={readSelection}
          className="rounded-lg border border-edge bg-panel px-3 py-2.5 text-sm leading-relaxed text-ink whitespace-pre-wrap select-text"
        >
          {segments.map((s, i) => (
            <span
              key={i}
              data-off={s.start}
              className={s.changed ? "bg-accent-soft underline decoration-accent/40" : undefined}
            >
              {s.text}
            </span>
          ))}
        </div>
      )}

      {!readOnly && (
        <>
          {isApp && selection && !editing && (
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] text-faint">Selected:</span>
              {NUDGES.map((n) => (
                <button
                  key={n.key}
                  type="button"
                  disabled={busy}
                  onClick={() =>
                    void apply({
                      nudge: n.key,
                      instruction: n.sentence,
                      selection: selection.text,
                    })
                  }
                  className="rounded-full border border-edge2 bg-panel2 px-2.5 py-1 text-xs text-sub hover:border-accent hover:text-accent transition-colors cursor-pointer disabled:opacity-50"
                >
                  {n.label}
                </button>
              ))}
              <button
                type="button"
                disabled={busy}
                onClick={() => setAsking(true)}
                className="rounded-full border border-accent/40 bg-accent-soft px-2.5 py-1 text-xs text-accent hover:border-accent transition-colors cursor-pointer disabled:opacity-50"
              >
                Ask…
              </button>
            </div>
          )}

          {isApp && asking && (
            <div className="rounded-lg border border-edge bg-panel2/60 p-3 space-y-2">
              <p className="text-[11px] font-medium uppercase tracking-wide text-faint">
                {selection ? "Changing the selected sentence" : "Ask for a change — or an opinion"}
              </p>
              <textarea
                autoFocus
                rows={2}
                value={instruction}
                onChange={(e) => setInstruction(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && (e.metaKey || e.ctrlKey) && instruction.trim()) {
                    e.preventDefault();
                    void apply({
                      nudge: null,
                      instruction: instruction.trim(),
                      selection: selection?.text ?? null,
                    });
                  }
                }}
                placeholder="e.g. too soft. lead with the number, one sentence — or: is the no-show line too much?"
                className="w-full resize-none rounded-lg bg-panel border border-edge2 px-3 py-2 text-sm text-ink placeholder:text-faint focus:outline-none focus:border-accent"
              />
              <div className="flex justify-end gap-1.5">
                <Button size="sm" variant="ghost" onClick={() => setAsking(false)} disabled={busy}>
                  Cancel
                </Button>
                <Button
                  size="sm"
                  disabled={busy || !instruction.trim()}
                  onClick={() =>
                    void apply({
                      nudge: null,
                      instruction: instruction.trim(),
                      selection: selection?.text ?? null,
                    })
                  }
                >
                  {busy ? "Working…" : "Send"}
                </Button>
              </div>
            </div>
          )}

          {answer && (
            <div className="rounded-lg border border-edge2 bg-panel2 px-3 py-2.5">
              <p className="text-sm text-ink leading-relaxed whitespace-pre-wrap">{answer}</p>
              <p className="mt-1 text-[11px] text-faint">
                {"An answer, not an edit — the text is unchanged."}
              </p>
              <button
                type="button"
                onClick={() => setAnswer(null)}
                className="mt-1 text-[11px] text-accent underline cursor-pointer"
              >
                Dismiss
              </button>
            </div>
          )}

          {note && <p className="text-[11px] text-sub">{note}</p>}
          {error && <p className="text-xs text-bad">{error}</p>}

          <div className="flex flex-wrap items-center gap-1.5">
            <button
              type="button"
              onClick={() => setEditing((v) => !v)}
              className="inline-flex items-center gap-1 text-xs text-sub hover:text-accent transition-colors cursor-pointer"
            >
              <Pencil size={12} /> {editing ? "Done typing" : "Type over it"}
            </button>
            {isApp && (
              <button
                type="button"
                disabled={busy}
                onClick={() => {
                  setSelection(null);
                  setAsking(true);
                }}
                className="inline-flex items-center gap-1 text-xs text-sub hover:text-accent transition-colors cursor-pointer disabled:opacity-50"
              >
                <MessageCircleQuestion size={12} /> Ask for a change
              </button>
            )}
            {undo && (
              <button
                type="button"
                onClick={() => {
                  onChange(undo.text);
                  setChanged(undo.changed);
                  setUndo(null);
                }}
                className="inline-flex items-center gap-1 text-xs text-sub hover:text-accent transition-colors cursor-pointer"
              >
                <Undo2 size={12} /> Undo last change
              </button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

function splitByRange(
  text: string,
  range: Range | null,
): Array<{ text: string; start: number; changed: boolean }> {
  if (!range || range.start >= range.end || range.end > text.length) {
    return [{ text, start: 0, changed: false }];
  }
  const out: Array<{ text: string; start: number; changed: boolean }> = [];
  if (range.start > 0) out.push({ text: text.slice(0, range.start), start: 0, changed: false });
  out.push({ text: text.slice(range.start, range.end), start: range.start, changed: true });
  if (range.end < text.length) {
    out.push({ text: text.slice(range.end), start: range.end, changed: false });
  }
  return out;
}

function offsetOf(root: HTMLElement, node: Node, offset: number): number | null {
  let el: Node | null = node;
  if (el.nodeType === Node.TEXT_NODE) el = el.parentElement;
  while (el && el !== root && !(el instanceof HTMLElement && el.dataset.off !== undefined)) {
    el = el.parentElement;
  }
  if (el instanceof HTMLElement && el.dataset.off !== undefined) {
    return Number(el.dataset.off) + offset;
  }
  if (el === root) {
    const child = root.childNodes[Math.min(offset, root.childNodes.length - 1)];
    if (child instanceof HTMLElement && child.dataset.off !== undefined) {
      const past = offset >= root.childNodes.length;
      return Number(child.dataset.off) + (past ? (child.textContent?.length ?? 0) : 0);
    }
  }
  return null;
}
