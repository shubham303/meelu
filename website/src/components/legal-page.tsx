import { site } from "@/lib/site";

export const legalLinkClass =
  "text-ink underline decoration-edge underline-offset-4 transition-colors hover:decoration-accent";

export function formatEffective(date: string) {
  return new Date(`${date}T00:00:00Z`).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
    timeZone: "UTC",
  });
}

export function legalJsonLd({
  title,
  path,
  description,
  effective,
}: {
  title: string;
  path: string;
  description: string;
  effective: string;
}) {
  return {
    "@context": "https://schema.org",
    "@type": "WebPage",
    name: `${title} — ${site.name}`,
    url: `${site.url}${path}`,
    description,
    dateModified: effective,
    isPartOf: { "@type": "WebSite", name: site.name, url: site.url },
  };
}

export function LegalEmail() {
  return (
    <a href={`mailto:${site.legalEmail}`} className={legalLinkClass}>
      {site.legalEmail}
    </a>
  );
}

export function LegalSection({
  id,
  heading,
  children,
}: {
  id: string;
  heading: string;
  children: React.ReactNode;
}) {
  return (
    <section id={id} className="scroll-mt-20 border-t border-edge pt-10">
      <h2 className="font-display text-2xl tracking-tight text-ink">{heading}</h2>
      <div className="mt-4 flex flex-col gap-4 text-base text-sub text-pretty">{children}</div>
    </section>
  );
}

export function LegalList({ children }: { children: React.ReactNode }) {
  return <ul className="flex list-disc flex-col gap-2 pl-5">{children}</ul>;
}

export function LegalPage({
  title,
  intro,
  effective,
  sections,
  jsonLd,
  children,
}: {
  title: string;
  intro: React.ReactNode;
  effective: string;
  sections: readonly { id: string; label: string }[];
  jsonLd: object;
  children: React.ReactNode;
}) {
  return (
    <div>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
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
        <div className="relative mx-auto w-full max-w-4xl px-6 py-16 sm:py-20">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">Legal</p>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            {title}
          </h1>
          <p className="mt-5 max-w-2xl text-base text-sub text-pretty sm:text-lg">{intro}</p>
          <p className="mt-5 font-mono text-[11px] uppercase tracking-widest text-faint">
            Last updated {formatEffective(effective)}
          </p>
        </div>
      </section>

      <section className="mx-auto w-full max-w-4xl px-6 py-16">
        <nav aria-label="On this page" className="rounded-2xl border border-edge bg-panel p-6">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">On this page</p>
          <ul className="mt-4 grid gap-x-8 gap-y-2 text-sm text-sub sm:grid-cols-2">
            {sections.map((section) => (
              <li key={section.id}>
                <a href={`#${section.id}`} className="transition-colors hover:text-ink">
                  {section.label}
                </a>
              </li>
            ))}
          </ul>
        </nav>

        <div className="mt-14 flex flex-col gap-10">{children}</div>
      </section>
    </div>
  );
}
