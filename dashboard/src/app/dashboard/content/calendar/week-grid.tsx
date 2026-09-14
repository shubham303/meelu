"use client";

import { useMemo, useState } from "react";
import { AlertCircle, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { ContentPieceSlim } from "@/lib/types";
import { STATUS_BAR } from "../types";
import { isOverdue } from "./status";
import {
  cellInstant,
  dayLabel,
  hourLabel,
  sameDay,
  slotKey,
  slotKeyOf,
  timeLabel,
  zonedParts,
  type CivilDay,
} from "./time";

const HOURS = Array.from({ length: 24 }, (_, i) => i);

export function WeekGrid({
  days,
  timezone,
  posts,
  now,
  channelLabels,
  onOpen,
  onCreate,
  onMove,
}: {
  days: CivilDay[];
  timezone: string;
  posts: ContentPieceSlim[];
  now: Date;
  channelLabels: Record<string, string>;
  onOpen: (post: ContentPieceSlim) => void;
  onCreate: (at: Date) => void;
  onMove: (post: ContentPieceSlim, at: Date) => void;
}) {
  const [dragId, setDragId] = useState<string | null>(null);
  const [hover, setHover] = useState<string | null>(null);

  const bySlot = useMemo(() => {
    const map = new Map<string, ContentPieceSlim[]>();
    for (const post of posts) {
      if (!post.scheduledAt) continue;
      const key = slotKeyOf(post.scheduledAt, timezone);
      const bucket = map.get(key);
      if (bucket) bucket.push(post);
      else map.set(key, [post]);
    }
    return map;
  }, [posts, timezone]);

  const nowParts = zonedParts(now, timezone);
  const nowMinute = nowParts.minute;

  return (
    <div className="bg-panel border border-edge rounded-2xl overflow-hidden">
      <div className="overflow-auto max-h-[calc(100vh-15rem)]">
        <div
          className="grid min-w-[52rem]"
          style={{ gridTemplateColumns: "4.25rem repeat(7, minmax(0, 1fr))" }}
        >
          <div className="sticky top-0 z-20 bg-panel border-b border-edge" />
          {days.map((day) => {
            const label = dayLabel(day, timezone);
            const isToday = sameDay(day, nowParts);
            return (
              <div
                key={`${day.year}-${day.month}-${day.day}`}
                className="sticky top-0 z-20 bg-panel border-b border-l border-edge px-2 py-2.5 text-center"
              >
                <p
                  className={cn(
                    "text-[11px] uppercase tracking-wide",
                    isToday ? "text-accent" : "text-sub",
                  )}
                >
                  {label.weekday}
                </p>
                <p
                  className={cn(
                    "text-sm mt-0.5 inline-flex items-center gap-1.5",
                    isToday ? "text-accent font-medium" : "text-ink",
                  )}
                >
                  {label.date}
                  {isToday && <span className="size-1.5 rounded-full bg-accent" />}
                </p>
              </div>
            );
          })}

          {HOURS.map((hour) => (
            <HourRow
              key={hour}
              hour={hour}
              days={days}
              timezone={timezone}
              now={now}
              nowParts={nowParts}
              nowMinute={nowMinute}
              bySlot={bySlot}
              dragId={dragId}
              hover={hover}
              channelLabels={channelLabels}
              setHover={setHover}
              setDragId={setDragId}
              onOpen={onOpen}
              onCreate={onCreate}
              onMove={onMove}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function HourRow({
  hour,
  days,
  timezone,
  now,
  nowParts,
  nowMinute,
  bySlot,
  dragId,
  hover,
  channelLabels,
  setHover,
  setDragId,
  onOpen,
  onCreate,
  onMove,
}: {
  hour: number;
  days: CivilDay[];
  timezone: string;
  now: Date;
  nowParts: ReturnType<typeof zonedParts>;
  nowMinute: number;
  bySlot: Map<string, ContentPieceSlim[]>;
  dragId: string | null;
  hover: string | null;
  channelLabels: Record<string, string>;
  setHover: (key: string | null) => void;
  setDragId: (id: string | null) => void;
  onOpen: (post: ContentPieceSlim) => void;
  onCreate: (at: Date) => void;
  onMove: (post: ContentPieceSlim, at: Date) => void;
}) {
  return (
    <>
      <div className="border-b border-edge px-2 py-1 text-right">
        <span className="text-[11px] text-faint">{hourLabel(hour)}</span>
      </div>
      {days.map((day) => {
        const key = slotKey(day, hour);
        const at = cellInstant(day, hour, timezone);
        const past = at.getTime() + 3_600_000 <= now.getTime();
        const items = bySlot.get(key) ?? [];
        const isNowCell = sameDay(day, nowParts) && nowParts.hour === hour;
        const dropping = hover === key && dragId !== null;

        return (
          <div
            key={key}
            onDragOver={(e) => {
              if (past || !dragId) return;
              e.preventDefault();
              if (hover !== key) setHover(key);
            }}
            onDragLeave={() => {
              if (hover === key) setHover(null);
            }}
            onDrop={(e) => {
              e.preventDefault();
              setHover(null);
              const id = e.dataTransfer.getData("text/plain");
              const post = [...bySlot.values()].flat().find((p) => p.id === id);
              setDragId(null);
              if (!post || past) return;
              if (new Date(post.scheduledAt ?? "").getTime() === at.getTime()) return;
              onMove(post, at);
            }}
            className={cn(
              "group relative border-b border-l border-edge min-h-14 p-1",
              past && "bg-panel2/50",
              dropping && "bg-accent-soft ring-1 ring-inset ring-accent",
            )}
          >
            {isNowCell && (
              <div
                className="absolute left-0 right-0 z-10 pointer-events-none"
                style={{ top: `${(nowMinute / 60) * 100}%` }}
                aria-hidden
              >
                <div className="h-px bg-accent" />
                <div className="absolute -left-0.5 -top-1 size-2 rounded-full bg-accent" />
              </div>
            )}

            <div className="relative z-[1] space-y-1">
              {items.map((post) => (
                <PostChip
                  key={post.id}
                  post={post}
                  timezone={timezone}
                  overdue={isOverdue(post, now)}
                  channelLabel={channelLabels[post.channelKey] ?? post.channelKey}
                  onOpen={onOpen}
                  onDragStart={() => setDragId(post.id)}
                  onDragEnd={() => {
                    setDragId(null);
                    setHover(null);
                  }}
                />
              ))}
            </div>

            {!past && items.length === 0 && (
              <button
                onClick={() => onCreate(at)}
                aria-label={`Add a post at ${hourLabel(hour)}`}
                className="absolute inset-0 z-[2] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer"
              >
                <span className="inline-flex items-center justify-center rounded-lg bg-accent-soft text-accent size-6">
                  <Plus size={14} />
                </span>
              </button>
            )}
          </div>
        );
      })}
    </>
  );
}

function PostChip({
  post,
  timezone,
  overdue,
  channelLabel,
  onOpen,
  onDragStart,
  onDragEnd,
}: {
  post: ContentPieceSlim;
  timezone: string;
  overdue: boolean;
  channelLabel: string;
  onOpen: (post: ContentPieceSlim) => void;
  onDragStart: () => void;
  onDragEnd: () => void;
}) {
  return (
    <div
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/plain", post.id);
        e.dataTransfer.effectAllowed = "move";
        onDragStart();
      }}
      onDragEnd={onDragEnd}
      onClick={() => onOpen(post)}
      title={overdue ? `Overdue — ${post.title}` : post.title}
      className={cn(
        "cursor-pointer rounded-md border border-l-2 px-1.5 py-1 transition-colors",
        overdue
          ? "border-bad/40 border-l-bad bg-bad/10 hover:border-bad/60"
          : cn("border-edge bg-panel2 hover:border-edge2", STATUS_BAR[post.status]),
        post.status === "failed" && "opacity-70",
      )}
    >
      <p
        className={cn(
          "text-[11px] leading-tight truncate",
          overdue ? "text-bad font-medium" : "text-ink",
        )}
      >
        {post.title}
      </p>
      <p
        className={cn(
          "text-[10px] truncate mt-0.5 flex items-center gap-1",
          overdue ? "text-bad/80" : "text-faint",
        )}
      >
        {overdue && <AlertCircle size={9} className="shrink-0" />}
        {timeLabel(post.scheduledAt ?? "", timezone)} · {channelLabel}
      </p>
    </div>
  );
}
