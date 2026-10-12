import type { Metadata } from "next";
import Link from "next/link";
import {
  CheckCircle2,
  Download,
  FileWarning,
  Globe2,
  ImageOff,
  Route,
  Search,
} from "lucide-react";
import { BrokenLinkChecker } from "@/components/link-check/checker-tool";
import { MAX_LINKS } from "@/lib/link-check/run";
import { MAX_PAGES } from "@/lib/seo-audit/crawl";
import { site } from "@/lib/site";

const url = `${site.url}/tools/broken-link-checker`;

const title = "Free Broken Link Checker — Find Dead Links & 404s";
const description =
  "Enter your site address and it checks your pages for dead links, 404s and missing images, showing which page each sits on. Export to CSV, no sign-up.";

export const metadata: Metadata = {
  title,
  description,
  keywords: [
    "broken link checker",
    "free broken link checker",
    "dead link checker",
    "dead link finder",
    "404 checker",
    "404 error checker",
    "find broken links on website",
    "website link checker",
    "online link checker",
    "link validator",
    "broken image checker",
    "redirect checker",
    "internal link checker",
    "external link checker",
    "link rot",
    "w3c link checker alternative",
  ],
  alternates: { canonical: url },
  openGraph: { title, description, url, type: "website" },
};

const faqs: Array<{ q: string; a: string }> = [
  {
    q: "What is a broken link?",
    a: "A broken link is a link that no longer reaches a working page. Clicking it returns an error instead of content, usually a 404 because the page was deleted or its URL changed, or a server error, or nothing at all because the domain has expired. Links break on their own over time as other sites reorganise, which is why a page that was fine last year may not be now. Images and scripts break the same way.",
  },
  {
    q: "Do broken links hurt SEO?",
    a: "Broken internal links do hurt, because they waste crawl budget, break the flow of link value through your site and leave visitors at dead ends. Broken outbound links are a smaller issue on their own, but a page full of them signals neglect and looks like low-quality content to both readers and search engines. There is no specific penalty for a single dead link. The damage is cumulative and mostly shows up as worse user experience and weaker internal linking.",
  },
  {
    q: "What is a 404 error?",
    a: "A 404 is the HTTP status code a server returns when the page you asked for does not exist. It usually means the page was deleted, moved without a redirect, or the URL was typed or linked wrongly. A 404 is a normal and correct response for a URL that genuinely has no content. The problem is not the code itself but pages on your site still linking to it.",
  },
  {
    q: "How do I find broken links on my website?",
    a: "Crawl the site and check the status code of every link it contains. A link checker follows your internal links page by page, requests each destination and reports anything returning a 4xx or 5xx code or failing to resolve. Google Search Console will also show 404s it has encountered, though only for URLs it already knows about. Doing it yourself catches links that were never crawled and gives you the source page and anchor text for each one.",
  },
  {
    q: "How do I fix broken links?",
    a: "Redirect or replace them. If the page moved, add a 301 redirect from the old URL to the new one so links and rankings carry over. If it is gone for good, point the link at the closest relevant page, or remove it if nothing fits. For broken links to other people's sites, find the current URL, swap in a different source, or delete the link.",
  },
  {
    q: "What is link rot?",
    a: "Link rot is the gradual decay of links across the web as pages are deleted, moved or their domains lapse. Studies of long-lived web content have found a substantial share of links stop working within a decade, with news and academic citations hit particularly hard. Nothing you do to your own site prevents it, since the failures happen at the other end. The only answer is checking outbound links periodically.",
  },
  {
    q: "What is the difference between a 404 and a 410?",
    a: "A 404 means the page is not found and might come back, while a 410 means it was deliberately removed and is not coming back. Search engines treat 410 as a stronger signal and typically drop the URL from the index faster. Use 410 when you have permanently retired content with no replacement, and a 301 redirect when there is a suitable page to send people to.",
  },
  {
    q: "How often should you check for broken links?",
    a: "Monthly is enough for most sites, and quarterly is fine for a small site that rarely changes. Check after any migration, redesign or bulk content change, because those are when internal links break in numbers. Large sites and anything with lots of outbound references benefit from a scheduled crawl, since external links break without warning.",
  },
];

