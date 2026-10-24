import type { Metadata } from "next";
import Link from "next/link";
import { listCaseStudies, formatDate } from "@/lib/blog";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Case studies — SEO and AI search results with Meelu",
  description:
    "Real sites and real numbers: what we changed, what Search Console and GA4 showed, and what we would do again. A new case study every week.",
  alternates: { canonical: `${site.url}/case-studies` },
};

export default function CaseStudiesIndex() {
  const studies = listCaseStudies();

  return (
    <div className="mx-auto w-full max-w-3xl px-6 py-20">
      <p className="text-xs font-medium uppercase tracking-widest text-faint">Case studies</p>
      <h1 className="mt-3 font-display text-3xl tracking-tight text-ink sm:text-4xl">Real sites, real numbers.</h1>
      <p className="mt-4 text-sub text-pretty">
        What we changed, what the data showed and what we would do again. A new case study every week.
      </p>

      <div className="mt-12 flex flex-col gap-5">
        {studies.map((study) => (
          <article
            key={study.slug}
            className="rounded-2xl border border-edge bg-panel p-6 transition-colors hover:border-edge2"
          >
            <time className="font-mono text-xs text-faint">{formatDate(study.date)}</time>
            <h2 className="mt-2 text-lg font-medium leading-snug text-ink">
              <Link href={`/blog/${study.slug}`} className="transition-colors hover:text-accent">
                {study.title}
              </Link>
            </h2>
            <p className="mt-2 line-clamp-3 text-sm leading-relaxed text-sub">{study.description}</p>
          </article>
        ))}
        {studies.length === 0 && <p className="text-sub">The first case study is coming soon.</p>}
      </div>
    </div>
  );
}
