"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import {
  ArrowLeft,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Search as SearchIcon,
} from "lucide-react";
import { PageEnter } from "@demo/components/animate";
import { Badge, Card, Spinner, StatCard, type BadgeTone } from "@demo/components/ui";
import { LinkPreviews } from "@demo/components/link-previews";
import { apiPaged, useApi } from "@demo/lib/use-api";
import { formatRelative } from "@demo/lib/utils";
import type { SitePage, SitePageLinks, SitePageLlmExtraction } from "@demo/lib/types";

const PAGE_TYPE_TONE: Record<string, BadgeTone> = {
  money: "good",
  hub: "good",
};

export default function SitePageDetailPage() {
  const { id } = useParams<{ id: string }>();
  const { data: page, loading } = useApi<SitePage>(`/api/v1/site/pages/${id}`);
  const { data: extraction } = useApi<SitePageLlmExtraction>(
    `/api/v1/site/page-llm-extractions/by-page/${id}`,
  );
  const { data: links } = useApi<SitePageLinks>(`/api/v1/site/pages/${id}/links`);

  return (
    <PageEnter>
      <div className="mb-4 flex flex-wrap items-center gap-4">
        <Link
          href="/demo/dashboard/site/pages"
          className="inline-flex items-center gap-1.5 text-sm text-sub transition-colors hover:text-ink"
        >
          <ArrowLeft size={14} /> Pages
        </Link>
        <div className="ml-auto w-full sm:w-72">
          <JumpSearch currentId={id} />
        </div>
      </div>

      {loading ? (
        <Spinner />
      ) : !page ? (
        <p className="text-sm text-sub">This page is not in the crawl any more.</p>
      ) : (
        <PageDetail page={page} extraction={extraction} links={links} />
      )}
    </PageEnter>
  );
}

