"use client";

import { useState } from "react";
import { Check, Copy, ExternalLink } from "lucide-react";
import { DraftChat } from "@/components/agent";
import { Badge, Button, Drawer, Field, Textarea } from "@/components/ui";
import { useIsApp } from "@/lib/use-app-mode";
import { api } from "@/lib/use-api";
import type { SocialListeningPost } from "@/lib/types";

export function ReplyDrawer({
  post,
  siteId,
  platformLabel,
  onClose,
  onSaved,
}: {
  post: SocialListeningPost | null;
  siteId: string | null;
  platformLabel: (id: string) => string;
  onClose: () => void;
  onSaved: () => void;
}) {
  const isApp = useIsApp();
  const [reply, setReply] = useState("");
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [lastPostId, setLastPostId] = useState<string | null>(null);
  if ((post?.id ?? null) !== lastPostId) {
    setLastPostId(post?.id ?? null);
    setReply(post?.replyText ?? "");
    setCopied(false);
    setError(null);
  }

  const patch = async (body: Record<string, unknown>) => {
    if (!post) return;
    setSaving(true);
    setError(null);
    try {
      await api(`/api/v1/social-listening/posts/${post.id}`, { method: "PATCH", body });
      onSaved();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The change did not save.");
    } finally {
      setSaving(false);
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(reply);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
      if (post && reply.trim() && post.status === "needs_reply") {
        await api(`/api/v1/social-listening/posts/${post.id}`, {
          method: "PATCH",
          body: { status: "drafted", replyText: reply },
        });
        onSaved();
      }
    } catch {}
  };

  return (
    <Drawer
      open={post !== null}
      onClose={onClose}
      title={<h2 className="font-display text-lg text-ink">Draft a reply</h2>}
    >
      {post && (
        <div className="space-y-5">
          <div>
            <div className="flex items-center gap-2 flex-wrap text-xs text-sub">
              <Badge>{platformLabel(post.platform)}</Badge>
              {post.context?.subreddit && <span>r/{post.context.subreddit}</span>}
              {post.authorHandle && <span>@{post.authorHandle}</span>}
            </div>
            <blockquote className="mt-2 border-l-2 border-edge2 pl-3 text-[13px] text-sub">
              {post.title ?? post.text?.slice(0, 300)}
            </blockquote>
          </div>

          {post.suggestedAngle && (
            <div className="rounded-r-lg border-l-2 border-accent bg-accent-soft px-3 py-2.5 text-[13px]">
              <p className="text-[11px] font-medium uppercase tracking-wide text-accent mb-1">
                Meelu&apos;s angle
              </p>
              {post.suggestedAngle}
            </div>
          )}

          <Field
            label="Your reply"
            hint="Meelu suggests the angle — you write the words, then paste them on the platform yourself."
          >
            <Textarea rows={7} value={reply} onChange={(e) => setReply(e.target.value)} />
          </Field>

          {isApp && (
            <div className="rounded-2xl border border-edge bg-panel2/50 p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-faint mb-2">
                Work it out with Meelu
              </p>
              <DraftChat
                scope="compose-reply"
                siteId={siteId}
                intro="Ask Meelu to draft, tighten or check the reply — it has the post, the author and the suggested angle."
                framing={[
                  `A ${platformLabel(post.platform)} post worth engaging with:`,
                  post.authorHandle ? `Author: @${post.authorHandle}` : "",
                  post.title ? `Title: ${post.title}` : "",
                  post.text ? `Text: ${post.text.slice(0, 1500)}` : "",
                  `Link: ${post.url}`,
                  post.keepReason ? `Why it surfaced: ${post.keepReason}` : "",
                  post.suggestedAngle ? `Suggested angle: ${post.suggestedAngle}` : "",
                  reply.trim() ? `My current draft: ${reply}` : "",
                ]
                  .filter(Boolean)
                  .join("\n")}
                placeholder="e.g. Draft a helpful reply that follows the angle"
              />
            </div>
          )}

          {error && <p className="text-sm text-bad">{error}</p>}

          <div className="flex items-center gap-2">
            <Button onClick={() => void copy()} disabled={!reply.trim()}>
              {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copied" : "Copy reply"}
            </Button>
            <Button variant="outline" onClick={() => window.open(post.url, "_blank")}>
              <ExternalLink size={14} /> Open post
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="ml-auto"
              disabled={saving}
              onClick={() => void patch({ status: "replied", replyText: reply || null })}
            >
              Mark replied
            </Button>
          </div>
        </div>
      )}
    </Drawer>
  );
}
