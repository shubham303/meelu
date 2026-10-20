import Link from "next/link";
import { Logo } from "@/components/logo";

const links = [
  { href: "/tools", label: "Free tools", short: "Tools" },
  { href: "/docs", label: "Docs", short: "Docs" },
  { href: "/pricing", label: "Pricing", short: "Pricing" },
  { href: "/blog", label: "Blog", short: "Blog" },
] as const;

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-40 border-b border-edge bg-bg/80 backdrop-blur">
      <div className="mx-auto flex h-14 w-full max-w-6xl items-center justify-between gap-2 px-4 sm:px-6">
        <Link href="/" aria-label="Meelu home">
          <Logo />
        </Link>
        <nav className="flex min-w-0 items-center gap-0.5 sm:gap-4">
          {links.map((link) => (
            <Link
              key={link.href}
              href={link.href}
              className="whitespace-nowrap rounded-lg px-1.5 py-2 text-[13px] text-sub transition-colors hover:bg-panel2 hover:text-ink sm:px-3 sm:text-sm"
            >
              <span className="sm:hidden">{link.short}</span>
              <span className="hidden sm:inline">{link.label}</span>
            </Link>
          ))}
          <Link
            href="/download"
            className="ml-1 whitespace-nowrap rounded-lg bg-accent px-3 py-2 text-[13px] font-medium text-white transition-colors hover:bg-accent-hi sm:px-3.5 sm:text-sm"
          >
            <span className="sm:hidden">Download</span>
            <span className="hidden sm:inline">Download beta</span>
          </Link>
        </nav>
      </div>
    </header>
  );
}
