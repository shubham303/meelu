"use client";

import { useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, ChevronLeft, ChevronRight, Sparkles } from "lucide-react";
import { PageEnter } from "@/components/animate";
import { Badge, Button, Drawer, IconButton, Spinner } from "@/components/ui";
import { ChatMarkdown } from "@/components/agent/chat-markdown";
import { cn } from "@/lib/utils";
import { api, useApi } from "@/lib/use-api";
import { useIsApp } from "@/lib/use-app-mode";
import { providerCall, useProviderConnected } from "@/lib/providers";
import type { ContentPiece, ContentPieceSlim, SiteChannel } from "@/lib/types";
import { useAgentTasks } from "../../agent-tasks";
import * as chips from "@/features/prompt-chips/content";
import { ChannelDot } from "../channel-dot";
import { CHANNEL_LABEL, STATUS_LABEL, STATUS_TONE, channelLabel } from "../types";
import { dateTimeLabel, localTimezone, rangeLabel, rollingDays, shiftWeeks } from "./time";
import { WeekGrid } from "./week-grid";

const noopSubscribe = () => () => {};

export default function ContentCalendarPage() {
  const isClient = useSyncExternalStore(noopSubscribe, () => true, () => false);
  const isApp = useIsApp();
  const router = useRouter();
  const { launchTask } = useAgentTasks();

  const { data: channels } = useApi<SiteChannel[]>("/api/v1/content/channels");
  const { data: fetched, loading, refresh } = useApi<ContentPieceSlim[]>(
    "/api/v1/content/pieces?page_size=100",
  );

  const [now, setNow] = useState(() => new Date());
  const [reference, setReference] = useState(() => new Date());
  const [picked, setPicked] = useState<Set<string>>(() => new Set());
  const [pendingMoves, setPendingMoves] = useState<Record<string, string>>({});
  const [err, setErr] = useState<string | null>(null);
  const [openPost, setOpenPost] = useState<ContentPieceSlim | null>(null);
  const { data: openPiece } = useApi<ContentPiece>(
    openPost ? `/api/v1/content/pieces/${openPost.id}` : null,
  );

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 60_000);
    return () => clearInterval(id);
  }, []);

  const enabled = useMemo(() => (channels ?? []).filter((c) => c.enabled), [channels]);
  const timezone = enabled[0]?.timezone ?? localTimezone();
  const days = useMemo(() => rollingDays(reference, timezone), [reference, timezone]);

  const pieces = useMemo(() => {
    const list = (fetched ?? [])
      .filter((p) => p.scheduledAt)
      .filter((p) => picked.size === 0 || picked.has(p.channelKey))
      .map((p) => (pendingMoves[p.id] ? { ...p, scheduledAt: pendingMoves[p.id] } : p));
    return list.sort(
      (a, b) => new Date(a.scheduledAt ?? 0).getTime() - new Date(b.scheduledAt ?? 0).getTime(),
    );
  }, [fetched, pendingMoves, picked]);

  const socialReady = useProviderConnected("social");
  const reconciledRef = useRef(false);
  useEffect(() => {
    if (reconciledRef.current || !isApp || !socialReady) return;
    reconciledRef.current = true;
    void providerCall<{ reconciled: number }>("social_reconcile")
      .then((r) => (r.reconciled > 0 ? refresh() : undefined))
      .catch(() => {});
  }, [isApp, socialReady, refresh]);

  function clearMove(id: string) {
    setPendingMoves((current) => {
      if (!(id in current)) return current;
      const next = { ...current };
      delete next[id];
      return next;
    });
  }

  async function move(p: ContentPieceSlim, at: Date) {
    setErr(null);
    setPendingMoves((current) => ({ ...current, [p.id]: at.toISOString() }));
    try {
      if (p.status === "scheduled") {
        await providerCall("social_reschedule", { pieceId: p.id, scheduledAt: at.toISOString() });
      } else {
        await api(`/api/v1/content/pieces/${p.id}`, {
          method: "PATCH",
          body: { scheduledAt: at.toISOString() },
        });
      }
      await refresh();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Could not move that piece");
    } finally {
      clearMove(p.id);
    }
  }

  const openAsk = () => {
    launchTask({
      title: "Ask — Content",
      endpoint: "/api/agent/ask-content",
      emptyHint:
        "Ask about what is on the calendar, or say what you want drafted. Nothing is scheduled or published from here.",
      suggestions: chips.ask,
      draft: {
        week: `${rangeLabel(days, timezone)} (${timezone})`,
        channels: enabled.map((c) => c.channelKey).join(", "),
      },
      onCreated: async () => {
        await refresh();
      },
    });
  };

  if (!isClient) {
    return (
      <PageEnter>
        <Spinner />
      </PageEnter>
    );
  }

  return (
    <PageEnter>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <Link
            href="/dashboard/content"
            className="inline-flex items-center gap-1.5 text-sm text-sub transition-colors hover:text-ink"
          >
            <ArrowLeft size={14} /> Content
          </Link>
          <h1 className="mt-1 font-display text-2xl text-ink">Calendar</h1>
          <p className="mt-1 text-sm text-sub">
            Every piece with a slot, across website and social. Drag to reschedule; click to open.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => setReference(shiftWeeks(days, -1, timezone))} aria-label="Previous week">
            <ChevronLeft size={14} />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setReference(new Date())}>
            Today
          </Button>
          <Button variant="outline" size="sm" onClick={() => setReference(shiftWeeks(days, 1, timezone))} aria-label="Next week">
            <ChevronRight size={14} />
          </Button>
          <span className="ml-1 text-sm font-medium text-ink">{rangeLabel(days, timezone)}</span>
          {isApp && (
            <IconButton
              title="Ask about the calendar"
              aria-label="Ask about the calendar"
              className="border border-accent/30 bg-accent-soft text-accent hover:bg-accent-soft hover:text-accent"
              onClick={openAsk}
            >
              <Sparkles size={16} />
            </IconButton>
          )}
        </div>
      </div>

      <div className="mb-4 flex flex-wrap items-center gap-2">
        {enabled.map((c) => {
          const on = picked.size === 0 || picked.has(c.channelKey);
          return (
            <button
              key={c.channelKey}
              type="button"
              aria-pressed={picked.has(c.channelKey)}
              onClick={() =>
                setPicked((current) => {
                  const next = new Set(current);
                  if (next.has(c.channelKey)) next.delete(c.channelKey);
                  else next.add(c.channelKey);
                  return next;
                })
              }
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors cursor-pointer",
                picked.has(c.channelKey)
                  ? "border-accent/40 bg-accent-soft text-accent"
                  : "border-edge bg-panel text-sub hover:text-ink",
                !on && "opacity-50",
              )}
            >
              <ChannelDot channelKey={c.channelKey} size={14} />
              {c.label}
            </button>
          );
        })}
        {picked.size > 0 && (
          <button
            type="button"
            onClick={() => setPicked(new Set())}
            className="text-xs text-faint hover:text-ink cursor-pointer"
          >
            Show all
          </button>
        )}
        <Link href="/dashboard/content/channels" className="ml-auto text-xs text-accent hover:underline">
          Channel guidelines →
        </Link>
      </div>

      {err && <p className="mb-3 text-sm text-bad">{err}</p>}

      {loading && pieces.length === 0 ? (
        <Spinner />
      ) : (
        <WeekGrid
          days={days}
          timezone={timezone}
          posts={pieces}
          now={now}
          channelLabels={CHANNEL_LABEL}
          onOpen={setOpenPost}
          onCreate={() => router.push("/dashboard/content")}
          onMove={move}
        />
      )}

      <Drawer
        open={openPost !== null}
        onClose={() => setOpenPost(null)}
        title={<p className="font-display text-lg text-ink">{openPost?.title}</p>}
        actions={
          openPost && (
            <Button size="sm" variant="outline" onClick={() => router.push(`/dashboard/content/${openPost.id}`)}>
              Open in editor
            </Button>
          )
        }
      >
        {openPost && (
          <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2 text-xs text-sub">
              <ChannelDot channelKey={openPost.channelKey} size={14} />
              <span>{channelLabel(openPost.channelKey)}</span>
              <Badge tone={STATUS_TONE[openPost.status]}>{STATUS_LABEL[openPost.status]}</Badge>
              {openPost.scheduledAt && (
                <span className="text-faint">
                  {dateTimeLabel(openPost.scheduledAt, timezone)} ({timezone})
                </span>
              )}
            </div>
            {openPiece ? (
              openPiece.bodyMarkdown.trim() ? (
                <div className="text-sm leading-relaxed text-ink">
                  <ChatMarkdown text={openPiece.bodyMarkdown} />
                </div>
              ) : (
                <p className="text-sm text-faint">Nothing written yet.</p>
              )
            ) : (
              <Spinner />
            )}
          </div>
        )}
      </Drawer>
    </PageEnter>
  );
}
