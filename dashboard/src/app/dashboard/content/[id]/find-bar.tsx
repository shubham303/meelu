"use client";

import { useEffect, useRef, useState } from "react";
import { useEditorState, type Editor } from "@tiptap/react";
import { ChevronDown, ChevronUp, Search, X } from "lucide-react";
import { findAll, findKey } from "./find-in-doc";

export function FindBar({
  editor,
  focusSignal,
  onClose,
}: {
  editor: Editor;
  focusSignal: number;
  onClose: () => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const doc = useEditorState({ editor, selector: ({ editor }) => editor.state.doc });
  const matches = findAll(doc, query);
  const current = matches.length ? Math.min(active, matches.length - 1) : 0;

  useEffect(() => {
    input.current?.focus();
    input.current?.select();
  }, [focusSignal]);

  const target = matches[current]?.from;

  useEffect(() => {
    editor.view.dispatch(editor.state.tr.setMeta(findKey, { query, active: current }));
  }, [editor, query, current]);

  useEffect(() => {
    if (target === undefined) return;
    const { node } = editor.view.domAtPos(target);
    const el = node instanceof Element ? node : node.parentElement;
    el?.scrollIntoView({ block: "center", behavior: "smooth" });
  }, [editor, target]);

  useEffect(
    () => () => {
      if (!editor.isDestroyed) editor.view.dispatch(editor.state.tr.setMeta(findKey, { query: "", active: 0 }));
    },
    [editor],
  );

  const step = (by: number) => {
    if (!matches.length) return;
    setActive((current + by + matches.length) % matches.length);
  };

  return (
    <div className="sticky top-0 z-20 -mt-2 mb-4 flex justify-end">
      <div className="flex items-center gap-1.5 rounded-lg border border-edge bg-panel px-2.5 py-1.5 shadow-lg">
        <Search size={13} className="text-faint" />
        <input
          ref={input}
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setActive(0);
          }}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              step(e.shiftKey ? -1 : 1);
            } else if (e.key === "Escape") {
              e.preventDefault();
              onClose();
            }
          }}
          placeholder="Find in body"
          aria-label="Find in body"
          className="w-48 bg-transparent text-sm text-ink placeholder:text-faint focus:outline-none"
        />
        <span className="min-w-12 text-right text-xs tabular-nums text-faint">
          {query ? (matches.length ? `${current + 1}/${matches.length}` : "0/0") : ""}
        </span>
        <button type="button" aria-label="Previous match" onClick={() => step(-1)} className="rounded p-0.5 text-sub hover:bg-panel2 hover:text-ink cursor-pointer">
          <ChevronUp size={14} />
        </button>
        <button type="button" aria-label="Next match" onClick={() => step(1)} className="rounded p-0.5 text-sub hover:bg-panel2 hover:text-ink cursor-pointer">
          <ChevronDown size={14} />
        </button>
        <button type="button" aria-label="Close find" onClick={onClose} className="rounded p-0.5 text-sub hover:bg-panel2 hover:text-ink cursor-pointer">
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
