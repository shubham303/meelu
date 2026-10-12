"use client";

import { useState } from "react";
import { ExternalLink, MessageCircle } from "lucide-react";
import { Badge, Button, Card } from "@demo/components/ui";
import { cn, formatRelative } from "@demo/lib/utils";
import type { SocialListeningPost } from "@demo/lib/types";
import { CLASS_LABEL, CLASS_TONE, INTENT_TONE, sentimentTone } from "./lib";

export function PostCard({
  post,
  platformLabel,
  onSkip,
  onDraft,
  busy,
}: {
  post: SocialListeningPost;
  platformLabel: (id: string) => string;
  onSkip: (post: SocialListeningPost) => void;
  onDraft: (post: SocialListeningPost) => void;
  busy?: boolean;
}) {
  const [expanded, setExpanded] = useState(false);
  const text = post.text ?? "";
  const truncated = text.length > 240;
  const snippet = expanded ? text : text.slice(0, 240);
  const negative = post.sentiment === "negative" && post.kind === "brand";
  const replied = post.status === "replied";

  return (
    <Card className={cn(negative && "border-bad/30", replied && "opacity-85")}>
      <div className="flex items-center gap-2 flex-wrap text-xs text-sub">
        <Badge>{platformLabel(post.platform)}</Badge>
        {post.context?.subreddit && <span>r/{post.context.subreddit}</span>}
        {post.authorHandle && <span>@{post.authorHandle}</span>}
        {post.postedAt && <span>{formatRelative(post.postedAt)}</span>}
        {post.engagement?.score != null && <span>▲ {post.engagement.score}</span>}
        {post.engagement?.comments != null && (
          <span className="inline-flex items-center gap-0.5">
            <MessageCircle size={11} /> {post.engagement.comments}
          </span>
        )}
      </div>

      {post.title && <p className="mt-2 font-medium text-ink">{post.title}</p>}
      {text && (
        <p className="mt-1 text-sm text-sub whitespace-pre-wrap">
          {snippet}
          {truncated && !expanded && "… "}
          {truncated && (
            <button
              type="button"
              className="text-accent hover:underline cursor-pointer"
              onClick={() => setExpanded((v) => !v)}
            >
              {expanded ? "show less" : "show more"}
            </button>
          )}
        </p>
      )}
      {post.keepReason && <p className="mt-2 text-sm italic text-ink">Kept: {post.keepReason}</p>}

      {post.suggestedAngle && !replied && (
        <div
          className={cn(
            "mt-3 rounded-r-lg border-l-2 px-3 py-2.5 text-[13px]",
            negative ? "border-bad bg-bad/5" : "border-accent bg-accent-soft",
          )}
        >
          <p
            className={cn(
              "text-[11px] font-medium uppercase tracking-wide mb-1",
              negative ? "text-bad" : "text-accent",
            )}
          >
            Suggested angle
          </p>
          {post.suggestedAngle}
        </div>
      )}

      {replied && (
        <div className="mt-3 rounded-r-lg border-l-2 border-good bg-good/5 px-3 py-2 text-[13px] text-good">
          ✓ Replied {post.repliedAt ? formatRelative(post.repliedAt) : ""}
          {post.replyText ? ` — “${post.replyText.slice(0, 120)}${post.replyText.length > 120 ? "…" : ""}”` : ""}
        </div>
      )}

      <div className="mt-3 flex items-center gap-2 flex-wrap">
        {post.intent && (
          <Badge tone={INTENT_TONE[post.intent] ?? "neutral"}>{post.intent.replace(/_/g, " ")}</Badge>
        )}
        {post.sentiment && <Badge tone={sentimentTone(post.sentiment)}>{post.sentiment}</Badge>}
        {post.classes.map((c) => (
          <Badge key={c} tone={CLASS_TONE[c]}>
            {CLASS_LABEL[c]}
          </Badge>
        ))}
        {post.kind === "brand" && <Badge tone="accent">brand mention</Badge>}
        {post.kind === "competitor" &&
          post.matchedTargets.map((t) => (
            <Badge key={t} tone="warn">
              {t}
            </Badge>
          ))}
        {post.kind === "topic" && post.similarity != null && (
          <Badge>{Math.round(post.similarity * 100)}% close</Badge>
        )}
        <div
          className="h-1.5 w-20 rounded-full bg-panel2 overflow-hidden"
          title={`Match ${((post.compositeScore ?? 0) * 100).toFixed(0)}%`}
        >
          <div
            className="h-full rounded-full bg-accent"
            style={{ width: `${Math.round(Math.min(1, post.compositeScore ?? 0) * 100)}%` }}
          />
        </div>
        <div className="ml-auto flex items-center gap-1.5">
          <Button size="sm" variant="ghost" onClick={() => window.open(post.url, "_blank")}>
            <ExternalLink size={13} /> Open
          </Button>
          {!replied && post.status !== "skipped" && (
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => onSkip(post)}>
              Skip
            </Button>
          )}
          {!replied && (
            <Button size="sm" variant="outline" onClick={() => onDraft(post)}>
              Draft a reply
            </Button>
          )}
        </div>
      </div>
    </Card>
  );
}
