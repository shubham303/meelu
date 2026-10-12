"use client";

import { useRef, useState } from "react";
import { AgentChat, type AgentChatItem } from "./agent-chat";
import { refuseOnWeb, streamTurn, type RunningTurn } from "./bridge";

interface Turn {
  role: "user" | "agent";
  text: string;
}

export interface DraftChatProps {
  scope: string;
  siteId?: string | null;
  intro: string;
  framing: string;
  placeholder?: string;
  onTurn?: () => void;
}

export function DraftChat({ scope, siteId, intro, framing, placeholder, onTurn }: DraftChatProps) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const runningRef = useRef<RunningTurn | null>(null);

  const send = async (text: string) => {
    const instruction = text.trim();
    if (!instruction || thinking) return;
    if (refuseOnWeb(`${scope} turn`)) return;

    setError(null);
    const history = turns;
    setTurns((prev) => [...prev, { role: "user", text: instruction }]);
    setThinking(true);

    const message = [
      framing,
      "",
      ...history.map((t) => `${t.role === "user" ? "Me" : "You"}: ${t.text}`),
      "",
      `Me: ${instruction}`,
    ].join("\n");

    const turn = streamTurn({ action: scope, message, siteId: siteId ?? null });
    runningRef.current = turn;
    const res = await turn.result;
    runningRef.current = null;
    setThinking(false);

    if (!res.ok) {
      setError(res.error ?? "The turn stopped before it answered.");
      return;
    }
    setTurns((prev) => [...prev, { role: "agent", text: res.text || "Done." }]);
    onTurn?.();
  };

  const items: AgentChatItem[] = turns.map((t, i) =>
    t.role === "user"
      ? { kind: "user", key: i, text: t.text }
      : { kind: "assistant", key: i, text: t.text },
  );

  return (
    <AgentChat
      layout="bounded"
      logClassName="max-h-80"
      items={items}
      busy={thinking}
      emptyState={<p className="text-sm text-sub">{intro}</p>}
      onSend={(text) => void send(text)}
      placeholder={placeholder ?? "Tell Meelu what you want…"}
      error={error}
      autoFocus
    />
  );
}
