"use client";

import { useRef } from "react";
import Link from "next/link";
import { Check } from "lucide-react";
import { gsap, useGSAP } from "@/components/animate";

const PLANS: Array<{
  name: string;
  price: string;
  cadence: string;
  blurb: string;
  cta: string;
  href: string;
  highlighted: boolean;
  tag?: string;
  features: string[];
}> = [
  {
    name: "Solo",
    price: "$0",
    cadence: "bring your own keys",
    blurb: "The full coworker for one site. You bring your own Search Console access — we never mark up your data.",
    cta: "Start free",
    href: "/login",
    highlighted: false,
    features: [
      "One site workspace",
      "All five desks, including the Growth Loop",
      "GitHub & CMS connectors",
      "Your keys, your data, your approvals",
    ],
  },
  {
    name: "Agency",
    price: "$19",
    cadence: "per client / month",
    blurb: "One brain per client. Isolated workspaces with their own context, connectors, and approval queues — priced by the client, nothing else.",
    cta: "Start with a client",
    href: "/login",
    highlighted: true,
    tag: "For agencies",
    features: [
      "Everything in Solo, per client",
      "A workspace and context brain per client",
      "Client-ready reports with method & sample size",
      "Add or drop clients any month",
    ],
  },
];

export function Pricing() {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        ".pricing-head",
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
        ".plan-card",
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
    <section ref={ref} id="pricing" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20 sm:py-24">
      <div className="pricing-head max-w-xl">
        <h2 className="font-display text-3xl text-ink">Simple pricing</h2>
        <p className="mt-2 text-sm text-sub">
          Solo is free — bring your own keys. Agencies pay per client, and every
          client gets their own brain.
        </p>
      </div>

      <div className="mt-10 grid gap-4 md:grid-cols-2">
        {PLANS.map((p) => (
          <div
            key={p.name}
            className={`plan-card rounded-2xl border p-6 ${
              p.highlighted ? "border-accent bg-panel" : "border-edge bg-panel"
            }`}
          >
            <div className="flex items-center justify-between">
              <h3 className="font-display text-lg text-ink">{p.name}</h3>
              {p.tag && (
                <span className="rounded-full bg-accent-soft px-2.5 py-1 text-xs font-medium text-accent">
                  {p.tag}
                </span>
              )}
            </div>
            <div className="mt-4 flex items-baseline gap-1.5">
              <span className="font-display text-4xl text-ink">{p.price}</span>
              <span className="text-sm text-faint">{p.cadence}</span>
            </div>
            <p className="mt-3 text-sm text-sub">{p.blurb}</p>

            <ul className="mt-6 space-y-2.5">
              {p.features.map((f) => (
                <li key={f} className="flex items-center gap-2.5 text-sm">
                  <Check size={15} className="shrink-0 text-accent" />
                  <span className="text-ink">{f}</span>
                </li>
              ))}
            </ul>

            <Link
              href={p.href}
              className={`mt-7 block rounded-lg px-3.5 py-2 text-center text-sm font-medium transition-colors ${
                p.highlighted
                  ? "bg-accent text-white hover:bg-accent-hi"
                  : "border border-edge text-ink hover:bg-panel2"
              }`}
            >
              {p.cta}
            </Link>
          </div>
        ))}
      </div>
    </section>
  );
}
