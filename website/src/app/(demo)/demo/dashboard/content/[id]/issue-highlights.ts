import { Extension } from "@tiptap/core";
import type { Node as PMNode } from "@tiptap/pm/model";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";

export interface HighlightState {
  anchors: string[];
  active: string | null;
}

export const highlightKey = new PluginKey<HighlightState>("issueHighlights");

export interface TextRange {
  from: number;
  to: number;
}

export function findText(doc: PMNode, text: string): TextRange | null {
  const needle = text.trim();
  if (!needle) return null;
  let found: TextRange | null = null;
  doc.descendants((node, pos) => {
    if (found || !node.isTextblock) return !found;
    const segments: Array<{ from: number; text: string }> = [];
    node.forEach((child, offset) => {
      if (child.isText && child.text) segments.push({ from: pos + 1 + offset, text: child.text });
    });
    const full = segments.map((s) => s.text).join("");
    const index = full.indexOf(needle);
    if (index < 0) return true;
    const map = (offset: number): number => {
      let seen = 0;
      for (const s of segments) {
        if (offset <= seen + s.text.length) return s.from + (offset - seen);
        seen += s.text.length;
      }
      return segments[segments.length - 1].from + segments[segments.length - 1].text.length;
    };
    found = { from: map(index), to: map(index + needle.length) };
    return false;
  });
  return found;
}

function decorate(doc: PMNode, state: HighlightState): DecorationSet {
  const decorations: Decoration[] = [];
  for (const anchor of state.anchors) {
    const range = findText(doc, anchor);
    if (!range) continue;
    decorations.push(
      Decoration.inline(range.from, range.to, {
        class: anchor === state.active ? "issue-mark issue-mark-active" : "issue-mark",
      }),
    );
  }
  return DecorationSet.create(doc, decorations);
}

export const IssueHighlights = Extension.create({
  name: "issueHighlights",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: highlightKey,
        state: {
          init: (): HighlightState => ({ anchors: [], active: null }),
          apply: (tr, prev) => (tr.getMeta(highlightKey) as HighlightState | undefined) ?? prev,
        },
        props: {
          decorations(state) {
            const current = highlightKey.getState(state);
            if (!current || current.anchors.length === 0) return null;
            return decorate(state.doc, current);
          },
        },
      }),
    ];
  },
});