const highlights = [
  {
    icon: FileWarning,
    title: "404s, dead domains and server errors",
    body: "Every link is actually visited, not guessed at. Pages that have been deleted, sites whose servers are failing, and domains that no longer exist at all — a link to any of them looks perfectly healthy until someone clicks it.",
  },
  {
    icon: Globe2,
    title: "Tells you which ones are yours",
    body: "Broken links to your own pages are the urgent ones. Links to other people's sites that have since died are worth fixing in a batch. The report keeps them apart so you know where to start.",
  },
  {
    icon: Search,
    title: "Shows where each one lives",
    body: "Every broken link comes with the pages it appears on and the anchor text used, so you can find it in your CMS without searching the whole site.",
  },
  {
    icon: ImageOff,
    title: "Broken images too",
    body: "Images that no longer load are checked too, and reported with the page they are on. It is the failure readers notice fastest and site owners spot last.",
  },
  {
    icon: Route,
    title: "Does not cry wolf about redirects",
    body: "A link that quietly sends people somewhere else still works, so it is listed on its own rather than counted as broken. A redirect that ends in a dead page is called broken, because it is.",
  },
  {
    icon: Download,
    title: "CSV export, no sign-up",
    body: "One row per source page, so the file is a work list. Opens in Excel, Sheets or Numbers and hands straight to whoever is doing the fixing.",
  },
];

const steps = [
  {
    name: "Enter your URL",
    text: "A domain, a single page or an XML sitemap. example.com is enough — the scanner finds robots.txt and the sitemap on its own.",
  },
  {
    name: "It crawls, then tests every link",
    text: `Up to ${MAX_PAGES} pages are read, every link and image on them is collected, and each destination is visited once to see whether it still works.`,
  },
  {
    name: "Fix from the list",
    text: "Broken links are grouped by destination with the pages they sit on. Download the CSV and work down it, or filter to internal-only and start there.",
  },
];

