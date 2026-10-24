"use client";

import { useEffect, useState } from "react";
import { Recovery } from "@/components/recovery";
import { reloadForStaleBuild, shouldReloadForStaleBuild } from "@/lib/stale-build";

export default function DashboardError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  const [reloading] = useState(() => shouldReloadForStaleBuild(error));

  useEffect(() => {
    console.error(error);
    if (reloading) reloadForStaleBuild();
  }, [error, reloading]);

  if (reloading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center text-sm text-sub">
        Meelu was updated. Loading the new version…
      </div>
    );
  }

  return (
    <Recovery
      title="This screen ran into a problem."
      hint="Anything running in the background keeps going. Try again, go back, or head home."
      onRetry={retry}
    />
  );
}
