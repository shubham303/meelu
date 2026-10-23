import type { Metadata } from "next";
import Link from "next/link";
import {
  ArrowRight,
  BarChart3,
  Check,
  Download,
  FileChartColumn,
  FileText,
  Globe,
  MessageCircleQuestion,
  NotebookPen,
  Radar,
  Search,
  ShieldCheck,
  Sparkles,
  UserSearch,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
import { DemoFrame } from "@/components/demo-frame";
import { HeroDownload } from "@/components/download-buttons";
import { listPosts, formatDate } from "@/lib/blog";
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

const heroStats = [
  { value: "9", label: "desks, one coworker" },
  { value: "25+", label: "apps and data sources" },
  { value: "0", label: "changes without your OK" },
];

type Finding = {
  desk: string;
  icon: LucideIcon;
  tone: string;
  headline: string;
  evidence: string;
  action: string;
};

const findings: Finding[] = [
  {
    desk: "GEO",
    icon: MessageCircleQuestion,
    tone: "text-accent",
    headline: "ChatGPT and Claude cite four sites for “how do I find keyword cannibalization”. None of them is you.",
    evidence: "Your guide answers 5 of the 7 points a full answer needs. It skips how to fix it and when to merge.",
    action: "Extend the guide",
  },
  {
    desk: "SEO",
    icon: Search,
    tone: "text-good",
    headline: "“internal linking tool” sits at position 11.4. Page two, one step from page one.",
    evidence: "2,900 searches a month. 1,840 impressions in Search Console over 28 days, 9 clicks.",
    action: "Add three internal links",
  },
  {
    desk: "Social Listening",
    icon: Radar,
    tone: "text-warn",
    headline: "A Reddit thread with 42 comments asks for a tool that finds orphan pages.",
    evidence: "Posted 6 hours ago in r/TechSEO. Nobody has named a tool yet. A reply is drafted for you.",
    action: "Review the reply",
  },
  {
    desk: "Technical SEO",
    icon: Wrench,
    tone: "text-bad",
    headline: "18 pages render differently on mobile. The menu hides your pricing link.",
    evidence: "Found in the last crawl, comparing the raw HTML with the desktop and mobile render.",
    action: "See the 18 pages",
  },
  {
    desk: "Find Leads",
    icon: UserSearch,
    tone: "text-accent",
    headline: "A head of growth at a 40-person SaaS posted twice this week that organic traffic is flat.",
    evidence: "Both posts linked, with an opening angle based on what they wrote. You write the message.",
    action: "Open their profile",
  },
];

type Desk = { icon: LucideIcon; name: string; body: string; href: string };

const stages: { stage: string; title: string; desks: Desk[] }[] = [
  {
    stage: "Know",
    title: "See your site the way Google does",
    desks: [
      {
        icon: Globe,
        name: "Site",
        href: "/docs/site",
        body: "Meelu crawls every page, reads what each one says and maps how they link. Technical SEO finds broken links, missing tags and pages that render differently on mobile.",
      },
    ],
  },
  {
    stage: "Decide",
    title: "Know what to work on next",
    desks: [
      {
        icon: Search,
        name: "SEO",
        href: "/docs/seo",
        body: "Your Search Console and Google Analytics data next to live keyword volumes, Google's top 10, competitors and backlinks. Keywords are grouped so that each page targets one search.",
      },
      {
        icon: MessageCircleQuestion,
        name: "GEO",
        href: "/docs/geo",
        body: "Track the questions people ask AI search. See if one of your pages answers each one, and what ChatGPT, Claude and Google's AI Overview say and cite.",
      },
    ],
  },
  {
    stage: "Make",
    title: "Write pages that are built to rank",
    desks: [
      {
        icon: FileText,
        name: "Content",
        href: "/docs/content",
        body: "Title, H1, meta description, slug, target keyword and body, checked on every save. The writer picks the keyword and internal links from your own data, and can save a draft into Webflow or Contentful.",
      },
    ],
  },
  {
    stage: "Earn",
    title: "Go where your customers already are",
    desks: [
      {
        icon: Radar,
        name: "Social Listening",
        href: "/docs/social-listening",
        body: "Describe your business and Meelu finds conversations on Reddit, X, LinkedIn, Hacker News and more where a reply from you would help. You pick which ones to answer.",
      },
      {
        icon: UserSearch,
        name: "Find Leads",
        href: "/docs/find-leads",
        body: "Describe who you want to reach. Meelu finds people with a real reason to hear from you, and shows the posts behind each one. You write and send the message yourself.",
      },
    ],
  },
  {
    stage: "Measure",
    title: "Ask your data anything",
    desks: [
      {
        icon: BarChart3,
        name: "Analytics",
        href: "/docs/analytics",
        body: "Ask about traffic, clicks and rankings in plain words. Answers come with charts, the evidence behind them and how far to trust them.",
      },
      {
        icon: FileChartColumn,
        name: "Reports",
        href: "/docs/reports",
        body: "Keep the answers that matter from Analytics, SEO and Technical SEO. Rename them, save them as files, come back to them.",
      },
    ],
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
    body: "Connect once per website from the app. Every desk can read it.",
    items: [
      { name: "Google Search Console", color: "#4285F4" },
      { name: "Google Analytics 4", color: "#E37400" },
    ],
  },
  {
    title: "Email",
    body: "Drafts in your mailbox and draft campaigns. Through Resend, only email you approved is sent.",
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
    body: "Posts only the reply you approved, on the thread you picked.",
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
];

const dataSources = [
  { name: "DataForSEO", what: "Keyword volumes, Google results, backlinks and AI answers" },
  { name: "Apify", what: "Social search and LinkedIn people search" },
  { name: "ChatGPT · Claude · AI Overview", what: "What AI search answers and cites" },
  { name: "Claude or OpenRouter", what: "The model behind the agent. Bring your own Anthropic key if you like" },
];

const loop = [
  {
    step: "1",
    title: "You ask, or click a chip",
    body: "“Which pages lost clicks this month?” “Find threads where people ask for a tool like mine.” Every desk has ready-made prompts.",
  },
  {
    step: "2",
    title: "Meelu does the legwork",
    body: "It runs SQL over your own data, pulls live search and social data, reads your pages and checks its own work. You can watch every step.",
  },
  {
    step: "3",
    title: "You get a suggestion with evidence",
    body: "The pages, the numbers and the reason. Approve it, edit it or throw it away. Nothing changes on your site until you say so.",
  },
];

const reasons: { title: string; body: ReactNode }[] = [
  {
    title: "You decide, every time.",
    body: "Meelu points at what it found and shows the evidence. It never changes your site, publishes a page or sends an email on its own.",
  },
  {
    title: "Pay per website, not per seat.",
    body: (
      <>
        Each website costs 0.4 credits a day, 0.2 from the sixth website on, and outside data is charged at what it
        costs. Your whole team uses it with no seat fees. See{" "}
        <Link href="/pricing" className="text-ink underline underline-offset-4 hover:text-accent">
          pricing
        </Link>
        .
      </>
    ),
  },
  {
    title: "It remembers what you told it.",
    body: "Write a note once: your tone, your audience, the competitor you never mention. Meelu reads your notes before every task.",
  },
  {
    title: "Built in the open.",
    body: (
      <>
        Watch how Meelu is made and the SEO thinking behind every feature on the{" "}
        <Link href="/blog" className="text-ink underline underline-offset-4 hover:text-accent">
          blog
        </Link>
        .
      </>
    ),
  },
];

function Eyebrow({ children }: { children: ReactNode }) {
  return <p className="font-mono text-[11px] uppercase tracking-widest text-faint">{children}</p>;
}

function FindingCard({ finding }: { finding: Finding }) {
  const Icon = finding.icon;
  return (
    <div className="flex w-[19rem] shrink-0 flex-col rounded-2xl border border-edge bg-panel p-5 shadow-[0_1px_0_#1f2d3d0a] sm:w-[22rem]">
      <div className="flex items-center gap-2 text-xs font-medium">
        <Icon size={14} className={finding.tone} />
        <span className="text-ink">{finding.desk}</span>
        <span className="ml-auto rounded-full bg-panel2 px-2 py-0.5 font-mono text-[10px] uppercase tracking-wider text-faint">
          Suggestion
        </span>
      </div>
      <p className="mt-3 text-[15px] leading-snug text-ink text-pretty">{finding.headline}</p>
      <p className="mt-2 text-sm text-sub text-pretty">{finding.evidence}</p>
      <div className="mt-auto flex items-center gap-2 pt-4 text-xs">
        <span className="inline-flex items-center gap-1 rounded-md bg-accent px-2.5 py-1 font-medium text-white">
          <Check size={12} /> {finding.action}
        </span>
        <span className="rounded-md border border-edge2 px-2.5 py-1 text-sub">Dismiss</span>
      </div>
    </div>
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
  const posts = listPosts().slice(0, 4);

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
            background: "radial-gradient(55% 45% at 50% 0%, var(--color-accent-soft), transparent 72%)",
          }}
        />
        <div className="relative mx-auto w-full max-w-6xl px-4 pt-16 sm:px-6 sm:pt-24">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-edge2 bg-panel px-3 py-1 text-xs text-sub">
              <Sparkles size={12} className="text-accent" />
              New: GEO, Find Leads and 14 connected apps
            </span>
            <h1 className="mt-5 font-display text-4xl leading-[1.06] tracking-tight text-ink text-balance sm:text-5xl lg:text-6xl">
              Your AI <span className="text-accent">marketing coworker</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-base text-sub text-pretty sm:text-lg">
              Meelu is a desktop app with an AI agent that crawls your site, reads your Search Console, checks what
              ChatGPT says about your niche, writes pages, and finds the conversations and people worth your time.
              Every finding comes with its evidence. You make the call.
            </p>
            <div className="mt-9">
              <HeroDownload>
                <Link
                  href="/demo"
                  className="inline-flex h-12 items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-5 text-sm text-ink transition-colors hover:bg-panel2"
                >
                  Try the live demo <ArrowRight size={14} />
                </Link>
              </HeroDownload>
            </div>
            <dl className="mx-auto mt-10 grid max-w-xl grid-cols-3 gap-4">
              {heroStats.map((s) => (
                <div key={s.label}>
                  <dt className="sr-only">{s.label}</dt>
                  <dd className="font-display text-3xl text-ink sm:text-4xl">{s.value}</dd>
                  <dd className="mt-1 text-xs text-sub">{s.label}</dd>
                </div>
              ))}
            </dl>
          </div>
          <div className="mt-14 pb-16 sm:mt-16">
            <DemoFrame />
            <p className="mx-auto mt-6 max-w-xl text-center text-sm text-sub text-pretty">
              This is the real dashboard running on a sample website. Click anything. Nothing leaves your browser.
            </p>
          </div>
        </div>
      </section>

      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-4 pt-20 sm:px-6">
          <Eyebrow>A morning with Meelu</Eyebrow>
          <h2 className="mt-3 max-w-2xl font-display text-3xl tracking-tight text-ink text-balance sm:text-4xl">
            It finds the work. It shows you why. You decide what to do.
          </h2>
          <p className="mt-4 max-w-2xl text-sub text-pretty">
            Each desk watches one part of your marketing and hands you suggestions like these, each one with the data it
            came from.
          </p>
        </div>
        <div className="mt-10 overflow-x-auto pb-20 [scrollbar-width:none]">
          <div className="mx-auto flex w-max gap-4 px-4 sm:px-6 lg:max-w-6xl lg:w-auto lg:flex-wrap">
            {findings.map((f) => (
              <FindingCard key={f.desk} finding={f} />
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
          <Eyebrow>Nine desks</Eyebrow>
          <h2 className="mt-3 max-w-2xl font-display text-3xl tracking-tight text-ink text-balance sm:text-4xl">
            From the first crawl to the first customer
          </h2>
          <p className="mt-4 max-w-2xl text-sub text-pretty">
            A desk is one job: auditing, planning, writing, outreach or reporting. The agent works across all of them,
            so one question can pull from your pages, your search data and the web at once.
          </p>
          <ol className="mt-12 space-y-10">
            {stages.map((s, i) => (
              <li key={s.stage} className="grid gap-5 lg:grid-cols-[14rem_1fr] lg:gap-10">
                <div>
                  <span className="font-mono text-xs text-accent">
                    0{i + 1} · {s.stage}
                  </span>
                  <h3 className="mt-1 font-display text-xl text-ink text-balance">{s.title}</h3>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  {s.desks.map((d) => {
                    const Icon = d.icon;
                    return (
                      <Link
                        key={d.name}
                        href={d.href}
                        className="group rounded-2xl border border-edge bg-panel p-5 transition-colors hover:border-edge2"
                      >
                        <div className="flex items-center gap-2.5">
                          <span className="grid size-8 place-items-center rounded-lg bg-accent-soft text-accent">
                            <Icon size={16} />
                          </span>
                          <span className="font-medium text-ink">{d.name}</span>
                          <ArrowRight
                            size={14}
                            className="ml-auto text-faint transition-transform group-hover:translate-x-0.5 group-hover:text-accent"
                          />
                        </div>
                        <p className="mt-3 text-sm text-sub text-pretty">{d.body}</p>
                      </Link>
                    );
                  })}
                </div>
              </li>
            ))}
          </ol>
          <div className="mt-10 flex items-start gap-3 rounded-2xl border border-edge bg-panel p-5">
            <NotebookPen size={18} className="mt-0.5 shrink-0 text-accent" />
            <p className="text-sm text-sub text-pretty">
              <span className="font-medium text-ink">Plus Notes and an Overview.</span> Tell Meelu once about your
              audience, your tone or the competitor you never mention, and it reads that before every task. The Overview
              shows what is waiting on you across every desk.
            </p>
          </div>
        </div>
      </section>

      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
          <Eyebrow>Integrations</Eyebrow>
          <h2 className="mt-3 max-w-2xl font-display text-3xl tracking-tight text-ink text-balance sm:text-4xl">
            Works with the tools you already use
          </h2>
          <p className="mt-4 max-w-2xl text-sub text-pretty">
            Connect your mailbox, CMS, CRM and docs from the Connections screen. Meelu saves drafts, records and new
            pages there for you to review. It never publishes a page, and it sends email only through your own
            Resend account, once you approve it.
          </p>
          <div className="mt-10 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {integrationGroups.map((g) => (
              <div key={g.title} className="rounded-2xl border border-edge bg-panel p-5">
                <h3 className="font-medium text-ink">{g.title}</h3>
                <p className="mt-1 text-sm text-sub">{g.body}</p>
                <div className="mt-4 flex flex-wrap gap-2">
                  {g.items.map((item) => (
                    <IntegrationChip key={item.name} item={item} />
                  ))}
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6 grid gap-4 lg:grid-cols-2">
            <div className="rounded-2xl border border-edge bg-panel p-5">
              <h3 className="font-medium text-ink">Listens on</h3>
              <p className="mt-1 text-sm text-sub">Where Social Listening and Find Leads look for conversations.</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {listeningPlatforms.map((p) => (
                  <span key={p} className="rounded-full border border-edge2 px-3 py-1 text-sm text-ink">
                    {p}
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
                {dataSources.map((d) => (
                  <div key={d.name} className="flex flex-col gap-0.5 py-2.5 sm:flex-row sm:gap-4">
                    <dt className="shrink-0 text-sm font-medium text-ink sm:w-52">{d.name}</dt>
                    <dd className="text-sm text-sub">{d.what}</dd>
                  </div>
                ))}
              </dl>
            </div>
          </div>
        </div>
      </section>

      <section className="border-b border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
          <Eyebrow>How a task runs</Eyebrow>
          <h2 className="mt-3 max-w-2xl font-display text-3xl tracking-tight text-ink text-balance sm:text-4xl">
            Meelu suggests. You decide.
          </h2>
          <div className="mt-10 grid gap-4 md:grid-cols-3">
            {loop.map((l) => (
              <div key={l.step} className="rounded-2xl border border-edge bg-panel p-6">
                <span className="grid size-8 place-items-center rounded-full bg-accent font-mono text-sm text-white">
                  {l.step}
                </span>
                <h3 className="mt-4 font-medium text-ink">{l.title}</h3>
                <p className="mt-2 text-sm text-sub text-pretty">{l.body}</p>
              </div>
            ))}
          </div>
          <div className="mt-6 flex items-start gap-3 rounded-2xl border border-good/30 bg-good/5 p-5">
            <ShieldCheck size={18} className="mt-0.5 shrink-0 text-good" />
            <p className="text-sm text-sub text-pretty">
              <span className="font-medium text-ink">Your judgement stays in the loop.</span> When several pages split
              one search, Meelu names the query and suggests a pillar page. It does not rewrite, merge or redirect your
              pages. That is your call.
            </p>
          </div>
        </div>
      </section>

      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
          <Eyebrow>Why Meelu</Eyebrow>
          <h2 className="mt-3 font-display text-3xl tracking-tight text-ink sm:text-4xl">
            Why Meelu, not another SaaS tool?
          </h2>
          <dl className="mt-8 grid gap-8 sm:grid-cols-2">
            {reasons.map((r) => (
              <div key={r.title}>
                <dt className="text-base font-medium text-ink">{r.title}</dt>
                <dd className="mt-2 text-sm text-sub text-pretty">{r.body}</dd>
              </div>
            ))}
          </dl>
        </div>
      </section>

      {posts.length > 0 && (
        <section className="border-b border-edge">
          <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
            <div className="flex items-end justify-between gap-4">
              <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">From the blog</h2>
              <Link
                href="/blog"
                className="inline-flex shrink-0 items-center gap-1.5 rounded-lg border border-edge2 px-4 py-2 text-sm text-ink transition-colors hover:bg-panel2"
              >
                All posts <ArrowRight size={14} />
              </Link>
            </div>
            <div className="mt-8 divide-y divide-edge">
              {posts.map((post) => (
                <Link
                  key={post.slug}
                  href={`/blog/${post.slug}`}
                  className="group flex flex-col gap-1 py-5 sm:flex-row sm:items-baseline sm:justify-between"
                >
                  <span className="max-w-2xl font-medium text-ink group-hover:text-accent">{post.title}</span>
                  <time className="shrink-0 font-mono text-xs text-faint">{formatDate(post.date)}</time>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

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
            Give your site a coworker
          </h2>
          <p className="mx-auto mt-4 max-w-md text-sub text-pretty">
            Free to download for Mac and Windows. Your first website is free for three days. The app is in beta and
            not yet verified by Apple, Microsoft or Google, so expect a security warning the first time you open it.
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
            </a>
            .
          </p>
        </div>
      </section>
    </div>
  );
}
