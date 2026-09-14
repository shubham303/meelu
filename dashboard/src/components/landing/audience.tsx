"use client";

import { useRef } from "react";
import { Building2, Rocket, type LucideIcon } from "lucide-react";
import { gsap, useGSAP } from "@/components/animate";

const AUDIENCES: Array<{ icon: LucideIcon; title: string; body: string }> = [
  {
    icon: Building2,
    title: "For agencies: one brain per client",
    body: "Every client gets its own workspace — its own context, connectors, and approval queue. Switch clients without switching heads, and hand over reports that carry their own receipts.",
  },
  {
    icon: Rocket,
    title: "For builders: your whole marketing team",
    body: "You keep shipping product; your coworker keeps shipping the marketing — keywords, content, outreach, reviews — and asks before it touches anything.",
  },
];

export function Audience() {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        ".aud-card",
        { opacity: 0, y: 22 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          ease: "power3.out",
          stagger: 0.1,
          scrollTrigger: { trigger: ref.current, start: "top 80%", once: true },
        },
      );
    },
    { scope: ref },
  );

  return (
    <section ref={ref} className="mx-auto max-w-6xl px-6 pb-20 sm:pb-24">
      <div className="grid gap-4 md:grid-cols-2">
        {AUDIENCES.map((a) => (
          <div
            key={a.title}
            className="aud-card grain relative overflow-hidden rounded-2xl border border-edge bg-panel p-6"
          >
            <div
              aria-hidden
              className="absolute inset-0"
              style={{
                background:
                  "radial-gradient(60% 90% at 0% 100%, var(--color-accent-soft), transparent 70%)",
              }}
            />
            <div className="relative">
              <div className="flex items-center gap-3">
                <div className="rounded-lg bg-accent-soft p-2">
                  <a.icon size={17} className="text-accent" />
                </div>
                <h3 className="font-display text-lg text-ink">{a.title}</h3>
              </div>
              <p className="mt-3 text-sm text-sub">{a.body}</p>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
