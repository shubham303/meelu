import type { Metadata } from "next";
import { ArrowUpRight } from "lucide-react";
import { site } from "@/lib/site";

const title = "Contact — Talk to the person building Meelu";
const description =
  "Meelu is built and run by Shubham Randive, a machine learning engineer. Reach out by email or on X with questions, feedback, bugs or partnership ideas.";

const twitterHandle = site.twitter.replace(/^https?:\/\/(www\.)?(x|twitter)\.com\//, "");

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${site.url}/contact` },
  openGraph: { title, description, url: `${site.url}/contact`, type: "website" },
};

const jsonLd = {
  "@context": "https://schema.org",
  "@type": "ContactPage",
  name: title,
  url: `${site.url}/contact`,
  description,
  mainEntity: {
    "@type": "Organization",
    name: site.name,
    url: site.url,
    email: site.email,
    sameAs: [site.twitter, site.github],
    founder: {
      "@type": "Person",
      name: site.author.name,
      url: "https://shubhamrandive.com",
      sameAs: [site.author.url],
    },
  },
};

export default function ContactPage() {
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
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Contact
          </p>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            Write to the person who builds Meelu
          </h1>
          <p className="mt-5 max-w-2xl text-base text-sub text-pretty sm:text-lg">
            Meelu is a small project with one person behind it. There is no
            support queue and no ticket number. Whatever you send lands with the
            person who wrote the code, and that person answers.
          </p>
        </div>
      </section>

      <section className="mx-auto w-full max-w-4xl px-6 py-16">
        <div className="grid gap-5 sm:grid-cols-2">
          <a
            href={`mailto:${site.email}`}
            className="group rounded-2xl border border-edge bg-panel p-6 transition-colors hover:border-accent"
          >
            <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
              Email
            </p>
            <p className="mt-3 flex items-center gap-2 text-lg font-medium text-ink">
              {site.email}
              <ArrowUpRight className="size-4 text-faint transition-colors group-hover:text-accent" />
            </p>
            <p className="mt-2 text-sm text-sub">
              Best for bugs, feature requests, partnership ideas and anything
              longer than a sentence or two.
            </p>
          </a>
          <a
            href={site.twitter}
            target="_blank"
            rel="noreferrer"
            className="group rounded-2xl border border-edge bg-panel p-6 transition-colors hover:border-accent"
          >
            <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
              X / Twitter
            </p>
            <p className="mt-3 flex items-center gap-2 text-lg font-medium text-ink">
              @{twitterHandle}
              <ArrowUpRight className="size-4 text-faint transition-colors group-hover:text-accent" />
            </p>
            <p className="mt-2 text-sm text-sub">
              Best for quick questions, and for following what ships next.
            </p>
          </a>
        </div>

        <div className="mt-16 max-w-2xl">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Who you are writing to
          </p>
          <h2 className="mt-3 font-display text-2xl tracking-tight text-ink">
            Shubham Randive
          </h2>
          <div className="mt-4 flex flex-col gap-4 text-base text-sub text-pretty">
            <p>
              Shubham is a machine learning engineer who builds AI agents and
              ships software. Meelu is his answer to a problem he kept running
              into himself: marketing work that is repetitive enough to
              automate, but too consequential to hand to an agent without
              checking every step. Meelu suggests and asks for approval before
              anything changes, because that is the version he would be
              willing to run on his own projects.
            </p>
            <p>
              He builds Meelu the same way he approaches most problems. Train
              the model if the model needs training, stand up the product if the
              product needs standing up, and learn the marketing if the
              marketing needs learning. The free tools on this site and the open
              source analytics MCP server on GitHub are that work, released as it
              matures.
            </p>
            <p>
              If you have hit a bug, want a tool that is not here yet, or have a
              marketing workflow you think an agent should handle, that is
              exactly the kind of message he wants to read. You can also see
              more of his writing and past work at{" "}
              <a
                href="https://shubhamrandive.com"
                target="_blank"
                rel="noreferrer"
                className="text-ink underline decoration-edge underline-offset-4 transition-colors hover:decoration-accent"
              >
                shubhamrandive.com
              </a>
              .
            </p>
          </div>
        </div>
      </section>
    </div>
  );
}
