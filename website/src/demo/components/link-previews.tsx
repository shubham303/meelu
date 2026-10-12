"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, Search as SearchIcon } from "lucide-react";
import type { SitePage } from "@demo/lib/types";

function truncate(text: string, max: number): string {
  if (text.length <= max) return text;
  return `${text.slice(0, max - 1).trimEnd()}…`;
}

function breadcrumb(url: string): { host: string; trail: string } {
  try {
    const u = new URL(url);
    const parts = u.pathname.split("/").filter(Boolean);
    return { host: u.hostname, trail: [u.hostname, ...parts].join(" › ") };
  } catch {
    return { host: url, trail: url };
  }
}

function faviconUrl(url: string): string | null {
  try {
    const host = new URL(url).hostname;
    return `https://www.google.com/s2/favicons?domain=${host}&sz=64`;
  } catch {
    return null;
  }
}

function siteName(page: SitePage): string {
  return page.socialMeta?.["og:site_name"] ?? breadcrumb(page.url).host;
}

function searchQuery(page: SitePage): string {
  return page.keywords?.[0] ?? page.title ?? breadcrumb(page.url).host;
}

const DUMMY_RESULTS = [
  {
    site: "Wikipedia",
    host: "en.wikipedia.org",
    trail: "en.wikipedia.org › wiki",
    title: "Marketing — Wikipedia",
    desc: "Marketing is the act of acquiring, satisfying and retaining customers. It is one of the primary components of business management and commerce.",
  },
  {
    site: "Forbes",
    host: "www.forbes.com",
    trail: "www.forbes.com › advisor › business",
    title: "The Best Marketing Tools Of 2026 – Forbes Advisor",
    desc: "We compared pricing, features and support across the leading platforms to find the best options for small businesses this year.",
  },
  {
    site: "HubSpot",
    host: "blog.hubspot.com",
    trail: "blog.hubspot.com › marketing",
    title: "19 Marketing Trends to Watch, According to Experts",
    desc: "Discover the trends shaping marketing this year, with data and predictions from industry leaders and our own research team.",
  },
];

