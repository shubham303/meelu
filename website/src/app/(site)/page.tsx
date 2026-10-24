import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Download } from "lucide-react";
import type { ReactNode } from "react";
import { DemoFrame } from "@/components/demo-frame";
import { HeroDownload } from "@/components/download-buttons";
import { listCaseStudies } from "@/lib/blog";
import { useCases } from "@/lib/use-cases";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  alternates: { canonical: site.url },
};

const organizationSchema = {
  "@context": "https://schema.org",
  "@graph": [
    {
      "@type": "Organization",
      "@id": `${site.url}/#organization`,
      name: site.name,
      url: site.url,
      logo: {
        "@type": "ImageObject",
        url: `${site.url}/meelu-logo.png`,
        width: 558,
        height: 144,
      },
      image: `${site.url}/meelu-mark.png`,
      email: site.email,
      sameAs: [site.github, site.twitter],
      founder: { "@type": "Person", name: site.author.name, url: site.author.url },
    },
    {
      "@type": "WebSite",
      "@id": `${site.url}/#website`,
      name: site.name,
      url: site.url,
      description: site.description,
      publisher: { "@id": `${site.url}/#organization` },
    },
  ],
};

const heroFindings = [
  {
    headline: "“internal linking tool” sits at position 11.4",
    evidence: "One step from page one. 1,840 impressions, 9 clicks in 28 days.",
  },
  {
    headline: "ChatGPT cites four sites for your main question. Not you.",
    evidence: "Your guide covers 5 of the 7 points a full answer needs.",
  },
  {
    headline: "A 42-comment r/TechSEO thread asks for a tool like yours",
    evidence: "Posted 6 hours ago. A reply is drafted for you to review.",
  },
];

const problems = [
  {
    title: "“Data gathering takes half my day.”",
    body: "A marketer on r/DigitalMarketing. Founders say the same.",
  },
  {
    title: "You audit once, then never again.",
    body: "A full audit takes a day. Your site changes every week.",
  },
  {
    title: "Search Console gives you numbers.",
    body: "It does not tell you which page to fix first.",
  },
];

const genericAiGaps = [
  {
    title: "It knows your site",
    body: "Meelu reads every page on your website and remembers it between tasks. A chat starts from zero each time.",
  },
  {
    title: "It tracks what changes",
    body: "Each crawl records the pages you changed and the content you published, so Meelu can see what moved the numbers.",
  },
  {
    title: "It reads your numbers",
    body: "Meelu checks your Search Console and traffic data to find which pages work and which do not.",
  },
  {
    title: "It uses the right tool",
    body: "Counting, grouping and trends run as SQL and statistics. The AI does not spend its effort guessing at numbers.",
  },
];

const cmoPrices = [
  { name: "Okara", slug: "okara", price: "$129 to $249 a month", note: "Reddit, articles and publishing on the $249 plan" },
  { name: "Indexly", slug: "indexly", price: "From $299 a month", note: "For the bundle; single modules from $49" },
  { name: "RankAI", slug: "rankai", price: "From $199 a month", note: "10 pages a month on one website" },
  { name: "Writesonic", slug: "writesonic", price: "From $99 a month", note: "$79 a month billed yearly" },
  { name: "Search Atlas", slug: "search-atlas", price: "From $99 a month", note: "AI search tracking from $199" },
];

const promises = [
  {
    title: "Watch every step",
    body: "You can see each query Meelu runs and each page it reads.",
  },
  {
    title: "It remembers",
    body: "Write your tone and audience in a note once. Meelu reads it before every task.",
  },
  {
    title: "Ready-made prompts",
    body: "Click a prompt such as “Which pages lost clicks this month?”",
  },
  {
    title: "Built in the open",
    body: "The blog shows how each feature is made.",
  },
];

type Integration = { name: string; color: string };

