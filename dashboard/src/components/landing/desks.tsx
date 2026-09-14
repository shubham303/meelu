"use client";

import { useRef } from "react";
import {
  BarChart3,
  PenLine,
  RefreshCw,
  Send,
  Star,
  type LucideIcon,
} from "lucide-react";
import { gsap, useGSAP } from "@/components/animate";

const FLAGSHIP: {
  icon: LucideIcon;
  name: string;
  pitch: string;
  outputs: string[];
} = {
  icon: RefreshCw,
  name: "Growth Loop",
  pitch:
    "The flagship. Its own crawl shows what every page actually says, and Search Console shows where you truly rank. Then the plan ships — as pull requests you approve — and rankings verify the result.",
  outputs: [
    "A full crawl of your site, page by page",
    "True positions, impressions, and clicks (Search Console)",
    "On-page issues found, judged, and tracked to fixed",
    "Action plans that ship as PRs or CMS publishes — after your approval",
    "Verification when the ranking actually moves",
  ],
};

const DESKS: Array<{
  icon: LucideIcon;
  name: string;
  pitch: string;
  outputs: string[];
}> = [
  {
    icon: PenLine,
    name: "Content Studio",
    pitch:
      "Drafts articles, pages, and posts in your voice — then takes your revision notes until it's right.",
    outputs: [
      "Drafts → revisions → approval, with full version history",
      "Blog posts published via GitHub PR or your CMS",
      "Social and community drafts queued for review",
    ],
  },
  {
    icon: Send,
    name: "Outreach",
    pitch:
      "A partnerships and link-building CRM. Finds the sites and people worth your time, drafts every email in your voice.",
    outputs: [
      "Prospect lists with a reason for every fit",
      "Drafts you approve before anything sends",
      "An inbox with reply sentiment",
    ],
  },
  {
    icon: Star,
    name: "Reviews",
    pitch:
      "Watches your reputation across G2, Google, Trustpilot and more — clusters themes, flags spikes, drafts replies.",
    outputs: [
      "Reputation themes with method and sample size",
      "Alerts when a complaint suddenly doubles",
      "A reply queue you approve before posting",
    ],
  },
  {
    icon: BarChart3,
    name: "Data Analyst",
    pitch:
      "Your data, deterministic answers. Local algorithms do the math — the model never guesses arithmetic.",
    outputs: [
      "A searchable Q&A log, tagged by topic",
      "Reports with metrics, trends, and narrative",
    ],
  },
];

function DeskOutputs({ outputs }: { outputs: string[] }) {
  return (
    <ul className="mt-4 space-y-2">
      {outputs.map((o) => (
        <li key={o} className="flex items-start gap-2.5 text-sm text-ink">
          <span aria-hidden className="mt-[7px] h-1 w-1 shrink-0 rounded-full bg-accent" />
          {o}
        </li>
      ))}
    </ul>
  );
}

export function Desks() {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        ".desks-head",
        { opacity: 0, y: 20 },
        {
          opacity: 1,
          y: 0,
          duration: 0.55,
          ease: "power3.out",
          scrollTrigger: { trigger: ref.current, start: "top 78%", once: true },
        },
      );
      gsap.fromTo(
        ".desk-card",
        { opacity: 0, y: 24 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          ease: "power3.out",
          stagger: 0.09,
          scrollTrigger: { trigger: ref.current, start: "top 72%", once: true },
        },
      );
    },
    { scope: ref },
  );

  return (
    <section ref={ref} id="desks" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20 sm:py-24">
      <div className="desks-head max-w-xl">
        <h2 className="font-display text-3xl text-ink">Meet the desks</h2>
        <p className="mt-2 text-sm text-sub">
          Five agents, one workspace. Each files its finished work on its own
          desk — and nothing moves without your sign-off.
        </p>
      </div>

      <div className="mt-10 grid gap-4 md:grid-cols-2">
        <div className="desk-card relative overflow-hidden rounded-2xl border border-accent bg-panel p-6 md:col-span-2">
          <div
            aria-hidden
            className="absolute inset-0"
            style={{
              background:
                "radial-gradient(45% 90% at 100% 0%, var(--color-accent-soft), transparent 70%)",
            }}
          />
          <div className="relative">
            <div className="flex flex-wrap items-center gap-3">
              <div className="rounded-lg bg-accent-soft p-2">
                <FLAGSHIP.icon size={17} className="text-accent" />
              </div>
              <h3 className="font-display text-lg text-ink">{FLAGSHIP.name}</h3>
              <span className="rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent">
                Flagship
              </span>
            </div>
            <div className="mt-3 grid gap-x-10 gap-y-1 lg:grid-cols-[1fr_1.1fr]">
              <p className="text-sm text-sub">{FLAGSHIP.pitch}</p>
              <DeskOutputs outputs={FLAGSHIP.outputs} />
            </div>
          </div>
        </div>

        {DESKS.map((d) => (
          <div key={d.name} className="desk-card rounded-2xl border border-edge bg-panel p-6">
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-accent-soft p-2">
                <d.icon size={17} className="text-accent" />
              </div>
              <h3 className="font-display text-lg text-ink">{d.name}</h3>
            </div>
            <p className="mt-3 text-sm text-sub">{d.pitch}</p>
            <DeskOutputs outputs={d.outputs} />
          </div>
        ))}
      </div>
    </section>
  );
}
