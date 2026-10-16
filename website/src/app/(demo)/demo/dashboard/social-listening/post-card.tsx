"use client";

import { useState } from "react";
import { ExternalLink } from "lucide-react";
import { Badge, Button, Card } from "@demo/components/ui";
import { cn } from "@demo/lib/utils";
import type { SocialListeningPost, SocialListeningReviewStatus } from "@demo/lib/types";
import { hoursAgo, OUTCOME, type TabKey } from "./lib";

const SNIPPET_CHARS = 280;

export function PostCard({
  post,
  tab,
  line,
  platformLabel,
  fresh,
  busy,
  onStatus,
  onDraft,
}: {
  post: SocialListeningPost;
  tab: TabKey;
  line: string | null;
  platformLabel: (id: string) => string;
  fresh: boolean;
  busy: boolean;
  onStatus: (post: SocialListeningPost, status: SocialListeningReviewStatus) => void;
  onDraft: (post: SocialListeningPost) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const text = post.text ?? "";
  const long = text.length > SNIPPET_CHARS;
  const outcome = OUTCOME[post.status as SocialListeningReviewStatus];
  const stats = [
    post.engagement?.score != null ? `▲ ${post.engagement.score}` : null,
    post.engagement?.comments != null ? `${post.engagement.comments} replies` : null,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Card className={cn("space-y-2 px-4 py-4 sm:px-[18px]", fresh && "border-accent/40")}>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1 text-[12.5px] text-sub">
          {fresh && <Badge tone="accent">New</Badge>}
          <span className="font-semibold text-ink">{platformLabel(post.platform)}</span>
          {post.context?.subreddit && <span>r/{post.context.subreddit}</span>}
          {!post.context?.subreddit && post.authorHandle && <span>@{post.authorHandle}</span>}
          {post.postedAt && (
            <>
              <span>·</span>
              <span>{hoursAgo(post.postedAt)}</span>
            </>
          )}
          {stats && (
            <>
              <span>·</span>
              <span className="tabular-nums">{stats}</span>
            </>
          )}
        </div>
        {tab === "done" && outcome ? (
          <Badge tone={outcome.tone}>
            {outcome.label}
            {post.status === "replied" && post.repliedAt ? ` · ${hoursAgo(post.repliedAt)} ago` : ""}
          </Badge>
        ) : (
          line && (
            <span
              title="The line that found this post"
              className="max-w-[320px] truncate rounded-md bg-panel2 px-2 py-0.5 text-[11.5px] text-sub"
            >
              {line}
            </span>
          )
        )}
      </div>

      {post.title && <h3 className="text-[15px] font-medium text-ink">{post.title}</h3>}
      {text && tab !== "done" && (
        <p className={cn("whitespace-pre-wrap text-[13.5px]", post.title ? "text-sub" : "text-ink")}>
          {expanded || !long ? text : `${text.slice(0, SNIPPET_CHARS)}… `}
          {long && (
            <button
              type="button"
              className="cursor-pointer text-accent hover:underline"
              onClick={() => setExpanded((v) => !v)}
            >
              {expanded ? " show less" : "show more"}
            </button>
          )}
        </p>
      )}
      {tab === "done" && !post.title && text && (
        <p className="text-[13.5px] text-ink">{text.slice(0, SNIPPET_CHARS)}</p>
      )}
      {tab === "to_reply" && post.keepReason && (
        <p className="text-[13px] text-ink">
          <span className="text-sub">Why it surfaced · </span>
          {post.keepReason}
        </p>
      )}
      {tab === "drafted" && post.replyText && (
        <div className="space-y-1 rounded-xl bg-panel2 px-3 py-2.5">
          <p className="text-[11px] font-semibold uppercase tracking-wide text-sub">
            Your draft · copied {hoursAgo(post.updatedAt)} ago
          </p>
          <p className="whitespace-pre-line text-[13.5px] text-ink">{post.replyText}</p>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-1.5 pt-0.5">
        <a
          href={post.url}
          target="_blank"
          rel="noreferrer"
          className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-sub hover:bg-panel2 hover:text-ink"
        >
          <ExternalLink size={13} /> Open post
        </a>
        <span className="flex-1" />
        {tab === "to_reply" && (
          <>
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus(post, "rejected")}>
              Not relevant
            </Button>
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus(post, "skipped")}>
              Skip
            </Button>
            <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus(post, "replied")}>
              Mark done
            </Button>
            <Button size="sm" variant="outline" onClick={() => onDraft(post)}>
              Draft reply
            </Button>
          </>
        )}
        {tab === "drafted" && (
          <>
            <Button size="sm" variant="ghost" onClick={() => onDraft(post)}>
              Edit draft
            </Button>
            <Button size="sm" variant="outline" disabled={busy} onClick={() => onStatus(post, "replied")}>
              Mark replied
            </Button>
          </>
        )}
        {tab === "done" && (
          <Button size="sm" variant="ghost" disabled={busy} onClick={() => onStatus(post, "to_reply")}>
            Move back to To reply
          </Button>
        )}
      </div>
    </Card>
  );
}
