"use client";

import "@demo/mock/install";
import { useEffect, useState } from "react";
import { Compass } from "lucide-react";
import { TourProvider, useTour } from "@demo/tour/tour";

function TourSwitch() {
  const tour = useTour();
  return (
    <button
      type="button"
      onClick={tour.on ? tour.stop : tour.start}
      className="inline-flex shrink-0 items-center gap-1 font-medium text-accent hover:underline"
    >
      <Compass size={12} /> {tour.on ? "Turn off tour" : "Take the tour"}
    </button>
  );
}

export function DemoBoot({ children }: { children: React.ReactNode }) {
  const [embedded, setEmbedded] = useState(true);

  useEffect(() => {
    setEmbedded(window.self !== window.top);
  }, []);

  return (
    <TourProvider enabled={!embedded}>
      {!embedded && (
        <div className="sticky top-0 z-50 flex items-center justify-between gap-3 border-b border-accent/20 bg-accent-soft px-4 py-1.5 text-xs text-ink">
          <span>
            You are in the Meelu demo. Everything here is sample data for a made-up business; nothing leaves your browser.
          </span>
          <div className="flex shrink-0 items-center gap-4">
            <TourSwitch />
            <a href="/download" className="font-medium text-accent hover:underline">
              Download the app →
            </a>
          </div>
        </div>
      )}
      {children}
    </TourProvider>
  );
}
