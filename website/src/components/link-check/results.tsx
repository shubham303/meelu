"use client";

import { useMemo, useState } from "react";
import { ChevronDown, Copy, Download, ExternalLink, FileSpreadsheet, Search } from "lucide-react";
import type { CheckedLink, LinkCheckResult, LinkState } from "@/lib/link-check/types";
import {
  allLinksCsv,
  brokenLinksCsv,
  fileStem,
  pagesCsv,
} from "@/lib/link-check/csv";
import { CopyButton, STATE_LABEL, StatePill, copyText, shortUrl } from "./shared";

function download(name: string, body: string) {
  // The byte-order mark is what makes Excel read the file as UTF-8.
  const blob = new Blob([`﻿${body}`], { type: "text/csv;charset=utf-8;" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

type View = "problems" | "all" | "pages";
type Side = "all" | "internal" | "external" | "image";

export function LinkCheckResults({
  result,
  onReset,
}: {
  result: LinkCheckResult;
  onReset: () => void;
}) {
  const [view, setView] = useState<View>("problems");
  const [state, setState] = useState<LinkState | "all">("all");
  const [side, setSide] = useState<Side>("all");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const [copiedAll, setCopiedAll] = useState<"idle" | "copied" | "failed">("idle");

  const { summary, links, pages, origin } = result;
  const stem = fileStem(result);

  const matches = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return links.filter((link) => {
      if (state !== "all" && link.state !== state) return false;
      if (side === "image" && link.asset !== "image") return false;
      if (side === "internal" && (link.side !== "internal" || link.asset === "image")) {
        return false;
      }
      if (side === "external" && (link.side !== "external" || link.asset === "image")) {
        return false;
      }
      if (!needle) return true;
      return (
        link.url.toLowerCase().includes(needle) ||
        link.sources.some((s) => s.page.toLowerCase().includes(needle)) ||
        link.sources.some((s) => s.anchor.toLowerCase().includes(needle))
      );
    });
  }, [links, state, side, query]);

  const problems = useMemo(
    () =>
      matches.filter(
        (link) =>
          link.state === "broken" ||
          link.state === "no-answer" ||
          link.state === "blocked",
      ),
    [matches],
  );

  const rows = view === "problems" ? problems : matches;

  const tiles: Array<{ key: LinkState; label: string; count: number }> = [
    { key: "broken", label: "Broken", count: summary.broken },
    { key: "no-answer", label: "No answer", count: summary.noAnswer },
    { key: "blocked", label: "Unverified", count: summary.blocked },
    { key: "redirect", label: "Redirects", count: summary.redirects },
    { key: "ok", label: "Working", count: summary.ok },
  ];

  return (
    <div className="mt-8">
      <section className="rounded-2xl border border-edge bg-panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="text-center">
              <p
                className={`font-display text-5xl leading-none ${
                  summary.broken === 0 ? "text-good" : "text-bad"
                }`}
              >
                {summary.broken}
              </p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-faint">
                Broken
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-ink">
                {new URL(origin).hostname}
              </p>
              <p className="mt-1 text-sm text-sub">
                {summary.linksChecked} of {summary.linksFound} link
                {summary.linksFound === 1 ? "" : "s"} checked across{" "}
                {summary.pagesCrawled} page{summary.pagesCrawled === 1 ? "" : "s"}
                {" · "}
                {(summary.durationMs / 1000).toFixed(0)}s
              </p>
              {summary.broken > 0 && (
                <p className="mt-1 text-xs text-sub">
                  {summary.brokenInternal} internal · {summary.brokenExternal}{" "}
                  external · {summary.brokenImages} image
                  {summary.brokenImages === 1 ? "" : "s"}
                </p>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => download(`${stem}.csv`, brokenLinksCsv(result))}
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
            >
              <Download size={14} />
              Broken links CSV
            </button>
            <button
              type="button"
              onClick={() => download(`${stem}-all-links.csv`, allLinksCsv(result))}
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink transition-colors hover:bg-panel2"
            >
              <FileSpreadsheet size={14} />
              All links CSV
            </button>
            <button
              type="button"
              onClick={() => download(`${stem}-pages.csv`, pagesCsv(result))}
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink transition-colors hover:bg-panel2"
            >
              <FileSpreadsheet size={14} />
              Pages CSV
            </button>
            <button
              type="button"
              onClick={async () => {
                const urls = links
                  .filter((l) => l.state === "broken")
                  .map((l) => l.url)
                  .join("\n");
                const ok = urls.length > 0 && (await copyText(urls));
                setCopiedAll(ok ? "copied" : "failed");
                window.setTimeout(() => setCopiedAll("idle"), 2000);
              }}
              disabled={summary.broken === 0}
              aria-label="Copy every broken URL to the clipboard"
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink transition-colors hover:bg-panel2 disabled:cursor-not-allowed disabled:text-faint disabled:hover:bg-panel"
            >
              <Copy size={14} />
              {copiedAll === "copied"
                ? "Copied"
                : copiedAll === "failed"
                  ? "Copy failed"
                  : "Copy broken URLs"}
            </button>
            <span className="sr-only" aria-live="polite">
              {copiedAll === "copied"
                ? `Copied ${summary.broken} broken URLs to the clipboard`
                : copiedAll === "failed"
                  ? "Copy failed. Use the CSV download instead."
                  : ""}
            </span>
            <button
              type="button"
              onClick={onReset}
              className="rounded-lg px-3 py-2 text-sm text-sub transition-colors hover:bg-panel2 hover:text-ink"
            >
              New scan
            </button>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-5">
          {tiles.map((tile) => (
            <button
              key={tile.key}
              type="button"
              onClick={() => {
                setState(state === tile.key ? "all" : tile.key);
                if (tile.key === "redirect" || tile.key === "ok") setView("all");
              }}
              className={`rounded-xl border p-3 text-left transition-colors ${
                state === tile.key
                  ? "border-accent bg-accent/5"
                  : "border-edge bg-bg hover:border-edge2"
              }`}
            >
              <span className="font-mono text-[10px] uppercase tracking-widest text-faint">
                {tile.label}
              </span>
              <span className="mt-1 block font-display text-2xl text-ink tabular-nums">
                {tile.count}
              </span>
            </button>
          ))}
        </div>

        {summary.blocked > 0 && (
          <p className="mt-5 rounded-xl border border-edge bg-bg p-4 text-xs leading-relaxed text-sub">
            <strong className="font-medium text-ink">
              &ldquo;Unverified&rdquo; is not &ldquo;broken&rdquo;.
            </strong>{" "}
            {summary.blocked} destination{summary.blocked === 1 ? "" : "s"} refused
            an automated request with a 401, 403 or 429. That is usually bot
            protection or rate limiting rather than a dead page, so this tool
            reports them separately instead of padding the broken count. Open a
            couple in a browser to be sure.
          </p>
        )}

        {result.notes.length > 0 && (
          <ul className="mt-5 space-y-1.5 border-t border-edge pt-4">
            {result.notes.map((note) => (
              <li key={note} className="text-xs leading-relaxed text-faint">
                {note}
              </li>
            ))}
          </ul>
        )}
      </section>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <div className="inline-flex rounded-lg border border-edge bg-panel p-0.5">
          {(
            [
              ["problems", `Problems (${problems.length})`],
              ["all", `All links (${matches.length})`],
              ["pages", `Pages (${pages.length})`],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setView(id)}
              className={`rounded-md px-3 py-1.5 text-sm transition-colors ${
                view === id ? "bg-panel2 font-medium text-ink" : "text-sub hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="inline-flex rounded-lg border border-edge bg-panel p-0.5">
          {(
            [
              ["all", "All"],
              ["internal", "Internal"],
              ["external", "External"],
              ["image", "Images"],
            ] as const
          ).map(([id, label]) => (
            <button
              key={id}
              type="button"
              onClick={() => setSide(id)}
              className={`rounded-md px-2.5 py-1.5 text-sm transition-colors ${
                side === id ? "bg-panel2 font-medium text-ink" : "text-sub hover:text-ink"
              }`}
            >
              {label}
            </button>
          ))}
        </div>

        <div className="relative flex-1 sm:max-w-xs">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter by URL, page or anchor"
            aria-label="Filter links"
            className="h-9 w-full rounded-lg border border-edge2 bg-panel pl-8 pr-3 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>

        {state !== "all" && (
          <button
            type="button"
            onClick={() => setState("all")}
            className="text-xs text-accent hover:text-accent-hi"
          >
            Clear {STATE_LABEL[state].toLowerCase()} filter
          </button>
        )}
      </div>

      {view === "pages" ? (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-edge bg-panel">
          <table className="w-full min-w-[40rem] text-left text-sm">
            <thead>
              <tr className="border-b border-edge text-xs uppercase tracking-wider text-faint">
                <th className="px-5 py-3 font-medium">Page</th>
                <th className="px-5 py-3 font-medium">Links out</th>
                <th className="px-5 py-3 font-medium">Broken on this page</th>
              </tr>
            </thead>
            <tbody>
              {pages.slice(0, 200).map((page) => (
                <tr key={page.url} className="border-b border-edge/60">
                  <td className="px-5 py-3">
                    <span className="inline-flex items-center gap-1.5">
                      <a
                        href={page.url}
                        target="_blank"
                        rel="noreferrer noopener nofollow"
                        title={page.url}
                        className="break-all font-mono text-xs text-accent hover:text-accent-hi"
                      >
                        {shortUrl(page.url, origin)}
                      </a>
                      <CopyButton
                        value={page.url}
                        label={`Copy the page URL ${page.url}`}
                      />
                    </span>
                  </td>
                  <td className="px-5 py-3 font-mono text-xs text-sub tabular-nums">
                    {page.linksOut}
                  </td>
                  <td className="px-5 py-3 font-mono text-xs tabular-nums">
                    <span className={page.broken > 0 ? "text-bad" : "text-faint"}>
                      {page.broken}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : rows.length === 0 ? (
        <p className="mt-4 rounded-2xl border border-edge bg-panel p-10 text-center text-sm text-sub">
          {view === "problems" && state === "all" && query === ""
            ? "No broken links found. Every destination answered."
            : "Nothing matches that filter."}
        </p>
      ) : (
        <div className="mt-4 flex flex-col gap-2">
          {rows.slice(0, 300).map((link) => (
            <LinkRow
              key={`${link.asset}:${link.url}`}
              link={link}
              origin={origin}
              isOpen={open === `${link.asset}:${link.url}`}
              onToggle={() =>
                setOpen(
                  open === `${link.asset}:${link.url}`
                    ? null
                    : `${link.asset}:${link.url}`,
                )
              }
            />
          ))}
          {rows.length > 300 && (
            <p className="p-3 text-center text-xs text-faint">
              Showing the first 300. The CSV has all {rows.length}.
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function LinkRow({
  link,
  origin,
  isOpen,
  onToggle,
}: {
  link: CheckedLink;
  origin: string;
  isOpen: boolean;
  onToggle: () => void;
}) {
  return (
    <article className="rounded-xl border border-edge bg-panel">
      <div className="flex w-full items-start justify-between gap-4 p-4 text-left">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <StatePill state={link.state} />
            <span className="font-mono text-[11px] text-faint">
              {link.asset === "image" ? "image" : link.side}
            </span>
          </div>
          <div className="mt-2 flex items-start gap-2">
            <a
              href={link.url}
              target="_blank"
              rel="noreferrer noopener nofollow"
              title={link.url}
              className="min-w-0 break-all font-mono text-xs text-ink underline decoration-edge2 underline-offset-2 transition-colors hover:text-accent hover:decoration-accent"
            >
              {link.url}
            </a>
            <CopyButton value={link.url} label={`Copy link ${link.url}`} />
          </div>
          <p className="mt-1 text-sm text-sub">{link.reason}</p>
        </div>
        <button
          type="button"
          onClick={onToggle}
          aria-expanded={isOpen}
          aria-label={
            isOpen
              ? `Hide the pages that link to ${link.url}`
              : `Show the ${link.sourceCount} page${link.sourceCount === 1 ? "" : "s"} that link to ${link.url}`
          }
          className="flex shrink-0 items-center gap-3 rounded-lg px-2 py-1 transition-colors hover:bg-panel2"
        >
          <span className="whitespace-nowrap font-mono text-xs text-faint">
            {link.sourceCount} page{link.sourceCount === 1 ? "" : "s"}
          </span>
          <ChevronDown
            size={15}
            className={`text-faint transition-transform ${isOpen ? "rotate-180" : ""}`}
          />
        </button>
      </div>
      {isOpen && (
        <div className="border-t border-edge px-4 py-3">
          <p className="font-mono text-[10px] uppercase tracking-widest text-faint">
            Linked from
          </p>
          <ul className="mt-2 flex flex-col gap-2">
            {link.sources.map((source, i) => (
              <li key={`${source.page}-${i}`} className="text-sm">
                <span className="inline-flex max-w-full items-center gap-1.5 align-middle">
                  <a
                    href={source.page}
                    target="_blank"
                    rel="noreferrer noopener nofollow"
                    title={source.page}
                    className="inline-flex min-w-0 items-center gap-1 break-all font-mono text-xs text-accent hover:text-accent-hi"
                  >
                    {shortUrl(source.page, origin)}
                    <ExternalLink size={11} className="shrink-0" />
                  </a>
                  <CopyButton
                    value={source.page}
                    label={`Copy the page URL ${source.page}`}
                  />
                </span>
                <span className="ml-2 text-sub">&ldquo;{source.anchor}&rdquo;</span>
                {source.rel && (
                  <span className="ml-2 font-mono text-[11px] text-faint">
                    rel={source.rel}
                  </span>
                )}
              </li>
            ))}
          </ul>
          {link.sourceCount > link.sources.length && (
            <p className="mt-2 text-xs text-faint">
              …and {link.sourceCount - link.sources.length} more. The CSV has one
              row per page.
            </p>
          )}
        </div>
      )}
    </article>
  );
}
