import type { Metadata } from "next";
import Link from "next/link";
import {
  Bot,
  CheckCircle2,
  Download,
  FileSearch,
  Gauge,
  Link2,
  ShieldCheck,
} from "lucide-react";
import { AuditTool } from "@/components/seo-audit/audit-tool";
import { CATEGORY_LABEL } from "@/components/seo-audit/shared";
import { CHECK_TOTAL, catalogByCategory } from "@/lib/seo-audit/catalog";
import { MAX_PAGES } from "@/lib/seo-audit/audit";
import { site } from "@/lib/site";

const url = `${site.url}/tools/seo-audit`;

const title = "Free SEO Audit Tool & Website SEO Checker";
const description =
  "Enter your website address and find out what stops your pages showing up in Google: missing titles, broken links, hidden pages, and what to fix first.";

export const metadata: Metadata = {
  title,
  description,
  keywords: [
    "free seo audit tool",
    "seo checker",
    "website seo checker",
    "technical seo audit",
    "site audit tool",
    "seo analyzer",
    "on-page seo checker",
    "seo crawler online",
    "broken link checker",
    "meta tag checker",
    "robots.txt tester",
    "xml sitemap checker",
    "canonical tag checker",
    "hreflang checker",
    "schema markup checker",
    "screaming frog alternative",
  ],
  alternates: { canonical: url },
  openGraph: {
    title,
    description,
    url,
    type: "website",
  },
};

const faqs: Array<{ q: string; a: string }> = [
  {
    q: "What is a technical SEO audit?",
    a: "A technical SEO audit is a check of whether a search engine can crawl, render, understand and index your pages. It looks at the machinery rather than the words: robots.txt rules, status codes, redirects, canonical tags, sitemaps, headings, structured data and internal links. The output is a list of faults that stop pages ranking, ordered by how much damage each one does.",
  },
  {
    q: "What should an SEO audit include?",
    a: "A complete audit covers five areas. Crawlability and indexing, which decide whether a page can appear at all. On-page elements: titles, meta descriptions, headings and content. Site architecture: internal links, URL structure, redirects and orphan pages. Machine-readable markup: canonicals, hreflang, structured data and Open Graph tags. And performance, meaning how fast the server answers and how the page behaves once loaded.",
  },
  {
    q: "How often should you audit a website?",
    a: "Once a month is enough for a site that is not changing much, and once a quarter is the minimum for anything. Always run an audit after a redesign, a domain migration, a CMS upgrade or a platform change, because that is when canonicals, redirects and robots.txt rules break. Those faults are invisible on screen and expensive in the results pages, which is why they need checking rather than noticing.",
  },
  {
    q: "What is the difference between technical SEO and on-page SEO?",
    a: "Technical SEO is about access: can a crawler reach the page, read it and index it. On-page SEO is about relevance: does the title, the content and the markup match what someone searched for. Technical work has to come first, because the best page on the internet earns nothing if a Disallow rule is hiding it.",
  },
  {
    q: "What are the most common technical SEO problems?",
    a: "The recurring ones are missing or duplicated title tags, pages blocked by robots.txt or a stray noindex tag, canonical tags pointing at the wrong URL, redirect chains left behind by a migration, broken internal links, and URLs that exist but appear in no sitemap and no menu. Most of these come from a change made for another reason. None of them announce themselves.",
  },
  {
    q: "What is a canonical tag and when do you need one?",
    a: "A canonical tag tells a search engine which URL is the real version of a page when several URLs show the same content. You need one whenever the same content is reachable at more than one address: tracking parameters, print versions, filtered category pages, or the same article under two paths. Without it the search engine picks for you, and it often picks the wrong one.",
  },
  {
    q: "How do you check whether Google can index a page?",
    a: "Check four things in order. Does robots.txt allow the URL, does the server return a 200 rather than a redirect or an error, does the page carry a noindex directive in its HTML or HTTP headers, and does the canonical tag point at itself rather than at somewhere else. If all four are clean the page is indexable, and anything still missing from the index is a quality or discovery problem rather than a technical one.",
  },
  {
    q: "Should you let AI crawlers access your site?",
    a: "It is two separate decisions, and it helps to treat them that way. Search crawlers such as OAI-SearchBot, PerplexityBot and Claude-SearchBot decide whether your pages can be cited in AI answers, so blocking them removes you from that surface. Training crawlers only feed model training and give nothing back directly. Many sites allow the first group and block the second, which robots.txt lets you do with one rule per user agent.",
  },
];

