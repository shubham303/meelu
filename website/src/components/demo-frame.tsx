"use client";

import { useEffect, useRef, useState } from "react";
import { Compass, Play } from "lucide-react";

const NATIVE_WIDTH = 1280;
const NATIVE_HEIGHT = 820;

const SCREENS = [
  { label: "Overview", path: "/demo/dashboard" },
  { label: "Site", path: "/demo/dashboard/site" },
  { label: "Technical SEO", path: "/demo/dashboard/site/technical-seo" },
  { label: "SEO", path: "/demo/dashboard/seo" },
  { label: "Search", path: "/demo/dashboard/seo/search" },
  { label: "GEO", path: "/demo/dashboard/geo" },
  { label: "Content", path: "/demo/dashboard/content" },
  { label: "Social", path: "/demo/dashboard/social-listening" },
  { label: "Find Leads", path: "/demo/dashboard/find-leads" },
  { label: "Analytics", path: "/demo/dashboard/analytics" },
  { label: "Connections", path: "/demo/dashboard/connections" },
] as const;

export function DemoFrame() {
  const shellRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef<HTMLIFrameElement>(null);
  const [scale, setScale] = useState(1);
  const [armed, setArmed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [screen, setScreen] = useState<string>(SCREENS[0].path);

  useEffect(() => {
    const el = shellRef.current;
    if (!el) return;
    const measure = () => setScale(Math.min(1, el.clientWidth / NATIVE_WIDTH));
    measure();
    const ro = new ResizeObserver(measure);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // The demo is a whole app (GSAP, charts) running on this page's main thread,
  // so it must never compete with the hero. Phones wait for a tap, since the
  // frame is scaled too small to read there anyway. Wider screens load it once
  // the page has finished loading and the frame is near the viewport.
  useEffect(() => {
    const el = shellRef.current;
    if (!el || armed) return;
    if (!window.matchMedia("(min-width: 1024px)").matches) return;
    let io: IntersectionObserver | undefined;
    const observe = () => {
      io = new IntersectionObserver(
        (entries) => {
          if (entries.some((e) => e.isIntersecting)) setArmed(true);
        },
        { rootMargin: "400px 0px" },
      );
      io.observe(el);
    };
    if (document.readyState === "complete") observe();
    else window.addEventListener("load", observe, { once: true });
    return () => {
      window.removeEventListener("load", observe);
      io?.disconnect();
    };
  }, [armed]);

  const go = (path: string) => {
    setScreen(path);
    const win = frameRef.current?.contentWindow;
    if (win) win.location.replace(path);
  };

  return (
    <div className="w-full">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1.5">
          {SCREENS.map((s) => (
            <button
              key={s.path}
              type="button"
              onClick={() => go(s.path)}
              className={`rounded-full border px-3 py-1 text-xs transition-colors ${
                screen === s.path
                  ? "border-accent/40 bg-accent-soft text-accent"
                  : "border-edge2 bg-panel text-sub hover:text-ink"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
        <a
          href="/demo/dashboard"
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-sub transition-colors hover:text-ink"
        >
          <Compass size={12} /> Take the guided tour
        </a>
      </div>

      <div
        ref={shellRef}
        className="overflow-hidden rounded-2xl border border-edge2 bg-panel shadow-[0_1px_2px_rgba(31,45,61,0.05),0_30px_60px_-30px_rgba(31,45,61,0.35)]"
      >
        <div className="flex h-10 items-center gap-2 border-b border-edge bg-panel2 px-3">
          <span className="flex gap-1.5">
            <i className="h-2.5 w-2.5 rounded-full bg-[#ff5f57]" />
            <i className="h-2.5 w-2.5 rounded-full bg-[#febc2e]" />
            <i className="h-2.5 w-2.5 rounded-full bg-[#28c840]" />
          </span>
          <span className="mx-auto flex h-6 max-w-sm flex-1 items-center justify-center rounded-md border border-edge bg-panel px-3 font-mono text-[11px] text-faint">
            Meelu · ledgerly.app
          </span>
          <span className="w-12" />
        </div>

        <div
          className="relative w-full"
          style={{ height: Math.round(NATIVE_HEIGHT * scale) }}
        >
          {armed ? (
            <iframe
              ref={frameRef}
              title="Meelu interactive demo"
              src={SCREENS[0].path}
              onLoad={() => setLoaded(true)}
              className="absolute left-0 top-0 border-0 bg-bg"
              style={{
                width: NATIVE_WIDTH,
                height: NATIVE_HEIGHT,
                transform: `scale(${scale})`,
                transformOrigin: "top left",
              }}
            />
          ) : null}
          {!loaded && (
            <button
              type="button"
              onClick={() => setArmed(true)}
              className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-bg text-sub"
            >
              <span className="flex h-12 w-12 items-center justify-center rounded-full border border-edge2 bg-panel text-accent shadow-sm">
                <Play size={18} className="ml-0.5" />
              </span>
              <span className="text-sm">{armed ? "Loading the demo…" : "Load the interactive demo"}</span>
            </button>
          )}
        </div>
      </div>
      <p className="mt-3 text-center text-xs text-faint">
        A made-up business, real screens. Click anything — nothing leaves your browser.
      </p>
    </div>
  );
}
