"use client";

import { useRef } from "react";
import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { gsap, useGSAP } from "@/components/animate";

export function CtaBand() {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        ".cta-band",
        { opacity: 0, y: 24 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          ease: "power3.out",
          scrollTrigger: { trigger: ref.current, start: "top 82%", once: true },
        },
      );
    },
    { scope: ref },
  );

  return (
    <section ref={ref} className="mx-auto max-w-6xl px-6 pb-20 sm:pb-24">
      <div className="cta-band grain relative overflow-hidden rounded-2xl border border-edge bg-panel px-8 py-14 text-center">
        <div
          aria-hidden
          className="absolute inset-0"
          style={{
            background:
              "radial-gradient(60% 80% at 50% 100%, var(--color-accent-soft), transparent 70%)",
          }}
        />
        <div className="relative">
          <h2 className="font-display text-3xl text-ink sm:text-4xl">
            Give your website an AI coworker.
          </h2>
          <p className="mx-auto mt-3 max-w-md text-sm text-sub">
            Two minutes to connect. It starts learning your site today — and
            every approved task makes it sharper.
          </p>
          <div className="mt-7 flex flex-wrap items-center justify-center gap-3">
            <Link
              href="/signup"
              className="inline-flex items-center gap-1.5 rounded-lg bg-accent px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
            >
              Get started <ArrowRight size={15} />
            </Link>
            <Link
              href="/login"
              className="inline-flex items-center rounded-lg px-5 py-2.5 text-sm text-sub transition-colors hover:bg-panel2 hover:text-ink"
            >
              Sign in
            </Link>
          </div>
        </div>
      </div>
    </section>
  );
}
