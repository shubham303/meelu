"use client";

import "@demo/mock/install";
import { useEffect, useState } from "react";

export function DemoBoot({ children }: { children: React.ReactNode }) {
  const [embedded, setEmbedded] = useState(true);

  useEffect(() => {
    setEmbedded(window.self !== window.top);
  }, []);

  return (
    <>
      {!embedded && (
        <div className="sticky top-0 z-50 flex items-center justify-between gap-3 border-b border-accent/20 bg-accent-soft px-4 py-1.5 text-xs text-ink">
          <span>
            You are in the Meelu demo. Everything here is sample data for a made-up business; nothing leaves your browser.
          </span>
          <a href="/download" className="shrink-0 font-medium text-accent hover:underline">
            Download the app →
          </a>
        </div>
      )}
      {children}
    </>
  );
}