function DummyFavicon({ label }: { label: string }) {
  return (
    <span className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full border border-[#ecedef] bg-[#f1f3f4] text-[11px] font-medium text-[#5f6368]">
      {label[0]}
    </span>
  );
}

function Favicon({ url }: { url: string }) {
  const [failed, setFailed] = useState(false);
  const src = faviconUrl(url);
  if (!src || failed) {
    return <div className="h-[26px] w-[26px] shrink-0 rounded-full bg-[#e2eeff]" />;
  }
  return (
    <span className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full border border-[#ecedef] bg-white">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={src} alt="" className="h-[18px] w-[18px]" onError={() => setFailed(true)} />
    </span>
  );
}

function ResultHeader({
  favicon,
  site,
  trail,
}: {
  favicon: React.ReactNode;
  site: string;
  trail: string;
}) {
  return (
    <div className="mb-1 flex items-center gap-3">
      {favicon}
      <div className="min-w-0">
        <div className="truncate text-sm leading-tight text-[#202124]">{site}</div>
        <div className="truncate text-xs leading-tight text-[#4d5156]">{truncate(trail, 70)}</div>
      </div>
    </div>
  );
}

function GoogleSearchBar({ query, mobile }: { query: string; mobile?: boolean }) {
  return (
    <div
      className={`flex items-center gap-3 rounded-full border border-[#dfe1e5] bg-white px-4 shadow-sm ${mobile ? "py-2" : "max-w-[600px] py-2.5"}`}
    >
      <span className="truncate text-sm text-[#202124]">{query}</span>
      <SearchIcon className="ml-auto h-4 w-4 shrink-0 text-[#4285f4]" />
    </div>
  );
}

function DesktopDummyResult({ r }: { r: (typeof DUMMY_RESULTS)[number] }) {
  return (
    <div className="max-w-[600px]">
      <ResultHeader favicon={<DummyFavicon label={r.site} />} site={r.site} trail={r.trail} />
      <div className="cursor-default truncate text-xl leading-snug text-[#1a0dab]">{r.title}</div>
      <p className="mt-1 text-sm leading-snug text-[#4d5156]">{truncate(r.desc, 160)}</p>
    </div>
  );
}

function NoDescription() {
  return (
    <span className="italic text-[#9aa0a6]">
      No meta description — Google will pick a snippet from the page text itself.
    </span>
  );
}

export function SerpDesktopPreview({ page }: { page: SitePage }) {
  const { trail } = breadcrumb(page.url);
  const title = page.title || page.url;
  const desc = page.metaDescription;
  return (
    <div className="w-full rounded-lg bg-white px-6 py-5 font-[arial,sans-serif]">
      <GoogleSearchBar query={searchQuery(page)} />
      <div className="mt-3 max-w-[600px] border-b border-[#ebebeb] pb-2 text-xs text-[#70757a]">
        About 1,240,000 results (0.42 seconds)
      </div>
      <div className="mt-5 space-y-7">
        <DesktopDummyResult r={DUMMY_RESULTS[0]} />
        <div className="-mx-3 max-w-[624px] rounded-lg px-3 py-2 ring-1 ring-accent/40">
          <ResultHeader favicon={<Favicon url={page.url} />} site={siteName(page)} trail={trail} />
          <a
            href={page.url}
            target="_blank"
            rel="noreferrer"
            className="block truncate text-xl leading-snug text-[#1a0dab] visited:text-[#681da8] hover:underline"
          >
            {truncate(title, 65)}
          </a>
          <p className="mt-1 text-sm leading-snug text-[#4d5156]">
            {desc ? truncate(desc, 160) : <NoDescription />}
          </p>
        </div>
        <DesktopDummyResult r={DUMMY_RESULTS[1]} />
        <DesktopDummyResult r={DUMMY_RESULTS[2]} />
      </div>
    </div>
  );
}

function MobileDummyResult({ r }: { r: (typeof DUMMY_RESULTS)[number] }) {
  return (
    <div className="rounded-xl border border-[#dadce0] bg-white p-4">
      <div className="mb-1.5 flex items-center gap-2.5">
        <DummyFavicon label={r.site} />
        <div className="min-w-0">
          <div className="truncate text-[13px] leading-tight text-[#202124]">{r.site}</div>
          <div className="truncate text-xs leading-tight text-[#4d5156]">{r.host}</div>
        </div>
      </div>
      <div className="cursor-default text-lg leading-snug text-[#1558d6] [-webkit-box-orient:vertical] [-webkit-line-clamp:2] [display:-webkit-box] overflow-hidden">
        {r.title}
      </div>
      <p className="mt-1 text-[13px] leading-snug text-[#4d5156] [-webkit-box-orient:vertical] [-webkit-line-clamp:3] [display:-webkit-box] overflow-hidden">
        {r.desc}
      </p>
    </div>
  );
}

export function SerpMobilePreview({ page }: { page: SitePage }) {
  const { host } = breadcrumb(page.url);
  const title = page.title || page.url;
  const desc = page.metaDescription;
  return (
    <div className="flex w-full justify-center rounded-lg bg-[#f1f3f4] py-6 font-[arial,sans-serif]">
      <div className="w-full max-w-[400px] space-y-3 px-3">
        <GoogleSearchBar query={searchQuery(page)} mobile />
        <MobileDummyResult r={DUMMY_RESULTS[0]} />
        <div className="rounded-xl border border-[#dadce0] bg-white p-4 ring-1 ring-accent/40">
          <div className="mb-1.5 flex items-center gap-2.5">
            <Favicon url={page.url} />
            <div className="min-w-0">
              <div className="truncate text-[13px] leading-tight text-[#202124]">
                {siteName(page)}
              </div>
              <div className="truncate text-xs leading-tight text-[#4d5156]">{host}</div>
            </div>
          </div>
          <a
            href={page.url}
            target="_blank"
            rel="noreferrer"
            className="block text-lg leading-snug text-[#1558d6] visited:text-[#681da8] hover:underline [-webkit-box-orient:vertical] [-webkit-line-clamp:2] [display:-webkit-box] overflow-hidden"
          >
            {title}
          </a>
          <p className="mt-1 text-[13px] leading-snug text-[#4d5156] [-webkit-box-orient:vertical] [-webkit-line-clamp:3] [display:-webkit-box] overflow-hidden">
            {desc ?? <NoDescription />}
          </p>
        </div>
        <MobileDummyResult r={DUMMY_RESULTS[1]} />
      </div>
    </div>
  );
}

export function WhatsAppPreview({ page }: { page: SitePage }) {
  const [imageFailed, setImageFailed] = useState(false);
  const meta = page.socialMeta ?? {};
  const title = meta["og:title"] ?? meta["twitter:title"] ?? page.title;
  const desc = meta["og:description"] ?? meta["twitter:description"] ?? page.metaDescription;
  const image = meta["og:image"] ?? meta["twitter:image"];
  const { host } = breadcrumb(page.url);
  const hasCard = Boolean(title);

  return (
    <div className="flex w-full justify-center rounded-lg bg-[#efeae2] py-6">
      <div className="w-full max-w-[420px] space-y-2 px-3">
        <div className="mr-auto w-fit max-w-[75%] rounded-lg rounded-tl-none bg-white px-2.5 py-1.5 text-[13px] text-[#111b21] shadow-sm">
          hey, found something for the campaign
          <span className="ml-2 align-bottom text-[10px] text-[#8696a0]">10:02</span>
        </div>
        <div className="mr-auto w-fit max-w-[75%] rounded-lg bg-white px-2.5 py-1.5 text-[13px] text-[#111b21] shadow-sm">
          send me the link?
          <span className="ml-2 align-bottom text-[10px] text-[#8696a0]">10:02</span>
        </div>
        <div className="ml-auto w-fit max-w-[85%] rounded-lg rounded-tr-none bg-[#d9fdd3] p-1.5 shadow-sm">
          {hasCard ? (
            <div className="overflow-hidden rounded-md bg-[#d1f4cc]">
              {image && !imageFailed && (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={image}
                  alt=""
                  className="aspect-[1.91/1] w-full object-cover"
                  onError={() => setImageFailed(true)}
                />
              )}
              <div className="p-2.5">
                <div className="text-[13px] font-medium leading-snug text-[#111b21] [-webkit-box-orient:vertical] [-webkit-line-clamp:2] [display:-webkit-box] overflow-hidden">
                  {title}
                </div>
                {desc && (
                  <div className="mt-0.5 text-xs leading-snug text-[#54656f] [-webkit-box-orient:vertical] [-webkit-line-clamp:2] [display:-webkit-box] overflow-hidden">
                    {desc}
                  </div>
                )}
                <div className="mt-1 text-xs text-[#8696a0]">{host}</div>
              </div>
            </div>
          ) : null}
          <div className="px-1.5 py-1">
            <a
              href={page.url}
              target="_blank"
              rel="noreferrer"
              className="break-all text-[13px] text-[#027eb5] underline"
            >
              {page.url}
            </a>
            <span className="ml-2 align-bottom text-[10px] text-[#8696a0]">10:03 ✓✓</span>
          </div>
        </div>
        <div className="mr-auto w-fit max-w-[75%] rounded-lg bg-white px-2.5 py-1.5 text-[13px] text-[#111b21] shadow-sm">
          {hasCard ? "nice, opening it now 👀" : "just a plain link? no preview?"}
          <span className="ml-2 align-bottom text-[10px] text-[#8696a0]">10:04</span>
        </div>
      </div>
    </div>
  );
}

function CollapsiblePreview({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div>
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="flex cursor-pointer items-center gap-1 text-xs font-medium uppercase tracking-wide text-sub transition-colors hover:text-ink"
      >
        {expanded ? <ChevronDown size={13} /> : <ChevronRight size={13} />}
        {label}
      </button>
      {expanded && <div className="mt-2">{children}</div>}
    </div>
  );
}

export function LinkPreviews({ page }: { page: SitePage }) {
  const issues = previewIssues(page);
  return (
    <div className="space-y-3">
      <CollapsiblePreview label="Google · desktop">
        <SerpDesktopPreview page={page} />
      </CollapsiblePreview>
      <CollapsiblePreview label="Google · mobile">
        <SerpMobilePreview page={page} />
      </CollapsiblePreview>
      <CollapsiblePreview label="WhatsApp & social apps">
        <WhatsAppPreview page={page} />
      </CollapsiblePreview>
      {issues.length > 0 && (
        <ul className="space-y-1 border-t border-edge2 pt-3 text-xs text-sub">
          {issues.map((issue) => (
            <li key={issue} className="flex gap-1.5">
              <span className="text-warn">•</span> {issue}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export function previewIssues(page: SitePage): string[] {
  const meta = page.socialMeta ?? {};
  const issues: string[] = [];
  if (!page.title) issues.push("The page has no <title>, so search results fall back to the URL.");
  else if ((page.titlePixels ?? 0) > 580)
    issues.push("The title is wider than ~580px and Google will cut it off on desktop.");
  if (!page.metaDescription)
    issues.push("No meta description — Google writes its own snippet, which you don't control.");
  else if (page.metaDescription.length > 160)
    issues.push("The meta description is over 160 characters and will be truncated.");
  if (!meta["og:title"] && !meta["twitter:title"]) {
    if (page.socialMetaCount > 0)
      issues.push(
        "This page has social tags, but they were crawled before Meelu stored their contents — the card preview fills in on the next crawl.",
      );
    else
      issues.push(
        "No Open Graph tags — WhatsApp, Slack and social apps show a bare link with no card.",
      );
  } else if (!meta["og:image"] && !meta["twitter:image"])
    issues.push("No og:image — link cards render as text only, with no picture.");
  if (page.robotsDirectives?.includes("nosnippet"))
    issues.push("A nosnippet directive hides the description in Google results.");
  return issues;
}
