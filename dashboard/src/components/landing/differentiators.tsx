"use client";

import { useRef } from "react";
import { Brain, GitPullRequest, Sigma, type LucideIcon } from "lucide-react";
import { gsap, useGSAP } from "@/components/animate";

const PILLARS: Array<{ n: string; icon: LucideIcon; title: string; body: string }> = [
  {
    n: "01",
    icon: Sigma,
    title: "Deterministic numbers",
    body: "Local algorithms compute every metric — a language model never guesses arithmetic. Every figure on the dashboard carries its method and sample size, so you can trust it or check it.",
  },
  {
    n: "02",
    icon: Brain,
    title: "The context brain",
    body: "Every task makes the coworker smarter about YOUR site — rankings, voice, decisions, even your downvotes become standing instructions. It's all served through one API, read before every new task. Week two beats week one.",
  },
  {
    n: "03",
    icon: GitPullRequest,
    title: "Ships, not suggests",
    body: "Approved work becomes real artifacts: pull requests and published pages, with the URL to prove it. Never un-reviewed changes — you approve on the dashboard, and for code the PR is a second human gate.",
  },
];

export function Differentiators() {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        ".diff-head",
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
        ".diff-card",
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
    <section ref={ref} className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20 sm:py-24">
      <div className="diff-head max-w-xl">
        <h2 className="font-display text-3xl text-ink">Not another chatbot</h2>
        <p className="mt-2 text-sm text-sub">
          A bare chatbot starts every session from zero and hands you homework.
          Your coworker keeps the numbers honest, remembers your site, and
          finishes the job.
        </p>
      </div>

      <div className="mt-10 grid gap-4 md:grid-cols-3">
        {PILLARS.map((p) => (
          <div key={p.n} className="diff-card rounded-2xl border border-edge bg-panel p-5">
            <div className="flex items-center justify-between">
              <div className="rounded-lg bg-accent-soft p-2">
                <p.icon size={16} className="text-accent" />
              </div>
              <span className="font-display text-sm text-faint">{p.n}</span>
            </div>
            <h3 className="mt-4 font-display text-lg text-ink">{p.title}</h3>
            <p className="mt-1.5 text-sm text-sub">{p.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
