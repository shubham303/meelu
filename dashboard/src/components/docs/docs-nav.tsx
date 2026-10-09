"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { useSession } from "@/lib/session";

export function DocsNav() {
  const { data: session, isPending } = useSession();

  if (isPending) return <div className="h-9" aria-hidden />;

  if (session?.user) {
    return (
      <Link
        href="/dashboard"
        className="inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-sm font-medium text-sub transition-colors hover:bg-panel2 hover:text-ink"
      >
        <ArrowLeft size={14} />
        Back to dashboard
      </Link>
    );
  }

  return (
    <>
      <Link
        href="/login"
        className="rounded-lg px-3.5 py-2 text-sm font-medium text-sub transition-colors hover:bg-panel2 hover:text-ink"
      >
        Sign in
      </Link>
      <Link
        href="/login"
        className="rounded-lg bg-accent px-3.5 py-2 text-sm font-medium text-white transition-colors hover:bg-accent-hi"
      >
        Get started
      </Link>
    </>
  );
}