const integrationGroups: {
  title: string;
  body: string;
  items: Integration[];
}[] = [
  {
    title: "Your own data",
    body: "Connect once per website from the app. Every part of Meelu can read it.",
    items: [
      { name: "Google Search Console", color: "#4285F4" },
      { name: "Google Analytics 4", color: "#E37400" },
    ],
  },
  {
    title: "Email",
    body: "Drafts in your mailbox and draft campaigns. Through Resend, Meelu sends only email you approved.",
    items: [
      { name: "Gmail", color: "#EA4335" },
      { name: "Outlook", color: "#0078D4" },
      { name: "Mailchimp", color: "#B8860B" },
      { name: "Kit", color: "#FB6970" },
      { name: "Resend", color: "#000000" },
    ],
  },
  {
    title: "CMS",
    body: "New pages land as drafts. You publish them.",
    items: [
      { name: "Webflow", color: "#146EF5" },
      { name: "Contentful", color: "#2478CC" },
    ],
  },
  {
    title: "CRM",
    body: "Save a lead as a contact, with a note on why.",
    items: [
      { name: "HubSpot", color: "#FF7A59" },
      { name: "Attio", color: "#1f2d3d" },
      { name: "Pipedrive", color: "#017737" },
    ],
  },
  {
    title: "Docs",
    body: "Briefs, plans and reports saved where your team reads.",
    items: [
      { name: "Notion", color: "#1f2d3d" },
      { name: "Google Docs", color: "#4285F4" },
    ],
  },
  {
    title: "Social replies",
    body: "Meelu posts only the reply you approved, on the thread you picked.",
    items: [
      { name: "Reddit", color: "#FF4500" },
      { name: "LinkedIn", color: "#0A66C2" },
      { name: "GitHub", color: "#1f2d3d" },
    ],
  },
];

const listeningPlatforms = [
  "Reddit",
  "X (Twitter)",
  "LinkedIn",
  "Bluesky",
  "Facebook",
  "Hacker News",
  "Stack Exchange",
  "Dev.to",
  "GitHub Issues",
  "Forums and Q&A across the web",
];

const dataSources = [
  { name: "DataForSEO", what: "Keyword volumes, Google results, backlinks and AI answers" },
  { name: "Web search", what: "Public posts and profiles for social listening and leads" },
  { name: "ChatGPT · Claude · AI Overview", what: "What AI search answers and cites" },
  { name: "Claude or OpenRouter", what: "The model behind the agent. You can bring your own Anthropic key." },
];

function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="font-mono text-[11px] uppercase tracking-widest text-faint">{children}</p>;
}

function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h2 className="mt-3 max-w-2xl font-display text-3xl tracking-tight text-ink text-balance sm:text-4xl">
      {children}
    </h2>
  );
}

function IntegrationChip({ item }: { item: Integration }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-lg border border-edge bg-bg px-2.5 py-1.5 text-sm text-ink">
      <span
        aria-hidden
        className="grid size-5 place-items-center rounded-[5px] text-[11px] font-semibold text-white"
        style={{ background: item.color }}
      >
        {item.name[0]}
      </span>
      {item.name}
    </span>
  );
}

