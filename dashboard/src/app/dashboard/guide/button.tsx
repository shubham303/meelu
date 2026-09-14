"use client";

import Link from "next/link";
import { BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";

export function GuideButton({ agent, className }: { agent: string; className?: string }) {
  return (
    <Link
      href={`/dashboard/guide/${agent}`}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium",
        "text-sub transition-colors hover:bg-panel2 hover:text-ink",
        className,
      )}
    >
      <BookOpen size={14} /> What it does
    </Link>
  );
}
