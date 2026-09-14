import type { Metadata } from "next";
import Link from "next/link";
import { Logo } from "@/components/logo";
import { DocsNav } from "@/components/docs/docs-nav";

export const metadata: Metadata = {
  title: {
    default: "Docs",
    template: "%s · Meelu Docs",
  },
  description:
    "How to connect Meelu's agent server, and the MCP servers worth connecting alongside it.",
};

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-bg text-ink">
      <header className="sticky top-0 z-40 border-b border-edge bg-bg/80 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-4xl items-center justify-between px-6">
          <div className="flex items-center gap-3">
            <Link href="/" aria-label="Meelu home">
              <Logo />
            </Link>
            <Link href="/docs" className="text-sm text-sub transition-colors hover:text-ink">
              Docs
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <DocsNav />
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-4xl px-6 py-12">{children}</main>

      <footer className="border-t border-edge">
        <div className="mx-auto flex max-w-4xl flex-wrap items-center justify-between gap-4 px-6 py-8">
          <Logo size={18} />
          <p className="text-xs text-faint">Human-approved. Agent-applied.</p>
          <Link href="/docs" className="text-xs text-sub transition-colors hover:text-ink">
            All docs →
          </Link>
        </div>
      </footer>
    </div>
  );
}
