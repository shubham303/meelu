"use client";

import { useState } from "react";
import { Megaphone, Swords } from "lucide-react";
import { Badge, Card, EmptyState, Select, Spinner } from "@/components/ui";
import { cn } from "@/lib/utils";
import { usePagedApi } from "@/lib/use-api";
import type {
  SocialListeningClass,
  SocialListeningPost,
  SocialListeningSummary,
  SocialListeningTarget,
} from "@/lib/types";
import { postsQuery } from "./lib";
import { PostCard } from "./post-card";

function ClassTile({
  label,
  count,
  sub,
  tone,
  selected,
  onClick,
}: {
  label: string;
  count: number;
  sub: string;
  tone: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "rounded-2xl border border-edge bg-panel px-3.5 py-3 text-left flex flex-col gap-0.5 cursor-pointer transition-shadow",
        selected && "border-accent shadow-[0_0_0_2px_#2563eb4d]",
      )}
    >
      <span className={cn("text-[11px] font-medium uppercase tracking-wide", tone)}>{label}</span>
      <span className="font-display text-[22px] text-ink tabular-nums">{count}</span>
      <span className="text-xs text-faint">{sub}</span>
    </button>
  );
}

function MentionList({
  posts,
  loading,
  error,
  emptyTitle,
  emptyHint,
  emptyIcon,
  platformLabel,
  onSkip,
  onDraft,
}: {
  posts: SocialListeningPost[];
  loading: boolean;
  error: string | null;
  emptyTitle: string;
  emptyHint: string;
  emptyIcon: typeof Megaphone;
  platformLabel: (id: string) => string;
  onSkip: (post: SocialListeningPost) => void;
  onDraft: (post: SocialListeningPost) => void;
}) {
  if (loading) return <Spinner />;
  if (error) return <p className="text-sm text-bad">{error}</p>;
  if (posts.length === 0)
    return <EmptyState icon={emptyIcon} title={emptyTitle} hint={emptyHint} />;
  return (
    <div className="space-y-3">
      {posts.map((p) => (
        <PostCard
          key={p.id}
          post={p}
          platformLabel={platformLabel}
          onSkip={onSkip}
          onDraft={onDraft}
        />
      ))}
    </div>
  );
}

export function BrandMentionsTab({
  summary,
  platformLabel,
  onSkip,
  onDraft,
  version,
}: {
  summary: SocialListeningSummary | null;
  platformLabel: (id: string) => string;
  onSkip: (post: SocialListeningPost) => void;
  onDraft: (post: SocialListeningPost) => void;
  version: number;
}) {
  const [cls, setCls] = useState<SocialListeningClass | null>(null);
  const { data, loading, error } = usePagedApi<SocialListeningPost>(
    postsQuery({ kind: "brand", cls, sort: "newest", page_size: 50, v: version }),
  );
  const posts = data?.data ?? [];
  const mc = summary?.mentionClasses;

  return (
    <div>
      <div className="grid gap-3 mb-4 [grid-template-columns:repeat(auto-fit,minmax(150px,1fr))]">
        <ClassTile
          label="All mentions"
          count={summary?.brandMentions ?? 0}
          sub="everything naming you"
          tone="text-sub"
          selected={cls === null}
          onClick={() => setCls(null)}
        />
        <ClassTile
          label="Praise"
          count={mc?.praise ?? 0}
          sub="worth thanking or reposting"
          tone="text-good"
          selected={cls === "praise"}
          onClick={() => setCls("praise")}
        />
        <ClassTile
          label="Complaint"
          count={mc?.complaint ?? 0}
          sub="answer these first"
          tone="text-bad"
          selected={cls === "complaint"}
          onClick={() => setCls("complaint")}
        />
        <ClassTile
          label="Feature request"
          count={mc?.featureRequest ?? 0}
          sub="signal for the roadmap"
          tone="text-warn"
          selected={cls === "feature_request"}
          onClick={() => setCls("feature_request")}
        />
        <ClassTile
          label="Question"
          count={mc?.question ?? 0}
          sub="easy wins"
          tone="text-sub"
          selected={cls === "question"}
          onClick={() => setCls("question")}
        />
      </div>

      {summary && (
        <Card className="mb-4 flex items-center gap-4 flex-wrap">
          <p className="text-xs font-medium uppercase tracking-wide text-faint">Sentiment</p>
          <div className="flex gap-1.5">
            <Badge tone="good">positive {summary.sentiment.positive}</Badge>
            <Badge>neutral {summary.sentiment.neutral}</Badge>
            <Badge tone="bad">negative {summary.sentiment.negative}</Badge>
          </div>
          <p className="text-xs text-faint">
            For deeper analysis, download the data and ask the Analytics desk.
          </p>
        </Card>
      )}

      <MentionList
        posts={posts}
        loading={loading}
        error={error}
        emptyTitle="No brand mentions"
        emptyHint="Nobody has named the brand in the kept posts yet. Check the brand names on the Queries & setup tab."
        emptyIcon={Megaphone}
        platformLabel={platformLabel}
        onSkip={onSkip}
        onDraft={onDraft}
      />
    </div>
  );
}

