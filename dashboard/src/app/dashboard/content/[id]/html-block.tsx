"use client";

import { useEffect, useRef, useState } from "react";
import { Node } from "@tiptap/core";
import {
  NodeViewWrapper,
  ReactNodeViewRenderer,
  useEditorState,
  type ReactNodeViewProps,
} from "@tiptap/react";
import { Code2, Eye, Trash2 } from "lucide-react";
import { Lexer } from "marked";
import { openDocLink } from "./links";

const WRAP_OPEN = "<div data-meelu-html>";
const WRAP_CLOSE = "</div>";

function readsAsBlock(html: string): boolean {
  const tokens = Lexer.lex(html).filter((t) => t.type !== "space");
  return tokens.length === 1 && tokens[0].type === "html" && Boolean(tokens[0].block);
}

export function htmlToMarkdown(html: string): string {
  const trimmed = html.trim();
  if (!trimmed || readsAsBlock(trimmed)) return trimmed;
  const compact = trimmed.replace(/\n\s*\n/g, "\n");
  return readsAsBlock(compact) ? compact : `${WRAP_OPEN}\n${compact}\n${WRAP_CLOSE}`;
}

export function htmlFromMarkdown(raw: string): string {
  const trimmed = raw.trim();
  const open = `${WRAP_OPEN}\n`;
  const close = `\n${WRAP_CLOSE}`;
  if (trimmed.startsWith(open) && trimmed.endsWith(close)) {
    return trimmed.slice(open.length, trimmed.length - close.length);
  }
  return trimmed;
}

export const HtmlBlock = Node.create({
  name: "htmlBlock",
  group: "block",
  atom: true,
  selectable: true,
  draggable: true,

  addAttributes() {
    return {
      html: { default: "" },
      editing: { default: false, rendered: false },
    };
  },

  parseHTML() {
    return [
      {
        tag: "div[data-html-block]",
        getAttrs: (el) => ({ html: (el as HTMLElement).getAttribute("data-html") ?? "" }),
      },
    ];
  },

  renderHTML({ node }) {
    return ["div", { "data-html-block": "", "data-html": node.attrs.html }];
  },

  markdownTokenName: "html",

  parseMarkdown: (token, helpers) => {
    if (!token.block) return [];
    const html = htmlFromMarkdown(String(token.raw ?? token.text ?? ""));
    if (!html) return [];
    return helpers.createNode("htmlBlock", { html });
  },

  renderMarkdown: (node) => htmlToMarkdown(String(node.attrs?.html ?? "")),

  addNodeView() {
    return ReactNodeViewRenderer(HtmlBlockView);
  },
});

export function htmlSnippet(text: string): string | null {
  const html = text.trim();
  if (!/^<[a-zA-Z][\w-]*[\s>/]/.test(html) || !html.endsWith(">")) return null;
  const parsed = new DOMParser().parseFromString(html, "text/html");
  return parsed.body.children.length > 0 || parsed.head.children.length > 0 ? html : null;
}

function frameDocument(html: string): string {
  const style = typeof document === "undefined" ? null : getComputedStyle(document.body);
  const color = style?.color ?? "inherit";
  const font = style?.fontFamily ?? "inherit";
  return `<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;padding:0;background:transparent;color:${color};font-family:${font};font-size:17px;line-height:1.7;overflow:hidden}
img,video,iframe{max-width:100%;height:auto}
table{border-collapse:collapse}
th,td{border:1px solid color-mix(in srgb,currentColor 25%,transparent);padding:6px 10px;text-align:left}
a{color:inherit}
</style></head><body>${html}</body></html>`;
}

function HtmlBlockView({
  node,
  editor,
  updateAttributes,
  deleteNode,
  selected,
}: ReactNodeViewProps) {
  const html = String(node.attrs.html ?? "");
  const [editing, setEditing] = useState<boolean>(Boolean(node.attrs.editing) || !html.trim());
  const frame = useRef<HTMLIFrameElement>(null);
  const [height, setHeight] = useState(40);
  const editable = useEditorState({ editor, selector: ({ editor }) => editor.isEditable });

  useEffect(() => {
    if (editing) return;
    const el = frame.current;
    if (!el) return;
    let observer: ResizeObserver | null = null;
    const onClick = (event: MouseEvent) => {
      const anchor = (event.target as Element | null)?.closest("a") ?? null;
      if (!anchor) return;
      event.preventDefault();
      if (!editor.isEditable) openDocLink(anchor, el);
    };
    const measure = () => {
      const doc = el.contentDocument;
      if (!doc?.documentElement) return;
      setHeight(Math.max(24, doc.documentElement.scrollHeight));
    };
    const onLoad = () => {
      measure();
      const doc = el.contentDocument;
      if (doc?.documentElement) {
        observer = new ResizeObserver(measure);
        observer.observe(doc.documentElement);
        doc.addEventListener("click", onClick);
      }
    };
    el.addEventListener("load", onLoad);
    return () => {
      el.removeEventListener("load", onLoad);
      el.contentDocument?.removeEventListener("click", onClick);
      observer?.disconnect();
    };
  }, [editing, html, editor]);

  return (
    <NodeViewWrapper
      className={
        "group relative rounded-lg border " +
        (selected || editing ? "border-accent/50" : "border-transparent hover:border-edge2")
      }
    >
      {editable && (
        <div
          contentEditable={false}
          className={
            "absolute -top-3 right-2 z-10 flex items-center gap-1 rounded-md border border-edge bg-panel px-1 py-0.5 text-xs text-sub shadow-sm " +
            (editing || selected ? "" : "opacity-0 group-hover:opacity-100")
          }
        >
          <span className="px-1 text-faint">HTML</span>
          <button
            type="button"
            onClick={() => setEditing((v) => !v)}
            className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 hover:bg-panel2 hover:text-ink cursor-pointer"
          >
            {editing ? <Eye size={12} /> : <Code2 size={12} />}
            {editing ? "Preview" : "Edit HTML"}
          </button>
          <button
            type="button"
            aria-label="Remove HTML block"
            onClick={() => deleteNode()}
            className="inline-flex items-center rounded px-1 py-0.5 hover:bg-panel2 hover:text-bad cursor-pointer"
          >
            <Trash2 size={12} />
          </button>
        </div>
      )}
      {editing && editable ? (
        <textarea
          contentEditable={false}
          value={html}
          autoFocus
          spellCheck={false}
          onChange={(e) => updateAttributes({ html: e.target.value })}
          onKeyDown={(e) => e.stopPropagation()}
          placeholder="<table>…</table>"
          rows={Math.min(24, Math.max(4, html.split("\n").length + 1))}
          className="block w-full resize-y rounded-lg bg-panel2 p-3 font-mono text-[13px] leading-relaxed text-ink focus:outline-none"
        />
      ) : (
        <iframe
          ref={frame}
          title="HTML block"
          sandbox="allow-same-origin"
          srcDoc={frameDocument(html)}
          style={{ height }}
          className="block w-full border-0"
        />
      )}
    </NodeViewWrapper>
  );
}
