import type { Metadata } from "next";
import Link from "next/link";
import { site } from "@/lib/site";
import { softwareApplicationJson } from "@/lib/software-schema";

const title = "Meelu pricing: pay per website, plus what you use";
const description =
  "One plan, no subscription. 1 credit is 1 US dollar, a website costs 0.5 credits a day (0.25 after five), and data and AI services are charged per use.";

export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: `${site.url}/pricing` },
  openGraph: { title, description, url: `${site.url}/pricing`, type: "website" },
};

const services = [
  {
    name: "DataForSEO",
    what: "Keyword volumes, rankings, backlinks, search results pages, and the answers ChatGPT, Claude and Google's AI Overview give for GEO checks.",
  },
  {
    name: "Apify",
    what: "Searches across social platforms for social listening and Find Leads, LinkedIn people search and reading the recent posts of shortlisted leads. A run needs a balance of at least $5 to start.",
  },
  {
    name: "OpenRouter",
    what: "AI models that read and classify your pages, and judge whether they answer the questions you track on the GEO desk.",
  },
];

const byoKeySteps = [
  {
    title: "Create a key.",
    body: "Sign in to the Anthropic Console, open Settings, then API keys, and create a new key. Add a payment method or credits to your Anthropic account.",
  },
  {
    title: "Open Connections.",
    body: "In the Meelu app, go to Connections and find the Your Anthropic key card.",
  },
  {
    title: "Save it.",
    body: "Paste the key and choose Save key. Meelu checks it with Anthropic before saving.",
  },
  {
    title: "Pick a default model.",
    body: "Choose which Claude model your tasks use. From then on, tasks run on your key by default.",
  },
];

const faqs = [
  {
    q: "Is there a monthly plan or a free tier?",
    a: "No. There is one way to pay: credits. You never pick a plan, a tier or a seat count.",
  },
  {
    q: "Is there a free trial?",
    a: "Yes. The first website you add is free for the first day of your account. External data and AI services still need credits, or you can run the agent on your own LLM key, set up in Connections.",
  },
  {
    q: "When is the daily website fee taken?",
    a: "Once every 24 hours for each website you have added, starting when you add it. Remove a website and its fee stops.",
  },
  {
    q: "How do I know what a service call cost?",
    a: "Every charge shows in the credit history under Settings in the app, with what it was for and the amount.",
  },
  {
    q: "What happens when my credits run out?",
    a: "A website whose next day can't be paid is paused. Its data stays, and calls to external services stop. Add credits and it works again right away. A website that stays paused for 30 days is deleted, with all its data.",
  },
];

