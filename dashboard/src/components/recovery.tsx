"use client";

import { useRouter } from "next/navigation";
import { ArrowLeft, Home, RotateCw, TriangleAlert } from "lucide-react";
import { Button, Card } from "@/components/ui";

const HOME = "/dashboard";

export function Recovery({
  title,
  hint,
  onRetry,
}: {
  title: string;
  hint: string;
  onRetry?: () => void;
}) {
  const router = useRouter();
  const goBack = () => {
    if (window.history.length > 1) router.back();
    else router.push(HOME);
  };
  return (
    <div className="flex flex-1 items-center justify-center py-16">
      <Card className="flex max-w-md flex-col items-center py-12 text-center">
        <div className="mb-4 rounded-2xl bg-accent-soft p-3">
          <TriangleAlert className="text-accent" size={22} />
        </div>
        <p className="font-display text-lg text-ink">{title}</p>
        <p className="mt-1.5 max-w-sm text-sm text-sub">{hint}</p>
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <Button variant="outline" onClick={goBack}>
            <ArrowLeft size={14} />
            Back
          </Button>
          {onRetry && (
            <Button variant="outline" onClick={onRetry}>
              <RotateCw size={14} />
              Try again
            </Button>
          )}
          <Button onClick={() => router.push(HOME)}>
            <Home size={14} />
            Home
          </Button>
        </div>
      </Card>
    </div>
  );
}
