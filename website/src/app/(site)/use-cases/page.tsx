import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { useCases } from "@/lib/use-cases";
import { site } from "@/lib/site";

export const metadata: Metadata = {
  title: "Use cases: SEO, AI search, content, social listening and leads",
  description:
    "What Meelu does for your website: SEO, AI search, technical SEO, internal links, content writing, social listening, finding leads and data analysis.",
  alternates: { canonical: `${site.url}/use-cases` },
};

export default function UseCasesIndex() {
  return (
    <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
      <p className="font-mono text-[11px] uppercase tracking-widest text-faint">Use cases</p>
      <h1 className="mt-3 max-w-3xl font-display text-4xl tracking-tight text-ink text-balance sm:text-5xl">
        What Meelu does for your website.
      </h1>
      <p className="mt-5 max-w-2xl text-sub text-pretty">
        Each job below runs in the same app, on the same data about your site. Meelu suggests, and you decide.
      </p>
      <div className="mt-12 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {useCases.map((useCase) => (
          <Link
            key={useCase.slug}
            href={`/use-cases/${useCase.slug}`}
            className="group flex flex-col rounded-2xl border border-edge bg-panel p-6 transition-colors hover:border-edge2"
          >
            <p className="font-mono text-[11px] uppercase tracking-widest text-faint">{useCase.name}</p>
            <p className="mt-3 font-medium leading-snug text-ink text-pretty">{useCase.title}</p>
            <span className="mt-auto inline-flex items-center gap-1.5 pt-5 text-sm text-sub transition-colors group-hover:text-accent">
              See how <ArrowRight size={14} />
            </span>
          </Link>
        ))}
      </div>
    </div>
  );
}
