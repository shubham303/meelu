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
    body: "A lead is unique per project, so a second campaign can't cold-email someone the first one already found — checked on write, refused with the campaign that already owns it. One post per channel per hour. A suggestion is stored in your words and can't be rewritten. These hold whether or not the agent read the instructions.",
  },
  {
    title: "It remembers what the conversation would lose",
    body: "That you emailed that newsletter in March. That you hate the word “solution”. That your pricing page says £29 and not “affordable”. It's read back before anything gets written, which is why week two beats week one.",
  },
  {
    title: "It says where it put things",
    body: "Every saved record comes back naming the business it landed under. An agent filing work in the wrong place is invisible until you open the dashboard, so it gets said in the sentence it happens.",
  },
  {
    title: "It holds no credential that isn't yours",
    body: "The configs we publish carry obvious placeholders. You substitute your own, in your own file, on your own machine. Nothing here is a place worth breaking into.",
  },
];

const COSTS = [
  {
    title: "Nothing is awake",
    body: "The server runs inside your conversation and stops when it closes. Installing a publishing server does not mean a post goes out at 9am — the alternative is us running the agent and holding everyone's tokens, which is exactly the custody this design refuses.",
  },
  {
    title: "Determinism goes with the canvas",
    body: "An n8n graph runs the same way every time; an agent doesn't. “The workflow is generated per task” and “I can't tell you exactly what will happen” are one sentence read two ways. The answer is rules enforced by a server, and your yes on anything that leaves the building.",
  },
  {
    title: "Coverage isn't ours to decide",
    body: "LinkedIn publishes no MCP server, and the community ones risk your account. So we draft and schedule, and you paste it in — and the docs page says exactly that instead of shipping a command we don't trust.",
  },
  {
    title: "It assumes you have a host",
    body: "You need to already be in Claude, Cursor or Codex, and willing to edit a config once. A platform asks for a signup; this asks for an install. That's a narrower door, chosen deliberately.",
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
            Meelu is one MCP server that holds a business&apos;s marketing memory, and nothing
            else. It sends no email and publishes no post. That looks like a missing feature
            until you notice what changed about software.
          </p>
        </header>

        <blockquote className="mt-10 rounded-2xl border border-accent/30 bg-accent-soft/40 p-6 sm:p-8">
          <p className="font-display text-xl leading-snug text-ink sm:text-2xl">
            The expensive part of software used to be the wiring between components. It
            isn&apos;t any more.
          </p>
          <p className="mt-3 text-sm leading-relaxed text-sub">
            An agent writes the wiring at runtime. What it can&apos;t do is supply a component
            that works, or remember your business between conversations. So that is what we
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
            Email is your email provider&apos;s problem. Publishing is a CMS&apos;s problem. Repos are
            GitHub&apos;s problem. Each is somebody&apos;s entire company, each already ships an
            MCP server, and every one we reimplement would be a worse version of a thing that
            exists — plus a credential we&apos;d then have to guard.
          </p>

          <div className="mt-8 grid gap-4 md:grid-cols-2">
            <div className="rounded-2xl border border-accent/30 bg-accent-soft/40 p-6">
              <div className="w-fit rounded-lg bg-accent-soft p-2">
                <Brain size={16} className="text-accent" />
              </div>
              <h3 className="mt-4 font-display text-lg text-ink">Meelu is the memory</h3>
              <p className="mt-1.5 text-sm leading-relaxed text-sub">
                Your business, your positioning, the briefs, the leads, the drafts, the
                calendar, the corrections you&apos;ve already made once, and the record of what
                actually happened. It performs no outward action at all — and never will.
              </p>
            </div>
            <div className="rounded-2xl border border-edge bg-panel p-6">
              <div className="w-fit rounded-lg bg-panel2 p-2">
                <Hand size={16} className="text-sub" />
              </div>
              <h3 className="mt-4 font-display text-lg text-ink">
                The servers you install are the hands
              </h3>
              <p className="mt-1.5 text-sm leading-relaxed text-sub">
                Sending an outreach email means you connected your own email provider and your
                assistant used both in one conversation: draft here, get your yes on the exact
                text, send there, record the outcome here.
              </p>
            </div>
          </div>

          <div className="mt-4 rounded-2xl border border-edge bg-panel p-6">
            <div className="w-fit rounded-lg bg-panel2 p-2">
              <Boxes size={16} className="text-sub" />
            </div>
            <h3 className="mt-4 font-display text-lg text-ink">
              Every server you add multiplies, rather than adds
            </h3>
            <p className="mt-1.5 max-w-3xl text-sm leading-relaxed text-sub">
              Install three and your assistant can pull data out of one, transform it, and write
              it into another — a workflow nobody configured, for a case nobody anticipated.
              That composition is the entire return on this design, and it&apos;s the thing a
              platform structurally can&apos;t offer, because it only composes with itself.
              Capability becomes an install, not a roadmap item. And if the component you need
              doesn&apos;t exist yet, the right move is to build that one — as its own server,
              not as a feature buried in ours.
            </p>
          </div>
        </section>

        <section className="mt-20">
          <h2 className="font-display text-3xl text-ink">Why memory is the piece worth building</h2>
          <div className="mt-3 max-w-2xl space-y-3 text-sm leading-relaxed text-sub">
            <p>
              Of everything one could build, why this? Because it&apos;s the piece nobody else
              supplies. The agent brings the reasoning. The servers you install bring the reach.
              What&apos;s missing from every bare chat session is durable, corrected,
              business-specific context — and the enforcement of rules a model won&apos;t
              reliably remember on its own.
            </p>
            <p>
              A chat session forgets. Ask it again next week and it will confidently redo the
              work and re-email the lead. That&apos;s the gap this fills, and it sets the bar
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
            Then what stops it sending the wrong thing?
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
            Not the absence of a tool. That was the old answer, and it was really a missing
            feature dressed up as a safety property. The real ones:
          </p>
          <ul className="mt-6 space-y-4">
            <li className="border-l-2 border-accent/40 pl-4">
              <p className="font-display text-base text-ink">
                Approval is on the text, not the transport
              </p>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-sub">
                Nothing goes out without your yes on the exact subject and body. Being able to
                send is precisely what makes that approval load-bearing rather than ceremonial.
              </p>
            </li>
            <li className="border-l-2 border-accent/40 pl-4">
              <p className="font-display text-base text-ink">The record follows the act</p>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-sub">
                It sends, then marks it sent. Never the reverse. A draft recorded as sent that
                never left is the one failure that would make the memory untrustworthy — and the
                memory is the whole product.
              </p>
            </li>
            <li className="border-l-2 border-accent/40 pl-4">
              <p className="font-display text-base text-ink">A status is evidence, not a guess</p>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-sub">
                Sent means a send actually succeeded, or you said you sent it. Never that a draft
                looked ready to go.
              </p>
            </li>
            <li className="border-l-2 border-accent/40 pl-4">
              <p className="font-display text-base text-ink">
                Where the evidence is weak, you keep the pen
              </p>
              <p className="mt-1 max-w-2xl text-sm leading-relaxed text-sub">
                A mail provider returns a result worth trusting, so your assistant can mark an
                email sent. A social feed doesn&apos;t — it can hold a post for review, mangle
                the formatting, drop the image — so only you can mark a post published, even
                when the agent published it. Asymmetric on purpose.
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
            One server that works, then as many hands as you need
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-sm leading-relaxed text-sub">
            Connect Meelu to the assistant you already use. Connect your email when you want it to
            send, a CMS when you want it to publish. Each one is a five-minute setup, and a
            checked config we keep up to date.
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
          <p className="text-xs text-faint">Human-approved. Agent-applied.</p>
          <Link href="/" className="text-xs text-sub transition-colors hover:text-ink">
            Back home →
          </Link>
        </div>
      </footer>
    </div>
  );
}
