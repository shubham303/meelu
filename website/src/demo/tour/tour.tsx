"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, useSyncExternalStore, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { ArrowLeft, ArrowRight, Compass, X } from "lucide-react";
import { Button } from "@demo/components/ui";
import { TOUR_STEPS, type TourTarget } from "./steps";

const STORAGE_KEY = "meelu-demo-tour";

interface TourState {
  on: boolean;
  step: number;
}

interface TourControls {
  on: boolean;
  start: () => void;
  stop: () => void;
}

const TourContext = createContext<TourControls>({ on: false, start: () => {}, stop: () => {} });

export function useTour(): TourControls {
  return useContext(TourContext);
}

function readState(): TourState {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return { on: true, step: 0 };
    const parsed = JSON.parse(raw) as Partial<TourState>;
    const step = typeof parsed.step === "number" ? Math.min(Math.max(0, parsed.step), TOUR_STEPS.length - 1) : 0;
    return { on: parsed.on !== false, step };
  } catch {
    return { on: true, step: 0 };
  }
}

function writeState(state: TourState): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
  } catch {}
}

const listeners = new Set<() => void>();
let cached: TourState | undefined;

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

function snapshot(): TourState {
  if (cached === undefined) cached = readState();
  return cached;
}

function serverSnapshot(): TourState | null {
  return null;
}

function setTourState(next: TourState): void {
  cached = next;
  writeState(next);
  for (const listener of listeners) listener();
}

function samePath(a: string, b: string): boolean {
  return a.replace(/\/$/, "") === b.replace(/\/$/, "");
}

function findTarget(target: TourTarget): Element | null {
  let el: Element | null = null;
  if (target.selector) {
    el = Array.from(document.querySelectorAll(target.selector)).find((node) => node.getClientRects().length > 0) ?? null;
  } else if (target.text) {
    const wanted = target.text.trim();
    el =
      Array.from(document.querySelectorAll("main h1, main h2, main h3, main p, h1, h2, h3")).find(
        (node) => node.textContent?.trim() === wanted && node.getClientRects().length > 0,
      ) ?? null;
  }
  if (el && target.card) el = el.closest(".rounded-2xl") ?? el;
  return el;
}

interface Box {
  top: number;
  left: number;
  width: number;
  height: number;
}

function sameBox(a: Box | null, b: Box | null): boolean {
  if (!a || !b) return a === b;
  return a.top === b.top && a.left === b.left && a.width === b.width && a.height === b.height;
}

