"use client";

import { useEffect } from "react";
import { Recovery } from "@/components/recovery";

export default function DashboardError({ error, retry }: { error: Error & { digest?: string }; retry: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <Recovery
      title="This screen ran into a problem."
      hint="Anything running in the background keeps going. Try again, go back, or head home."
      onRetry={retry}
    />
  );
}
