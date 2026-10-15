"use client";

import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ChartFrame } from "./chart-frame";

type HastNode = {
  type?: string;
  tagName?: string;
  value?: string;
  properties?: { className?: unknown };
  children?: HastNode[];
};

function inAppPath(href: string | undefined): string | null {
  if (!href) return null;
  if (href.startsWith("/") && !href.startsWith("//")) return href;
  try {
    const url = new URL(href);
    if (url.origin !== window.location.origin) return null;
    return url.pathname + url.search + url.hash;
  } catch {
    return null;
  }
}

function chartSource(pre: HastNode | undefined): string | null {
  const code = pre?.children?.find((c) => c.tagName === "code");
  const classes = code?.properties?.className;
  if (!Array.isArray(classes) || !classes.includes("language-chart")) return null;
  return (code?.children ?? []).map((c) => c.value ?? "").join("");
}

export function ChatMarkdown({ text }: { text: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        p: (props) => <p className="mb-2 last:mb-0" {...props} />,
        ul: (props) => <ul className="list-disc pl-5 mb-2 last:mb-0 space-y-1" {...props} />,
        ol: (props) => <ol className="list-decimal pl-5 mb-2 last:mb-0 space-y-1" {...props} />,
        strong: (props) => <strong className="font-semibold" {...props} />,
        a: ({ href, ...props }) => {
          const path = inAppPath(href);
          if (path) return <Link href={path} className="text-accent underline" {...props} />;
          return (
            <a
              className="text-accent underline"
              href={href}
              target="_blank"
              rel="noreferrer"
              {...props}
            />
          );
        },
        h1: (props) => <p className="font-semibold mt-3 mb-1.5" {...props} />,
        h2: (props) => <p className="font-semibold mt-3 mb-1.5" {...props} />,
        h3: (props) => <p className="font-semibold mt-3 mb-1.5" {...props} />,
        h4: (props) => <p className="font-semibold mt-3 mb-1.5" {...props} />,
        blockquote: (props) => (
          <blockquote className="border-l-2 border-edge2 pl-3 text-sub mb-2" {...props} />
        ),
        code: (props) => (
          <code className="rounded bg-panel2 px-1 py-0.5 font-mono text-[0.85em]" {...props} />
        ),
        pre: ({ node, ...props }) => {
          const chart = chartSource(node as HastNode | undefined);
          if (chart !== null) {
            return (
              <div className="mb-2 overflow-hidden rounded-xl border border-edge bg-white">
                <ChartFrame html={chart} />
              </div>
            );
          }
          return (
            <pre
              className="mb-2 overflow-x-auto rounded-lg border border-edge bg-panel2 p-2.5 text-xs [&_code]:bg-transparent [&_code]:p-0"
              {...props}
            />
          );
        },
        hr: () => <hr className="border-edge my-3" />,
        table: (props) => (
          <div className="overflow-x-auto mb-2">
            <table
              className="text-xs border-collapse [&_th]:border [&_th]:border-edge [&_th]:px-2 [&_th]:py-1 [&_th]:text-left [&_td]:border [&_td]:border-edge [&_td]:px-2 [&_td]:py-1"
              {...props}
            />
          </div>
        ),
        img: ({ alt, ...props }) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            {...props}
            alt={alt ?? ""}
            loading="lazy"
            className="mb-2 max-w-full rounded-lg border border-edge"
          />
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  );
}