export default function Home() {
  const latestCaseStudy = listCaseStudies()[0];

  return (
    <div>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationSchema) }}
      />

      <section className="relative overflow-hidden border-b border-edge">
        <div aria-hidden className="grain absolute inset-0" />
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background: "radial-gradient(55% 45% at 30% 0%, var(--color-accent-soft), transparent 72%)",
          }}
        />
        <div className="relative mx-auto grid w-full max-w-6xl items-center gap-12 px-4 py-16 sm:px-6 sm:py-24 lg:grid-cols-[1.15fr_1fr]">
          <div>
            <Eyebrow>For founders and marketers</Eyebrow>
            <h1 className="mt-5 font-display text-4xl leading-[1.06] tracking-tight text-ink text-balance sm:text-5xl lg:text-6xl">
              Meelu,
              <br />
              <span className="text-accent">your AI CMO.</span>
            </h1>
            <p className="mt-6 max-w-xl text-base text-sub text-pretty sm:text-lg">
              SEO, AI search, content, social listening, lead finding and analytics for your website, in one app.
              Every suggestion shows the data behind it, and you make the call.
            </p>
            <div className="mt-9">
              <HeroDownload align="start">
                <Link
                  href="/demo"
                  className="inline-flex h-12 items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-5 text-sm text-ink transition-colors hover:bg-panel2"
                >
                  Try the live demo <ArrowRight size={14} />
                </Link>
              </HeroDownload>
              <p className="mt-2 text-xs text-faint">
                Free for your first day.{" "}
                <Link
                  href="/pricing"
                  className="text-sub underline decoration-edge underline-offset-4 transition-colors hover:text-ink hover:decoration-accent"
                >
                  See pricing
                </Link>
              </p>
            </div>
          </div>

          <div className="rounded-2xl border border-edge bg-panel p-5 shadow-[0_24px_48px_-32px_rgba(31,45,61,0.35)] sm:p-6">
            <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
              This week on yoursite.com · example
            </p>
            <div className="mt-4 flex flex-col gap-3">
              {heroFindings.map((finding) => (
                <div key={finding.headline} className="rounded-xl border border-edge bg-bg px-4 py-3.5">
                  <p className="text-[15px] font-medium leading-snug text-ink">{finding.headline}</p>
                  <p className="mt-1 text-sm text-sub">{finding.evidence}</p>
                </div>
              ))}
            </div>
            <div aria-hidden className="mt-4 grid grid-cols-3 gap-2 text-sm">
              <span className="rounded-lg bg-ink py-2.5 text-center font-medium text-panel">Approve</span>
              <span className="rounded-lg border border-edge2 py-2.5 text-center text-ink">Edit</span>
              <span className="rounded-lg border border-edge2 py-2.5 text-center text-ink">Reject</span>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-edge bg-panel2/60">
        <div className="mx-auto grid w-full max-w-6xl gap-8 px-4 py-14 sm:grid-cols-3 sm:px-6">
          {problems.map((problem) => (
            <div key={problem.title}>
              <p className="font-display text-xl text-ink">{problem.title}</p>
              <p className="mt-2 text-sm text-sub text-pretty">{problem.body}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <Eyebrow>Use cases</Eyebrow>
              <SectionTitle>Everything Meelu does for your site</SectionTitle>
            </div>
            <Link href="/use-cases" className="text-sm text-ink underline underline-offset-4 hover:text-accent">
              All use cases
            </Link>
          </div>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {useCases.map((useCase, index) => (
              <Link
                key={useCase.slug}
                href={`/use-cases/${useCase.slug}`}
                className="group flex flex-col rounded-2xl border border-edge bg-panel p-5 transition-colors hover:border-edge2"
              >
                <p className="font-mono text-xs text-accent">{String(index + 1).padStart(2, "0")}</p>
                <p className="mt-2 text-lg font-medium text-ink">{useCase.name}</p>
                <p className="mt-2 text-sm text-sub text-pretty">{useCase.summary}</p>
                <span className="mt-auto inline-flex items-center gap-1.5 pt-4 text-sm text-sub transition-colors group-hover:text-accent">
                  See how <ArrowRight size={14} />
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-edge bg-panel/60">
        <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.2fr]">
          <div>
            <Eyebrow>Why not a general AI chat</Eyebrow>
            <SectionTitle>Why not just ask ChatGPT or Claude?</SectionTitle>
            <p className="mt-4 max-w-xl text-sub text-pretty">
              A general AI chat does not keep enough context about your website. It also spends a lot of effort on
              work that a dedicated tool does faster and cheaper. Meelu is an AI agent built for digital marketing. It
              turns what it knows about your site into a short list of things to do to grow it.
            </p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {genericAiGaps.map((gap) => (
              <div key={gap.title} className="rounded-2xl border border-edge bg-panel p-5">
                <p className="font-medium text-ink">{gap.title}</p>
                <p className="mt-1.5 text-sm text-sub text-pretty">{gap.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-edge">
        <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1fr_1.2fr]">
          <div>
            <Eyebrow>Pricing</Eyebrow>
            <SectionTitle>An AI CMO for $15 a month</SectionTitle>
            <p className="mt-4 max-w-xl text-sub text-pretty">
              Other AI CMO tools charge a flat monthly plan. Meelu charges 50 cents a day for each website, plus the
              searches, data and AI it uses, at what they cost. You see every charge in the app.
            </p>
            <Link
              href="/pricing"
              className="mt-6 inline-flex items-center gap-1.5 text-sm text-ink underline underline-offset-4 hover:text-accent"
            >
              See how pricing works <ArrowRight size={14} />
            </Link>
          </div>
          <div className="overflow-hidden rounded-2xl border border-edge bg-panel">
            <div className="flex items-baseline justify-between gap-4 border-b border-edge bg-accent-soft px-5 py-4">
              <p className="font-medium text-ink">Meelu</p>
              <p className="text-right text-sm text-ink">
                <span className="font-medium">$15 a month</span>
                <span className="block text-xs text-sub">per website, plus usage at cost</span>
              </p>
            </div>
            {cmoPrices.map((tool) => (
              <Link
                key={tool.slug}
                href={`/alternatives/${tool.slug}`}
                className="flex items-baseline justify-between gap-4 border-b border-edge px-5 py-4 transition-colors last:border-b-0 hover:bg-panel2"
              >
                <p className="text-ink">{tool.name}</p>
                <p className="text-right text-sm text-ink">
                  {tool.price}
                  <span className="block text-xs text-sub">{tool.note}</span>
                </p>
              </Link>
            ))}
            <p className="border-t border-edge px-5 py-3 text-xs text-faint">
              Prices from each tool&apos;s own pricing page, checked October 24, 2026.
            </p>
          </div>
        </div>
      </section>

      {latestCaseStudy && (
        <section className="border-b border-edge">
          <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
            <div className="flex flex-wrap items-end justify-between gap-4">
              <div>
                <Eyebrow>Case studies</Eyebrow>
                <SectionTitle>Real sites, real numbers</SectionTitle>
              </div>
              <p className="text-sm text-sub">
                A new case study every week.{" "}
                <Link href="/case-studies" className="text-ink underline underline-offset-4 hover:text-accent">
                  Read them all
                </Link>
              </p>
            </div>
            <Link
              href={`/blog/${latestCaseStudy.slug}`}
              className="mt-10 flex flex-wrap items-center justify-between gap-8 rounded-3xl bg-ink px-6 py-10 text-panel transition-opacity hover:opacity-95 sm:px-10"
            >
              <div className="min-w-0 flex-[1_1_28rem]">
                <p className="font-mono text-[11px] uppercase tracking-widest text-panel/70">Case study</p>
                <p className="mt-3 font-display text-3xl leading-tight tracking-tight text-balance sm:text-4xl">
                  {latestCaseStudy.title}
                </p>
                <p className="mt-4 max-w-2xl text-panel/75 text-pretty">{latestCaseStudy.description}</p>
              </div>
              <span className="inline-flex items-center gap-1.5 rounded-lg bg-panel px-5 py-3 text-sm font-medium text-ink">
                Read the case study <ArrowRight size={14} />
              </span>
            </Link>
          </div>
        </section>
      )}

      <section className="border-b border-edge">
        <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2">
          <div>
            <h2 className="font-display text-3xl tracking-tight text-ink sm:text-4xl">
              You spend your time on decisions.
            </h2>
            <p className="mt-4 max-w-xl text-sub text-pretty">
              Meelu never changes your site, publishes a page or sends an email by itself. Each suggestion shows the
              pages, the numbers and the reason. You approve it, edit it or reject it.
            </p>
          </div>
          <div className="grid gap-6 sm:grid-cols-2">
            {promises.map((promise) => (
              <div key={promise.title} className="border-t-2 border-ink pt-3">
                <p className="font-medium text-ink">{promise.title}</p>
                <p className="mt-1.5 text-sm text-sub text-pretty">{promise.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
          <Eyebrow>Try it</Eyebrow>
          <SectionTitle>Click through Meelu on a sample site</SectionTitle>
          <div className="mt-10">
            <DemoFrame />
            <p className="mx-auto mt-6 max-w-xl text-center text-sm text-sub text-pretty">
              This is the real dashboard running on a sample website. Click anything. Nothing leaves your browser.
            </p>
          </div>
        </div>
      </section>

      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
          <Eyebrow>Integrations</Eyebrow>
          <SectionTitle>Works with the tools you already use</SectionTitle>
          <p className="mt-4 max-w-2xl text-sub text-pretty">
            Connect your mailbox, CMS, CRM and docs from the Connections screen. Meelu saves drafts, records and new
            pages there for you to review. It never publishes a page. It sends email only through your own Resend
            account, after you approve it.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {integrationGroups.map((group) => (
              <div key={group.title} className="rounded-2xl border border-edge bg-panel p-5">
                <h3 className="font-medium text-ink">{group.title}</h3>
                <p className="mt-1 text-sm text-sub">{group.body}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {group.items.map((item) => (
                    <IntegrationChip key={item.name} item={item} />
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-edge bg-panel p-5">
              <h3 className="font-medium text-ink">Listens on</h3>
              <p className="mt-1 text-sm text-sub">Where social listening and Find leads look for conversations.</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {listeningPlatforms.map((platform) => (
                  <span key={platform} className="rounded-full border border-edge2 px-3 py-1 text-sm text-ink">
                    {platform}
                  </span>
                ))}
              </div>
            </div>
            <div className="rounded-2xl border border-edge bg-panel p-5">
              <h3 className="font-medium text-ink">Live data, no extra accounts</h3>
              <p className="mt-1 text-sm text-sub">
                Meelu holds the vendor accounts. You pay what each call costs, from one credit balance.
              </p>
              <dl className="mt-4 divide-y divide-edge">
                {dataSources.map((source) => (
                  <div key={source.name} className="flex flex-col gap-0.5 py-2.5 sm:flex-row sm:gap-4">
                    <dt className="shrink-0 text-sm font-medium text-ink sm:w-52">{source.name}</dt>
                    <dd className="text-sm text-sub">{source.what}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </div>
      </section>

      <section className="relative overflow-hidden border-b border-edge">
        <div aria-hidden className="grain absolute inset-0" />
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background: "radial-gradient(50% 60% at 50% 100%, var(--color-accent-soft), transparent 72%)",
          }}
        />
        <div className="relative mx-auto w-full max-w-6xl px-4 py-24 text-center sm:px-6">
          <h2 className="font-display text-3xl tracking-tight text-ink text-balance sm:text-5xl">
            See what Meelu finds on your site.
          </h2>
          <p className="mx-auto mt-4 max-w-md text-sub text-pretty">
            Free to download for Mac and Windows. Your first website is free for one day. Meelu is in beta.
          </p>
          <div className="mx-auto mt-8 flex flex-wrap justify-center gap-3">
            <Link
              href="/download"
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
            >
              <Download size={15} /> Download the beta
            </Link>
            <Link
              href="/demo"
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-5 py-2.5 text-sm text-ink transition-colors hover:bg-panel2"
            >
              Take the guided tour <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      <section>
        <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
          <Eyebrow>Who builds it</Eyebrow>
          <h2 className="mt-3 font-display text-2xl tracking-tight text-ink">Built by Shubham Randive</h2>
          <p className="mt-4 max-w-2xl text-base text-sub text-pretty">
            Follow along on{" "}
            <a
              href={site.twitter}
              target="_blank"
              rel="noreferrer"
              className="text-ink underline underline-offset-4 hover:text-accent"
            >
              X (@shubham_19hshs)
            </a>{" "}
            and on the{" "}
            <Link href="/blog" className="text-ink underline underline-offset-4 hover:text-accent">
              blog
            </Link>
            .
          </p>
        </div>
      </section>
    </div>
  );
}