export default function PricingPage() {
  return (
    <div>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: softwareApplicationJson }} />
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
        <div className="relative mx-auto w-full max-w-4xl px-6 py-16 text-center sm:py-20">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Pricing
          </p>
          <h1 className="mt-4 font-display text-4xl leading-[1.1] tracking-tight text-ink text-balance sm:text-5xl">
            One plan. Pay for what you use.
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base text-sub text-pretty sm:text-lg">
            Meelu runs on credits. <span className="text-ink">1 credit is 1 US dollar.</span>{" "}
            You pay a small daily fee for each website, and external services
            are charged only when they are used. There is no other plan.
          </p>
        </div>
      </section>

      <section className="mx-auto w-full max-w-4xl px-6 py-16">
        <div className="grid gap-5 sm:grid-cols-2">
          <div className="rounded-2xl border border-edge bg-panel p-6">
            <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
              Per website
            </p>
            <p className="mt-4 font-display text-4xl tracking-tight text-ink">
              0.5 <span className="text-lg text-sub">credits / day</span>
            </p>
            <p className="mt-1 text-sm text-faint">
              About 15 credits a month for each of your first five websites, then 0.25 credits a
              day (about 7.5 a month) for every website after that
            </p>
            <p className="mt-4 text-sm text-sub text-pretty">
              Taken automatically every day for each website you add. It covers
              keeping the website in Meelu: its pages, crawls, history and the
              agent&apos;s work on it.
            </p>
          </div>
          <div className="rounded-2xl border border-edge bg-panel p-6">
            <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
              External services
            </p>
            <p className="mt-4 font-display text-4xl tracking-tight text-ink">
              Per use
            </p>
            <p className="mt-1 text-sm text-faint">At the price the service charges for the call</p>
            <p className="mt-4 text-sm text-sub text-pretty">
              Some work needs data or AI from outside services. Each call takes
              extra credits, only when it runs. No call, no charge.
            </p>
          </div>
        </div>

        <div className="mt-5 rounded-2xl border border-edge bg-panel p-6">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Services charged per use
          </p>
          <ul className="mt-4 divide-y divide-edge">
            {services.map((s) => (
              <li key={s.name} className="flex flex-col gap-1 py-3 sm:flex-row sm:gap-6">
                <span className="w-32 shrink-0 text-sm text-ink">{s.name}</span>
                <span className="text-sm text-sub">{s.what}</span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-sm text-faint text-pretty">
            More services may be added. Each one is charged the same way: per
            use, shown in your credit history.
          </p>
        </div>
      </section>

      <section className="border-t border-edge">
        <div className="mx-auto w-full max-w-4xl px-6 py-16">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Example
          </p>
          <h2 className="mt-3 font-display text-2xl tracking-tight text-ink">
            Seven websites for 30 days
          </h2>
          <div className="mt-6 rounded-2xl border border-edge bg-panel p-6 text-sm">
            <div className="flex justify-between gap-4 py-2 text-sub">
              <span>First 5 websites × 0.5 credits × 30 days</span>
              <span className="shrink-0 whitespace-nowrap font-mono text-ink">75 credits</span>
            </div>
            <div className="flex justify-between gap-4 py-2 text-sub">
              <span>2 more websites × 0.25 credits × 30 days</span>
              <span className="shrink-0 whitespace-nowrap font-mono text-ink">15 credits</span>
            </div>
            <div className="flex justify-between gap-4 py-2 text-sub">
              <span>External service calls that month</span>
              <span className="shrink-0 whitespace-nowrap font-mono text-ink">what you used</span>
            </div>
            <div className="mt-2 flex justify-between gap-4 border-t border-edge pt-4 text-ink">
              <span>Total</span>
              <span className="shrink-0 whitespace-nowrap font-mono">$90 + usage</span>
            </div>
          </div>
          <p className="mt-6 text-sm text-sub text-pretty">
            Your first website is <span className="text-ink">free for one day</span>.
            External services need credits, or you can run the agent on your own LLM key.
          </p>
        </div>
      </section>

      <section className="border-t border-edge">
        <div className="mx-auto w-full max-w-4xl px-6 py-16">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Your own key
          </p>
          <h2 className="mt-3 font-display text-2xl tracking-tight text-ink">
            Bring your own Anthropic key
          </h2>
          <p className="mt-4 text-sm text-sub text-pretty">
            The agent can run on your own Anthropic API key. Its model calls then go straight
            from your device to Anthropic and are billed to your Anthropic account, not to your
            Meelu credits.
          </p>
          <ol className="mt-6 space-y-4 rounded-2xl border border-edge bg-panel p-6 text-sm text-sub">
            {byoKeySteps.map((step, i) => (
              <li key={step.title} className="flex gap-4">
                <span className="shrink-0 font-mono text-ink">{i + 1}</span>
                <span className="text-pretty">
                  <span className="text-ink">{step.title}</span> {step.body}
                </span>
              </li>
            ))}
          </ol>
          <ul className="mt-6 space-y-2 text-sm text-sub text-pretty">
            <li>
              The key is encrypted on your device and never sent to Meelu.
            </li>
            <li>
              You can still pick a Meelu model for a single task in the chat. That task is
              charged to your credits.
            </li>
            <li>
              Search data, social search and page classification still use credits, because
              they run on Meelu&apos;s servers.
            </li>
            <li>
              On a Claude Max or Team plan? You can{" "}
              <a
                href="https://support.claude.com/en/articles/17154008-monthly-api-credits-for-max-and-team-plans"
                target="_blank"
                rel="noreferrer"
                className="text-ink underline underline-offset-4 hover:text-accent"
              >
                claim monthly API credits
              </a>{" "}
              for your key.
            </li>
          </ul>
        </div>
      </section>

      <section className="border-t border-edge">
        <div className="mx-auto w-full max-w-4xl px-6 py-16">
          <p className="font-mono text-[11px] uppercase tracking-widest text-faint">
            Questions
          </p>
          <dl className="mt-6 space-y-6">
            {faqs.map((f) => (
              <div key={f.q}>
                <dt className="text-base text-ink">{f.q}</dt>
                <dd className="mt-2 text-sm text-sub text-pretty">{f.a}</dd>
              </div>
            ))}
          </dl>
          <div className="mt-12 text-center">
            <Link
              href="/download"
              className="inline-block rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
            >
              Download the app
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
