import type { Metadata } from "next";
import Link from "next/link";
import {
  BarChart3,
  CheckCircle2,
  Download,
  Filter,
  GitFork,
  Layers,
  ScanSearch,
} from "lucide-react";
import { KeywordClusterTool } from "@/components/keyword-clusters/cluster-tool";
import { CLUSTER_LIMITS } from "@/lib/keyword-clusters/limits";
import { site } from "@/lib/site";

const url = `${site.url}/tools/keyword-clustering-tool`;

const title = "Free Keyword Clustering Tool: Group Keywords by Search Intent";
const description =
  "Free keyword clustering tool: enter seed keywords and get clusters split by search intent, checked against Google's top 10, with real search volume.";

export const metadata: Metadata = {
  title,
  description,
  keywords: [
    "keyword clustering tool",
    "free keyword clustering tool",
    "keyword grouping tool",
    "ai seo tool",
    "keyword clustering",
    "search intent clustering",
    "serp keyword clustering",
    "keyword cluster generator",
    "group keywords by intent",
    "topic clusters seo",
    "keyword cannibalization",
  ],
  alternates: { canonical: url },
  openGraph: { title, description, url, type: "website" },
};

const faqs: Array<{ q: string; a: string }> = [
  {
    q: "What is keyword clustering?",
    a: "Keyword clustering is grouping search queries that one page can answer. Instead of writing a page per keyword, you write one page per cluster and cover every phrase in it. A good cluster holds queries with the same intent, so the page fully satisfies everyone who searches any of them.",
  },
  {
    q: "How is this different from SERP-based clustering?",
    a: "SERP clustering groups keywords when Google shows the same pages for them. That works most of the time, but a small query can inherit the results of a bigger one that uses the same words. 'Light blue glasses' shows the same top results as 'blue light glasses', yet the searchers want different things. This tool splits by intent first and then uses the SERP as evidence, and it flags the cases where the two disagree.",
  },
  {
    q: "What does the SERP overlap number mean?",
    a: "It is how many of the organic top-10 URLs two keywords share, after removing tracking parameters. Four or more shared URLs means Google currently treats the two searches alike. One or none means it treats them as different. It describes how Google ranks today, not what the searcher wants, so read it next to the intent label.",
  },
  {
    q: "Why does the tool show CPC and not keyword difficulty?",
    a: "CPC is what advertisers actually pay for a click, so it is a real market signal of how valuable a query is. Difficulty scores are each vendor's own estimate and disagree from tool to tool. The clusters are ranked by real searches, and CPC is shown next to them.",
  },
  {
    q: "Is the tool free? What are the limits?",
    a: `Yes, with no sign-up. Each run uses up to ${CLUSTER_LIMITS.maxSeeds} seed keywords, clusters up to ${CLUSTER_LIMITS.maxKeywords} related keywords and checks up to ${CLUSTER_LIMITS.maxSerpCalls} Google results pages. The keyword data and search results are paid lookups, so the tool runs ${CLUSTER_LIMITS.dailyRuns} times a day in total across everyone, resetting at midnight UTC.`,
  },
];

const highlights = [
  {
    icon: GitFork,
    title: "Splits by intent, not by words",
    body: "Keywords that share a core term are split into distinct searcher intents by a language model. Over-splitting is allowed, merging two different intents is not.",
  },
  {
    icon: ScanSearch,
    title: "Checked against Google's top 10",
    body: "The biggest clusters are checked against live organic results. Shared URLs are counted after removing tracking parameters, so the overlap is real.",
  },
  {
    icon: BarChart3,
    title: "Real per-phrase volume",
    body: "Google Ads merges word-order variants into one number. Clickstream volume shows how often each exact phrase is typed, and the tool flags every merged figure.",
  },
  {
    icon: Filter,
    title: "Removes noise you can see",
    body: "Low-volume phrases and keywords that drift away from your seed are removed and listed, so you can put back anything the filters got wrong.",
  },
  {
    icon: Layers,
    title: "One cluster, one page",
    body: "Each cluster is a page suggestion with its keywords, intent, real searches, Ads volume and CPC. You decide which pages to write.",
  },
  {
    icon: Download,
    title: "CSV export, no sign-up",
    body: "One row per keyword with its cluster, intent, both volumes, CPC and any flags. Opens in Excel, Sheets or Numbers.",
  },
];

const steps = [
  {
    name: "Enter seed keywords",
    text: `Up to ${CLUSTER_LIMITS.maxSeeds} seed keywords. The tool stays focused on them: it does not try to find every keyword your business could target.`,
  },
  {
    name: "It expands, filters and splits",
    text: "Each seed becomes a list of related searches. Low-volume keywords and keywords unrelated to their seed are removed, the rest are grouped by core keyword and each group is split by searcher intent.",
  },
  {
    name: "Review the evidence and decide",
    text: "Each cluster comes with Google's overlap, real search volume and flags where the evidence disagrees. Keep, merge or split the clusters, then export the CSV.",
  },
];

