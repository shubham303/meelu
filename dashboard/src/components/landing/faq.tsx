"use client";

import { useRef } from "react";
import { gsap, useGSAP } from "@/components/animate";

const FAQS: Array<{ q: string; a: string }> = [
  {
    q: "Which data sources does it use?",
    a: "Google Search Console for true positions, impressions, and clicks, plus its own crawl of your site. You bring your own keys — your data stays yours, and we never mark it up.",
  },
  {
    q: "Is anything published without my approval?",
    a: "No. Every action, post, and reply waits in a queue until you approve it on the dashboard. For code changes it opens a pull request, so your normal review is a second gate on top.",
  },
  {
    q: "Does it work with my stack?",
    a: "If your site lives in a GitHub repo, changes ship as pull requests. On WordPress, Ghost, or Webflow, it publishes through the CMS connector. Anything else, it hands you the finished artifact to apply manually.",
  },
  {
    q: "Where does the intelligence live?",
    a: "In the MCP server, inside Claude or any MCP client. This dashboard is the desk — it stores, organizes, and gates the work, and never calls a model itself.",
  },
];

export function Faq() {
  const ref = useRef<HTMLElement>(null);

  useGSAP(
    () => {
      gsap.fromTo(
        ".faq-head",
        { opacity: 0, y: 20 },
        {
          opacity: 1,
          y: 0,
          duration: 0.55,
          ease: "power3.out",
          scrollTrigger: { trigger: ref.current, start: "top 80%", once: true },
        },
      );
      gsap.fromTo(
        ".faq-item",
        { opacity: 0, y: 18 },
        {
          opacity: 1,
          y: 0,
          duration: 0.5,
          ease: "power3.out",
          stagger: 0.08,
          scrollTrigger: { trigger: ref.current, start: "top 76%", once: true },
        },
      );
    },
    { scope: ref },
  );

  return (
    <section ref={ref} id="faq" className="mx-auto max-w-6xl scroll-mt-24 px-6 py-20 sm:py-24">
      <h2 className="faq-head font-display text-3xl text-ink">Fair questions</h2>
      <div className="mt-8 grid gap-x-10 gap-y-8 md:grid-cols-2">
        {FAQS.map((f) => (
          <div key={f.q} className="faq-item">
            <h3 className="font-display text-lg text-ink">{f.q}</h3>
            <p className="mt-1.5 text-sm text-sub">{f.a}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
