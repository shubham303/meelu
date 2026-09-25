"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { ArrowUp, Paperclip, Sparkles, Square } from "lucide-react";
import { IconButton } from "@/components/ui";
import { cn } from "@/lib/utils";
import { ChatMarkdown } from "./chat-markdown";

function Said({ children }: { children: ReactNode }) {
  return (
    <div className="flex gap-3">
      <Sparkles size={14} className="mt-1 shrink-0 text-accent" aria-hidden />
      <div className="min-w-0 flex-1">{children}</div>
    </div>
  );
}

function ChatBubble({ children }: { children: ReactNode }) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[85%] rounded-2xl rounded-br-md bg-accent-soft px-4 py-2.5 text-sm leading-relaxed whitespace-pre-wrap text-ink">
        {children}
      </div>
    </div>
  );
}

function Dot({ delay }: { delay: string }) {
  return (
    <span
      className="h-1 w-1 self-end rounded-full bg-faint animate-bounce"
      style={{ animationDelay: delay }}
      aria-hidden
    />
  );
}

export interface ChatChip {
  label: string;
  hint?: string;
  tier?: "L" | "M" | "H";
  disabled?: boolean;
}

function ChatChips<TChip extends ChatChip>({
  chips,
  roomy,
  busy,
  onPick,
}: {
  chips: TChip[];
  roomy?: boolean;
  busy?: boolean;
  onPick: (chip: TChip) => void;
}) {
  if (chips.length === 0) return null;
  return (
    <div className={cn("flex flex-wrap gap-1.5", roomy && "gap-2")}>
      {chips.map((chip) => (
        <button
          key={chip.label}
          type="button"
          disabled={busy || chip.disabled}
          title={chip.hint}
          onClick={() => onPick(chip)}
          className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent-soft px-3 py-1.5 text-xs font-medium text-accent transition-colors hover:border-accent cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Sparkles size={11} className="shrink-0" />
          {chip.label}
          {chip.tier && (
            <span className="rounded bg-accent/15 px-1 font-mono text-[10px] leading-4">
              {chip.tier}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}

export type AgentChatItem =
  | { kind: "user"; key: string | number; text: string; files?: string[] }
  | { kind: "assistant"; key: string | number; text: string }
  | { kind: "tool"; key: string | number; text: string }
  | { kind: "custom"; key: string | number; render: ReactNode };

export interface AgentChatProps<TChip extends ChatChip = ChatChip> {
  items: AgentChatItem[];
  busy?: boolean;
  thinkingLabel?: string;
  emptyState?: ReactNode;
  chips?: TChip[];
  chipsRoomy?: boolean;
  onPickChip?: (chip: TChip) => void;
  onSend: (text: string) => void;
  onStop?: () => void;
  allowEmptySend?: boolean;
  disabled?: boolean;
  placeholder?: string;
  busyPlaceholder?: string;
  onAttach?: () => void;
  attachmentsSlot?: ReactNode;
  helperText?: string;
  error?: string | null;
  footer?: ReactNode;
  sendLabel?: string;
  stopLabel?: string;
  autoFocus?: boolean;
  showThinking?: boolean;
  layout?: "panel" | "bounded" | "inline";
  logClassName?: string;
  className?: string;
}

export function AgentChat<TChip extends ChatChip = ChatChip>({
  items,
  busy,
  thinkingLabel = "Thinking",
  showThinking = true,
  emptyState,
  chips = [],
  chipsRoomy,
  onPickChip,
  onSend,
  onStop,
  allowEmptySend,
  disabled,
  placeholder = "Ask something, or say what you want done…",
  busyPlaceholder = "Working…",
  onAttach,
  attachmentsSlot,
  helperText,
  error,
  footer,
  sendLabel = "Send",
  stopLabel = "Stop",
  autoFocus,
  layout = "panel",
  logClassName,
  className,
}: AgentChatProps<TChip>) {
  const [text, setText] = useState("");
  const logRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (layout === "inline") return;
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [items, busy, layout]);

  const canSend = !busy && !disabled && (text.trim().length > 0 || Boolean(allowEmptySend));

  function submit() {
    if (!canSend) return;
    const value = text.trim();
    setText("");
    if (inputRef.current) inputRef.current.style.height = "auto";
    onSend(value);
  }

  const showEmpty = items.length === 0 && !busy && (Boolean(emptyState) || chips.length > 0);
  const lastKind = items[items.length - 1]?.kind;

  return (
    <div className={cn("flex flex-col gap-4", layout === "panel" && "h-full", className)}>
      <div
        ref={logRef}
        className={cn(
          "space-y-6",
          layout === "inline" ? "" : "overflow-y-auto pr-1",
          layout === "panel" && "flex-1",
          layout === "bounded" && (logClassName ?? "max-h-80"),
        )}
      >
        {showEmpty && (
          <div className="space-y-5 pt-2">
            {emptyState}
            <ChatChips chips={chips} roomy={chipsRoomy} busy={busy} onPick={(c) => onPickChip?.(c)} />
          </div>
        )}

        {items.map((item) => {
          if (item.kind === "user") {
            return (
              <ChatBubble key={item.key}>
                {(item.files ?? []).length > 0 && (
                  <span className="flex flex-wrap gap-1.5 mb-1.5">
                    {(item.files ?? []).map((name, j) => (
                      <span
                        key={j}
                        className="inline-flex items-center gap-1 rounded-full border border-edge bg-panel px-2 py-0.5 text-[11px] text-sub"
                      >
                        <Paperclip size={10} className="shrink-0" />
                        {name}
                      </span>
                    ))}
                  </span>
                )}
                {item.text}
              </ChatBubble>
            );
          }
          if (item.kind === "assistant") {
            return (
              <Said key={item.key}>
                <div className="text-sm leading-relaxed text-ink">
                  <ChatMarkdown text={item.text} />
                </div>
              </Said>
            );
          }
          if (item.kind === "tool") {
            return (
              <p
                key={item.key}
                className="flex items-center gap-1.5 text-[11px] text-faint font-mono"
              >
                {item.text}
              </p>
            );
          }
          return <div key={item.key}>{item.render}</div>;
        })}

        {showThinking && busy && lastKind !== "assistant" && (
          <Said>
            <span className="inline-flex items-center gap-1.5 text-sm text-faint">
              {thinkingLabel}
              <span className="inline-flex gap-0.5">
                <Dot delay="0ms" />
                <Dot delay="150ms" />
                <Dot delay="300ms" />
              </span>
            </span>
          </Said>
        )}
      </div>

      {error && <p className="text-xs text-bad">{error}</p>}

      {footer ?? (
        <div className={cn("flex flex-col gap-4", layout === "inline" && "sticky bottom-4")}>
          <div
            className={cn(
              "rounded-2xl border border-edge2 bg-panel2 px-3 py-2.5 focus-within:border-accent transition-colors",
              layout === "inline" && "shadow-[0_6px_20px_rgb(31_45_61/0.06)]",
            )}
          >
            {attachmentsSlot}
            <div className="flex items-end gap-2">
              {onAttach && (
                <IconButton
                  type="button"
                  onClick={onAttach}
                  disabled={busy}
                  aria-label="Attach files"
                >
                  <Paperclip size={15} />
                </IconButton>
              )}
              <textarea
                ref={inputRef}
                autoFocus={autoFocus}
                rows={1}
                value={text}
                disabled={busy || disabled}
                onChange={(e) => {
                  setText(e.target.value);
                  const el = e.currentTarget;
                  el.style.height = "auto";
                  el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    submit();
                  }
                }}
                placeholder={busy ? busyPlaceholder : placeholder}
                className="flex-1 resize-none bg-transparent py-1.5 text-sm text-ink placeholder:text-faint focus:outline-none disabled:opacity-60 max-h-44"
              />
              {busy && onStop ? (
                <button
                  type="button"
                  onClick={onStop}
                  aria-label={stopLabel}
                  title={stopLabel}
                  className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-edge2 text-sub transition-colors hover:border-accent hover:text-accent cursor-pointer"
                >
                  <Square size={12} />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={submit}
                  disabled={!canSend}
                  aria-label={sendLabel}
                  title={sendLabel}
                  className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-white transition-opacity hover:opacity-90 cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  <ArrowUp size={15} />
                </button>
              )}
            </div>
          </div>
          {helperText && <p className="text-xs text-faint leading-relaxed">{helperText}</p>}
        </div>
      )}
    </div>
  );
}
