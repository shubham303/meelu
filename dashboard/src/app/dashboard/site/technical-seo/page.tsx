"use client";

import { useCallback, useMemo, useRef, useState } from "react";
import Link from "next/link";
import {
  ArrowLeft,
  Check,
  ChevronDown,
  ChevronRight,
  Copy,
  Download,
  ExternalLink,
  FileText,
  Monitor,
  RotateCcw,
  Search as SearchIcon,
  ShieldCheck,
  Smartphone,
  Square,
  X,
  type LucideIcon,
} from "lucide-react";
import { PageEnter } from "@/components/animate";
import {
  Badge,
  Button,
  EmptyState,
  PageHeader,
  Spinner,
} from "@/components/ui";
import { siteHeader } from "@/lib/current-site";
import { api, useApi, useCurrentSite } from "@/lib/use-api";
import { cn, formatRelative } from "@/lib/utils";
import { CrawlProgress } from "../crawl-progress";
import { RenderProgress } from "../render-progress";
import { SiteAskButton } from "../site-ask";
import { useCrawl } from "../tracked";
import { type Render, useRender } from "../tracked-render";
import * as chips from "@/features/prompt-chips/site";
import {
  SITE_ISSUE_SEVERITIES,
  SITE_ISSUE_STATES,
  SITE_ISSUE_TYPES,
  type SiteIssueGroup,
  type SiteIssueSeverity,
  type SiteIssueKind,
  type SiteIssueState,
  type SiteIssueSummary,
  type SiteIssueType,
  type SitePageIssue,
} from "@/lib/types";

const TAB_LABEL: Record<SiteIssueType, string> = {
  static: "Static checks",
  desktop: "Desktop rendering",
  mobile: "Mobile rendering",
};

const TAB_ICON: Record<SiteIssueType, LucideIcon> = {
  static: FileText,
  desktop: Monitor,
  mobile: Smartphone,
};

const RUN_LABEL: Record<SiteIssueType, string> = {
  static: "Run the static checks",
  desktop: "Run the desktop checks",
  mobile: "Run the mobile checks",
};

const STATE_LABEL: Record<SiteIssueState, string> = {
  open: "Open",
  rejected: "Turned down",
};

const SEVERITY_LABEL: Record<SiteIssueSeverity, string> = {
  p0: "Fix now",
  p1: "Costing visibility",
  p2: "Worth doing",
  p3: "Polish",
};

const SEVERITY_HINT: Record<SiteIssueSeverity, string> = {
  p0: "The site cannot be crawled or indexed properly until these are dealt with.",
  p1: "Pages that should rank are being held back, or whole sets of them are being ignored.",
  p2: "Real gains, none of them urgent. Work through them when the ones above are clear.",
  p3: "Small, cheap corrections. Do not let a long list of these hide anything above.",
};

type Phase = "idle" | "crawling" | "rendering" | "checking";

