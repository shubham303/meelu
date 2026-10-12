import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Download, Sparkles } from "lucide-react";
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

const features = [
  {
    title: "SEO audits",
    body: "Crawl your site and find what's broken: technical issues, missing tags and pages that render differently on mobile. Results in minutes, not weeks.",
  },
  {
    title: "Content planning",
    body: "Group keywords into clusters checked against Google's top 10, so each page targets one search. See the search volume and who ranks today, and pick the fights you can win.",
  },
  {
    title: "Page writing",
    body: "Write pages for your own site in Meelu: title, H1, meta description, slug and target keyword in one place. The agent drafts and checks the page. You edit it and put it live yourself.",
  },
  {
    title: "Internal links",
    body: "See how your pages link to each other. Meelu suggests links to add or remove, and a pillar page where several pages split one search, with the reason for each.",
  },
  {
    title: "Analytics",
    body: "Ask questions about your traffic and search data from Google Analytics and Search Console without switching tabs. Every answer says how far to trust it.",
  },
];

const reasons: { title: string; body: ReactNode }[] = [
  {
    title: "You decide, every time.",
    body: "Meelu points at what it found and shows the evidence. It never changes your site or your content on its own.",
  },
  {
    title: "Pay per website, not per seat.",
    body: (
      <>
        Each website costs 0.4 credits a day, and outside data is charged per use.
        Your whole team uses it with no seat fees. See{" "}
        <Link href="/pricing" className="text-ink underline underline-offset-4 hover:text-accent">
          pricing
        </Link>
        .
      </>
    ),
  },
  {
    title: "Built in the open.",
    body: (
      <>
        Watch how Meelu is made and the SEO thinking behind every feature. Read the{" "}
        <Link href="/blog" className="text-ink underline underline-offset-4 hover:text-accent">
          blog
        </Link>{" "}
        for updates.
      </>
    ),
  },
  {
    title: "Made for makers.",
    body: "Solo founder, agency or content team. Meelu grows with you without charging per seat.",
  },
];

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
            background:
              "radial-gradient(55% 45% at 50% 0%, var(--color-accent-soft), transparent 72%)",
          }}
        />
        <div className="relative mx-auto w-full max-w-6xl px-6 pt-20 sm:pt-24">
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-edge2 bg-panel px-3 py-1 text-xs text-sub">
              <Sparkles size={12} className="text-accent" />
              In development · Built in the open
            </span>
            <h1 className="mt-5 font-display text-4xl leading-[1.08] tracking-tight text-ink text-balance sm:text-5xl lg:text-6xl">
              Meelu
              <br />
              <span className="text-accent">AI Assistant</span> for Digital Marketing
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-base text-sub text-pretty sm:text-lg">
              Meelu brings marketing AI to your laptop. No seats. No plan tiers. No
              changes without your approval. Just tools that work on your machine.
            </p>
            <div className="mt-9">
              <HeroDownload>
                <Link
                  href="/blog"
                  className="inline-flex h-12 items-center gap-1.5 rounded-lg border border-edge2 px-5 text-sm text-ink transition-colors hover:bg-panel2"
                >
                  Read the blog <ArrowRight size={14} />
                </Link>
              </HeroDownload>
            </div>
          </div>
          <div className="mt-16 pb-16 sm:mt-20">
            <DemoFrame />
            <p className="mx-auto mt-6 max-w-xl text-center text-sm text-sub text-pretty">
              Click anything in the demo above. Nothing leaves your browser. This
              is how Meelu works: you stay in control.
            </p>
          </div>
        </div>
      </section>

      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-6 py-20">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            What Meelu does
          </p>
          <h2 className="mt-3 font-display text-2xl tracking-tight text-ink sm:text-3xl">
            One desk for the work behind your site
          </h2>
          <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
            {features.map((f) => (
              <div key={f.title} className="rounded-2xl border border-edge bg-panel p-6">
                <h3 className="text-base font-medium text-ink">{f.title}</h3>
                <p className="mt-3 text-sm text-sub text-pretty">{f.body}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-6 py-20">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Why Meelu
          </p>
          <h2 className="mt-3 font-display text-2xl tracking-tight text-ink sm:text-3xl">
            Why Meelu, not a SaaS tool?
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
          <div className="mx-auto w-full max-w-6xl px-6 py-20">
            <div className="flex items-end justify-between gap-4">
              <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
                From the blog
              </h2>
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
                  <span className="max-w-2xl font-medium text-ink group-hover:text-accent">
                    {post.title}
                  </span>
                  <time className="shrink-0 font-mono text-xs text-faint">
                    {formatDate(post.date)}
                  </time>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="relative overflow-hidden border-b border-edge">
        <div aria-hidden className="grain absolute inset-0" />
        <div className="relative mx-auto w-full max-w-6xl px-6 py-24 text-center">
          <h2 className="font-display text-3xl tracking-tight text-ink text-balance sm:text-4xl">
            Download Meelu
          </h2>
          <p className="mx-auto mt-4 max-w-md text-sub text-pretty">
            Free to download for Mac and Windows. Sign in with your Meelu account.
            New accounts start with 1 free credit.
          </p>
          <div className="mx-auto mt-8 flex flex-wrap justify-center gap-3">
            <Link
              href="/download"
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
            >
              <Download size={15} /> Download the app
            </Link>
            <Link
              href="/pricing"
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 px-5 py-2.5 text-sm text-ink transition-colors hover:bg-panel2"
            >
              See pricing <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      </section>

      <section>
        <div className="mx-auto w-full max-w-6xl px-6 py-20">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Who builds it
          </p>
          <h2 className="mt-3 font-display text-2xl tracking-tight text-ink">
            Built by Shubham Randive
          </h2>
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
