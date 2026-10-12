import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  Bot,
  Copy,
  Gauge,
  Layers,
  Search,
  SmilePlus,
  Unlink,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { CHECK_TOTAL } from "@/lib/seo-audit/catalog";
import { MAX_PAGES } from "@/lib/seo-audit/audit";
import { MAX_LINKS } from "@/lib/link-check/run";
import { CLUSTER_LIMITS } from "@/lib/keyword-clusters/limits";
import { site } from "@/lib/site";

const title = "Free SEO and marketing tools";
const description =
  "Seven free SEO and content tools: SEO audit, broken links, keyword clustering, readability, similarity, AI detection and review sentiment. No sign-up.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${site.url}/tools` },
  openGraph: { title, description, url: `${site.url}/tools`, type: "website" },
};

type Tool = {
  href: string;
  icon: LucideIcon;
  name: string;
  tagline: string;
  body: string;
  /** Shown as a small tag on the card. */
  note?: string;
};

type Group = {
  heading: string;
  blurb: string;
  tools: Tool[];
};

const groups: Group[] = [
  {
    heading: "Search and content",
    blurb: "Crawl a site, then check what it says once you get there.",
    tools: [
      {
        href: "/tools/seo-audit",
        icon: Search,
        name: "SEO audit",
        tagline: "Website SEO checker and technical site crawler",
        body: `Crawl a domain, page or sitemap — up to ${MAX_PAGES} URLs — and get ${CHECK_TOTAL} technical checks in a table you can export. Titles, canonicals, redirects, structured data, hreflang and AI crawler access.`,
      },
      {
        href: "/tools/broken-link-checker",
        icon: Unlink,
        name: "Broken link checker",
        tagline: "Dead link finder and 404 checker",
        body: `Test every internal link, external link and image — up to ${MAX_LINKS} destinations — for 404s, dead domains and redirect chains. Shows the page and anchor text for each one.`,
      },
      {
        href: "/tools/keyword-clustering-tool",
        icon: Layers,
        name: "Keyword clustering tool",
        tagline: "Group keywords into pages by search intent",
        body: `Expand up to ${CLUSTER_LIMITS.maxSeeds} seed keywords, split them by what the searcher wants, and check each cluster against Google's top 10 and real per-phrase search volume.`,
      },
      {
        href: "/tools/readability-checker",
        icon: Gauge,
        name: "Readability checker",
        tagline: "Flesch, grade level and the sentences dragging you down",
        body: "Six readability formulas computed exactly, plus the long sentences, complex words and passive constructions behind the number.",
        note: "Nothing uploaded",
      },
      {
        href: "/tools/similarity-checker",
        icon: Copy,
        name: "Similarity checker",
        tagline: "Duplicate content and shared passages",
        body: "Compare two documents or URLs and see how much they share — in both directions, since how much of yours is in theirs is a different question from the reverse.",
        note: "Nothing uploaded",
      },
      {
        href: "/tools/ai-content-detector",
        icon: Bot,
        name: "AI content detector",
        tagline: "Does this text read as machine-written?",
        body: "A real classifier running in your browser, not a heuristic. States its own error rate plainly, including the false positives on formal and non-native English.",
        note: "Runs in browser",
      },
    ],
  },
  {
    heading: "Customers and feedback",
    blurb: "A file people already have, read properly instead of skimmed.",
    tools: [
      {
        href: "/tools/review-sentiment-analyzer",
        icon: SmilePlus,
        name: "Review sentiment analysis",
        tagline: "Score a CSV of reviews positive, negative or neutral",
        body: "Every review labelled, the complaints ranked by how often they come up, and the reviews whose star rating disagrees with their wording.",
        note: "Nothing uploaded",
      },
    ],
  },
];

export default function ToolsPage() {
  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-20">
      <h1 className="font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
        Free tools
      </h1>

      <div className="mt-14 flex flex-col gap-14">
        {groups.map((group) => (
          <section key={group.heading}>
            <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
              <h2 className="font-display text-2xl tracking-tight text-ink">
                {group.heading}
              </h2>
              <span className="font-mono text-xs text-faint">
                {group.tools.length} {group.tools.length === 1 ? "tool" : "tools"}
              </span>
            </div>
            <p className="mt-1.5 text-sm text-sub">{group.blurb}</p>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              {group.tools.map((tool) => (
                <Link
                  key={tool.href}
                  href={tool.href}
                  className="group flex flex-col rounded-2xl border border-edge bg-panel p-5 transition-colors hover:border-edge2"
                >
                  <div className="flex items-start justify-between gap-3">
                    <tool.icon size={18} className="shrink-0 text-accent" />
                    <ArrowRight
                      size={16}
                      className="mt-0.5 shrink-0 text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-accent"
                    />
                  </div>
                  <h3 className="mt-3 font-display text-lg tracking-tight text-ink">
                    {tool.name}
                  </h3>
                  <p className="mt-1 text-sm text-sub">{tool.tagline}</p>
                  <p className="mt-3 text-sm leading-relaxed text-sub">{tool.body}</p>
                  {tool.note ? (
                    <span className="mt-4 inline-flex w-fit items-center rounded-full border border-good/25 bg-good/5 px-2 py-0.5 font-mono text-[10px] text-good">
                      {tool.note}
                    </span>
                  ) : null}
                </Link>
              ))}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
