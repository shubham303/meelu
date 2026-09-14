"use client";

import Link from "next/link";
import { Logo } from "@/components/logo";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { Desks } from "@/components/landing/desks";
import { Differentiators } from "@/components/landing/differentiators";
import { Audience } from "@/components/landing/audience";
import { Pricing } from "@/components/landing/pricing";
import { Faq } from "@/components/landing/faq";
import { CtaBand } from "@/components/landing/cta-band";

const NAV_LINKS = [
  { href: "#how", label: "How it works" },
  { href: "#desks", label: "Desks" },
  { href: "#pricing", label: "Pricing" },
  { href: "/why", label: "Why" },
  { href: "#faq", label: "FAQ" },
  { href: "/docs", label: "Docs" },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="sticky top-0 z-40 border-b border-edge bg-bg/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-6">
          <Link href="/" aria-label="Meelu home">
            <Logo />
          </Link>
          <nav className="hidden items-center gap-6 text-sm text-sub sm:flex">
            {NAV_LINKS.map((l) => (
              <a key={l.href} href={l.href} className="transition-colors hover:text-ink">
                {l.label}
              </a>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            <Link
              href="/login"
              className="rounded-lg px-3.5 py-2 text-sm font-medium text-sub transition-colors hover:bg-panel2 hover:text-ink"
            >
              Sign in
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

      <main>
        <Hero />
        <HowItWorks />
        <Desks />
        <Differentiators />
        <Audience />
        <Pricing />
        <Faq />
        <CtaBand />
      </main>

      <footer className="border-t border-edge">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-8">
          <Logo size={18} />
          <p className="text-xs text-faint">Human-approved. Agent-applied.</p>
          <div className="flex items-center gap-4">
            <Link href="/why" className="text-xs text-sub transition-colors hover:text-ink">
              Why we built it this way
            </Link>
            <Link href="/signup" className="text-xs text-sub transition-colors hover:text-ink">
              Get started →
            </Link>
          </div>
        </div>
      </footer>
    </div>
  );
}
