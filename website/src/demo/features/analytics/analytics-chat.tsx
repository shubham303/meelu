"use client";

import { useState, useSyncExternalStore } from "react";
import { BookmarkPlus } from "lucide-react";
import { Card } from "@demo/components/ui";
import { usePinnedSite } from "@demo/components/agent";
import { AgentChat, type AgentChatItem } from "@demo/components/agent/agent-chat";
import { PermissionPrompt } from "@demo/components/agent/permission-prompt";
import { ask as askChips, SAVE_REPORT_PROMPT } from "@demo/features/prompt-chips/analytics";
import { openChatSession, type Decision } from "./chat-session";

export function AnalyticsChatView({ chatId, canChat }: { chatId?: string; canChat: boolean }) {
  const siteId = usePinnedSite();
  const [session] = useState(() => openChatSession(chatId, siteId));
  const { chat, items, hasEarlier, loading, busy, error } = useSyncExternalStore(
    session.subscribe,
    session.getState,
    session.getState,
  );

  const send = (message: string, displayAs?: string) => void session.send(message, displayAs);
  const loadEarlier = () => session.loadEarlier();
  const answer = (requestId: string, decision: Decision) => session.answer(requestId, decision);

  const lastAnswer = items.findLastIndex((i) => i.kind === "assistant");
  const chatItems: AgentChatItem[] = [];
  if (hasEarlier) {
    chatItems.push({
      kind: "custom",
      key: "earlier",
      render: (
        <button
          type="button"
          onClick={() => void loadEarlier()}
          className="mx-auto block cursor-pointer text-xs text-faint transition-colors hover:text-ink"
        >
          Show earlier messages
        </button>
      ),
    });
  }
  items.forEach((item, index) => {
    if (item.kind === "permission") {
      chatItems.push({
        kind: "custom",
        key: item.id,
        render: <PermissionPrompt item={item} onAnswer={(d) => void answer(item.requestId, d)} />,
      });
    } else {
      chatItems.push({ kind: item.kind, key: item.id, text: item.text });
    }
    if (index === lastAnswer && canChat && !busy) {
      chatItems.push({
        kind: "custom",
        key: `${item.id}-save`,
        render: (
          <button
            type="button"
            onClick={() => void send(SAVE_REPORT_PROMPT, "Save this as a report")}
            className="inline-flex items-center gap-1.5 rounded-full border border-accent/30 bg-accent-soft px-3 py-1.5 text-xs font-medium text-accent transition-colors hover:border-accent cursor-pointer"
          >
            <BookmarkPlus size={13} /> Save as report
          </button>
        ),
      });
    }
  });

  return (
    <Card className="flex h-[calc(100vh-4rem)] min-h-[28rem] flex-col p-0">
      <div className="border-b border-edge px-5 py-3">
        <h1 className="truncate font-display text-lg text-ink">{chat?.title ?? "New analysis"}</h1>
      </div>
      <AgentChat
        className="flex-1 min-h-0 px-5 py-4"
        items={chatItems}
        busy={busy}
        thinkingLabel="Meelu is analysing"
        emptyState={
          loading ? null : (
            <p className="text-sm text-sub">
              Ask about this website&apos;s Search Console and Analytics data. Meelu shapes the data
              in the database, runs the analysis there and shows you what it found.
            </p>
          )
        }
        chips={chatId || !canChat ? [] : askChips}
        chipsRoomy
        onPickChip={(chip) => void send(chip.prompt, chip.label)}
        onSend={(text) => void send(text)}
        onStop={() => session.stop()}
        error={error}
        disabled={!canChat || loading}
        footer={canChat ? undefined : (
          <p className="text-xs text-faint">Open Meelu on your computer to continue this chat.</p>
        )}
        placeholder="Ask about this website's data…"
        busyPlaceholder="Meelu is working…"
        autoFocus
      />
    </Card>
  );
}