const highlights = [
  {
    icon: FileSearch,
    title: "Tells you what is holding your pages back",
    body: `${CHECK_TOTAL} checks on titles, descriptions, headings and the tags Google reads — each one naming the page it found the problem on and what to change.`,
  },
  {
    icon: Link2,
    title: "Finds the links that stopped working",
    body: "Broken internal links, redirects pointing at redirects, and pages nothing on your site links to — the faults visitors and Google both trip over, and nobody notices.",
  },
  {
    icon: Bot,
    title: "Shows whether AI search can read you",
    body: "Whether the crawlers behind ChatGPT, Claude, Perplexity and Google's AI answers are allowed on your site, so being left out of AI answers is a choice rather than an accident.",
  },
  {
    icon: ShieldCheck,
    title: "Says why a page could not be read",
    body: "Blocked in robots.txt, a server refusing the request, a security challenge, a host that never answers — named plainly, because the same thing stops Google.",
  },
  {
    icon: Download,
    title: "CSV export, no sign-up",
    body: "The whole issue list, downloadable. Open it in Excel or Sheets, or hand it straight to whoever is doing the fixing.",
  },
  {
    icon: Gauge,
    title: "Done in under a minute",
    body: "Enter an address and watch it work. Nothing to install, no Java, no account, no queue.",
  },
];

const steps = [
  {
    name: "Enter your website address",
    text: "A domain, a single page or a sitemap link. example.com is enough — the audit finds the rest of your pages itself.",
  },
  {
    name: "Watch it read your pages",
    text: "It fetches your pages the way Google would, gently, so it never becomes load on your server. Progress shows as it goes.",
  },
  {
    name: "Fix the top of the list",
    text: "Problems are ranked worst first, each with the page it was found on, what is wrong and how to put it right. Download the CSV to work through them.",
  },
];

