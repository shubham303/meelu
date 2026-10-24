import type { Metadata } from "next";
import Link from "next/link";
import { listComparisons } from "@/lib/alternatives";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Meelu alternatives and comparisons for small SaaS teams",
  description:
    "How Meelu compares with Semrush, Ahrefs, Screaming Frog, Surfer, Peec AI and other SEO, GEO and social listening tools. Prices, features and who each one suits.",
  alternates: { canonical: `${site.url}/alternatives` },
};

export default function AlternativesIndex() {
  const comparisons = listComparisons();
  const categories = [...new Set(comparisons.map((comparison) => comparison.category))];

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-20">
      <p className="text-xs font-medium uppercase tracking-widest text-faint">Comparisons</p>
      <h1 className="mt-3 font-display text-3xl tracking-tight text-ink sm:text-4xl">Meelu compared with the tools you know.</h1>
      <p className="mt-4 text-sub text-pretty">
        Most marketing tools do one job: an SEO suite, a crawler, a content editor, an AI visibility tracker or a Reddit
        monitor. Meelu does SEO, GEO, content writing, social listening, finding leads and data analytics for one
        website, and it suggests while you decide. These pages say where each tool is the better pick, and where Meelu
        is.
      </p>

      {categories.map((category) => (
        <section key={category} className="mt-12">
          <h2 className="text-xs font-medium uppercase tracking-widest text-faint">{category}</h2>
          <div className="mt-4 flex flex-col gap-4">
            {comparisons
              .filter((comparison) => comparison.category === category)
              .map((comparison) => (
                <article
                  key={comparison.slug}
                  className="rounded-2xl border border-edge bg-panel p-5 transition-colors hover:border-edge2"
                >
                  <h3 className="text-base font-medium leading-snug text-ink">
                    <Link href={`/alternatives/${comparison.slug}`} className="transition-colors hover:text-accent">
                      Meelu vs {comparison.competitor}
                    </Link>
                  </h3>
                  <p className="mt-1 text-sm leading-relaxed text-sub">{comparison.summary}</p>
                </article>
              ))}
          </div>
        </section>
      ))}
    </div>
  );
}
