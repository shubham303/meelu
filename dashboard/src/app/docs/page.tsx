import type { Metadata } from "next";
import Link from "next/link";
import { ArrowRight, Plug, ShieldCheck, TriangleAlert } from "lucide-react";
import { CATEGORY_LABEL, MCP_CATALOG, type CatalogCategory } from "@/lib/mcp-catalog";

export const metadata: Metadata = {
  title: "Docs",
  description:
    "Connect Meelu's agent server, and the tools you already use — Google Search Console, Google Analytics — to the same conversation.",
};

const CATEGORY_ORDER: CatalogCategory[] = ["cms", "social", "data", "design"];

export default function DocsIndexPage() {
  const grouped = CATEGORY_ORDER.map((category) => ({
    category,
    entries: MCP_CATALOG.filter((e) => e.category === category),
  })).filter((g) => g.entries.length > 0);

  return (
    <div className="space-y-12">
      <header>
        <h1 className="font-display text-3xl text-ink">Docs</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          Meelu&apos;s agent server speaks MCP over HTTP. You point Claude Code, Claude Desktop,
          Cursor or any other MCP client at it, and your assistant gains your pages,
          content, social posts and analytics. The pages below cover that connection, and the other
          servers worth having in the same conversation.
        </p>
      </header>

      <section>
        <Link
          href="/docs/meelu"
          className="group block rounded-2xl border border-accent/30 bg-accent-soft/40 p-6 transition-colors hover:border-accent/60"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-accent">Start here</p>
              <h2 className="mt-1 font-display text-xl text-ink">Connect Meelu</h2>
              <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-sub">
                Five minutes, nothing to install — a URL and an API key from Settings.
              </p>
            </div>
            <ArrowRight
              size={18}
              className="mt-6 shrink-0 text-accent transition-transform group-hover:translate-x-1"
            />
          </div>
        </Link>
      </section>

      <section>
        <Link
          href="/docs/crawl-access"
          className="group block rounded-2xl border border-edge bg-panel p-6 transition-colors hover:border-edge2 hover:bg-panel2"
        >
          <div className="flex items-start justify-between gap-4">
            <div>
              <p className="text-[11px] uppercase tracking-wide text-faint">Your website</p>
              <h2 className="mt-1 font-display text-xl text-ink">Let the crawler through</h2>
              <p className="mt-1.5 max-w-xl text-sm leading-relaxed text-sub">
                If Cloudflare or a firewall blocks the crawl, grant it access with a secret
                header — the rule is one line, and the free plan is enough.
              </p>
            </div>
            <ArrowRight
              size={18}
              className="mt-6 shrink-0 text-sub transition-transform group-hover:translate-x-1"
            />
          </div>
        </Link>
      </section>

      <section>
        <h2 className="font-display text-xl text-ink">Connect your other tools</h2>
        <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-sub">
          Each of these is a separate MCP server, published and maintained by the company behind
          the product. Meelu doesn&apos;t proxy them or hold your credentials — you install
          them into the same client you connected Meelu to, and your assistant can then use all
          of them together. If you&apos;re wondering why capability works by installation rather than
          being built in,{" "}
          <Link href="/why" className="text-accent hover:underline">
            here&apos;s the argument
          </Link>
          .
        </p>

        <p className="mt-4 flex items-start gap-2 rounded-xl border border-edge bg-panel p-3.5 text-xs leading-relaxed text-sub">
          <ShieldCheck size={15} className="mt-px shrink-0 text-good" />
          <span>
            <span className="text-ink">Your tokens stay yours.</span> Every config on these pages
            uses an obvious placeholder like <code className="font-mono text-accent">re_replace_me</code>.
            You replace it in your own file. Meelu never asks for a third-party credential and
            never stores one — and most of these servers don&apos;t need one at all, because they
            sign you in through the browser on first use.
          </span>
        </p>

        <div className="mt-8 space-y-8">
          {grouped.map(({ category, entries }) => (
            <div key={category}>
              <h3 className="mb-3 text-xs uppercase tracking-wide text-faint">
                {CATEGORY_LABEL[category]}
              </h3>
              <div className="grid gap-3 sm:grid-cols-2">
                {entries.map((entry) => (
                  <Link
                    key={entry.id}
                    href={`/docs/mcp/${entry.id}`}
                    className="group flex flex-col rounded-xl border border-edge bg-panel p-4 transition-colors hover:border-edge2 hover:bg-panel2"
                  >
                    <div className="flex items-center gap-2">
                      <h4 className="text-sm font-medium text-ink">{entry.name}</h4>
                      {entry.publisher === "community" && (
                        <span className="inline-flex items-center gap-1 rounded-full border border-warn/30 bg-warn/10 px-2 py-0.5 text-[10px] font-medium text-warn">
                          <TriangleAlert size={9} /> No official server
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs leading-relaxed text-sub">{entry.blurb}</p>
                    <span className="mt-3 inline-flex items-center gap-1 text-[11px] text-faint transition-colors group-hover:text-accent">
                      <Plug size={11} /> Install guide
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="rounded-2xl border border-edge bg-panel p-6">
        <h2 className="font-display text-lg text-ink">What installing a server does not do</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          It does not put anything on a schedule. Meelu runs inside your chat session and
          stops when you close it, so nothing publishes or sends at 9am on its own. What works is
          the other way round: start a session, ask what&apos;s due, and your assistant handles
          it with whichever servers you have connected.
        </p>
      </section>
    </div>
  );
}