export default function SiteTechnicalSeoPage() {
  const [state, setState] = useState<SiteIssueState>("open");
  const [tab, setTab] = useState<SiteIssueType>("static");
  const [q, setQ] = useState("");
  const [severity, setSeverity] = useState<SiteIssueSeverity | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [asking, setAsking] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [problem, setProblem] = useState<string | null>(null);
  const siteId = useCurrentSite();
  const waiting = useRef(false);
  const running = phase !== "idle";

  const { refresh: refreshSummary } = useApi<SiteIssueSummary>("/api/v1/site/technical-seo/summary");
  const {
    data: openGroups,
    loading,
    error,
    refresh: refreshOpen,
  } = useApi<SiteIssueGroup[]>("/api/v1/site/technical-seo/groups?state=open");
  const { data: rejectedGroups, refresh: refreshRejected } = useApi<SiteIssueGroup[]>(
    "/api/v1/site/technical-seo/groups?state=rejected",
  );
  const refreshGroups = useCallback(() => {
    void refreshOpen();
    void refreshRejected();
  }, [refreshOpen, refreshRejected]);

  const groups = state === "open" ? openGroups : rejectedGroups;
  const allRows = useMemo(() => groups ?? [], [groups]);
  const rows = useMemo(() => allRows.filter((r) => r.issueType === tab), [allRows, tab]);
  const tabCounts = useMemo(() => {
    const counts: Record<SiteIssueType, number> = { static: 0, desktop: 0, mobile: 0 };
    for (const r of allRows) counts[r.issueType] += 1;
    return counts;
  }, [allRows]);

  const visible = useMemo(() => {
    const needle = q.trim().toLowerCase();
    return rows.filter(
      (r) =>
        (!severity || r.severity === severity) &&
        (!needle ||
          r.kind.includes(needle) ||
          r.issue.toLowerCase().includes(needle) ||
          r.examples.some((u) => u.toLowerCase().includes(needle))),
    );
  }, [rows, severity, q]);

  const narrowed = visible.length < rows.length;
  const affected = visible.reduce((n, r) => n + (r.scope === "site" ? 1 : r.pages), 0);

  const counts = {
    open: (openGroups ?? []).filter((r) => r.issueType === tab).length,
    rejected: (rejectedGroups ?? []).filter((r) => r.issueType === tab).length,
  };

  const reload = useCallback(() => {
    void refreshSummary();
    void refreshGroups();
  }, [refreshSummary, refreshGroups]);

  const pickState = (next: SiteIssueState) => {
    setState(next);
    setSeverity(null);
  };

  const pickTab = (next: SiteIssueType) => {
    setTab(next);
    setSeverity(null);
    setAsking(false);
  };

  const check = useCallback(
    async () => {
      setPhase("checking");
      try {
        await api("/api/v1/site/technical-seo/run-audit", { method: "POST", body: {} });
        setProblem(null);
        reload();
      } catch (e) {
        setProblem(e instanceof Error ? e.message : "The checks could not run.");
      }
      setPhase("idle");
    },
    [reload],
  );

  const settle = useCallback(() => {
    if (!waiting.current) return;
    waiting.current = false;
    void check();
  }, [check]);

  const crawl = useCrawl(siteId, settle);
  const desktop = useRender(siteId, "desktop", settle);
  const mobile = useRender(siteId, "mobile", settle);
  const render = tab === "mobile" ? mobile : desktop;
  const renderTab = tab !== "static";
  const canRun = renderTab ? render.canRender : true;

  const ask = () => {
    setProblem(null);
    if (!renderTab && !crawl.canCrawl) {
      void check();
      return;
    }
    setAsking(true);
  };

  const checkOnly = async () => {
    setAsking(false);
    await check();
  };

  const crawlThenCheck = async () => {
    setAsking(false);
    setPhase("crawling");
    waiting.current = true;
    const started = await crawl.start();
    if (!started) {
      waiting.current = false;
      setPhase("idle");
    }
  };

  const renderThenCheck = async (opts: { limit?: number; url?: string } = {}) => {
    setAsking(false);
    setPhase("rendering");
    waiting.current = true;
    const started = await render.start(opts);
    if (!started) {
      waiting.current = false;
      setPhase("idle");
    }
  };

  const stopCurrent = () => {
    if (phase === "crawling") void crawl.stop();
    if (phase === "rendering") void render.stop();
  };

  const stopping = phase === "crawling" ? crawl.stopping : render.stopping;

  const stoppable = phase === "crawling" || phase === "rendering";

  const runLabel =
    phase === "crawling"
      ? "Re-reading the site…"
      : phase === "rendering"
        ? `Rendering ${(render.status?.rendered ?? 0) + (render.status?.skipped ?? 0) + (render.status?.failed ?? 0)}/${render.status?.total ?? 0}…`
        : phase === "checking"
          ? "Checking…"
          : RUN_LABEL[tab];

  const download = async () => {
    setDownloading(true);
    try {
      const params = new URLSearchParams({ state, type: tab });
      if (narrowed) params.set("kind", visible.map((r) => r.kind).join(","));
      const res = await fetch(`/api/v1/site/technical-seo/download?${params}`, { headers: siteHeader() });
      if (!res.ok) throw new Error("The CSV could not be built.");
      const name =
        /filename="([^"]+)"/.exec(res.headers.get("content-disposition") ?? "")?.[1] ??
        "site-issues.csv";
      const href = URL.createObjectURL(await res.blob());
      const link = document.createElement("a");
      link.href = href;
      link.download = name;
      link.click();
      URL.revokeObjectURL(href);
      setProblem(null);
    } catch (e) {
      setProblem(e instanceof Error ? e.message : "The CSV could not be built.");
    } finally {
      setDownloading(false);
    }
  };

  const emptyHint =
    state !== "open"
      ? "Change the state filter to see the checks that are open."
      : !renderTab
        ? "Every check passed on the pages that have been read. After you change the website, run the checks again and say yes to reading it first."
        : (render.status?.renderedPages ?? 0) > 0
          ? `The pages rendered on ${tab} behave the same with and without JavaScript. Render again after the website changes.`
          : `No page has been rendered on ${tab} yet. Run the ${tab} checks to see what crawlers miss when JavaScript does not run.`;

  return (
    <PageEnter>
      <Link
        href="/dashboard/site"
        className="mb-4 inline-flex items-center gap-1.5 text-sm text-sub transition-colors hover:text-ink"
      >
        <ArrowLeft size={14} /> Site
      </Link>

      <PageHeader
        title="Technical SEO"
        description="One tab per way of looking at the site. The button runs the checks for the tab you are on and asks first whether to read or render the site again, or use what is already on record. Checks you have turned down stay turned down."
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={download} disabled={downloading || affected === 0}>
              <Download size={14} />
              {downloading ? "Building…" : `Download ${affected} row${affected === 1 ? "" : "s"}`}
            </Button>
            {stoppable ? (
              <Button onClick={stopCurrent} disabled={stopping} title="Stop">
                <Square size={14} />
                {stopping ? "Stopping…" : runLabel}
              </Button>
            ) : (
              <Button
                onClick={ask}
                disabled={running || asking || !canRun}
                title={canRun ? undefined : "Rendering runs in the Meelu app."}
              >
                {runLabel}
              </Button>
            )}
            <SiteAskButton
              title="Ask — Technical SEO"
              hint="Ask which of these checks matter, what one of them means, or what a fix would look like on the pages it flagged."
              suggestions={chips.technicalSeo()}
              draft={{ showing: `${STATE_LABEL[state]} ${TAB_LABEL[tab].toLowerCase()}`, check: "every check" }}
              onRan={reload}
            />
          </div>
        }
      />

      <div className="space-y-4">
        <div className="flex gap-6 border-b border-edge">
          {SITE_ISSUE_TYPES.map((t) => {
            const Icon = TAB_ICON[t];
            const active = tab === t;
            return (
              <button
                key={t}
                onClick={() => pickTab(t)}
                aria-pressed={active}
                className={cn(
                  "-mb-px flex cursor-pointer items-center gap-2 border-b-2 px-0.5 py-2.5 text-sm transition-colors",
                  active
                    ? "border-accent font-medium text-ink"
                    : "border-transparent text-sub hover:text-ink",
                )}
              >
                <Icon size={14} />
                {TAB_LABEL[t]}
                <span className="rounded-full border border-edge2 bg-panel2 px-1.5 text-[11px] text-sub">
                  {tabCounts[t]}
                </span>
              </button>
            );
          })}
        </div>

        <Freshness
          tab={tab}
          lastCrawledAt={crawl.status?.lastCrawledAt ?? null}
          pages={crawl.status?.pages ?? 0}
          render={render}
        />

        {asking && !renderTab && (
          <RecrawlAsk
            lastCrawledAt={crawl.status?.lastCrawledAt ?? null}
            pages={crawl.status?.pages ?? 0}
            onCrawl={() => void crawlThenCheck()}
            onSkip={() => void checkOnly()}
            onCancel={() => setAsking(false)}
          />
        )}

        {asking && renderTab && (
          <RerenderAsk
            render={render}
            onRender={(opts) => void renderThenCheck(opts)}
            onSkip={() => void checkOnly()}
            onCancel={() => setAsking(false)}
          />
        )}

        <CrawlProgress crawl={crawl} />
        {renderTab && <RenderProgress render={render} />}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {SITE_ISSUE_SEVERITIES.map((sev) => (
            <SeverityTile
              key={sev}
              severity={sev}
              checks={rows.filter((r) => r.severity === sev).length}
              pages={rows
                .filter((r) => r.severity === sev)
                .reduce((n, r) => n + (r.scope === "site" ? 1 : r.pages), 0)}
              active={severity === sev}
              onClick={() => setSeverity((cur) => (cur === sev ? null : sev))}
            />
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <div className="inline-flex gap-0.5 rounded-lg border border-edge2 bg-panel2 p-[3px]">
            {SITE_ISSUE_STATES.map((s) => (
              <button
                key={s}
                onClick={() => pickState(s)}
                aria-pressed={state === s}
                className={cn(
                  "cursor-pointer whitespace-nowrap rounded-md px-3 py-1 text-[13px] transition-colors",
                  state === s
                    ? "bg-panel font-medium text-ink shadow-[0_1px_2px_#1f2d3d14]"
                    : "text-sub hover:text-ink",
                )}
              >
                {STATE_LABEL[s]} · {counts[s]}
              </button>
            ))}
          </div>
          <div className="relative min-w-56 flex-1">
            <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Filter by wording, check name or example URL…"
              className="w-full rounded-lg border border-edge2 bg-panel2 py-2 pl-9 pr-3 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none"
            />
          </div>
          <span className="shrink-0 text-xs tabular-nums text-faint">
            {narrowed ? `${visible.length} of ${rows.length} checks` : `${rows.length} checks`}
          </span>
        </div>

        {(problem || error) && <p className="text-sm text-bad">{problem ?? error}</p>}
        {crawl.note && !running && !renderTab && <p className="text-xs text-faint">{crawl.note}</p>}
        {render.note && !running && renderTab && <p className="text-xs text-faint">{render.note}</p>}

        {loading ? (
          <Spinner />
        ) : rows.length === 0 ? (
          <EmptyState
            icon={renderTab ? TAB_ICON[tab] : ShieldCheck}
            title={state === "open" ? "Nothing open" : `Nothing ${STATE_LABEL[state].toLowerCase()}`}
            hint={emptyHint}
          />
        ) : visible.length === 0 ? (
          <EmptyState
            icon={SearchIcon}
            title="No check matches those filters"
            hint="Widen the check filter or clear the search box."
          />
        ) : (
          <div className="space-y-5">
            {SITE_ISSUE_SEVERITIES.filter((sev) => visible.some((r) => r.severity === sev)).map(
              (sev) => (
                <section key={sev} className="space-y-2">
                  <SeverityHeading severity={sev} />
                  <div className="divide-y divide-edge overflow-hidden rounded-2xl border border-edge bg-panel">
                    {visible
                      .filter((r) => r.severity === sev)
                      .map((group) => (
                        <IssueCard
                          key={`${group.scope}:${group.kind}`}
                          group={group}
                          onChanged={reload}
                        />
                      ))}
                  </div>
                </section>
              ),
            )}
          </div>
        )}
      </div>
    </PageEnter>
  );
}

function Freshness({
  tab,
  lastCrawledAt,
  pages,
  render,
}: {
  tab: SiteIssueType;
  lastCrawledAt: string | null;
  pages: number;
  render: Render;
}) {
  const s = render.status;
  let text: string;
  if (tab === "static") {
    text = lastCrawledAt
      ? `Static checks read the HTML the server sends. ${pages} page${pages === 1 ? "" : "s"} on record, last read ${formatRelative(lastCrawledAt)}.`
      : "Static checks read the HTML the server sends. Nothing has been read from this website yet.";
  } else {
    const how =
      tab === "desktop"
        ? "Desktop rendering loads each page in a real browser as Googlebot and compares it with the raw HTML."
        : "Mobile rendering loads each page at phone width as Googlebot smartphone and compares it with the desktop render and the raw HTML.";
    const count = s
      ? `${s.renderedPages} of ${s.eligiblePages} page${s.eligiblePages === 1 ? "" : "s"} rendered` +
        (s.lastRenderedAt ? `, last ${formatRelative(s.lastRenderedAt)}` : "") +
        (s.pendingPages > 0 ? ` · ${s.pendingPages} changed since` : "") +
        "."
      : "";
    text = `${how} ${count}`.trim();
    if (!render.canRender) text += " Rendering runs in the Meelu app.";
  }
  return (
    <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-1">
      <span className="text-xs text-sub">{text}</span>
      <span className="text-xs text-faint">Turn-downs stay turned down between runs.</span>
    </div>
  );
}

function RerenderAsk({
  render,
  onRender,
  onSkip,
  onCancel,
}: {
  render: Render;
  onRender: (opts: { limit?: number; url?: string }) => void;
  onSkip: () => void;
  onCancel: () => void;
}) {
  const [limit, setLimit] = useState("");
  const [url, setUrl] = useState("");
  const s = render.status;
  const device = render.device === "mobile" ? "Googlebot smartphone" : "Googlebot";
  const onlyUrl = url.trim();
  const cap = Number(limit);
  const opts = {
    ...(onlyUrl ? { url: onlyUrl } : {}),
    ...(!onlyUrl && Number.isFinite(cap) && cap > 0 ? { limit: Math.floor(cap) } : {}),
  };
  const yes = onlyUrl
    ? "Yes — render that page, then check"
    : opts.limit
      ? `Yes — render up to ${opts.limit} pages, then check`
      : "Yes — render again, then check";
  const rendered = s?.renderedPages ?? 0;
  const meta = rendered
    ? `${rendered} page${rendered === 1 ? "" : "s"} rendered${s?.lastRenderedAt ? ` ${formatRelative(s.lastRenderedAt)}` : ""}` +
      (s && s.pendingPages > 0
        ? `, ${s.pendingPages} page${s.pendingPages === 1 ? "" : "s"} changed since the last render.`
        : ". Nothing has changed since the last render.")
    : "Nothing has been rendered on this device yet — the checks would have nothing to run on.";
  return (
    <div className="space-y-2.5 rounded-xl border border-accent/30 bg-accent-soft p-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-accent">
        Render the pages again?
      </p>
      <p className="text-sm text-ink">
        Rendering loads each page in a real browser as {device} and takes a few seconds per page.
        Use the last render if the website has not changed since.
      </p>
      <p className="text-xs text-faint">{meta}</p>
      <div className="flex flex-wrap items-center gap-2">
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Only this page (paste a URL)"
          className="min-w-64 flex-1 rounded-lg border border-edge2 bg-panel py-1.5 px-3 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none"
        />
        <input
          value={limit}
          onChange={(e) => setLimit(e.target.value.replace(/\D/g, ""))}
          inputMode="numeric"
          placeholder="Up to N pages"
          disabled={!!onlyUrl}
          className="w-36 rounded-lg border border-edge2 bg-panel py-1.5 px-3 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none disabled:opacity-50"
        />
      </div>
      <div className="flex flex-wrap gap-1.5">
        <Button size="sm" onClick={() => onRender(opts)}>
          {yes}
        </Button>
        <Button size="sm" variant="outline" onClick={onSkip} disabled={!rendered}>
          No — check the pages already rendered
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          Not now
        </Button>
      </div>
    </div>
  );
}

function RecrawlAsk({
  lastCrawledAt,
  pages,
  onCrawl,
  onSkip,
  onCancel,
}: {
  lastCrawledAt: string | null;
  pages: number;
  onCrawl: () => void;
  onSkip: () => void;
  onCancel: () => void;
}) {
  return (
    <div className="space-y-2.5 rounded-xl border border-accent/30 bg-accent-soft p-3">
      <p className="text-[11px] font-medium uppercase tracking-wide text-accent">
        Has the website changed?
      </p>
      <p className="text-sm text-ink">
        Have you changed the website since it was last read? Reading it again takes a while — it
        fetches every page — so it is only worth doing if something has actually changed.
      </p>
      <p className="text-xs text-faint">
        {lastCrawledAt
          ? `${pages} page${pages === 1 ? "" : "s"} on record, last read ${formatRelative(lastCrawledAt)}.`
          : "Nothing has been read from this website yet — the checks would have nothing to run on."}
      </p>
      <div className="flex flex-wrap gap-1.5">
        <Button size="sm" onClick={onCrawl}>
          Yes — read the site again, then check
        </Button>
        <Button size="sm" variant="outline" onClick={onSkip} disabled={!lastCrawledAt}>
          No — check the pages already read
        </Button>
        <Button size="sm" variant="ghost" onClick={onCancel}>
          Not now
        </Button>
      </div>
    </div>
  );
}

const SEVERITY_DOT: Record<SiteIssueSeverity, string> = {
  p0: "bg-bad",
  p1: "bg-bad/60",
  p2: "bg-warn",
  p3: "bg-faint",
};

const SEVERITY_TEXT: Record<SiteIssueSeverity, string> = {
  p0: "text-bad",
  p1: "text-bad",
  p2: "text-warn",
  p3: "text-sub",
};

function SeverityTile({
  severity,
  checks,
  pages,
  active,
  onClick,
}: {
  severity: SiteIssueSeverity;
  checks: number;
  pages: number;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      aria-pressed={active}
      disabled={checks === 0}
      className={cn(
        "flex cursor-pointer flex-col items-start gap-1 rounded-2xl border bg-panel px-4 py-3.5 text-left transition-colors disabled:cursor-default disabled:opacity-60",
        active ? "border-accent ring-2 ring-accent/30" : "border-edge hover:border-edge2",
      )}
    >
      <span className={cn("text-[11px] font-medium uppercase tracking-wide", SEVERITY_TEXT[severity])}>
        {SEVERITY_LABEL[severity]}
      </span>
      <span className="font-display text-2xl leading-none text-ink">{checks}</span>
      <span className="text-xs text-faint">
        {checks === 0 ? "nothing here" : `${pages} page${pages === 1 ? "" : "s"}`}
      </span>
    </button>
  );
}

function SeverityHeading({ severity }: { severity: SiteIssueSeverity }) {
  return (
    <div className="flex flex-wrap items-center gap-2.5 px-1">
      <span className={cn("h-2 w-2 rounded-full", SEVERITY_DOT[severity])} />
      <span className="text-[13px] font-semibold text-ink">{SEVERITY_LABEL[severity]}</span>
      <span className="text-xs text-faint">{SEVERITY_HINT[severity]}</span>
    </div>
  );
}

const PAGE_ISSUE_PAGE_SIZE = 100;

async function fetchPageIssues(
  kind: SiteIssueKind,
  state: SiteIssueState,
  limit: number,
): Promise<SitePageIssue[]> {
  const rows: SitePageIssue[] = [];
  for (let page = 1; rows.length < limit; page++) {
    const batch = await api<SitePageIssue[]>(
      `/api/v1/site/technical-seo/page-issues?page=${page}&page_size=${PAGE_ISSUE_PAGE_SIZE}&state=${state}&kind=${encodeURIComponent(kind)}`,
    );
    rows.push(...batch);
    if (batch.length < PAGE_ISSUE_PAGE_SIZE) break;
  }
  return rows.slice(0, limit);
}

function IssueCard({ group, onChanged }: { group: SiteIssueGroup; onChanged: () => void }) {
  const { scope, kind, issue, pages, matched, examples, state } = group;
  const [expanded, setExpanded] = useState(false);
  const [urls, setUrls] = useState<SitePageIssue[] | null>(null);
  const [confirming, setConfirming] = useState(false);
  const [why, setWhy] = useState("");
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const copyIssue = async () => {
    const lines = [issue, `Check: ${kind}`];
    if (scope === "site") {
      lines.push("Scope: site-wide");
    } else {
      const rows = await fetchPageIssues(kind, state, pages);
      const urls = rows.flatMap((r) => (r.url ? [r.url] : []));
      lines.push(`Pages affected (${urls.length}):`, ...urls);
    }
    try {
      await navigator.clipboard.writeText(lines.join("\n"));
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
    }
  };

  const loadUrls = async () => {
    setUrls(await fetchPageIssues(kind, state, 200));
  };

  const toggle = async () => {
    if (window.getSelection()?.toString()) return;
    const next = !expanded;
    setExpanded(next);
    if (next && scope === "pages" && urls === null) await loadUrls();
  };

  const move = async (to: SiteIssueState, reason?: string) => {
    setBusy(true);
    try {
      const path = scope === "site" ? "issues" : "page-issues";
      await api(`/api/v1/site/technical-seo/${path}`, {
        method: "PATCH",
        body: { kind, state: to, rejectionReason: reason },
      });
      setConfirming(false);
      setWhy("");
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const movePage = async (id: string, to: SiteIssueState) => {
    setBusy(true);
    try {
      await api(`/api/v1/site/technical-seo/page-issues/${id}`, {
        method: "PATCH",
        body: { state: to },
      });
      if (expanded) await loadUrls();
      onChanged();
    } finally {
      setBusy(false);
    }
  };

  const blast =
    scope === "site" ? "this site-wide check" : `all ${pages} page${pages === 1 ? "" : "s"}`;

  const stop = (e: React.SyntheticEvent) => e.stopPropagation();

  return (
    <div className="select-text">
      <div
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onClick={toggle}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            void toggle();
          }
        }}
        className="flex cursor-pointer items-start gap-3 px-4 py-4 transition-colors hover:bg-panel2/50"
      >
        <span className="mt-1 shrink-0 text-sub">
          {expanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
        </span>
        <div className="min-w-0 flex-1 space-y-2.5">
          <p className="text-[15px] leading-relaxed text-ink">{issue}</p>
          <div className="flex flex-wrap items-center gap-2.5 text-xs text-faint">
            <code className="rounded-md bg-panel2 px-1.5 py-0.5 font-mono text-sub">{kind}</code>
            <span className="font-medium text-sub">
              {scope === "site" ? "Site-wide" : matched > pages ? `${pages} of ${matched} pages` : `${pages} page${pages === 1 ? "" : "s"}`}
            </span>
            {state === "rejected" && <Badge tone="neutral">Turned down</Badge>}
            {!expanded && examples.length > 0 && (
              <span className="truncate">e.g. {examples.join(" · ")}</span>
            )}
          </div>
          {group.reason && (
            <p className="text-xs text-sub">
              <span className="text-faint">Turned down because </span>
              {group.reason}
            </p>
          )}
        </div>
        <div className="flex shrink-0 items-center gap-1" onClick={stop} onKeyDown={stop}>
          <Button
            variant="outline"
            size="sm"
            onClick={copyIssue}
            className={cn(copied && "border-good/30 text-good")}
            title="Copy the issue, the check name and every page it flagged"
          >
            {copied ? <Check size={13} /> : <Copy size={13} />}
            {copied ? "Copied" : "Copy"}
          </Button>
          {state === "open" && (
            <Button variant="ghost" size="sm" disabled={busy} onClick={() => setConfirming(true)}>
              <X size={13} /> Discard
            </Button>
          )}
          {state === "rejected" && (
            <Button variant="ghost" size="sm" disabled={busy} onClick={() => move("open")}>
              <RotateCcw size={13} /> Restore
            </Button>
          )}
        </div>
      </div>

      {confirming && (
        <div className="px-4 pb-4">
          <div className="space-y-2.5 rounded-xl border border-accent/30 bg-accent-soft p-3">
            <p className="text-[11px] font-medium uppercase tracking-wide text-accent">
              Discard the whole check
            </p>
            <p className="text-xs text-sub">
              This turns down <span className="font-medium text-ink">{blast}</span> this check
              flagged, in one go — not only the examples shown.
            </p>
            <p className="text-[11px] text-faint">
              It stays turned down through later runs. Switch the state filter to Turned down to
              bring it back.
            </p>
            <textarea
              value={why}
              onChange={(e) => setWhy(e.target.value)}
              rows={2}
              placeholder="Why does this not apply here? Optional — it shows against the check on the Turned down list."
              className="w-full resize-none rounded-lg border border-edge2 bg-panel2 px-3 py-2 text-xs text-ink placeholder:text-faint focus:border-accent focus:outline-none"
            />
            <div className="flex flex-wrap gap-1.5">
              <Button size="sm" disabled={busy} onClick={() => move("rejected", why.trim())}>
                Yes — discard {scope === "site" ? "it" : pages}
              </Button>
              <Button size="sm" variant="ghost" disabled={busy} onClick={() => setConfirming(false)}>
                Not yet
              </Button>
            </div>
          </div>
        </div>
      )}

      {expanded && (
        <div className="space-y-3 px-4 pb-4 pl-[42px]">
          <div className="grid gap-x-6 gap-y-1 text-xs sm:grid-cols-[auto_1fr]">
            <span className="text-faint">Check</span>
            <code className="font-mono text-sub">{kind}</code>
            <span className="text-faint">Severity</span>
            <span className="text-sub">
              {SEVERITY_LABEL[group.severity]} — {SEVERITY_HINT[group.severity]}
            </span>
            <span className="text-faint">Scope</span>
            <span className="text-sub">
              {scope === "site"
                ? "Site-wide, one finding for the whole website"
                : `${pages} page${pages === 1 ? "" : "s"} flagged${matched > pages ? ` out of ${matched} that match` : ""}`}
            </span>
          </div>

          {scope === "site" && examples.length > 0 && (
            <div className="divide-y divide-edge rounded-xl border border-edge bg-panel2">
              {examples.map((u) => (
                <div key={u} className="px-3 py-1.5">
                  <PageLink url={u} />
                </div>
              ))}
            </div>
          )}

          {scope === "pages" &&
            (urls === null ? (
              <Spinner className="py-6" />
            ) : (
              <div className="divide-y divide-edge rounded-xl border border-edge bg-panel2">
                {urls.map((r) => (
                  <div key={r.id} className="flex items-center justify-between gap-3 px-3 py-1.5">
                    <PageLink url={r.url ?? ""} />
                    {state === "open" && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => movePage(r.id, "rejected")}
                        className="shrink-0"
                      >
                        <X size={12} /> Discard
                      </Button>
                    )}
                    {state === "rejected" && (
                      <Button
                        size="sm"
                        variant="ghost"
                        disabled={busy}
                        onClick={() => movePage(r.id, "open")}
                        className="shrink-0"
                      >
                        <RotateCcw size={12} /> Restore
                      </Button>
                    )}
                  </div>
                ))}
                {urls.length < pages && (
                  <p className="px-3 py-2 text-xs text-faint">
                    Showing {urls.length} of {pages}. Copy the issue or download the CSV for the whole list.
                  </p>
                )}
              </div>
            ))}
        </div>
      )}
    </div>
  );
}

function PageLink({ url }: { url: string }) {
  return (
    <a
      href={url}
      target="_blank"
      rel="noreferrer"
      className="inline-flex min-w-0 items-center gap-1.5 truncate font-mono text-xs text-sub hover:text-accent"
    >
      <span className="truncate">{url}</span>
      <ExternalLink size={11} className="shrink-0 text-faint" />
    </a>
  );
}
