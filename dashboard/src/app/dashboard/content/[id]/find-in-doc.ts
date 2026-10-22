import { Extension } from "@tiptap/core";
import type { Node as PMNode } from "@tiptap/pm/model";
import { Plugin, PluginKey } from "@tiptap/pm/state";
import { Decoration, DecorationSet } from "@tiptap/pm/view";
import type { TextRange } from "./issue-highlights";

export interface FindState {
  query: string;
  active: number;
}

export const findKey = new PluginKey<FindState>("findInDoc");

export function findAll(doc: PMNode, query: string): TextRange[] {
  const needle = query.toLocaleLowerCase();
  if (!needle) return [];
  const ranges: TextRange[] = [];
  doc.descendants((node, pos) => {
    if (!node.isTextblock) return true;
    const segments: Array<{ from: number; text: string }> = [];
    node.forEach((child, offset) => {
      if (child.isText && child.text) segments.push({ from: pos + 1 + offset, text: child.text });
    });
    if (segments.length === 0) return false;
    const full = segments.map((s) => s.text).join("").toLocaleLowerCase();
    const map = (offset: number): number => {
      let seen = 0;
      for (const s of segments) {
        if (offset <= seen + s.text.length) return s.from + (offset - seen);
        seen += s.text.length;
      }
      const last = segments[segments.length - 1];
      return last.from + last.text.length;
    };
    for (let index = full.indexOf(needle); index >= 0; index = full.indexOf(needle, index + needle.length)) {
      ranges.push({ from: map(index), to: map(index + needle.length) });
    }
    return false;
  });
  return ranges;
}

export const FindInDoc = Extension.create({
  name: "findInDoc",
  addProseMirrorPlugins() {
    return [
      new Plugin({
        key: findKey,
        state: {
          init: (): FindState => ({ query: "", active: 0 }),
          apply: (tr, prev) => (tr.getMeta(findKey) as FindState | undefined) ?? prev,
        },
        props: {
          decorations(state) {
            const current = findKey.getState(state);
            if (!current?.query) return null;
            const ranges = findAll(state.doc, current.query);
            return DecorationSet.create(
              state.doc,
              ranges.map((r, i) =>
                Decoration.inline(r.from, r.to, {
                  class: i === current.active ? "find-mark find-mark-active" : "find-mark",
                }),
              ),
            );
          },
        },
      }),
    ];
  },
});