export default function KeywordClusteringToolPage() {
  return (
    <div>
      <section className="relative overflow-hidden border-b border-edge">
        <div aria-hidden className="grain absolute inset-0" />
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(55% 45% at 50% 0%, var(--color-accent-soft), transparent 72%)",
          }}
        />
        <div className="relative mx-auto w-full max-w-4xl px-6 py-16 sm:py-20">
          <nav aria-label="Breadcrumb" className="font-mono text-xs text-faint">
            <Link href="/tools" className="transition-colors hover:text-accent">
              Free tools
            </Link>
            <span className="px-1.5">/</span>
            <span>Keyword clustering tool</span>
          </nav>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            Free keyword clustering tool
          </h1>
          <p className="mt-4 max-w-3xl text-base text-sub text-pretty sm:text-lg">
            A free AI SEO tool for keyword clustering. Enter up to {CLUSTER_LIMITS.maxSeeds} seed
            keywords. The tool expands them into related
            searches, removes the noise and groups the rest by search intent, with one cluster for
            each page you could write. Every cluster shows its real search volume and CPC, is checked
            against Google&rsquo;s top 10, and is flagged where the evidence disagrees. Export the
            results as a CSV.
          </p>

          <div className="mt-8">
            <KeywordClusterTool />
          </div>

          <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-faint">
            {[
              "No account",
              "Intent split by an LLM",
              "Live Google top 10",
              "Clickstream volume",
              "CSV export",
            ].map((item) => (
              <li key={item} className="flex items-center gap-1.5">
                <CheckCircle2 size={12} className="text-good" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mx-auto w-full max-w-5xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          What the keyword grouping tool does
        </h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {highlights.map(({ icon: Icon, title: heading, body }) => (
            <article key={heading} className="rounded-2xl border border-edge bg-panel p-5">
              <Icon size={18} className="text-accent" />
              <h3 className="mt-3 text-base font-medium text-ink">{heading}</h3>
              <p className="mt-2 text-sm leading-relaxed text-sub">{body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="border-y border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-5xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            How to cluster keywords by search intent
          </h2>
          <ol className="mt-8 grid gap-5 sm:grid-cols-3">
            {steps.map((step, i) => (
              <li key={step.name} className="rounded-2xl border border-edge bg-panel p-5">
                <span className="font-mono text-xs text-faint">Step {i + 1}</span>
                <h3 className="mt-2 text-base font-medium text-ink">{step.name}</h3>
                <p className="mt-2 text-sm leading-relaxed text-sub">{step.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          Frequently asked questions
        </h2>
        <div className="mt-8 flex flex-col gap-3">
          {faqs.map((faq) => (
            <details key={faq.q} className="group rounded-2xl border border-edge bg-panel p-5">
              <summary className="cursor-pointer list-none text-base font-medium text-ink marker:hidden">
                {faq.q}
              </summary>
              <p className="mt-3 text-sm leading-relaxed text-sub">{faq.a}</p>
            </details>
          ))}
        </div>
      </section>

      <section className="border-t border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            Clusters are where content planning starts
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            Once you know which pages to write, check the ones you already have with the{" "}
            <Link href="/tools/seo-audit" className="font-medium text-accent hover:text-accent-hi">
              free SEO audit tool
            </Link>{" "}
            and compare drafts against competitors with the{" "}
            <Link
              href="/tools/similarity-checker"
              className="font-medium text-accent hover:text-accent-hi"
            >
              similarity checker
            </Link>
            .
          </p>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            All of them are pieces of{" "}
            <Link href="/" className="font-medium text-accent hover:text-accent-hi">
              Meelu
            </Link>
            , a desktop app where an AI marketing agent suggests what to do with your site and you
            decide.{" "}
            <Link href="/download" className="font-medium text-accent hover:text-accent-hi">
              Download the app
            </Link>
            .
          </p>
        </div>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify([
            {
              "@context": "https://schema.org",
              "@type": "WebApplication",
              name: "Meelu Free Keyword Clustering Tool",
              url,
              applicationCategory: "BusinessApplication",
              operatingSystem: "Any",
              description,
              offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
              featureList: [
                "Expands seed keywords into related searches",
                "Removes low-volume and off-topic keywords",
                "Groups keywords by core keyword and splits each group by search intent",
                "Checks clusters against Google's organic top 10",
                "Shows Google Ads volume, clickstream volume and CPC",
                "Flags clusters where SERP overlap and intent disagree",
                "CSV export",
              ],
              publisher: { "@type": "Organization", name: site.name, url: site.url },
            },
            {
              "@context": "https://schema.org",
              "@type": "FAQPage",
              mainEntity: faqs.map((faq) => ({
                "@type": "Question",
                name: faq.q,
                acceptedAnswer: { "@type": "Answer", text: faq.a },
              })),
            },
            {
              "@context": "https://schema.org",
              "@type": "HowTo",
              name: "How to cluster keywords by search intent",
              step: steps.map((step, i) => ({
                "@type": "HowToStep",
                position: i + 1,
                name: step.name,
                text: step.text,
              })),
            },
            {
              "@context": "https://schema.org",
              "@type": "BreadcrumbList",
              itemListElement: [
                { "@type": "ListItem", position: 1, name: "Free tools", item: `${site.url}/tools` },
                { "@type": "ListItem", position: 2, name: "Keyword clustering tool", item: url },
              ],
            },
          ]),
        }}
      />
    </div>
  );
}
