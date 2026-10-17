"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Plus } from "lucide-react";
import { apiPaged, useCurrentSite } from "@/lib/use-api";
import { cn } from "@/lib/utils";
import { CHATS_PAGE_SIZE, chatHref, onChatsChanged, startNewChat } from "@/features/analytics/chats";
import type { AnalyticsChatSummary } from "@/lib/types";

const NEW_CHAT = "/dashboard/analytics";

export function AnalyticsTree({ canChat }: { canChat: boolean }) {
  const pathname = usePathname();
  const siteId = useCurrentSite();
  const [chats, setChats] = useState<AnalyticsChatSummary[]>([]);
  const [page, setPage] = useState(1);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (next: number) => {
    setLoading(true);
    try {
      const res = await apiPaged<AnalyticsChatSummary>(
        `/api/v1/analytics/chats?page=${next}&page_size=${CHATS_PAGE_SIZE}`,
      );
      setChats((prev) => {
        if (next === 1) return res.data;
        const seen = new Set(prev.map((c) => c.id));
        return [...prev, ...res.data.filter((c) => !seen.has(c.id))];
      });
      setHasMore(res.pagination.has_next);
      setPage(next);
    } catch {
      if (next === 1) setChats([]);
      setHasMore(false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void load(1);
  }, [load, siteId]);

  useEffect(() => onChatsChanged(() => void load(1)), [load]);

  const row = (href: string, active: boolean) =>
    cn(
      "flex items-center gap-2 truncate rounded-md px-2 py-1.5 text-[13px] transition-colors",
      active ? "bg-panel2 text-ink" : "text-sub hover:bg-panel2 hover:text-ink",
    );

  return (
    <div className="ml-[1.4rem] mt-0.5 mb-1 space-y-0.5 border-l border-edge pl-2">
      {canChat && (
        <Link href={NEW_CHAT} onClick={startNewChat} className={row(NEW_CHAT, pathname === NEW_CHAT)}>
          <Plus size={13} className="shrink-0" /> New chat
        </Link>
      )}
      {chats.map((chat) => (
        <Link
          key={chat.id}
          href={chatHref(chat.id)}
          title={chat.title}
          className={row(chatHref(chat.id), pathname === chatHref(chat.id))}
        >
          <span className="truncate">{chat.title}</span>
        </Link>
      ))}
      {hasMore && (
        <button
          type="button"
          disabled={loading}
          onClick={() => void load(page + 1)}
          className="w-full cursor-pointer rounded-md px-2 py-1 text-left text-[12px] text-faint transition-colors hover:text-ink disabled:opacity-50"
        >
          {loading ? "Loading…" : "Show more"}
        </button>
      )}
    </div>
  );
}
