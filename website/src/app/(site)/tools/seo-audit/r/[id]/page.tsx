import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { AuditResults } from "@/components/seo-audit/results";
import { formatDate } from "@/lib/blog";
import { loadSharedAudit, shareUrlPath } from "@/lib/seo-audit/share";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: PageProps<"/tools/seo-audit/r/[id]">): Promise<Metadata> {
  const { id } = await params;
  const shared = await loadSharedAudit(id);
  if (!shared) return { robots: { index: false, follow: false } };
  const host = new URL(shared.result.origin).hostname;
  return {
    title: `SEO audit of ${host}`,
    description: `Health score ${shared.result.summary.score}, ${shared.result.findings.length} issues found across ${shared.result.summary.pagesCrawled} pages of ${host}.`,
    robots: { index: false, follow: false },
  };
}

export default async function SharedAudit({ params }: PageProps<"/tools/seo-audit/r/[id]">) {
  const { id } = await params;
  const shared = await loadSharedAudit(id);
  if (!shared) notFound();

  const host = new URL(shared.result.origin).hostname;

  return (
    <div className="mx-auto w-full max-w-5xl px-6 py-14 sm:py-16">
      <nav aria-label="Breadcrumb" className="font-mono text-xs text-faint">
        <Link href="/tools" className="transition-colors hover:text-accent">
          Free tools
        </Link>
        <span className="px-1.5">/</span>
        <Link href="/tools/seo-audit" className="transition-colors hover:text-accent">
          SEO audit
        </Link>
      </nav>
      <h1 className="mt-4 font-display text-3xl leading-[1.1] tracking-tight text-ink text-balance sm:text-4xl">
        SEO audit of {host}
      </h1>
      <p className="mt-3 text-sub">
        Run on {formatDate(shared.savedAt.slice(0, 10))} with the free Meelu SEO audit. It reads the
        site the way Google does and lists what to fix first.
      </p>

      <AuditResults result={shared.result} shareUrl={shareUrlPath(id)} />

      <section className="mt-12 flex flex-wrap items-center justify-between gap-6 rounded-3xl bg-ink px-6 py-10 text-panel sm:px-10">
        <div className="min-w-0 flex-[1_1_26rem]">
          <p className="font-display text-2xl leading-tight tracking-tight text-balance sm:text-3xl">
            Want this every week, with your Search Console data?
          </p>
          <p className="mt-3 max-w-2xl text-panel/75 text-pretty">
            Meelu crawls your site, reads your Search Console and checks what ChatGPT says about your
            market. Then it gives you a short list of what to fix, with the data behind each item.
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <Link
            href="/download"
            className="inline-flex items-center gap-1.5 rounded-lg bg-panel px-5 py-3 text-sm font-medium text-ink"
          >
            Try Meelu <ArrowRight size={14} />
          </Link>
          <Link
            href="/tools/seo-audit"
            className="inline-flex items-center gap-1.5 rounded-lg border border-panel/30 px-5 py-3 text-sm text-panel"
          >
            Audit another site
          </Link>
        </div>
      </section>
    </div>
  );
}