function useTargetBox(target: TourTarget | undefined, active: boolean, stepId: string): Box | null {
  const [box, setBox] = useState<Box | null>(null);
  const scrolledFor = useRef<string | null>(null);

  useEffect(() => {
    if (!active || !target) return;
    const measure = () => {
      const el = findTarget(target);
      if (!el) {
        setBox((prev) => (prev === null ? prev : null));
        return;
      }
      if (scrolledFor.current !== stepId) {
        scrolledFor.current = stepId;
        const r = el.getBoundingClientRect();
        if (r.top < 0 || r.bottom > window.innerHeight) el.scrollIntoView({ block: "center", behavior: "smooth" });
      }
      const r = el.getBoundingClientRect();
      const next = { top: Math.round(r.top), left: Math.round(r.left), width: Math.round(r.width), height: Math.round(r.height) };
      setBox((prev) => (sameBox(prev, next) ? prev : next));
    };
    const first = window.requestAnimationFrame(measure);
    const timer = window.setInterval(measure, 250);
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      window.cancelAnimationFrame(first);
      window.clearInterval(timer);
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [target, active, stepId]);

  return active && target ? box : null;
}

export function TourProvider({ enabled, children }: { enabled: boolean; children: ReactNode }) {
  const router = useRouter();
  const pathname = usePathname() ?? "";
  const state = useSyncExternalStore(subscribe, snapshot, serverSnapshot);

  const goTo = useCallback(
    (index: number) => {
      const step = TOUR_STEPS[index];
      setTourState({ on: true, step: index });
      if (!samePath(pathname, step.path)) router.push(step.path);
    },
    [pathname, router],
  );

  const stop = useCallback(() => setTourState({ on: false, step: state?.step ?? 0 }), [state]);
  const start = useCallback(() => goTo(0), [goTo]);

  const lastPath = useRef(pathname);
  useEffect(() => {
    if (!state?.on || lastPath.current === pathname) return;
    lastPath.current = pathname;
    const current = TOUR_STEPS[state.step];
    const next = TOUR_STEPS[state.step + 1];
    if (next && !samePath(current.path, pathname) && samePath(next.path, pathname)) setTourState({ on: true, step: state.step + 1 });
  }, [pathname, state]);

  const controls = useMemo<TourControls>(() => ({ on: !!state?.on, start, stop }), [state, start, stop]);
  const showing = enabled && !!state?.on;

  return (
    <TourContext.Provider value={controls}>
      {children}
      {showing && state && <TourCard index={state.step} pathname={pathname} onGo={goTo} onStop={stop} onFinish={() => setTourState({ on: false, step: 0 })} />}
    </TourContext.Provider>
  );
}

function TourCard({
  index,
  pathname,
  onGo,
  onStop,
  onFinish,
}: {
  index: number;
  pathname: string;
  onGo: (index: number) => void;
  onStop: () => void;
  onFinish: () => void;
}) {
  const step = TOUR_STEPS[index];
  const here = samePath(pathname, step.path);
  const box = useTargetBox(step.target, here, step.id);
  const last = index === TOUR_STEPS.length - 1;

  return (
    <>
      {box && (
        <div
          aria-hidden
          className="pointer-events-none fixed z-[65] rounded-xl ring-2 ring-accent transition-all duration-200"
          style={{
            top: box.top - 6,
            left: box.left - 6,
            width: box.width + 12,
            height: box.height + 12,
            boxShadow: "0 0 0 6px rgba(37, 99, 235, 0.18)",
          }}
        />
      )}
      <div
        role="dialog"
        aria-label="Guided tour"
        className="fixed inset-x-4 bottom-4 z-[70] rounded-2xl border border-edge bg-panel p-4 shadow-xl sm:inset-x-auto sm:right-5 sm:bottom-5 sm:w-[360px]"
      >
        <div className="flex items-center justify-between gap-2">
          <span className="inline-flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-faint">
            <Compass size={12} className="text-accent" /> {step.chapter} · {index + 1} of {TOUR_STEPS.length}
          </span>
          <button
            type="button"
            onClick={onStop}
            aria-label="Turn off the tour"
            className="rounded-md p-1 text-faint transition-colors hover:bg-panel2 hover:text-ink"
          >
            <X size={14} />
          </button>
        </div>
        <div className="mt-2 h-1 overflow-hidden rounded-full bg-panel2">
          <div className="h-full rounded-full bg-accent transition-all" style={{ width: `${((index + 1) / TOUR_STEPS.length) * 100}%` }} />
        </div>
        <p className="mt-3 font-display text-base text-ink">{step.title}</p>
        <p className="mt-1.5 text-sm leading-relaxed text-sub">{step.body}</p>
        {!here && (
          <button type="button" onClick={() => onGo(index)} className="mt-2 text-xs font-medium text-accent hover:underline">
            Take me to this screen →
          </button>
        )}
        <div className="mt-4 flex items-center justify-between gap-2">
          <button type="button" onClick={onStop} className="text-xs text-faint transition-colors hover:text-ink">
            Turn off tour
          </button>
          <div className="flex items-center gap-1.5">
            {index > 0 && (
              <Button size="sm" variant="ghost" onClick={() => onGo(index - 1)}>
                <ArrowLeft size={13} /> Back
              </Button>
            )}
            {last ? (
              <Button size="sm" onClick={onFinish}>
                Finish
              </Button>
            ) : (
              <Button size="sm" onClick={() => onGo(index + 1)}>
                Next <ArrowRight size={13} />
              </Button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
