"use client";

import { useRef } from "react";
import Link from "next/link";
import {
  ArrowRight,
  GitPullRequest,
  MessageSquareWarning,
  Search,
  Sparkles,
  TrendingUp,
  type LucideIcon,
} from "lucide-react";
import { gsap, useGSAP } from "@/components/animate";
import { Badge, type BadgeTone } from "@/components/ui";
import { cn } from "@/lib/utils";

const WORDS: Array<{ t: string; accent?: boolean }> = [
  { t: "Hire" },
  { t: "an" },
  { t: "AI", accent: true },
  { t: "coworker", accent: true },
  { t: "for" },
  { t: "your" },
  { t: "website." },
];

const TICKER: Array<{
  icon: LucideIcon;
  summary: string;
  time: string;
  agent: string;
  tone: BadgeTone;
  tilt: string;
}> = [
  {
    icon: Search,
    summary: "Crawled 214 pages, 6 issues raised",
    time: "just now",
    agent: "SEO",
    tone: "accent",
    tilt: "lg:-rotate-1 lg:-translate-x-2",
  },
  {
    icon: TrendingUp,
    summary: "GSC: /pricing jumped #22 → #9",
    time: "26m ago",
    agent: "Verified",
    tone: "good",
    tilt: "lg:rotate-1 lg:translate-x-3",
  },
  {
    icon: GitPullRequest,
    summary: "PR #42 opened: new /vs/wave page",
    time: "1h ago",
    agent: "Shipped",
    tone: "accent",
    tilt: "lg:-rotate-1 lg:-translate-x-1",
  },
  {
    icon: MessageSquareWarning,
    summary: "Review alert: onboarding complaints doubled",
    time: "2h ago",
    agent: "Reviews",
    tone: "warn",
    tilt: "lg:rotate-1 lg:translate-x-2",
  },
];

export function Hero() {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      const tl = gsap.timeline({ defaults: { ease: "power3.out" } });
      tl.fromTo(
        ".hero-eyebrow",
        { opacity: 0, y: 10 },
        { opacity: 1, y: 0, duration: 0.4 },
      )
        .fromTo(
          ".hero-word",
          { opacity: 0, y: 26 },
          { opacity: 1, y: 0, duration: 0.55, stagger: 0.05 },
          "-=0.15",
        )
        .fromTo(
          ".hero-sub",
          { opacity: 0, y: 14 },
          { opacity: 1, y: 0, duration: 0.5 },
          "-=0.3",
        )
        .fromTo(
          ".hero-cta",
          { opacity: 0, y: 12 },
          { opacity: 1, y: 0, duration: 0.45, stagger: 0.08 },
          "-=0.3",
        )
        .fromTo(
          ".ticker-card",
          { opacity: 0, y: 22, scale: 0.97 },
          { opacity: 1, y: 0, scale: 1, duration: 0.5, stagger: 0.12 },
          "-=0.35",
        );
    },
    { scope: ref },
  );

  return (
    <section ref={ref} className="relative overflow-hidden">
      <div aria-hidden className="grain absolute inset-0" />
      <div
        aria-hidden
        className="absolute inset-0"
        style={{
          background:
            "radial-gradient(55% 45% at 50% 0%, var(--color-accent-soft), transparent 72%)",
        }}
      />

      <div className="relative mx-auto grid max-w-6xl items-center gap-12 px-6 py-20 sm:py-28 lg:grid-cols-[1.1fr_0.9fr]">
        <div>
          <span className="hero-eyebrow inline-flex items-center gap-1.5 rounded-full border border-edge2 bg-panel px-3 py-1 text-xs text-sub opacity-0">
            <Sparkles size={12} className="text-accent" />
            Lives in Claude, works via MCP
          </span>

          <h1 className="mt-5 font-display text-4xl leading-[1.08] tracking-tight text-ink sm:text-5xl lg:text-6xl">
            {WORDS.map((w, i) => (
              <span
                key={i}
                className={cn(
                  "hero-word mr-[0.26em] inline-block opacity-0",
                  w.accent && "text-accent",
                )}
              >
                {w.t}
              </span>
            ))}
          </h1>

          <p className="hero-sub mt-5 max-w-lg text-base text-sub opacity-0">
            It reads your site, drafts the content, and ships the fix as a
            PR — you just review. Nothing touches your site without your
            approval.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-3">
            <Link
              href="/login"
              className="hero-cta inline-flex items-center gap-1.5 rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white opacity-0 transition-colors hover:bg-accent-hi"
            >
              Get started <ArrowRight size={15} />
            </Link>
            <Link
              href="/login"
              className="hero-cta inline-flex items-center rounded-lg border border-edge2 px-5 py-2.5 text-sm text-ink opacity-0 transition-colors hover:bg-panel2"
            >
              Sign in
            </Link>
          </div>
        </div>

        <div className="flex flex-col gap-3">
          <p className="ticker-card text-xs uppercase tracking-wide text-faint opacity-0">
            While you were in meetings
          </p>
          {TICKER.map((t) => (
            <div
              key={t.summary}
              className={cn(
                "ticker-card flex items-center gap-3 rounded-2xl border border-edge bg-panel p-4 opacity-0",
                t.tilt,
              )}
            >
              <div className="rounded-lg bg-accent-soft p-2">
                <t.icon size={16} className="text-accent" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm text-ink">{t.summary}</p>
                <p className="mt-0.5 text-xs text-faint">{t.time}</p>
              </div>
              <Badge tone={t.tone}>{t.agent}</Badge>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
