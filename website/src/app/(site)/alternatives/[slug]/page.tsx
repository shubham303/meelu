import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { getComparison, listComparisons } from "@/lib/alternatives";
import { formatDate } from "@/lib/blog";
import { HeroDownload } from "@/components/download-buttons";
import { site } from "@/lib/site";

export function generateStaticParams() {
  return listComparisons().map((comparison) => ({ slug: comparison.slug }));
}

export async function generateMetadata({ params }: PageProps<"/alternatives/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const comparison = await getComparison(slug);
  if (!comparison) return {};
  const url = `${site.url}/alternatives/${comparison.slug}`;
  return {
    title: { absolute: comparison.metaTitle },
    description: comparison.metaDescription,
    alternates: { canonical: url },
    openGraph: {
      title: comparison.metaTitle,
      description: comparison.metaDescription,
      type: "article",
      url,
    },
  };
}

export default async function ComparisonPage({ params }: PageProps<"/alternatives/[slug]">) {
  const { slug } = await params;
  const comparison = await getComparison(slug);
  if (!comparison) notFound();

  const others = listComparisons().filter((other) => other.slug !== slug);
  const url = `${site.url}/alternatives/${comparison.slug}`;

  return (
    <article className="mx-auto w-full max-w-3xl px-6 py-20">
      <Link href="/alternatives" className="font-mono text-xs text-faint transition-colors hover:text-accent">
        ← All comparisons
      </Link>
      <header className="mt-6">
        <p className="font-mono text-xs text-faint">Meelu vs {comparison.competitor}</p>
        <h1 className="mt-2 font-display text-3xl leading-[1.15] tracking-tight text-ink text-balance sm:text-4xl">
          {comparison.title}
        </h1>
        <p className="mt-4 text-lg text-sub text-pretty">{comparison.description}</p>
        <p className="mt-4 font-mono text-xs text-faint">
          Prices and features checked on {formatDate(comparison.checked)} on{" "}
          <a
            href={comparison.competitorUrl}
            target="_blank"
            rel="noopener"
            className="text-accent underline-offset-2 hover:underline"
          >
            {comparison.competitor}&apos;s website
          </a>
          .
        </p>
      </header>

      <div
        className="prose mt-10 max-w-none prose-headings:font-display prose-headings:tracking-tight prose-headings:text-ink prose-p:text-ink/90 prose-a:text-accent prose-strong:text-ink prose-li:text-ink/90 prose-th:text-ink prose-td:text-ink/90 prose-table:text-sm"
        dangerouslySetInnerHTML={{ __html: comparison.html }}
      />

      {comparison.faq.length > 0 && (
        <section className="mt-14">
          <h2 className="font-display text-2xl tracking-tight text-ink">Questions people ask</h2>
          <div className="mt-6 flex flex-col divide-y divide-edge border-y border-edge">
            {comparison.faq.map((item) => (
              <details key={item.question} className="group py-4">
                <summary className="cursor-pointer list-none font-medium text-ink">{item.question}</summary>
                <p className="mt-2 text-sm leading-relaxed text-sub">{item.answer}</p>
              </details>
            ))}
          </div>
        </section>
      )}

      <section className="mt-14 rounded-2xl border border-edge bg-panel p-8 text-center">
        <h2 className="font-display text-2xl tracking-tight text-ink">See what Meelu finds on your site.</h2>
        <p className="mx-auto mt-3 max-w-md text-sm text-sub">
          Free to download for Mac and Windows. Your first website is free for one day. Meelu is in beta.
        </p>
        <div className="mt-6">
          <HeroDownload />
        </div>
        <p className="mt-4 text-xs text-faint">
          Not ready to install?{" "}
          <Link href="/tools/seo-audit" className="text-accent hover:text-accent-hi">
            Run the free SEO audit
          </Link>{" "}
          or{" "}
          <Link href="/demo" className="text-accent hover:text-accent-hi">
            try the live demo
          </Link>
          .
        </p>
      </section>

      {others.length > 0 && (
        <section className="mt-14">
          <p className="text-xs font-medium uppercase tracking-widest text-faint">Other comparisons</p>
          <div className="mt-4 flex flex-wrap gap-2">
            {others.map((other) => (
              <Link
                key={other.slug}
                href={`/alternatives/${other.slug}`}
                className="rounded-full border border-edge bg-panel px-3 py-1 text-sm text-sub transition-colors hover:border-edge2 hover:text-ink"
              >
                Meelu vs {other.competitor}
              </Link>
            ))}
          </div>
        </section>
      )}

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@graph": [
              {
                "@type": "Article",
                headline: comparison.title,
                description: comparison.description,
                datePublished: comparison.date,
                dateModified: comparison.checked,
                url,
                mainEntityOfPage: url,
                author: { "@type": "Person", name: site.author.name, url: site.author.url },
                publisher: {
                  "@type": "Organization",
                  name: site.name,
                  url: site.url,
                  logo: { "@type": "ImageObject", url: `${site.url}/meelu-logo.png` },
                },
              },
              ...(comparison.faq.length > 0
                ? [
                    {
                      "@type": "FAQPage",
                      mainEntity: comparison.faq.map((item) => ({
                        "@type": "Question",
                        name: item.question,
                        acceptedAnswer: { "@type": "Answer", text: item.answer },
                      })),
                    },
                  ]
                : []),
            ],
          }),
        }}
      />
    </article>
  );
}
