import type { Metadata } from "next";
import Link from "next/link";
import { ArrowLeft, ArrowRight } from "lucide-react";
import { CodeBlock } from "@/components/docs/code-block";
import { meeluCommand, meeluConfigJson } from "@/lib/mcp-catalog";

export const metadata: Metadata = {
  title: "Connect Meelu",
  description:
    "Connect Meelu's agent server to Claude Code, Claude Desktop, Cursor or any MCP client over HTTP.",
};

const OPTS = {
  apiKey: "emcp_your_key_here",
};

export default function MeeluInstallPage() {
  return (
    <article className="space-y-10">
      <div>
        <Link
          href="/docs"
          className="inline-flex items-center gap-1.5 text-xs text-faint transition-colors hover:text-accent"
        >
          <ArrowLeft size={12} /> Docs
        </Link>
        <h1 className="mt-3 font-display text-3xl text-ink">Connect Meelu</h1>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          Meelu&apos;s agent server runs on your machine as part of the Meelu stack — there is
          nothing extra to install. It speaks MCP over streamable HTTP at{" "}
          <code className="font-mono text-xs text-accent">http://127.0.0.1:8484/mcp/</code>, and
          any MCP client that reaches that URL with your API key gets what the in-app agent
          gets: read access to your workspace data, the analytics engine, and a small set of
          reviewed writes whose results land back in the dashboard.
        </p>
      </div>

      <section>
        <h2 className="font-display text-lg text-ink">1. Get your API key</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          Make sure the dashboard stack and the agent server are running, then sign in and open{" "}
          <Link href="/dashboard/settings" className="text-accent hover:underline">
            Settings
          </Link>
          . Under <span className="text-ink">Connect your coworker</span> there&apos;s a key
          starting <code className="font-mono text-xs text-accent">emcp_</code> — copy it. The
          key goes in an <code className="font-mono text-xs">x-api-key</code> header on every
          request, which is the whole of the authentication.
        </p>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          That page also shows the same config as below, with your real key already filled in. If
          you&apos;re signed in, copy it from there instead of retyping anything.
        </p>
      </section>

      <section>
        <h2 className="font-display text-lg text-ink">2. Register the server</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          Replace the placeholder key with your own. The URL is the default the agent server
          listens on — the same one the Meelu app reads from{" "}
          <code className="font-mono text-xs">MEELU_AGENT_MCP_URL</code> — so change it only if
          you run the server on a different host or port.
        </p>

        <h3 className="mt-5 text-sm font-medium text-ink">Claude Code</h3>
        <CodeBlock className="mt-2" label="Terminal" code={meeluCommand(OPTS)} />

        <h3 className="mt-6 text-sm font-medium text-ink">
          Claude Desktop, Cursor and other clients
        </h3>
        <p className="mt-1.5 text-sm leading-relaxed text-sub">
          Merge this into wherever your client keeps its MCP servers —{" "}
          <code className="font-mono text-xs">claude_desktop_config.json</code>,{" "}
          <code className="font-mono text-xs">.cursor/mcp.json</code>, or the equivalent.
        </p>
        <CodeBlock className="mt-2" label="mcpServers" code={meeluConfigJson(OPTS)} />
      </section>

      <section>
        <h2 className="font-display text-lg text-ink">3. Check it worked</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          Restart your client — a newly registered server isn&apos;t picked up by a session that
          was already running. In Claude Code, run{" "}
          <code className="font-mono text-xs text-accent">/mcp</code> and look for{" "}
          <span className="text-ink">meelu</span> as connected. Then ask your assistant
          something only Meelu would know, like{" "}
          <span className="text-ink">&ldquo;what content is on my calendar?&rdquo;</span>
        </p>
        <p className="mt-3 max-w-2xl text-sm leading-relaxed text-sub">
          If it fails to connect, it&apos;s almost always one of three things: the agent server
          isn&apos;t running (it answers{" "}
          <code className="font-mono text-xs text-accent">GET /health</code> when it is), the key
          was truncated on copy, or the client wasn&apos;t restarted.
        </p>
      </section>

      <section className="rounded-2xl border border-edge bg-panel p-6">
        <h2 className="font-display text-lg text-ink">Next: connect your other tools</h2>
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-sub">
          Meelu drafts posts; sending and publishing happen through the
          providers you connect in the Meelu app. Adding the right server closes other gaps
          in the same conversation.
        </p>
        <Link
          href="/docs"
          className="mt-4 inline-flex items-center gap-1.5 text-sm text-accent hover:underline"
        >
          Browse all servers <ArrowRight size={14} />
        </Link>
      </section>
    </article>
  );
}