export function CompetitorMentionsTab({
  summary,
  targets,
  platformLabel,
  onSkip,
  onDraft,
  version,
}: {
  summary: SocialListeningSummary | null;
  targets: SocialListeningTarget[];
  platformLabel: (id: string) => string;
  onSkip: (post: SocialListeningPost) => void;
  onDraft: (post: SocialListeningPost) => void;
  version: number;
}) {
  const [target, setTarget] = useState("");
  const [cls, setCls] = useState<SocialListeningClass | null>(null);
  const { data, loading, error } = usePagedApi<SocialListeningPost>(
    postsQuery({ kind: "competitor", target, sort: "newest", page_size: 100, v: version }),
  );
  const posts = data?.data ?? [];
  const shown = cls ? posts.filter((p) => p.classes.includes(cls)) : posts;
  const competitors = targets.filter((t) => t.kind === "competitor");

  const countFor = (c: SocialListeningClass) => posts.filter((p) => p.classes.includes(c)).length;

  return (
    <div>
      <div className="flex items-center gap-3 flex-wrap mb-4">
        <Select value={target} onChange={(e) => setTarget(e.target.value)} className="w-auto">
          <option value="">All competitors</option>
          {competitors.map((t) => (
            <option key={t.id} value={t.name}>
              {t.name}
            </option>
          ))}
        </Select>
        <p className="text-xs text-faint">Manage the competitor list on the Queries &amp; setup tab.</p>
      </div>

      <div className="grid gap-3 mb-4 [grid-template-columns:repeat(auto-fit,minmax(150px,1fr))]">
        <ClassTile
          label="All mentions"
          count={target ? posts.length : (summary?.competitorMentions ?? posts.length)}
          sub="everything naming them"
          tone="text-sub"
          selected={cls === null}
          onClick={() => setCls(null)}
        />
        <ClassTile
          label="Switch opportunity"
          count={countFor("switch_opportunity")}
          sub="unhappy or comparing"
          tone="text-accent"
          selected={cls === "switch_opportunity"}
          onClick={() => setCls("switch_opportunity")}
        />
        <ClassTile
          label="Complaint about them"
          count={countFor("complaint")}
          sub="their weak spots"
          tone="text-bad"
          selected={cls === "complaint"}
          onClick={() => setCls("complaint")}
        />
        <ClassTile
          label="Praise for them"
          count={countFor("praise")}
          sub="market signal"
          tone="text-good"
          selected={cls === "praise"}
          onClick={() => setCls("praise")}
        />
      </div>

      <MentionList
        posts={shown}
        loading={loading}
        error={error}
        emptyTitle="No competitor mentions"
        emptyHint="No kept post names a watched competitor yet. Add competitors on the Queries & setup tab."
        emptyIcon={Swords}
        platformLabel={platformLabel}
        onSkip={onSkip}
        onDraft={onDraft}
      />
    </div>
  );
}
