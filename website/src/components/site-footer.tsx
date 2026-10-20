import Link from "next/link";
import { Logo } from "@/components/logo";
import { featuredOn } from "@/lib/featured-on";
import { site } from "@/lib/site";

export function SiteFooter() {
  return (
    <footer className="border-t border-edge">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-4 px-6 py-8">
        <Link href="/" aria-label="Meelu home">
          <Logo size={18} />
        </Link>
        <nav className="flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-sub">
          <Link href="/tools" className="transition-colors hover:text-ink">
            Free tools
          </Link>
          <Link href="/docs" className="transition-colors hover:text-ink">
            Docs
          </Link>
          <Link href="/pricing" className="transition-colors hover:text-ink">
            Pricing
          </Link>
          <Link href="/blog" className="transition-colors hover:text-ink">
            Blog
          </Link>
          <Link href="/contact" className="transition-colors hover:text-ink">
            Contact
          </Link>
          <Link href="/terms" className="transition-colors hover:text-ink">
            Terms
          </Link>
          <Link href="/privacy" className="transition-colors hover:text-ink">
            Privacy
          </Link>
          <a
            href={site.github}
            target="_blank"
            rel="noreferrer"
            className="transition-colors hover:text-ink"
          >
            GitHub
          </a>
          <Link href="/rss.xml" className="transition-colors hover:text-ink">
            RSS
          </Link>
        </nav>
      </div>
      {featuredOn.length > 0 && (
        <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center gap-x-4 gap-y-3 px-6 pb-8 text-xs text-sub">
          <span>Featured on</span>
          {featuredOn.map((entry) => (
            <a
              key={entry.href}
              href={entry.href}
              target="_blank"
              className="transition-colors hover:text-ink"
            >
              {entry.badge ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={entry.badge.src}
                  alt={`Featured on ${entry.name}`}
                  width={entry.badge.width}
                  height={entry.badge.height}
                  className="h-8 w-auto"
                  loading="lazy"
                />
              ) : (
                entry.name
              )}
            </a>
          ))}
        </div>
      )}
    </footer>
  );
}
