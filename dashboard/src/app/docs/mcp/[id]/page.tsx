import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import {
  ArrowLeft,
  BookOpen,
  ExternalLink,
  Sparkles,
  TriangleAlert,
} from "lucide-react";
import { CodeBlock } from "@/components/docs/code-block";
import {
  CATEGORY_LABEL,
  MCP_CATALOG,
  catalogEntry,
  isInstallable,
  serverCommand,
  serverConfigJson,
} from "@/lib/mcp-catalog";

export function generateStaticParams() {
  return MCP_CATALOG.map((entry) => ({ id: entry.id }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ id: string }>;
}): Promise<Metadata> {
  const { id } = await params;
  const entry = catalogEntry(id);
  if (!entry) return { title: "Not found" };

  return {
    title: `Install the ${entry.name} MCP server`,
    description: `${entry.blurb} How to connect ${entry.name} to Claude Code, Claude Desktop, Cursor and other MCP clients, alongside Meelu.`,
  };
}

export default async function ServerDocPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const entry = catalogEntry(id);
  if (!entry) notFound();

  const installable = isInstallable(entry);
  const fields = entry.fields ?? [];
  const oauth = entry.transport.kind === "http" && entry.transport.auth === "oauth";

  return (
    <article className="space-y-10">
      <div>
        <Link
          href="/docs"
          className="inline-flex items-center gap-1.5 text-xs text-faint transition-colors hover:text-accent"
        >
          <ArrowLeft size={12} /> Docs
        </Link>

        <div className="mt-3 flex flex-wrap items-center gap-2.5">
          <h1 className="font-display text-3xl text-ink">{entry.name}</h1>
          <span className="rounded-full border border-edge2 bg-panel2 px-2 py-0.5 text-[11px] text-sub">
            {CATEGORY_LABEL[entry.category]}
          </span>
          {entry.publisher === "official" ? (
            <span className="rounded-full border border-good/30 bg-good/10 px-2 py-0.5 text-[11px] font-medium text-good">
              Official server
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 rounded-full border border-warn/30 bg-warn/10 px-2 py-0.5 text-[11px] font-medium text-warn">
              <TriangleAlert size={10} /> No official server
            </span>
          )}
        </div>

        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">{entry.blurb}</p>
      </div>

      {entry.agentGuidance && (
        <section className="rounded-2xl border border-edge bg-panel p-5">
          <h2 className="flex items-center gap-1.5 text-sm font-medium text-ink">
            <Sparkles size={14} className="text-accent" /> What it&apos;s for with Meelu
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">{entry.agentGuidance}</p>
        </section>
      )}

      {entry.caveat && (
        <section className="rounded-2xl border border-warn/30 bg-warn/5 p-5">
          <h2 className="flex items-center gap-1.5 text-sm font-medium text-warn">
            <TriangleAlert size={14} /> Read this first
          </h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">{entry.caveat}</p>
        </section>
      )}

      {installable ? (
        <>
          <section>
            <h2 className="font-display text-lg text-ink">Before you start</h2>
            {fields.length === 0 ? (
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
                {oauth
                  ? `Nothing to fetch. ${entry.name} signs you in through the browser the first time your assistant uses it — there is no token to create, copy or store.`
                  : "Nothing to fetch. This server needs no credentials."}
              </p>
            ) : (
              <>
                <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
                  You&apos;ll need {fields.length === 1 ? "one value" : `${fields.length} values`}{" "}
                  before the config below will work. Get{" "}
                  {fields.length === 1 ? "it" : "them"} first — a config pasted with the
                  placeholders still in it fails at first use rather than at setup, which is a far
                  more confusing way to find out.
                </p>
                <ul className="mt-4 space-y-4">
                  {fields.map((field) => (
                    <li key={field.key} className="rounded-xl border border-edge bg-panel p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-sm font-medium text-ink">{field.label}</span>
                        {field.secret && (
                          <span className="rounded-full border border-warn/30 bg-warn/10 px-2 py-0.5 text-[10px] font-medium text-warn">
                            Secret
                          </span>
                        )}
                        {field.optional && (
                          <span className="rounded-full border border-edge2 bg-panel2 px-2 py-0.5 text-[10px] text-sub">
                            Optional
                          </span>
                        )}
                      </div>
                      <p className="mt-1.5 text-xs leading-relaxed text-sub">{field.help}</p>
                      <p className="mt-2 text-xs text-faint">
                        Replaces{" "}
                        <code className="font-mono text-accent">{field.placeholder}</code> below.
                      </p>
                      {field.url && (
                        <a
                          href={field.url}
                          target="_blank"
                          rel="noreferrer"
                          className="mt-2 inline-flex items-center gap-1 text-xs text-accent hover:underline"
                        >
                          Get it from {entry.name} <ExternalLink size={11} />
                        </a>
                      )}
                    </li>
                  ))}
                </ul>
                <p className="mt-4 max-w-2xl text-xs leading-relaxed text-faint">
                  {fields.length === 1 ? "This value goes" : "These values go"} straight from you
                  into your own MCP config on your own machine. Meelu never asks for{" "}
                  {fields.length === 1 ? "it" : "them"} and never stores{" "}
                  {fields.length === 1 ? "it" : "them"}.
                </p>
              </>
            )}
          </section>

          <section>
            <h2 className="font-display text-lg text-ink">Install</h2>

            <h3 className="mt-4 text-sm font-medium text-ink">Claude Code</h3>
            <CodeBlock className="mt-2" label="Terminal" code={serverCommand(entry)} />

            <h3 className="mt-6 text-sm font-medium text-ink">
              Claude Desktop, Cursor and other clients
            </h3>
            <p className="mt-1.5 max-w-2xl text-sm leading-relaxed text-sub">
              Merge this into wherever your client keeps its MCP servers, alongside the{" "}
              <code className="font-mono text-xs">meelu</code> entry you already have.
            </p>
            <CodeBlock className="mt-2" label="mcpServers" code={serverConfigJson(entry)} />
          </section>

          <section>
            <h2 className="font-display text-lg text-ink">Check it worked</h2>
            <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
              Restart your client — a server registered mid-session isn&apos;t picked up until
              then. In Claude Code, run <code className="font-mono text-xs text-accent">/mcp</code>{" "}
              and look for <span className="text-ink">{entry.id}</span> in the list.
            </p>
            {oauth && (
              <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
                It will show as needing login. Select it, and {entry.name} opens in your browser to
                authorise the connection. That grants your assistant the same access your own
                account has, so review the permission screen rather than clicking through it.
              </p>
            )}
          </section>
        </>
      ) : (
        <section className="rounded-2xl border border-edge bg-panel p-6">
          <h2 className="font-display text-lg text-ink">There&apos;s nothing to install yet</h2>
          <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
            This page exists so the gap is visible rather than surprising. We won&apos;t publish a
            command for {entry.name} until there is one worth trusting — a wrong install
            instruction is worse than an honest missing one.
          </p>
          <p className="mt-3 max-w-2xl text-sm leading-relaxed text-sub">
            In the meantime, Meelu still drafts and schedules the work; you publish it
            yourself. Your assistant will tell you what&apos;s due and hand you the text.
          </p>
        </section>
      )}

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-edge pt-5">
        <a
          href={entry.docsUrl}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 text-sm text-accent hover:underline"
        >
          <BookOpen size={14} /> {entry.name}&apos;s own documentation <ExternalLink size={12} />
        </a>
        <span className="text-xs text-faint">Checked against their docs on {entry.verifiedOn}</span>
      </footer>
    </article>
  );
}
