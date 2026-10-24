"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import {
  Check,
  ChevronDown,
  Link2,
  Download,
  ExternalLink,
  FileSpreadsheet,
  Search,
} from "lucide-react";
import type { SlimResult } from "@/lib/seo-audit/audit";
import type { Severity } from "@/lib/seo-audit/types";
import { fileStem, issuesCsv, pagesCsv, summaryCsv } from "@/lib/seo-audit/csv";
import {
  CATEGORY_LABEL,
  SEVERITY_CLASS,
  SEVERITY_DOT,
  SEVERITY_LABEL,
  SEVERITY_ORDER,
  SeverityPill,
  scoreTone,
  shortUrl,
} from "./shared";

function download(name: string, body: string) {
  // The byte-order mark is what makes Excel read the file as UTF-8.
  const blob = new Blob([`\uFEFF${body}`], { type: "text/csv;charset=utf-8;" });
  const href = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = href;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(href);
}

type View = "checks" | "issues" | "pages";

function CopyShareLink({ path }: { path: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      onClick={async () => {
        await navigator.clipboard.writeText(new URL(path, window.location.origin).toString());
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }}
      className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink transition-colors hover:bg-panel2"
    >
      {copied ? <Check size={14} /> : <Link2 size={14} />}
      {copied ? "Link copied" : "Copy share link"}
    </button>
  );
}

