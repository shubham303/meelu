import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ArrowRight } from "lucide-react";
import { HeroDownload } from "@/components/download-buttons";
import { getUseCase, useCases } from "@/lib/use-cases";
import { site } from "@/lib/site";

export function generateStaticParams() {
  return useCases.map((useCase) => ({ slug: useCase.slug }));
}

export async function generateMetadata({ params }: PageProps<"/use-cases/[slug]">): Promise<Metadata> {
  const { slug } = await params;
  const useCase = getUseCase(slug);
  if (!useCase) return {};
  const url = `${site.url}/use-cases/${useCase.slug}`;
  return {
    title: { absolute: useCase.metaTitle },
    description: useCase.metaDescription,
    alternates: { canonical: url },
    openGraph: { title: useCase.metaTitle, description: useCase.metaDescription, url },
  };
}

export default async function UseCasePage({ params }: PageProps<"/use-cases/[slug]">) {
  const { slug } = await params;
  const useCase = getUseCase(slug);
  if (!useCase) notFound();
  const others = useCases.filter((other) => other.slug !== useCase.slug);

  return (
    <div>
      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6 sm:py-20">
          <Link href="/use-cases" className="font-mono text-xs text-faint transition-colors hover:text-accent">
            ← All use cases
          </Link>
          <p className="mt-6 font-mono text-[11px] uppercase tracking-widest text-faint">{useCase.name}</p>
          <h1 className="mt-3 max-w-3xl font-display text-4xl leading-[1.08] tracking-tight text-ink text-balance sm:text-5xl">
            {useCase.title}
          </h1>
          <p className="mt-6 max-w-2xl text-base text-sub text-pretty sm:text-lg">{useCase.description}</p>
          <div className="mt-9">
            <HeroDownload align="start">
              <Link
                href="/demo"
                className="inline-flex h-12 items-center gap-1.5 rounded-lg border border-edge2 bg-panel px-5 text-sm text-ink transition-colors hover:bg-panel2"
              >
                Try the live demo <ArrowRight size={14} />
              </Link>
            </HeroDownload>
          </div>
        </div>
      </section>

      <section className="border-b border-edge bg-panel2/60">
        <div className="mx-auto w-full max-w-6xl px-4 py-14 sm:px-6">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">The problem</p>
          <p className="mt-3 max-w-3xl font-display text-2xl leading-snug text-ink text-pretty sm:text-3xl">
            {useCase.problem}
          </p>
        </div>
      </section>

      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
          <h2 className="font-display text-3xl tracking-tight text-ink sm:text-4xl">How it works</h2>
          <ol className="mt-10 grid gap-6 md:grid-cols-3">
            {useCase.steps.map((step, index) => (
              <li key={step.title} className="rounded-2xl border border-edge bg-panel p-6">
                <span className="font-mono text-xs text-accent">0{index + 1}</span>
                <p className="mt-3 font-medium text-ink">{step.title}</p>
                <p className="mt-2 text-sm text-sub text-pretty">{step.body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="border-b border-edge bg-panel/60">
        <div className="mx-auto grid w-full max-w-6xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-2">
          <div>
            <h2 className="font-display text-3xl tracking-tight text-ink sm:text-4xl">What you get</h2>
            <ul className="mt-8 flex flex-col gap-4">
              {useCase.outcomes.map((outcome) => (
                <li key={outcome} className="flex gap-3 text-ink">
                  <span aria-hidden className="mt-2 size-1.5 shrink-0 rounded-full bg-accent" />
                  <span className="text-pretty">{outcome}</span>
                </li>
              ))}
            </ul>
            <p className="mt-8 text-sm text-sub">
              Meelu suggests, and you decide. It never changes your site on its own.{" "}
              <Link href={useCase.docsHref} className="text-ink underline underline-offset-4 hover:text-accent">
                Read the docs
              </Link>
            </p>
          </div>
          <div>
            <h2 className="font-display text-3xl tracking-tight text-ink sm:text-4xl">
              {useCase.promptsTitle ?? "Things to ask"}
            </h2>
            <div className="mt-8 flex flex-col gap-3">
              {useCase.prompts.map((prompt) => (
                <p key={prompt} className="rounded-xl border border-edge bg-bg px-4 py-3 text-[15px] text-ink">
                  “{prompt}”
                </p>
              ))}
            </div>
          </div>
        </div>
      </section>

      {useCase.table && (
        <section className="border-b border-edge">
          <div className="mx-auto w-full max-w-6xl px-4 py-20 sm:px-6">
            <h2 className="font-display text-3xl tracking-tight text-ink sm:text-4xl">{useCase.table.title}</h2>
            <div className="mt-10 overflow-x-auto rounded-2xl border border-edge bg-panel">
              <table className="w-full min-w-[640px] border-collapse text-left text-[15px]">
                <thead>
                  <tr className="border-b border-edge">
                    <th scope="col" className="px-5 py-4 font-medium text-sub">
                      Task
                    </th>
                    <th scope="col" className="px-5 py-4 font-medium text-ink">
                      By hand
                    </th>
                    <th scope="col" className="px-5 py-4 font-medium text-accent">
                      With Meelu
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {useCase.table.rows.map((row) => (
                    <tr key={row.task} className="border-b border-edge last:border-0">
                      <th scope="row" className="px-5 py-4 font-medium text-ink">
                        {row.task}
                      </th>
                      <td className="px-5 py-4 text-sub">{row.byHand}</td>
                      <td className="px-5 py-4 text-ink">{row.withMeelu}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      )}

      {useCase.freeTools && (
        <section className="border-b border-edge bg-panel2/60">
          <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
            <h2 className="font-display text-3xl tracking-tight text-ink sm:text-4xl">Try it free, no download</h2>
            <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {useCase.freeTools.map((tool) => (
                <Link
                  key={tool.href}
                  href={tool.href}
                  className="group flex flex-col rounded-2xl border border-edge bg-panel p-5 transition-colors hover:border-edge2"
                >
                  <p className="font-medium text-ink">{tool.name}</p>
                  <p className="mt-1.5 text-sm text-sub text-pretty">{tool.body}</p>
                  <span className="mt-auto inline-flex items-center gap-1.5 pt-4 text-sm text-sub transition-colors group-hover:text-accent">
                    Open the free tool <ArrowRight size={14} />
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>
      )}

      <section className="border-b border-edge">
        <div className="mx-auto w-full max-w-6xl px-4 py-16 sm:px-6">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">More use cases</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {others.map((other) => (
              <Link
                key={other.slug}
                href={`/use-cases/${other.slug}`}
                className="rounded-full border border-edge bg-panel px-3.5 py-1.5 text-sm text-sub transition-colors hover:border-edge2 hover:text-ink"
              >
                {other.name}
              </Link>
            ))}
          </div>
        </div>
      </section>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "WebPage",
            name: useCase.metaTitle,
            description: useCase.metaDescription,
            url: `${site.url}/use-cases/${useCase.slug}`,
            isPartOf: { "@type": "WebSite", name: site.name, url: site.url },
          }),
        }}
      />
    </div>
  );
}