function JumpSearch({ currentId }: { currentId: string }) {
  const router = useRouter();
  const [text, setText] = useState("");
  const [hits, setHits] = useState<SitePage[]>([]);
  const [open, setOpen] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const q = text.trim();
    const t = setTimeout(async () => {
      if (!q) {
        setHits([]);
        return;
      }
      try {
        const params = new URLSearchParams({ pageSize: "8", sort: "score:desc" });
        params.set(q.startsWith("/") ? "urlContains" : "titleContains", q);
        const res = await apiPaged<SitePage>(`/api/v1/site/pages?${params.toString()}`);
        setHits(res.data);
        setOpen(true);
      } catch {
        setHits([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [text]);

  useEffect(() => {
    const onDown = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, []);

  const shown = hits.filter((h) => h.id !== currentId);

  return (
    <div ref={boxRef} className="relative">
      <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-faint" />
      <input
        id="page-jump"
        value={text}
        onChange={(e) => setText(e.target.value)}
        onFocus={() => shown.length > 0 && setOpen(true)}
        placeholder="Jump to another page…"
        className="w-full rounded-lg border border-edge2 bg-panel py-2 pl-9 pr-3 text-sm text-ink placeholder:text-faint focus:border-accent focus:outline-none"
      />
      {open && shown.length > 0 && (
        <div className="absolute right-0 top-full z-20 mt-1 w-full min-w-72 overflow-hidden rounded-xl border border-edge2 bg-panel shadow-lg">
          {shown.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => {
                setOpen(false);
                setText("");
                router.push(`/demo/dashboard/site/pages/${p.id}`);
              }}
              className="block w-full cursor-pointer px-3 py-2 text-left transition-colors hover:bg-panel2"
            >
              <span className="block truncate text-sm text-ink">{p.title || p.url}</span>
              <span className="block truncate text-xs text-faint">{p.url}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function PageDetail({
  page: p,
  extraction,
  links,
}: {
  page: SitePage;
  extraction: SitePageLlmExtraction | null;
  links: SitePageLinks | null;
}) {
  const anchors = uniqueAnchors(links?.inbound);
  const inboundPages = uniqueUrls((links?.inbound ?? []).map((l) => l.srcUrl));
  const outboundPages = uniqueUrls((links?.outbound ?? []).map((l) => l.dstUrl));
  const externalPages = uniqueUrls((links?.external ?? []).map((l) => l.url));

  return (
    <div className="space-y-5">
      <div>
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <h1 className="font-display text-2xl text-ink">{p.title || p.url}</h1>
          {extraction?.pageType && (
            <Badge tone={PAGE_TYPE_TONE[extraction.pageType] ?? "neutral"}>
              {extraction.pageType}
            </Badge>
          )}
          {p.shallow && <Badge tone="neutral">{p.shallowReason ?? "skipped"}</Badge>}
        </div>
        <a
          href={p.url}
          target="_blank"
          rel="noreferrer"
          className="mt-1 inline-flex items-center gap-1 text-sm text-sub hover:text-ink hover:underline"
        >
          {p.url} <ExternalLink className="h-3.5 w-3.5" />
        </a>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-5">
        <StatCard
          label="Link score"
          value={typeof p.linkScore === "number" ? p.linkScore : "—"}
          hint="best-linked page scores 100"
        />
        <StatCard label="Inbound links" value={p.inlinks} />
        <StatCard label="Words" value={p.wordCount ?? "—"} />
        <StatCard label="Clicks from home" value={p.depth ?? "—"} />
        <StatCard label="Status" value={p.status ?? "—"} hint={p.stage ?? undefined} />
      </div>

      <Card>
        <SectionTitle>How the link appears in search and chats</SectionTitle>
        <LinkPreviews page={p} />
      </Card>

      <div className="grid gap-4 lg:grid-cols-2">
        <Card>
          <SectionTitle>Crawl</SectionTitle>
          <dl className="grid grid-cols-2 gap-3 text-xs">
            <Detail label="Stage" value={p.stage} />
            <Detail label="Crawled" value={p.lastCrawledAt ? formatRelative(p.lastCrawledAt) : "—"} />
            <Detail
              label="Text last really changed"
              value={
                p.contentChangedAt
                  ? formatRelative(p.contentChangedAt)
                  : "not measured yet — the crawl has seen this page once"
              }
            />
            <Detail
              label="Published"
              value={p.publishedAt ? formatRelative(p.publishedAt) : "none declared"}
            />
            <Detail
              label="Date the page declares"
              value={p.modifiedAt ? formatRelative(p.modifiedAt) : "none"}
            />
            <Detail label="In sitemap" value={p.inSitemap ? "yes" : "no"} />
            <Detail
              label="Noindex"
              value={p.robotsDirectives?.includes("noindex") ? "yes" : "no"}
            />
            <Detail label="Language" value={p.lang} />
            <Detail label="Format" value={p.format} />
          </dl>
          {p.canonical && p.canonical !== p.url && (
            <Block label="Canonical points elsewhere" text={p.canonical} />
          )}
          {p.redirectTo && <Block label="Redirects to" text={p.redirectTo} />}
          {p.fetchError && <Block label="Fetch error" text={p.fetchError} />}
        </Card>

        <Card>
          <SectionTitle>What the model read into it</SectionTitle>
          {extraction?.pageType ? (
            <dl className="grid grid-cols-2 gap-3 text-xs">
              <Detail
                label="Page type"
                value={
                  typeof extraction.confidence === "number"
                    ? `${extraction.pageType} · ${Math.round(extraction.confidence * 100)}% sure`
                    : extraction.pageType
                }
              />
              <Detail label="Model" value={extraction.model} />
              <Detail
                label="Extracted"
                value={extraction.extractedAt ? formatRelative(extraction.extractedAt) : "—"}
              />
            </dl>
          ) : (
            <p className="text-xs text-faint">
              Not classified yet — extraction runs on the server after each crawl settles.
            </p>
          )}
        </Card>

        <Card>
          <SectionTitle>Content</SectionTitle>
          <div className="space-y-3">
            {p.metaDescription && <Block label="Meta description" text={p.metaDescription} />}
            {!!p.h1?.length && <Block label="H1" text={p.h1.join(" · ")} />}
            {!!anchors.length && (
              <div>
                <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-sub">
                  What the site calls this page
                </h3>
                <ul className="space-y-1 text-xs text-sub">
                  {anchors.slice(0, 10).map((a) => (
                    <li key={a}>&ldquo;{a}&rdquo;</li>
                  ))}
                </ul>
              </div>
            )}
            {!p.metaDescription && !p.h1?.length && !anchors.length && (
              <p className="text-xs text-faint">The crawl read no meta or headings here.</p>
            )}
          </div>
        </Card>

        <Card>
          <SectionTitle>Link graph</SectionTitle>
          <div className="space-y-3">
            <UrlList label={`Pages that link here (${inboundPages.length})`} urls={inboundPages} />
            <UrlList
              label={`Pages this page links to (${outboundPages.length})`}
              urls={outboundPages}
            />
            <UrlList
              label={`Other sites this page links to (${externalPages.length})`}
              urls={externalPages}
            />
            {!inboundPages.length && !outboundPages.length && (
              <p className="text-xs text-faint">No internal links touch this page.</p>
            )}
          </div>
        </Card>
      </div>
    </div>
  );
}

function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <h2 className="mb-3 text-xs font-medium uppercase tracking-wide text-sub">{children}</h2>
  );
}

function uniqueAnchors(list: { anchor?: string }[] | undefined): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const { anchor } of list ?? []) {
    if (!anchor) continue;
    const key = anchor.trim().toLowerCase();
    if (!key || seen.has(key)) continue;
    seen.add(key);
    out.push(anchor.trim());
  }
  return out;
}

function uniqueUrls(urls: (string | undefined)[]): string[] {
  return [...new Set(urls.filter((u): u is string => !!u))];
}

function UrlList({ label, urls }: { label: string; urls: string[] }) {
  const [expanded, setExpanded] = useState(false);
  if (urls.length === 0) return null;
  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="mb-1 flex cursor-pointer items-center gap-1 text-xs font-medium uppercase tracking-wide text-sub transition-colors hover:text-ink"
      >
        {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        {label}
      </button>
      {expanded && (
        <ul className="space-y-1 text-xs">
          {urls.map((u) => (
            <li key={u}>
              <a
                href={u}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-start gap-1 break-all text-sub hover:text-ink hover:underline"
              >
                {u} <ExternalLink className="mt-0.5 h-3 w-3 shrink-0" />
              </a>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function Block({ label, text }: { label: string; text: string }) {
  return (
    <div className="mt-3">
      <h3 className="mb-1 text-xs font-medium uppercase tracking-wide text-sub">{label}</h3>
      <p className="break-words text-xs text-sub">{text}</p>
    </div>
  );
}

function Detail({ label, value }: { label: string; value: unknown }) {
  return (
    <div>
      <dt className="text-sub">{label}</dt>
      <dd>{value === null || value === undefined || value === "" ? "—" : String(value)}</dd>
    </div>
  );
}