export function AuditResults({
  result,
  onReset,
  shareUrl,
}: {
  result: SlimResult;
  onReset?: () => void;
  shareUrl?: string | null;
}) {
  const [view, setView] = useState<View>("checks");
  const [severity, setSeverity] = useState<Severity | "all">("all");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<string | null>(null);

  const { summary, findings, pages, origin } = result;
  const stem = fileStem(result);

  const filtered = useMemo(() => {
    const needle = query.trim().toLowerCase();
    return findings.filter((f) => {
      if (severity !== "all" && f.severity !== severity) return false;
      if (!needle) return true;
      return (
        f.label.toLowerCase().includes(needle) ||
        (f.url ?? "").toLowerCase().includes(needle) ||
        f.detail.toLowerCase().includes(needle)
      );
    });
  }, [findings, severity, query]);

  const grouped = useMemo(() => {
    const map = new Map<string, typeof filtered>();
    for (const finding of filtered) {
      const list = map.get(finding.id) ?? [];
      list.push(finding);
      map.set(finding.id, list);
    }
    return [...map.entries()]
      .map(([id, list]) => ({ id, list }))
      .sort(
        (a, b) =>
          SEVERITY_ORDER.indexOf(a.list[0].severity) -
            SEVERITY_ORDER.indexOf(b.list[0].severity) ||
          b.list.length - a.list.length,
      );
  }, [filtered]);

  const filteredPages = useMemo(() => {
    const needle = query.trim().toLowerCase();
    if (!needle) return pages;
    return pages.filter(
      (p) =>
        p.url.toLowerCase().includes(needle) ||
        (p.title ?? "").toLowerCase().includes(needle),
    );
  }, [pages, query]);

  return (
    <div className="mt-8">
      <section className="rounded-2xl border border-edge bg-panel p-6">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div className="flex items-center gap-5">
            <div className="text-center">
              <p className={`font-display text-5xl leading-none ${scoreTone(summary.score)}`}>
                {summary.score}
              </p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-widest text-faint">
                Health
              </p>
            </div>
            <div>
              <p className="text-sm font-medium text-ink">
                {new URL(origin).hostname}
              </p>
              <p className="mt-1 text-sm text-sub">
                {summary.pagesCrawled - summary.pagesBlocked} page
                {summary.pagesCrawled - summary.pagesBlocked === 1 ? "" : "s"} read
                {summary.urlsFound > summary.pagesCrawled &&
                  ` of ${summary.urlsFound} found`}
                {summary.pagesBlocked > 0 &&
                  ` · ${summary.pagesBlocked} blocked by robots.txt`}
                {" · "}
                {findings.length} issue{findings.length === 1 ? "" : "s"}
                {" · "}
                {(summary.durationMs / 1000).toFixed(0)}s
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={() => download(`${stem}-issues.csv`, issuesCsv(findings))}
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-3 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
            >
              <Download size={14} />
              Issues CSV
            </button>
            <button
              type="button"
              onClick={() => download(`${stem}-pages.csv`, pagesCsv(pages))}
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink transition-colors hover:bg-panel2"
            >
              <FileSpreadsheet size={14} />
              Pages CSV
            </button>
            <button
              type="button"
              onClick={() => download(`${stem}-summary.csv`, summaryCsv(result))}
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-3 py-2 text-sm text-ink transition-colors hover:bg-panel2"
            >
              <FileSpreadsheet size={14} />
              Summary CSV
            </button>
            {shareUrl && <CopyShareLink path={shareUrl} />}
            {onReset ? (
              <button
                type="button"
                onClick={onReset}
                className="rounded-lg px-3 py-2 text-sm text-sub transition-colors hover:bg-panel2 hover:text-ink"
              >
                New audit
              </button>
            ) : (
              <Link
                href="/tools/seo-audit"
                className="rounded-lg px-3 py-2 text-sm text-sub transition-colors hover:bg-panel2 hover:text-ink"
              >
                Run your own audit
              </Link>
            )}
          </div>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {SEVERITY_ORDER.map((level) => (
            <button
              key={level}
              type="button"
              onClick={() => setSeverity(severity === level ? "all" : level)}
              className={`rounded-xl border p-3 text-left transition-colors ${
                severity === level
                  ? SEVERITY_CLASS[level]
                  : "border-edge bg-bg hover:border-edge2"
              }`}
            >
              <span className="flex items-center gap-1.5">
                <span className={`size-1.5 rounded-full ${SEVERITY_DOT[level]}`} />
                <span className="font-mono text-[10px] uppercase tracking-widest text-faint">
                  {SEVERITY_LABEL[level]}
                </span>
              </span>
              <span className="mt-1 block font-display text-2xl text-ink tabular-nums">
                {summary.counts[level]}
              </span>
            </button>
          ))}
        </div>

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
              ["checks", `By check (${grouped.length})`],
              ["issues", `All issues (${filtered.length})`],
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
        <div className="relative flex-1 sm:max-w-xs">
          <Search
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-faint"
          />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Filter by URL or issue"
            aria-label="Filter results"
            className="h-9 w-full rounded-lg border border-edge2 bg-panel pl-8 pr-3 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none focus:ring-2 focus:ring-accent/30"
          />
        </div>
        {severity !== "all" && (
          <button
            type="button"
            onClick={() => setSeverity("all")}
            className="text-xs text-accent hover:text-accent-hi"
          >
            Clear {SEVERITY_LABEL[severity].toLowerCase()} filter
          </button>
        )}
      </div>

      {view === "checks" && (
        <div className="mt-4 flex flex-col gap-3">
          {grouped.length === 0 && <EmptyState />}
          {grouped.map(({ id, list }) => {
            const head = list[0];
            const isOpen = open === id;
            return (
              <article key={id} className="rounded-2xl border border-edge bg-panel">
                <button
                  type="button"
                  onClick={() => setOpen(isOpen ? null : id)}
                  aria-expanded={isOpen}
                  className="flex w-full items-start justify-between gap-4 p-5 text-left"
                >
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <SeverityPill severity={head.severity} />
                      <span className="font-mono text-[11px] text-faint">
                        {CATEGORY_LABEL[head.category]}
                      </span>
                    </div>
                    <h3 className="mt-2 text-base font-medium text-ink">{head.label}</h3>
                    <p className="mt-1 text-sm text-sub">{head.why}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-3">
                    <span className="font-display text-2xl text-ink tabular-nums">
                      {list.length}
                    </span>
                    <ChevronDown
                      size={16}
                      className={`text-faint transition-transform ${isOpen ? "rotate-180" : ""}`}
                    />
                  </div>
                </button>
                {isOpen && (
                  <div className="border-t border-edge px-5 py-4">
                    <p className="text-sm text-ink/90">
                      <span className="font-medium">How to fix: </span>
                      {head.fix}
                    </p>
                    <div className="mt-4 overflow-x-auto">
                      <table className="w-full min-w-[36rem] text-left text-sm">
                        <thead>
                          <tr className="border-b border-edge text-xs uppercase tracking-wider text-faint">
                            <th className="py-2 pr-4 font-medium">Page</th>
                            <th className="py-2 font-medium">What was found</th>
                          </tr>
                        </thead>
                        <tbody>
                          {list.slice(0, 100).map((finding, i) => (
                            <tr key={`${finding.url}-${i}`} className="border-b border-edge/60">
                              <td className="py-2 pr-4 align-top">
                                {finding.url ? (
                                  <a
                                    href={finding.url}
                                    target="_blank"
                                    rel="noreferrer nofollow"
                                    className="inline-flex items-center gap-1 font-mono text-xs text-accent hover:text-accent-hi"
                                  >
                                    {shortUrl(finding.url, origin)}
                                    <ExternalLink size={11} />
                                  </a>
                                ) : (
                                  <span className="font-mono text-xs text-faint">
                                    site-wide
                                  </span>
                                )}
                              </td>
                              <td className="py-2 align-top text-sub">{finding.detail}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {list.length > 100 && (
                        <p className="mt-3 text-xs text-faint">
                          Showing the first 100. The CSV has all {list.length}.
                        </p>
                      )}
                    </div>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}

      {view === "issues" && (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-edge bg-panel">
          {filtered.length === 0 ? (
            <EmptyState />
          ) : (
            <table className="w-full min-w-[52rem] text-left text-sm">
              <thead>
                <tr className="border-b border-edge text-xs uppercase tracking-wider text-faint">
                  <th className="px-5 py-3 font-medium">Severity</th>
                  <th className="px-5 py-3 font-medium">Issue</th>
                  <th className="px-5 py-3 font-medium">Page</th>
                  <th className="px-5 py-3 font-medium">What was found</th>
                </tr>
              </thead>
              <tbody>
                {filtered.slice(0, 500).map((finding, i) => (
                  <tr key={`${finding.id}-${finding.url}-${i}`} className="border-b border-edge/60">
                    <td className="px-5 py-3 align-top">
                      <SeverityPill severity={finding.severity} />
                    </td>
                    <td className="px-5 py-3 align-top text-ink">{finding.label}</td>
                    <td className="px-5 py-3 align-top">
                      {finding.url ? (
                        <a
                          href={finding.url}
                          target="_blank"
                          rel="noreferrer nofollow"
                          className="font-mono text-xs text-accent hover:text-accent-hi"
                        >
                          {shortUrl(finding.url, origin)}
                        </a>
                      ) : (
                        <span className="font-mono text-xs text-faint">site-wide</span>
                      )}
                    </td>
                    <td className="px-5 py-3 align-top text-sub">{finding.detail}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          {filtered.length > 500 && (
            <p className="px-5 py-3 text-xs text-faint">
              Showing the first 500 rows. The CSV has all {filtered.length}.
            </p>
          )}
        </div>
      )}

      {view === "pages" && (
        <div className="mt-4 overflow-x-auto rounded-2xl border border-edge bg-panel">
          <table className="w-full min-w-[64rem] text-left text-sm">
            <thead>
              <tr className="border-b border-edge text-xs uppercase tracking-wider text-faint">
                <th className="px-5 py-3 font-medium">URL</th>
                <th className="px-5 py-3 font-medium">Status</th>
                <th className="px-5 py-3 font-medium">Title</th>
                <th className="px-5 py-3 font-medium">Meta description</th>
                <th className="px-5 py-3 font-medium">H1</th>
                <th className="px-5 py-3 font-medium">Words</th>
                <th className="px-5 py-3 font-medium">Links in</th>
              </tr>
            </thead>
            <tbody>
              {filteredPages.slice(0, 200).map((page) => (
                <tr key={page.url} className="border-b border-edge/60 align-top">
                  <td className="px-5 py-3">
                    <a
                      href={page.url}
                      target="_blank"
                      rel="noreferrer nofollow"
                      className="font-mono text-xs text-accent hover:text-accent-hi"
                    >
                      {shortUrl(page.url, origin)}
                    </a>
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge page={page} />
                  </td>
                  <td className="max-w-[18rem] px-5 py-3 text-ink">
                    {page.title ? (
                      <>
                        <span className="line-clamp-2">{page.title}</span>
                        <span className="font-mono text-[11px] text-faint">
                          {page.title.length} chars
                        </span>
                      </>
                    ) : (
                      <span className="text-bad">missing</span>
                    )}
                  </td>
                  <td className="max-w-[18rem] px-5 py-3 text-sub">
                    {page.metaDescription ? (
                      <>
                        <span className="line-clamp-2">{page.metaDescription}</span>
                        <span className="font-mono text-[11px] text-faint">
                          {page.metaDescription.length} chars
                        </span>
                      </>
                    ) : (
                      <span className="text-warn">missing</span>
                    )}
                  </td>
                  <td className="max-w-[14rem] px-5 py-3 text-sub">
                    {page.h1.length === 0 ? (
                      <span className="text-warn">none</span>
                    ) : (
                      <span className="line-clamp-2">
                        {page.h1[0]}
                        {page.h1.length > 1 && (
                          <span className="text-warn"> (+{page.h1.length - 1})</span>
                        )}
                      </span>
                    )}
                  </td>
                  <td className="px-5 py-3 font-mono text-xs text-sub tabular-nums">
                    {page.wordCount}
                  </td>
                  <td className="px-5 py-3 font-mono text-xs text-sub tabular-nums">
                    {page.inlinks}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {filteredPages.length > 200 && (
            <p className="px-5 py-3 text-xs text-faint">
              Showing the first 200 pages. The CSV has all {filteredPages.length}.
            </p>
          )}
        </div>
      )}

      <CrawlerAccess result={result} />
    </div>
  );
}

function StatusBadge({ page }: { page: SlimResult["pages"][number] }) {
  const status = page.status;
  const tone =
    page.blockedByRobots || status === null
      ? "text-faint"
      : status >= 500
        ? "text-bad"
        : status >= 400
          ? "text-bad"
          : status >= 300
            ? "text-warn"
            : "text-good";
  return (
    <span className={`font-mono text-xs ${tone}`}>
      {page.blockedByRobots ? "blocked" : (status ?? "failed")}
      {page.redirectHops > 0 && ` ·${page.redirectHops}↷`}
    </span>
  );
}

function EmptyState() {
  return (
    <p className="p-8 text-center text-sm text-sub">
      Nothing matches that filter.
    </p>
  );
}

function CrawlerAccess({ result }: { result: SlimResult }) {
  const blocked = result.aiCrawlers.filter((c) => !c.allowed);
  return (
    <section className="mt-6 grid gap-4 sm:grid-cols-2">
      <div className="rounded-2xl border border-edge bg-panel p-5">
        <h3 className="text-sm font-medium text-ink">robots.txt and sitemaps</h3>
        <dl className="mt-3 space-y-2 text-sm">
          <Row
            label="robots.txt"
            value={
              result.robots.status === 200
                ? "found"
                : `HTTP ${result.robots.status ?? "no answer"}`
            }
            tone={result.robots.status === 200 ? "good" : "warn"}
          />
          <Row
            label="Sitemap"
            value={
              result.sitemapUrlCount > 0
                ? `${result.sitemapUrlCount} URLs`
                : "none found"
            }
            tone={result.sitemapUrlCount > 0 ? "good" : "warn"}
          />
          <Row
            label="/llms.txt"
            value={result.llmsTxtStatus === 200 ? "found" : "not published"}
            tone={result.llmsTxtStatus === 200 ? "good" : "neutral"}
          />
        </dl>
        {result.sitemapsUsed.length > 0 && (
          <p className="mt-3 break-all font-mono text-[11px] text-faint">
            {result.sitemapsUsed.slice(0, 3).join(", ")}
          </p>
        )}
      </div>
      <div className="rounded-2xl border border-edge bg-panel p-5">
        <h3 className="text-sm font-medium text-ink">AI crawler access</h3>
        <p className="mt-1 text-xs text-sub">
          What robots.txt says to the crawlers behind ChatGPT, Claude, Perplexity
          and Google AI answers.
        </p>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {result.aiCrawlers.map((crawler) => (
            <span
              key={crawler.agent}
              title={`${crawler.operator} · ${crawler.job}`}
              className={`rounded-md border px-1.5 py-0.5 font-mono text-[11px] ${
                crawler.allowed
                  ? "border-edge2 bg-panel2 text-sub"
                  : "border-bad/25 bg-bad/10 text-bad"
              }`}
            >
              {crawler.agent}
            </span>
          ))}
        </div>
        <p className="mt-3 text-xs text-faint">
          {blocked.length === 0
            ? "All fourteen are allowed by robots.txt."
            : `${blocked.length} of ${result.aiCrawlers.length} are disallowed.`}
        </p>
      </div>
    </section>
  );
}

function Row({
  label,
  value,
  tone,
}: {
  label: string;
  value: string;
  tone: "good" | "warn" | "neutral";
}) {
  const color =
    tone === "good" ? "text-good" : tone === "warn" ? "text-warn" : "text-sub";
  return (
    <div className="flex items-center justify-between gap-4">
      <dt className="text-sub">{label}</dt>
      <dd className={`font-mono text-xs ${color}`}>{value}</dd>
    </div>
  );
}
