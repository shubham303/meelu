import { demoBridge } from "./bridge";

declare global {
  interface Window {
    meeluDemoInstalled?: boolean;
  }
}

export function installDemoBridge(): void {
  if (typeof window === "undefined" || window.meeluDemoInstalled) return;
  (window as unknown as { meeluAgent: unknown }).meeluAgent = demoBridge;
  window.meeluDemoInstalled = true;
}

if (typeof window !== "undefined") installDemoBridge();
