"use client";

import { useState } from "react";
import { Inbox } from "lucide-react";
import { Button, EmptyState, Field, Select, Spinner } from "@demo/components/ui";
import { cn } from "@demo/lib/utils";
import { usePagedApi } from "@demo/lib/use-api";
import type {
  SocialListeningQuery,
  SocialListeningPost,
  SocialListeningInboxStatus,
  SocialListeningSummary,
} from "@demo/lib/types";
import { INTENT_OPTIONS, postsQuery, STATUS_LABEL, type PostSort } from "./lib";
import { PostCard } from "./post-card";

const STATUSES: SocialListeningInboxStatus[] = ["needs_reply", "drafted", "replied", "skipped"];

export function InboxTab({
  summary,
  queries,
  platforms,
  platformLabel,
  onSkip,
  onDraft,
  version,
}: {
  summary: SocialListeningSummary | null;
  queries: SocialListeningQuery[];
  platforms: string[];
  platformLabel: (id: string) => string;
  onSkip: (post: SocialListeningPost) => void;
  onDraft: (post: SocialListeningPost) => void;
  version: number;
}) {
  const [status, setStatus] = useState<SocialListeningInboxStatus>("needs_reply");
  const [platform, setPlatform] = useState("");
  const [intent, setIntent] = useState("");
  const [queryId, setQueryId] = useState("");
  const [sort, setSort] = useState<PostSort>("best");
  const [page, setPage] = useState(1);

  const { data, loading, error } = usePagedApi<SocialListeningPost>(
    postsQuery({
      kind: "topic",
      status,
      platform,
      intent,
      queryId,
      sort,
      page,
      page_size: 25,
      v: version,
    }),
  );
  const posts = data?.data ?? [];

  const counts: Record<SocialListeningInboxStatus, number> = {
    needs_reply: summary?.needsReply ?? 0,
    drafted: summary?.drafted ?? 0,
    replied: summary?.replied ?? 0,
    skipped: summary?.skipped ?? 0,
  };

  return (
    <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
      <div className="w-full lg:w-48 shrink-0 space-y-4">
        <div>
          <p className="text-xs font-medium text-sub mb-1.5">Status</p>
          <div className="flex flex-col gap-0.5 text-[13px]">
            {STATUSES.map((s) => (
              <button
                key={s}
                onClick={() => {
                  setStatus(s);
                  setPage(1);
                }}
                className={cn(
                  "flex items-center justify-between rounded-lg px-2.5 py-1.5 transition-colors cursor-pointer",
                  status === s
                    ? "bg-accent-soft text-accent"
                    : "text-sub hover:text-ink hover:bg-panel2",
                )}
              >
                {STATUS_LABEL[s]}
                <span className={cn("tabular-nums", status === s ? "" : "text-faint")}>
                  {counts[s]}
                </span>
              </button>
            ))}
          </div>
        </div>
        <Field label="Platform">
          <Select value={platform} onChange={(e) => setPlatform(e.target.value)}>
            <option value="">All platforms</option>
            {platforms.map((id) => (
              <option key={id} value={id}>
                {platformLabel(id)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Intent">
          <Select value={intent} onChange={(e) => setIntent(e.target.value)}>
            <option value="">All intents</option>
            {INTENT_OPTIONS.map((i) => (
              <option key={i} value={i}>
                {i.replace(/_/g, " ")}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Query">
          <Select value={queryId} onChange={(e) => setQueryId(e.target.value)}>
            <option value="">All queries</option>
            {queries.map((q) => (
              <option key={q.id} value={q.id}>
                {q.text}
              </option>
            ))}
          </Select>
        </Field>
        <Field label="Sort">
          <Select value={sort} onChange={(e) => setSort(e.target.value as PostSort)}>
            <option value="best">Best match</option>
            <option value="newest">Newest</option>
            <option value="engaged">Most engaged</option>
          </Select>
        </Field>
      </div>

      <div className="flex-1 min-w-0">
        {loading ? (
          <Spinner />
        ) : error ? (
          <p className="text-sm text-bad">{error}</p>
        ) : posts.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title="Nothing here"
            hint={
              status === "needs_reply"
                ? "No posts are waiting on you. Run listening, or loosen the filters."
                : "No posts match the current filters."
            }
          />
        ) : (
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
            {data && data.pagination.total_pages > 1 && (
              <div className="flex items-center justify-between pt-1">
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!data.pagination.has_prev}
                  onClick={() => setPage((p) => p - 1)}
                >
                  Previous
                </Button>
                <span className="text-xs text-faint">
                  Page {data.pagination.page} of {data.pagination.total_pages}
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  disabled={!data.pagination.has_next}
                  onClick={() => setPage((p) => p + 1)}
                >
                  Next
                </Button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