export default function SeoAuditPage() {
  const catalog = catalogByCategory();

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
        <div className="relative mx-auto w-full max-w-3xl px-6 py-16 sm:py-20">
          <nav
            aria-label="Breadcrumb"
            className="font-mono text-xs text-faint"
          >
            <Link href="/tools" className="transition-colors hover:text-accent">
              Free tools
            </Link>
            <span className="px-1.5">/</span>
            <span>SEO audit</span>
          </nav>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            Free SEO audit tool
          </h1>
          <p className="mt-4 text-base text-sub text-pretty sm:text-lg">
            Your pages are not showing up in Google and you cannot see why. Enter
            your website address and this free SEO checker reads your pages the
            way Google does, then hands you a list of what is wrong and what to
            fix first. No sign-up, nothing to install.
          </p>

          <div className="mt-8">
            <AuditTool />
          </div>

          <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-faint">
            {[
              "No account",
              "No card",
              "Ranked worst first",
              "CSV export",
              "Whole site or one page",
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
          What this website SEO checker does
        </h2>
        <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {highlights.map(({ icon: Icon, title: heading, body }) => (
            <article
              key={heading}
              className="rounded-2xl border border-edge bg-panel p-5"
            >
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
            How to run a technical SEO audit
          </h2>
          <ol className="mt-8 grid gap-5 sm:grid-cols-3">
            {steps.map((step, i) => (
              <li key={step.name} className="rounded-2xl border border-edge bg-panel p-5">
                <span className="font-mono text-xs text-faint">
                  Step {i + 1}
                </span>
                <h3 className="mt-2 text-base font-medium text-ink">{step.name}</h3>
                <p className="mt-2 text-sm leading-relaxed text-sub">{step.text}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section id="checks" className="mx-auto w-full max-w-5xl px-6 py-16 scroll-mt-20">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          Everything it checks
        </h2>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-sub">
          The whole list, grouped the way you would work through it. Nothing is
          held back for a paid upgrade — this is what you get.
        </p>
        <div className="mt-8 flex flex-col gap-8">
          {catalog.map(({ category, checks }) => (
            <div key={category}>
              <h3 className="font-mono text-xs uppercase tracking-widest text-faint">
                {CATEGORY_LABEL[category]}
              </h3>
              <ul className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
                {checks.map((check) => (
                  <li
                    key={`${check.scope}-${check.id}`}
                    className="flex items-start gap-2 border-b border-edge/60 py-2 text-sm"
                  >
                    <span
                      className={`mt-1.5 size-1.5 shrink-0 rounded-full ${
                        check.severity === "critical"
                          ? "bg-bad"
                          : check.severity === "high"
                            ? "bg-warn"
                            : check.severity === "medium"
                              ? "bg-accent"
                              : "bg-faint"
                      }`}
                      title={check.severity}
                    />
                    <span className="text-ink/90">{check.label}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      <section className="border-y border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            What it does not do
          </h2>
          <p className="mt-3 text-sm leading-relaxed text-sub">
            Free SEO checkers tend to be quiet about their limits, which makes the
            report harder to trust. Here are ours.
          </p>
          <ul className="mt-6 space-y-3 text-sm leading-relaxed text-ink/90">
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">No JavaScript rendering.</strong> It
              reads the HTML your server returns. If your content only appears
              after a client-side render, this audit reports it missing — which is
              itself worth knowing.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">No Core Web Vitals.</strong> Server
              response time is measured; LCP, INP and CLS are not. Those need a
              real browser and a real device profile.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">No backlinks or rankings.</strong>{" "}
              Those need a third-party crawl index behind them. This audit only
              reads your own pages.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">
                {MAX_PAGES} pages, and it says so.
              </strong>{" "}
              On a larger site the checks that need a complete link graph — orphan
              pages, pages missing from the sitemap, crawl depth — are skipped
              rather than guessed at from a partial crawl.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">A link, not a history.</strong> Each
              report is saved under a private link you can share. There is no
              trend line across runs. Download the CSV if you want the raw rows.
            </li>
          </ul>
        </div>
      </section>

      <section className="mx-auto w-full max-w-3xl px-6 py-16">
        <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
          Frequently asked questions
        </h2>
        <div className="mt-8 flex flex-col gap-3">
          {faqs.map((faq) => (
            <details
              key={faq.q}
              className="group rounded-2xl border border-edge bg-panel p-5"
            >
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
            This is one page of a bigger idea
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            The crawler behind this tool is part of{" "}
            <Link href="/" className="font-medium text-accent hover:text-accent-hi">
              Meelu
            </Link>
            , a desktop app where an AI marketing agent crawls your site, audits
            every page and suggests the fixes, and you decide what changes.
          </p>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            It is in development and built in the open.{" "}
            <Link
              href="/download"
              className="font-medium text-accent hover:text-accent-hi"
            >
              Download the app
            </Link>{" "}
            or read how the audit thinks on the{" "}
            <Link href="/blog" className="font-medium text-accent hover:text-accent-hi">
              blog
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
              name: "Meelu Free SEO Audit Tool",
              url,
              applicationCategory: "BusinessApplication",
              operatingSystem: "Any",
              description,
              offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
              featureList: [
                `Crawls up to ${MAX_PAGES} URLs from a domain, page or XML sitemap`,
                `${CHECK_TOTAL} technical and on-page SEO checks`,
                "Finds broken internal links and redirect chains",
                "Flags missing or duplicated titles and descriptions",
                "Tells you which pages are accidentally hidden from Google",
                "Checks the tags search engines read about your pages",
                "Shows whether AI search crawlers are allowed on your site",
                "CSV export of every issue, ranked worst first",
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
              name: "How to run a free technical SEO audit",
              description:
                "Enter your website address, see what is stopping your pages showing up in search, and export the list of fixes to CSV.",
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
                {
                  "@type": "ListItem",
                  position: 1,
                  name: "Free tools",
                  item: `${site.url}/tools`,
                },
                { "@type": "ListItem", position: 2, name: "SEO audit tool", item: url },
              ],
            },
          ]),
        }}
      />
    </div>
  );
}
