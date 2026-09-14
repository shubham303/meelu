"use client";

import { useRef } from "react";
import { Cable, ClipboardCheck, MessageSquare, type LucideIcon } from "lucide-react";
import { gsap, useGSAP } from "@/components/animate";

const STEPS: Array<{ n: string; icon: LucideIcon; title: string; body: string }> = [
  {
    n: "01",
    icon: Cable,
    title: "Connect your site",
    body: "Point it at your domain, link Search Console, and wire up GitHub or your CMS. That's the whole setup.",
  },
  {
    n: "02",
    icon: MessageSquare,
    title: "Talk to your coworker",
    body: "In Claude, via MCP. It pulls your site's full context before every task — pages, rankings, past decisions — so nothing starts from zero.",
  },
  {
    n: "03",
    icon: ClipboardCheck,
    title: "Approve, and it ships",
    body: "Proposed work lands on the dashboard. You approve; it opens the PR or publishes to your CMS. A human stays in the loop, always.",
  },
];

export function HowItWorks() {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        ".how-head",
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
        ".step-card",
        { opacity: 0, y: 24 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          ease: "power3.out",
          stagger: 0.1,
          scrollTrigger: { trigger: ref.current, start: "top 74%", once: true },
        },
      );
    },
    { scope: ref },
  );

  return (
    <section ref={ref} id="how" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20 sm:py-24">
      <div className="how-head max-w-xl">
        <h2 className="font-display text-3xl text-ink">How it works</h2>
        <p className="mt-2 text-sm text-sub">
          Three connections, one conversation, and a work queue you control.
          Your coworker meets you where you already think — and files results
          where you can act.
        </p>
      </div>

      <div className="mt-10 grid gap-4 md:grid-cols-3">
        {STEPS.map((s) => (
          <div key={s.n} className="step-card rounded-2xl border border-edge bg-panel p-5">
            <div className="flex items-center justify-between">
              <div className="rounded-lg bg-accent-soft p-2">
                <s.icon size={16} className="text-accent" />
              </div>
              <span className="font-display text-sm text-faint">{s.n}</span>
            </div>
            <h3 className="mt-4 font-display text-lg text-ink">{s.title}</h3>
            <p className="mt-1.5 text-sm text-sub">{s.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