export default function BrokenLinkCheckerPage() {
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
          <nav aria-label="Breadcrumb" className="font-mono text-xs text-faint">
            <Link href="/tools" className="transition-colors hover:text-accent">
              Free tools
            </Link>
            <span className="px-1.5">/</span>
            <span>Broken link checker</span>
          </nav>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            Free broken link checker
          </h1>
          <p className="mt-4 text-base text-sub text-pretty sm:text-lg">
            Somewhere on your site a link leads nowhere, and visitors are hitting it
            before you do. Enter your address and this checks up to {MAX_PAGES} pages
            for dead links, 404s and missing images — then tells you which page each
            broken one sits on and what it was linked as, so you can go and fix it.
            No sign-up, nothing to install.
          </p>

          <div className="mt-8">
            <BrokenLinkChecker />
          </div>

          <ul className="mt-6 flex flex-wrap gap-x-5 gap-y-2 text-xs text-faint">
            {[
              "No account",
              "Internal + external",
              "Broken images",
              `${MAX_PAGES} pages per run`,
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
          What the dead link checker finds
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
            How to find broken links on your website
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
          What each result means
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-sub">
          Most free link checkers give you one pile called &ldquo;broken&rdquo; and
          leave you to work out which ones really need fixing. These are the five
          answers you get here.
        </p>
        <dl className="mt-6 space-y-3">
          {[
            {
              term: "Broken",
              tone: "text-bad",
              body: "The page is gone, the site is failing, or the domain no longer exists. The link genuinely does not work. Fix it or take it out.",
            },
            {
              term: "No answer",
              tone: "text-warn",
              body: "Nothing came back in time. Often a slow site rather than a dead one, so click a few yourself before you delete anything.",
            },
            {
              term: "Unverified",
              tone: "text-sub",
              body: "The other site turned the check away — usually bot protection rather than a dead page. These are deliberately left out of the broken count, so you are not sent chasing links that are fine.",
            },
            {
              term: "Redirect",
              tone: "text-accent",
              body: "The link works, but it sends people somewhere else first. Worth tidying up if it hops through several addresses, harmless otherwise. If it ends on a dead page it is reported as broken instead.",
            },
            {
              term: "Working",
              tone: "text-good",
              body: "Loaded first time. Nothing to do.",
            },
          ].map((row) => (
            <div key={row.term} className="rounded-xl border border-edge bg-panel p-4">
              <dt className={`text-sm font-medium ${row.tone}`}>{row.term}</dt>
              <dd className="mt-1 text-sm leading-relaxed text-sub">{row.body}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section className="border-y border-edge bg-panel/60">
        <div className="mx-auto w-full max-w-3xl px-6 py-16">
          <h2 className="font-display text-2xl tracking-tight text-ink sm:text-3xl">
            What it does not do
          </h2>
          <ul className="mt-6 space-y-3 text-sm leading-relaxed text-ink/90">
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">It reads the page as delivered.</strong>{" "}
              Links that only appear once the page has run its own code are invisible
              to the scan — the same way they are to a search engine on first look.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">
                Up to {MAX_PAGES} pages and {MAX_LINKS} links per run.
              </strong>{" "}
              A bigger site is scanned as far as that goes, and the report tells you
              what it did not reach.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">It does not check jump links.</strong>{" "}
              A link to <code className="font-mono text-xs">/page#section</code> is
              checked as far as the page. Whether that particular section still exists
              on it is not tested.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">No mailto or tel links.</strong> There
              is nothing to request, so there is nothing to verify.
            </li>
            <li className="rounded-xl border border-edge bg-panel p-4">
              <strong className="font-medium">No monitoring.</strong> Nothing is
              stored, so there is no scheduled re-scan and no alert. Download the
              CSV if you want to keep the report.
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
            Broken links are one symptom
          </h2>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            The same crawl that finds dead links can tell you about missing
            canonicals, duplicate titles, noindex tags left on by accident and
            whether AI crawlers can read your site. That is the{" "}
            <Link
              href="/tools/seo-audit"
              className="font-medium text-accent hover:text-accent-hi"
            >
              free SEO audit tool
            </Link>{" "}
            — same engine, sixty-three checks.
          </p>
          <p className="mt-4 text-sm leading-relaxed text-sub">
            Both are pieces of{" "}
            <Link href="/" className="font-medium text-accent hover:text-accent-hi">
              Meelu
            </Link>
            , a desktop app where an AI marketing agent suggests what to do with your site and you decide.{" "}
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
              name: "Meelu Free Broken Link Checker",
              url,
              applicationCategory: "BusinessApplication",
              operatingSystem: "Any",
              description,
              offers: { "@type": "Offer", price: "0", priceCurrency: "USD" },
              featureList: [
                `Crawls up to ${MAX_PAGES} pages from a domain, page or XML sitemap`,
                "Checks links to your own pages, links to other sites, and images",
                "Finds deleted pages, failing servers and domains that no longer exist",
                "Keeps links that merely blocked the check out of the broken count",
                "Lists redirects separately instead of calling them broken",
                "Shows the page each broken link sits on and the words it was linked as",
                "CSV export of broken links, all links and per-page counts",
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
              name: "How to find broken links on a website",
              description: `Crawl up to ${MAX_PAGES} pages, test every link and image, and export the dead ones to CSV.`,
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
                {
                  "@type": "ListItem",
                  position: 2,
                  name: "Broken link checker",
                  item: url,
                },
              ],
            },
          ]),
        }}
      />
    </div>
  );
}
