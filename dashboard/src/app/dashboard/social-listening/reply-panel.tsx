"use client";

import { useState } from "react";
import { Check, Copy, ExternalLink, Sparkles } from "lucide-react";
import { Button, Drawer, Spinner } from "@/components/ui";
import { streamTurn } from "@/components/agent/bridge";
import { useIsApp } from "@/lib/use-app-mode";
import { api } from "@/lib/use-api";
import type { SocialListeningPost } from "@/lib/types";
import { hoursAgo } from "./lib";

export function ReplyPanel({
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
  const [ask, setAsk] = useState("");
  const [thinking, setThinking] = useState(false);
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastPostId, setLastPostId] = useState<string | null>(null);

  if ((post?.id ?? null) !== lastPostId) {
    setLastPostId(post?.id ?? null);
    setReply(post?.replyText ?? "");
    setAsk("");
    setCopied(false);
    setError(null);
  }

  const patch = async (body: Record<string, unknown>, close: boolean) => {
    if (!post) return;
    setError(null);
    try {
      await api(`/api/v1/social-listening/posts/${post.id}`, { method: "PATCH", body });
      onSaved();
      if (close) onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "The change did not save.");
    }
  };

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(reply);
    } catch {
      setError("Copying was blocked. Select the text and copy it yourself.");
      return;
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
    await patch({ status: "drafted", replyText: reply }, true);
  };

  const rewrite = async () => {
    const instruction = ask.trim();
    if (!post || !instruction || thinking) return;
    setThinking(true);
    setError(null);
    const message = [
      `A ${platformLabel(post.platform)} post worth replying to:`,
      post.authorHandle ? `Author: @${post.authorHandle}` : "",
      post.title ? `Title: ${post.title}` : "",
      post.text ? `Text: ${post.text.slice(0, 1500)}` : "",
      `Link: ${post.url}`,
      post.keepReason ? `Why it surfaced: ${post.keepReason}` : "",
      post.suggestedAngle ? `Suggested angle: ${post.suggestedAngle}` : "",
      reply.trim() ? `My current draft:\n${reply}` : "I have no draft yet.",
      "",
      `Request: ${instruction}`,
      "Answer with only the full reply text, ready to paste. No preamble, no quotes.",
    ]
      .filter(Boolean)
      .join("\n");
    const res = await streamTurn({ action: "compose-reply", message, siteId }).result;
    setThinking(false);
    if (!res.ok || !res.text.trim()) {
      setError(res.error ?? "Meelu did not return a reply. Try again.");
      return;
    }
    setReply(res.text.trim());
    setAsk("");
  };

  return (
    <Drawer
      open={post !== null}
      onClose={onClose}
      title={<h2 className="font-display text-lg text-ink">Draft a reply</h2>}
    >
      {post && (
        <div className="space-y-5">
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[12.5px] text-sub">
              <span className="font-semibold text-ink">{platformLabel(post.platform)}</span>
              {post.context?.subreddit && <span>r/{post.context.subreddit}</span>}
              {post.authorHandle && <span>@{post.authorHandle}</span>}
              {post.postedAt && <span>· {hoursAgo(post.postedAt)}</span>}
            </div>
            {post.title && <h3 className="text-base font-medium text-ink">{post.title}</h3>}
            {post.text && <p className="whitespace-pre-wrap text-[13.5px] text-sub">{post.text.slice(0, 1200)}</p>}
          </div>

          {post.suggestedAngle && (
            <p className="rounded-xl bg-accent-soft px-3 py-2.5 text-[13.5px] text-ink">
              <span className="font-medium text-accent">Angle · </span>
              {post.suggestedAngle}
            </p>
          )}

          <div className="space-y-2">
            <label htmlFor="sl-reply" className="text-[13px] font-medium text-ink">
              Your reply
            </label>
            <textarea
              id="sl-reply"
              rows={9}
              value={reply}
              onChange={(e) => setReply(e.target.value)}
              className="w-full resize-y rounded-xl border border-edge2 bg-panel px-3.5 py-3 text-sm leading-relaxed text-ink focus:border-accent focus:outline-none"
            />
            {isApp && (
              <div className="flex items-center gap-2">
                {thinking ? <Spinner className="h-4 w-4 py-0" /> : <Sparkles size={16} className="text-accent" />}
                <input
                  aria-label="Ask Meelu to change the reply"
                  placeholder="Ask Meelu: draft it, make it shorter, less salesy…"
                  value={ask}
                  disabled={thinking}
                  onChange={(e) => setAsk(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && void rewrite()}
                  className="h-9 min-w-0 flex-1 rounded-lg border border-edge2 bg-panel2 px-3 text-[13px] text-ink placeholder:text-faint focus:border-accent focus:outline-none"
                />
              </div>
            )}
          </div>

          {error && <p className="text-sm text-bad">{error}</p>}

          <div className="flex flex-wrap items-center gap-2 border-t border-edge pt-4">
            <Button onClick={() => void copy()} disabled={!reply.trim()}>
              {copied ? <Check size={14} /> : <Copy size={14} />} {copied ? "Copied" : "Copy reply"}
            </Button>
            <a
              href={post.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 rounded-lg border border-edge2 px-3.5 py-2 text-sm font-medium text-ink hover:bg-panel2"
            >
              <ExternalLink size={14} /> Open post
            </a>
            <span className="flex-1" />
            <Button
              variant="ghost"
              size="sm"
              onClick={() => void patch({ status: "replied", replyText: reply.trim() || null }, true)}
            >
              Mark replied
            </Button>
          </div>
          <p className="text-xs text-sub">Copy reply moves the post to Drafted. Post it yourself, then mark it replied.</p>
        </div>
      )}
    </Drawer>
  );
}
