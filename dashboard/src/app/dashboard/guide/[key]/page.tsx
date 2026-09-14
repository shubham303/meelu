"use client";

import Link from "next/link";
import { notFound, useParams } from "next/navigation";
import { ArrowLeft, ArrowRight, Ban, Sparkles, Terminal } from "lucide-react";
import { PageEnter, Stagger } from "@/components/animate";
import { Button, Card } from "@/components/ui";
import { AGENT_GUIDES, findAgentGuide } from "@/lib/agents";
import { useIsApp } from "@/lib/use-app-mode";
import { GUIDE_ICONS } from "../icons";
import { PromptCard } from "../prompt-card";

export default function AgentGuidePage() {
  const { key } = useParams<{ key: string }>();
  const isApp = useIsApp();
  const guide = findAgentGuide(key);
  if (!guide) notFound();

  const Icon = GUIDE_ICONS[guide.icon];
  const others = AGENT_GUIDES.filter((g) => g.key !== guide.key);
  const deskHref = guide.href;

  return (
    <PageEnter>
      <Link
        href={deskHref ?? "/dashboard"}
        className="mb-5 inline-flex items-center gap-1.5 text-sm text-sub transition-colors hover:text-ink"
      >
        <ArrowLeft size={14} /> {deskHref ? guide.name : "Overview"}
      </Link>

      <Card className="mb-6">
        <div className="flex flex-wrap items-start justify-between gap-5">
          <div className="min-w-0 max-w-2xl">
            <div className="flex items-center gap-3">
              <div className="shrink-0 rounded-xl bg-accent-soft p-2.5">
                <Icon className="text-accent" size={20} />
              </div>
              <div className="min-w-0">
                <h1 className="font-display text-2xl text-ink">{guide.name}</h1>
                <p className="mt-0.5 text-sm text-sub">{guide.tagline}</p>
              </div>
            </div>
            <p className="mt-5 text-[15px] leading-relaxed text-ink">{guide.summary}</p>
          </div>

          {deskHref ? (
            <Link href={deskHref}>
              <Button>
                Open {guide.name} <ArrowRight size={14} />
              </Button>
            </Link>
          ) : (
            <p className="max-w-xs text-xs leading-relaxed text-faint">
              These tools still work through the MCP server in Claude or Codex. They no longer
              have a screen of their own — the desk was cut, the data was not.
            </p>
          )}
        </div>
      </Card>

      {guide.chain && (
        <Card className="mb-6">
          <p className="mb-3 text-xs uppercase tracking-wide text-sub">How it fits together</p>
          <div className="flex flex-wrap items-stretch gap-2">
            {guide.chain.map((node, i) => (
              <div key={node.label} className="flex items-center gap-2">
                <div className="rounded-xl border border-edge2 bg-panel2 px-3.5 py-2.5">
                  <p className="font-display text-sm text-ink">{node.label}</p>
                  <p className="mt-0.5 text-xs text-faint">{node.sub}</p>
                </div>
                {i < guide.chain!.length - 1 && (
                  <ArrowRight size={14} className="shrink-0 text-faint" />
                )}
              </div>
            ))}
          </div>
          {guide.chainNote && (
            <p className="mt-3 max-w-3xl text-sm leading-relaxed text-sub">{guide.chainNote}</p>
          )}
        </Card>
      )}

      <section className="mb-6">
        <h2 className="font-display text-lg text-ink">What to say to your coworker</h2>
        {isApp ? (
          <p className="mt-1 mb-3 max-w-2xl text-sm leading-relaxed text-sub">
            Your coworker is built into this screen — any action marked with{" "}
            <Sparkles size={13} className="inline text-accent" /> launches it, with your form
            draft riding along. Say any of these when the chat opens and change the bits in{" "}
            <span className="text-accent">[brackets]</span>.
          </p>
        ) : (
          <p className="mt-1 mb-3 max-w-2xl text-sm leading-relaxed text-sub">
            This screen has no intelligence of its own — everything on it got there because
            somebody asked for it in Claude, and it lands back here for you to check. Copy any of
            these and change the bits in{" "}
            <span className="text-accent">[brackets]</span>.
          </p>
        )}
        <Stagger className="grid gap-3 md:grid-cols-2">
          {guide.prompts.map((prompt) => (
            <PromptCard key={prompt.say} prompt={prompt} />
          ))}
        </Stagger>
      </section>

      <div className="grid gap-6 lg:grid-cols-2 items-start">
        <section>
          <h2 className="mb-3 font-display text-lg text-ink">Worth knowing</h2>
          <Stagger className="space-y-3">
            {guide.rules.map((rule) => (
              <Card key={rule.title} className="stagger-item py-4">
                <div className="flex gap-3">
                  <Sparkles size={15} className="mt-0.5 shrink-0 text-accent" />
                  <div className="min-w-0">
                    <p className="text-sm font-medium text-ink">{rule.title}</p>
                    <p className="mt-1 text-sm leading-relaxed text-sub">{rule.detail}</p>
                  </div>
                </div>
              </Card>
            ))}
          </Stagger>
        </section>

        <section>
          <h2 className="mb-3 font-display text-lg text-ink">What it won&rsquo;t do</h2>
          <Stagger className="space-y-3">
            {guide.limits.map((limit) => (
              <Card key={limit} className="stagger-item flex gap-3 py-4">
                <Ban size={15} className="mt-0.5 shrink-0 text-faint" />
                <p className="text-sm leading-relaxed text-sub">{limit}</p>
              </Card>
            ))}
          </Stagger>

          <Card className="mt-3 py-4">
            <div className="flex gap-3">
              <Terminal size={15} className="mt-0.5 shrink-0 text-faint" />
              <div className="min-w-0">
                {isApp ? (
                  <p className="text-sm text-sub leading-relaxed">
                    Under the hood each task drives the{" "}
                    <code className="font-mono text-xs text-accent">{guide.tools}</code> tools,
                    run locally on this device with your own model — scoped to just this job, so
                    a task can only ever write what it was launched to write.
                  </p>
                ) : (
                  <p className="text-sm text-sub leading-relaxed">
                    Your coworker drives this through the{" "}
                    <code className="font-mono text-xs text-accent">{guide.tools}</code> tools.
                    Run <code className="font-mono text-xs">/mcp</code> in Claude Code to see
                    them, or{" "}
                    <Link href="/docs/meelu" className="text-accent hover:underline">
                      connect it first
                    </Link>{" "}
                    if you haven&rsquo;t yet.
                  </p>
                )}
              </div>
            </div>
          </Card>
        </section>
      </div>

      <section className="mt-8 border-t border-edge pt-5">
        <p className="mb-2.5 text-xs uppercase tracking-wide text-faint">The other agents</p>
        <div className="flex flex-wrap gap-2">
          {others.map((other) => {
            const OtherIcon = GUIDE_ICONS[other.icon];
            return (
              <Link
                key={other.key}
                href={`/dashboard/guide/${other.key}`}
                className="inline-flex items-center gap-1.5 rounded-full border border-edge bg-panel px-3 py-1.5 text-sm text-sub transition-colors hover:border-edge2 hover:text-ink"
              >
                <OtherIcon size={13} /> {other.name}
              </Link>
            );
          })}
        </div>
      </section>
    </PageEnter>
  );
}
