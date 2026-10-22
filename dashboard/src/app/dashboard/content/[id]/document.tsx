"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { EditorContent, useEditor, type Editor } from "@tiptap/react";
import { BubbleMenu } from "@tiptap/react/menus";
import StarterKit from "@tiptap/starter-kit";
import Image from "@tiptap/extension-image";
import Placeholder from "@tiptap/extension-placeholder";
import { Markdown } from "@tiptap/markdown";
import {
  ArrowUp,
  Bold,
  Code2,
  Heading2,
  Heading3,
  ImagePlus,
  Italic,
  Link2,
  List,
  ListOrdered,
  Quote,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { FindBar } from "./find-bar";
import { FindInDoc } from "./find-in-doc";
import { HtmlBlock, htmlSnippet } from "./html-block";
import { openDocLink } from "./links";
import { findText, highlightKey, IssueHighlights } from "./issue-highlights";

export interface SelectionRequest {
  instruction: string;
  passage: string;
}

export interface DocumentProps {
  markdown: string;
  version: number;
  onChange: (markdown: string) => void;
  onSelectionRequest?: (req: SelectionRequest) => Promise<string | null>;
  onReplaceSelection?: (passage: string, replacement: string) => void;
  anchors: string[];
  activeAnchor: string | null;
  editorRef: React.MutableRefObject<Editor | null>;
  editable?: boolean;
  siteOrigin?: string;
}

const QUICK: Array<{ label: string; sentence: string }> = [
  { label: "Rephrase", sentence: "Say this a different way — same meaning, fresh wording." },
  { label: "Shorter", sentence: "Make this shorter without losing the point." },
  { label: "Longer", sentence: "Expand this with a little more detail, in the same voice." },
  { label: "Simpler", sentence: "Simplify the language so a hurried reader gets it in one pass." },
  { label: "Formal", sentence: "Make this more formal and precise." },
];

async function uploadImage(file: File): Promise<string> {
  const form = new FormData();
  form.append("file", file, file.name);
  const res = await fetch("/api/v1/content/media", { method: "POST", body: form });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(payload?.error?.message ?? "Upload failed");
  return `/api/v1/content/media/${payload.data.id}`;
}

export function scrollToAnchor(editor: Editor, anchor: string): boolean {
  const range = findText(editor.state.doc, anchor);
  if (!range) return false;
  editor.chain().focus().setTextSelection(range).scrollIntoView().run();
  return true;
}

export function Document({
  markdown,
  version,
  onChange,
  onSelectionRequest,
  onReplaceSelection,
  anchors,
  activeAnchor,
  editorRef,
  editable = true,
  siteOrigin,
}: DocumentProps) {
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [findSignal, setFindSignal] = useState(0);
  const fileInput = useRef<HTMLInputElement>(null);
  const lastVersion = useRef(version);

  const editor = useEditor({
    immediatelyRender: false,
    extensions: [
      StarterKit.configure({
        heading: { levels: [2, 3, 4] },
        link: { openOnClick: false },
      }),
      Image.configure({ allowBase64: false }),
      Placeholder.configure({ placeholder: "Start writing, or hand the agent a brief…" }),
      Markdown,
      HtmlBlock,
      IssueHighlights,
      FindInDoc,
    ],
    content: markdown,
    contentType: "markdown",
    editorProps: {
      attributes: { class: "piece-doc focus:outline-none" },
      handleClick: (view, _pos, event) => {
        if (view.editable) return false;
        const anchor = (event.target as Element | null)?.closest("a") ?? null;
        if (!anchor) return false;
        event.preventDefault();
        return openDocLink(anchor, view.dom);
      },
      handlePaste: (view, event) => {
        const files = Array.from(event.clipboardData?.files ?? []).filter((f) =>
          f.type.startsWith("image/"),
        );
        if (files.length > 0) {
          event.preventDefault();
          void insertFiles(files);
          return true;
        }
        const html = htmlSnippet(event.clipboardData?.getData("text/plain") ?? "");
        if (!html) return false;
        event.preventDefault();
        view.dispatch(
          view.state.tr.replaceSelectionWith(view.state.schema.nodes.htmlBlock.create({ html })),
        );
        return true;
      },
      handleDrop: (view, event) => {
        const files = Array.from(event.dataTransfer?.files ?? []).filter((f) =>
          f.type.startsWith("image/"),
        );
        if (files.length === 0) return false;
        event.preventDefault();
        void insertFiles(files);
        return true;
      },
    },
    onUpdate: ({ editor }) => onChange(editor.getMarkdown()),
  });

  useEffect(() => {
    editorRef.current = editor;
  }, [editor, editorRef]);

  useEffect(() => {
    if (!editor || editor.isEditable === editable) return;
    editor.setEditable(editable, false);
    editor.view.dispatch(editor.state.tr.setMeta("editable", editable));
  }, [editor, editable]);

  useEffect(() => {
    if (!editor || version === lastVersion.current) return;
    lastVersion.current = version;
    editor.commands.setContent(markdown, { contentType: "markdown", emitUpdate: false });
  }, [editor, markdown, version]);

  useEffect(() => {
    if (!editor) return;
    editor.view.dispatch(editor.state.tr.setMeta(highlightKey, { anchors, active: activeAnchor }));
  }, [editor, anchors, activeAnchor]);

  const insertFiles = useCallback(
    async (files: File[]) => {
      if (!editor) return;
      setUploadError(null);
      for (const file of files) {
        try {
          const src = await uploadImage(file);
          editor.chain().focus().setImage({ src, alt: file.name.replace(/\.[a-z0-9]+$/i, "") }).run();
        } catch (e) {
          setUploadError(e instanceof Error ? e.message : "Upload failed");
        }
      }
    },
    [editor],
  );

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && !event.altKey && event.key.toLowerCase() === "f") {
        event.preventDefault();
        setFindSignal((n) => n + 1);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  if (!editor) return null;

  return (
    <div className="relative" data-site-origin={siteOrigin}>
      {findSignal > 0 && <FindBar editor={editor} focusSignal={findSignal} onClose={() => setFindSignal(0)} />}
      <BubbleMenu
        editor={editor}
        options={{ placement: "bottom-start", offset: 8 }}
        shouldShow={({ editor, state }) =>
          editor.isEditable && !state.selection.empty && !editor.isActive("image")
        }
        className="z-30"
      >
        <SelectionMenu
          editor={editor}
          onSelectionRequest={onSelectionRequest}
          onReplaceSelection={onReplaceSelection}
          onImage={() => fileInput.current?.click()}
        />
      </BubbleMenu>

      <EditorContent editor={editor} />

      {editable && (
        <div className="mt-8 flex items-center gap-3 border-t border-edge pt-4 text-xs text-faint">
          <button
            type="button"
            onClick={() => fileInput.current?.click()}
            className="inline-flex items-center gap-1.5 text-sub transition-colors hover:text-ink cursor-pointer"
          >
            <ImagePlus size={14} /> Add an image or GIF
          </button>
          <button
            type="button"
            onClick={() =>
              editor
                .chain()
                .focus()
                .insertContent({ type: "htmlBlock", attrs: { html: "", editing: true } })
                .run()
            }
            className="inline-flex items-center gap-1.5 text-sub transition-colors hover:text-ink cursor-pointer"
          >
            <Code2 size={14} /> Add HTML
          </button>
          <span>Paste or drop an image anywhere in the text. Markdown shortcuts work: # for a heading, - for a list.</span>
        </div>
      )}
      {uploadError && <p className="mt-2 text-xs text-bad">{uploadError}</p>}
      <input
        ref={fileInput}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/gif"
        multiple
        className="hidden"
        onChange={(e) => {
          const files = Array.from(e.target.files ?? []);
          e.target.value = "";
          if (files.length) void insertFiles(files);
        }}
      />
    </div>
  );
}

function SelectionMenu({
  editor,
  onSelectionRequest,
  onReplaceSelection,
  onImage,
}: {
  editor: Editor;
  onSelectionRequest?: (req: SelectionRequest) => Promise<string | null>;
  onReplaceSelection?: (passage: string, replacement: string) => void;
  onImage: () => void;
}) {
  const [ask, setAsk] = useState("");
  const [busy, setBusy] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);

  const selectedText = () => {
    const { from, to } = editor.state.selection;
    return editor.state.doc.textBetween(from, to, "\n");
  };

  const send = async (instruction: string) => {
    if (!onSelectionRequest || !onReplaceSelection || busy) return;
    const passage = selectedText().trim();
    if (!passage || !instruction.trim()) return;
    setBusy(true);
    setFailed(null);
    const replacement = await onSelectionRequest({ instruction: instruction.trim(), passage });
    setBusy(false);
    if (replacement === null) {
      setFailed("The agent did not answer.");
      return;
    }
    setAsk("");
    onReplaceSelection(passage, replacement);
  };

  const iconBtn = (active: boolean) =>
    cn(
      "inline-flex h-7 w-7 items-center justify-center rounded-md transition-colors cursor-pointer",
      active ? "bg-accent-soft text-accent" : "text-sub hover:bg-panel2 hover:text-ink",
    );

  const setLink = () => {
    const previous = editor.getAttributes("link").href as string | undefined;
    const url = window.prompt("Link to", previous ?? "https://");
    if (url === null) return;
    if (!url.trim()) editor.chain().focus().unsetLink().run();
    else editor.chain().focus().setLink({ href: url.trim() }).run();
  };

  return (
    <div className="flex w-[420px] max-w-[90vw] flex-col gap-2 rounded-xl border border-edge bg-panel p-2 shadow-xl">
      <div className="flex items-center gap-0.5">
        <button type="button" className={iconBtn(editor.isActive("bold"))} onClick={() => editor.chain().focus().toggleBold().run()} aria-label="Bold"><Bold size={14} /></button>
        <button type="button" className={iconBtn(editor.isActive("italic"))} onClick={() => editor.chain().focus().toggleItalic().run()} aria-label="Italic"><Italic size={14} /></button>
        <button type="button" className={iconBtn(editor.isActive("heading", { level: 2 }))} onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} aria-label="Heading"><Heading2 size={14} /></button>
        <button type="button" className={iconBtn(editor.isActive("heading", { level: 3 }))} onClick={() => editor.chain().focus().toggleHeading({ level: 3 }).run()} aria-label="Subheading"><Heading3 size={14} /></button>
        <button type="button" className={iconBtn(editor.isActive("bulletList"))} onClick={() => editor.chain().focus().toggleBulletList().run()} aria-label="Bullet list"><List size={14} /></button>
        <button type="button" className={iconBtn(editor.isActive("orderedList"))} onClick={() => editor.chain().focus().toggleOrderedList().run()} aria-label="Numbered list"><ListOrdered size={14} /></button>
        <button type="button" className={iconBtn(editor.isActive("blockquote"))} onClick={() => editor.chain().focus().toggleBlockquote().run()} aria-label="Quote"><Quote size={14} /></button>
        <button type="button" className={iconBtn(editor.isActive("link"))} onClick={setLink} aria-label="Link"><Link2 size={14} /></button>
        <button type="button" className={iconBtn(false)} onClick={onImage} aria-label="Image"><ImagePlus size={14} /></button>
      </div>
      {onSelectionRequest && (
        <>
          <div className="flex flex-wrap gap-1.5 border-t border-edge pt-2">
            {QUICK.map((q) => (
              <button
                key={q.label}
                type="button"
                disabled={busy}
                onClick={() => void send(q.sentence)}
                className="rounded-full border border-edge2 bg-panel px-2.5 py-1 text-xs text-sub transition-colors hover:text-ink disabled:opacity-50 cursor-pointer"
              >
                {q.label}
              </button>
            ))}
          </div>
          <div className="flex items-center gap-2 rounded-lg border border-edge2 bg-panel2 px-2.5 py-1.5">
            <Sparkles size={13} className="shrink-0 text-accent" />
            <input
              value={ask}
              disabled={busy}
              onChange={(e) => setAsk(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault();
                  void send(ask);
                }
              }}
              placeholder={busy ? "Rewriting…" : "or say what to change…"}
              className="flex-1 bg-transparent text-sm text-ink placeholder:text-faint focus:outline-none"
            />
            <button
              type="button"
              disabled={busy || !ask.trim()}
              onClick={() => void send(ask)}
              className="text-sub hover:text-ink disabled:opacity-40 cursor-pointer"
              aria-label="Send"
            >
              <ArrowUp size={14} />
            </button>
          </div>
          {failed && <p className="px-1 text-xs text-bad">{failed}</p>}
        </>
      )}
    </div>
  );
}
