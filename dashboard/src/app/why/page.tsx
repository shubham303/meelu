import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Boxes, Brain, Hand, Workflow } from "lucide-react";
import { Logo } from "@/components/logo";

export const metadata: Metadata = {
  title: "Why Meelu is built this way",
  description:
    "Every era of software before agents had a human authoring the workflow in advance. An agent writes it at runtime — so the scarce thing is no longer the wiring, it's a component that does one job correctly.",
};

const ERAS = [
  {
    n: "01",
    era: "The CRUD app",
    got: "One tool that did one job. A form, a table, a couple of views — you understood it in an afternoon, and its limits were obvious from the outside.",
    limit: "The limit was reach. Your invoices didn't know about your customers.",
    decides: "The developer, at build time",
    now: false,
  },
  {
    n: "02",
    era: "The platform",
    got: "One tool that tried to do everything. CRM plus email plus scheduling plus invoicing, until the pitch was “run your whole business here”.",
    limit:
      "The module you added to check a box is somebody else's entire company — so it is the worst email tool in your product, and the worst calendar.",
    decides: "The developer, at build time",
    now: false,
  },
  {
    n: "03",
    era: "The integration era",
    got: "Everything grew an API, so you connected instead of rebuilding. Two flavours: the SaaS that adds a connector per integration, and the automation canvas — Zapier, n8n — that handed workflow authorship to you.",
    limit:
      "Both share the thing the next era breaks: a human still draws every branch, in advance, before they need it.",
    decides: "Still a human, at build time",
    now: false,
  },
  {
    n: "04",
    era: "The agent era",
    got: "You hand over a goal and a set of components. The agent works out which to call, in what order, and what to do when one of them says something surprising.",
    limit: "Not a better canvas. The deletion of the canvas.",
    decides: "The agent, at runtime, from the goal",
    now: true,
  },
];

const BAR = [
  {
    title: "It does one job, correctly",
    body: "The reason not to reinvent email is the same reason to be excellent at this. A component that does one thing is reusable, replaceable and separately verifiable. The same thing buried in a platform is none of those.",
  },
  {
    title: "It enforces its rule in the server, not the prompt",
    body: "The agent reads your data through SQL that is scoped to your account and read-only on the core tables. It changes anything only through a desk's own write tools, and a task gets only the writes it was scoped for. A conversation Social Listening already suggested is not suggested again. These hold whether or not the agent read the instructions.",
  },
  {
    title: "It remembers what the conversation would lose",
    body: "That you rejected that pillar page last week. That you hate the word “solution”. That your pricing page says £29 and not “affordable”. Notes and past decisions are read back before anything gets written, which is why week two beats week one.",
  },
  {
    title: "It says where it put things",
    body: "Every saved record comes back naming the site it landed under. An agent filing work in the wrong place is invisible until you open the dashboard, so it gets said in the sentence it happens.",
  },
  {
    title: "It keeps your own credentials on your machine",
    body: "Your Search Console and Analytics connections live in the desktop app, on your machine. Shared data vendors run on one account on our server, and each call is charged to your credit balance, so you never hand us a vendor key.",
  },
];

const COSTS = [
  {
    title: "Nothing is awake",
    body: "Crawls, Search Console and Analytics fetches and schedules run in the desktop app, so they run only while the app is running. The alternative is us running them on our servers and holding everyone's Google tokens, which is exactly the custody this design refuses.",
  },
  {
    title: "Determinism goes with the canvas",
    body: "An n8n graph runs the same way every time; an agent doesn't. “The workflow is generated per task” and “I can't tell you exactly what will happen” are one sentence read two ways. The answer is rules enforced by a server, and your yes on anything that would change your site.",
  },
  {
    title: "The last step is yours",
    body: "Meelu does not publish. The Content desk writes and checks a page — title, H1, meta description, slug, target keyword and body — and you put it on your site by hand. A tool wired to your CMS would skip that step; we keep it on purpose.",
  },
  {
    title: "It needs the desktop app",
    body: "The web dashboard shows the same screens, but crawling and the agent run in the desktop app. A web tool asks for a signup; this also asks for an install. That's a narrower door, chosen deliberately.",
  },
];

export default function WhyPage() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="sticky top-0 z-40 border-b border-edge bg-bg/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Link href="/" aria-label="Meelu home">
              <Logo />
            </Link>
            <span className="text-sm text-sub">Why</span>
          </div>
          <div className="flex items-center gap-2">
            <Link
              href="/docs"
              className="rounded-lg px-3.5 py-2 text-sm font-medium text-sub transition-colors hover:bg-panel2 hover:text-ink"
            >
              Docs
            </Link>
            <Link
              href="/signup"
              className="rounded-lg bg-accent px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
            >
              Get started
            </Link>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-14 sm:py-20">
        <header className="max-w-2xl">
          <p className="text-[11px] uppercase tracking-wide text-accent">The argument</p>
          <h1 className="mt-2 font-display text-4xl leading-tight text-ink sm:text-5xl">
            Why Meelu is built this way
          </h1>
          <p className="mt-5 text-base leading-relaxed text-sub">
            Meelu reads your website and your search data, and tells you what it found and why
            it matters. It crawls and audits your pages, suggests internal links, tracks your
            keywords and drafts pages for your site. It never publishes and never changes your
            site on its own. That looks like a missing feature until you notice what changed
            about software.
          </p>
        </header>

        <blockquote className="mt-10 rounded-2xl border border-accent/30 bg-accent-soft/40 p-6 sm:p-8">
          <p className="font-display text-xl leading-snug text-ink sm:text-2xl">
            The expensive part of software used to be the wiring between components. It
            isn&apos;t any more.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-sub">
            An agent writes the wiring at runtime. What it can&apos;t do is supply a component
            that works, or remember your site between conversations. So that is what we
            build — and deliberately nothing else.
          </p>
        </blockquote>

        <section className="mt-20">
          <h2 className="font-display text-3xl text-ink">Four eras, and who decides the steps</h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
            Read only the right-hand column and you have the whole argument.
          </p>

          <ol className="mt-8 space-y-3">
            {ERAS.map((e) => (
              <li
                key={e.n}
                className={`rounded-2xl border p-5 sm:p-6 ${
                  e.now ? "border-accent/40 bg-accent-soft/30" : "border-edge bg-panel"
                }`}
              >
                <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                  <div className="max-w-xl">
                    <div className="flex items-baseline gap-3">
                      <span className="font-display text-sm text-faint">{e.n}</span>
                      <h3 className="font-display text-xl text-ink">{e.era}</h3>
                    </div>
                    <p className="mt-2 text-sm leading-relaxed text-sub">{e.got}</p>
                    <p
                      className={`mt-2 text-sm leading-relaxed ${
                        e.now ? "text-ink" : "text-faint"
                      }`}
                    >
                      {e.limit}
                    </p>
                  </div>

                  <div className="shrink-0 sm:w-52 sm:text-right">
                    <p className="text-[11px] uppercase tracking-wide text-faint">
                      Who decides the workflow
                    </p>
                    <p
                      className={`mt-1 text-sm font-medium ${
                        e.now ? "text-accent" : "text-sub"
                      }`}
                    >
                      {e.decides}
                    </p>
                  </div>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="mt-16 rounded-2xl border border-edge bg-panel2 p-6 sm:p-8">
          <div className="flex items-start gap-4">
            <div className="hidden rounded-lg bg-accent-soft p-2 sm:block">
              <Workflow size={18} className="text-accent" />
            </div>
            <div className="max-w-2xl">
              <h2 className="font-display text-2xl text-ink">
                An automation is a decision made once and executed forever
              </h2>
              <p className="mt-3 text-sm leading-relaxed text-sub">
                Whether or not it still fits. That&apos;s the cost every era before this one
                paid: you had to know the steps before you needed them, every new case was a
                branch somebody had to draw, and a step that returned something slightly
                unexpected had nowhere to go.
              </p>
              <p className="mt-3 text-sm leading-relaxed text-sub">
                An agent decides the conditionals, the loops and the path from the goal it was
                given. Follow that through and the economics invert. The workflow was the
                product for an entire generation of tools; now it&apos;s generated per task, for
                free, and it adapts to a case nobody anticipated.
              </p>
              <p className="mt-4 font-display text-xl leading-snug text-ink">
                So the scarce thing is no longer the wiring. It&apos;s a component that does one
                job correctly.
              </p>
            </div>
          </div>
        </section>

        <section className="mt-20">
          <h2 className="font-display text-3xl text-ink">
            So we build one component, properly
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
            Publishing is your CMS&apos;s problem. Email is your email provider&apos;s problem.
            Posting is the social network&apos;s problem. Each is somebody&apos;s entire company,
            and every one we reimplement would be a worse version of a thing that exists — plus
            a credential we&apos;d then have to guard.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-accent/30 bg-accent-soft/40 p-6">
              <div className="w-fit rounded-lg bg-accent-soft p-2">
                <Brain size={16} className="text-accent" />
              </div>
              <h3 className="mt-4 font-display text-lg text-ink">Meelu is the memory</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-sub">
                Your pages and how they link, your keyword, rank and volume history, the page
                drafts, your notes, and the suggestions you already approved or rejected. It
                reads and suggests. It does not change your site.
              </p>
            </div>
            <div className="rounded-2xl border border-edge bg-panel p-6">
              <div className="w-fit rounded-lg bg-panel2 p-2">
                <Hand size={16} className="text-sub" />
              </div>
              <h3 className="mt-4 font-display text-lg text-ink">
                You are the hands
              </h3>
              <p className="mt-1.5 text-sm leading-relaxed text-sub">
                When a suggestion is right, you make the change: edit the page, add the link,
                put the draft on your site. Meelu brings the evidence. The decision and the
                edit are yours.
              </p>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-edge bg-panel p-6">
            <div className="w-fit rounded-lg bg-panel2 p-2">
              <Boxes size={16} className="text-sub" />
            </div>
            <h3 className="mt-4 font-display text-lg text-ink">
              Every desk you add multiplies, rather than adds
            </h3>
            <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-sub">
              The agent in the desktop app works across desks. It can export your pages from
              the Site desk and question them in the Analytics desk in one conversation, and it
              can use other MCP servers you install in the app — a workflow nobody configured,
              for a case nobody anticipated.
              That composition is the entire return on this design, and it&apos;s the thing a
              platform structurally can&apos;t offer, because it only composes with itself.
              Capability becomes an install, not a roadmap item. And if the component you need
              doesn&apos;t exist yet, the right move is to build that one on its own, not as a
              feature buried in another desk.
            </p>
          </div>
        </section>

        <section className="mt-20">
          <h2 className="font-display text-3xl text-ink">Why memory is the piece worth building</h2>
          <div className="mt-3 max-w-2xl space-y-3 text-sm leading-relaxed text-sub">
            <p>
              Of everything one could build, why this? Because it&apos;s the piece nobody else
              supplies. The agent brings the reasoning. Search Console, Analytics and the data vendors bring the reach.
              What&apos;s missing from every bare chat session is durable, corrected,
              site-specific context — and the enforcement of rules a model won&apos;t
              reliably remember on its own.
            </p>
            <p>
              A chat session forgets. Ask it again next week and it will confidently redo the
              work and suggest the page you already rejected. That&apos;s the gap this fills, and it sets the bar
              for anything we add: there has to be one rule it enforces that a generic chat
              session cannot. If there isn&apos;t, it&apos;s a prompt, not a product.
            </p>
          </div>

          <div className="mt-8 divide-y divide-edge overflow-hidden rounded-2xl border border-edge bg-panel">
            {BAR.map((b) => (
              <div key={b.title} className="p-5 sm:p-6">
                <h3 className="font-display text-lg text-ink">{b.title}</h3>
                <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-sub">{b.body}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mt-20">
          <h2 className="font-display text-3xl text-ink">
            Then what stops it changing the wrong thing?
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
            Meelu suggests and you decide. In practice that means:
          </p>
          <ul className="mt-6 space-y-4">
            <li className="border-l-2 border-accent/40 pl-4">
              <p className="font-display text-base text-ink">
                Every step ends in a suggestion
              </p>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-sub">
                Each automated step ends in something you can approve, edit or reject. It never
                ends in a silent change to your site or your content.
              </p>
            </li>
            <li className="border-l-2 border-accent/40 pl-4">
              <p className="font-display text-base text-ink">A suggestion carries its evidence</p>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-sub">
                The data it came from, the pages involved and the reason come with it, so you
                can judge it quickly instead of taking it on trust.
              </p>
            </li>
            <li className="border-l-2 border-accent/40 pl-4">
              <p className="font-display text-base text-ink">It points, it doesn&apos;t rewrite</p>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-sub">
                When several pages split one search query, Meelu suggests a pillar page, names
                the query and says what each page adds. Whether to refocus, merge or leave them
                alone is your call.
              </p>
            </li>
            <li className="border-l-2 border-accent/40 pl-4">
              <p className="font-display text-base text-ink">
                Nothing leaves without you
              </p>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-sub">
                The Content desk writes a page and stops; you put it on your site. Social
                Listening finds conversations worth joining; it does not post. Meelu never
                claims something went live, because it never puts anything live.
              </p>
            </li>
          </ul>
        </section>

        <section className="mt-20">
          <h2 className="font-display text-3xl text-ink">What this costs</h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
            Every argument above has a bill, and an argument with no costs listed is marketing.
            All four of these are things a big platform does better.
          </p>
          <div className="mt-8 grid gap-4 sm:grid-cols-2">
            {COSTS.map((c) => (
              <div key={c.title} className="rounded-2xl border border-edge bg-panel2 p-5">
                <h3 className="font-display text-lg text-ink">{c.title}</h3>
                <p className="mt-1.5 text-sm leading-relaxed text-sub">{c.body}</p>
              </div>
            ))}
          </div>
          <p className="mt-6 max-w-2xl text-sm leading-relaxed text-sub">
            None of them are fatal. All of them are worth saying plainly, rather than pretending
            the trade is free.
          </p>
        </section>

        <section className="mt-20 rounded-2xl border border-edge bg-panel p-8 text-center">
          <h2 className="font-display text-2xl text-ink">
            Grounded suggestions, and you decide
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-sub">
            Install the desktop app, add your site, and connect Search Console and Analytics
            when you want search data. Meelu crawls, reads and suggests. You approve, edit or
            reject.
          </p>
          <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/signup"
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-4 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
            >
              Get started <ArrowRight size={15} />
            </Link>
            <Link
              href="/docs"
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge px-4 py-2.5 text-sm font-medium text-sub transition-colors hover:bg-panel2 hover:text-ink"
            >
              Read the install docs
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-edge">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-4 px-6 py-8">
          <Logo size={18} />
          <p className="text-xs text-faint">Meelu suggests. You decide.</p>
          <Link href="/" className="text-xs text-sub transition-colors hover:text-ink">
            Back home →
          </Link>
        </div>
      </footer>
    </div>
  );
}
