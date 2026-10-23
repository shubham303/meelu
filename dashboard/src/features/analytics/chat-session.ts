import { bridge, streamTurn, type RunningTurn } from "@/components/agent";
import { api, apiPaged } from "@/lib/use-api";
import type { AnalyticsChat, AnalyticsChatMessage } from "@/lib/types";
import { MESSAGES_PAGE_SIZE, chatHref, chatsChanged } from "./chats";

const ACTION = "ask-analytics";

export type Decision = "allow" | "always" | "full" | "deny";

export type Item =
  | { kind: "user"; id: string; text: string }
  | { kind: "assistant"; id: string; text: string }
  | { kind: "tool"; id: string; text: string }
  | {
      kind: "permission";
      id: string;
      requestId: string;
      tool: string;
      input: Record<string, unknown>;
      answered?: Decision;
    };

export interface ChatState {
  chat: AnalyticsChat | null;
  items: Item[];
  page: number;
  hasEarlier: boolean;
  loading: boolean;
  busy: boolean;
  error: string | null;
}

type Stored = { role: "user" | "assistant"; text: string };

function fromMessages(messages: AnalyticsChatMessage[]): Item[] {
  return [...messages].reverse().map((m) => ({ kind: m.role, id: m.id, text: m.text }));
}

function storedTurns(items: Item[]): Stored[] {
  return items.flatMap((i) =>
    i.kind === "user" || i.kind === "assistant" ? [{ role: i.kind, text: i.text }] : [],
  );
}

function messagesPath(chatId: string, page: number): string {
  return `/api/v1/analytics/chats/${chatId}/messages?page=${page}&page_size=${MESSAGES_PAGE_SIZE}`;
}

const sessions = new Map<string, ChatSession>();

export function openChatSession(chatId: string | undefined, siteId: string | null): ChatSession {
  const existing = chatId ? sessions.get(chatId) : undefined;
  if (existing) return existing;
  const session = new ChatSession(siteId, chatId ?? null);
  if (chatId) {
    sessions.set(chatId, session);
    void session.load(chatId);
  }
  return session;
}

export class ChatSession {
  private state: ChatState = {
    chat: null,
    items: [],
    page: 1,
    hasEarlier: false,
    loading: false,
    busy: false,
    error: null,
  };
  private listeners = new Set<() => void>();
  private running: RunningTurn | null = null;
  private resumed = false;
  private seq = 0;

  constructor(
    private readonly siteId: string | null,
    private key: string | null,
  ) {}

  getState = (): ChatState => this.state;

  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    if (this.key && !sessions.has(this.key)) sessions.set(this.key, this);
    return () => {
      this.listeners.delete(listener);
      this.forgetIfIdle();
    };
  };

  private set(patch: Partial<ChatState> | ((s: ChatState) => Partial<ChatState>)) {
    const next = typeof patch === "function" ? patch(this.state) : patch;
    this.state = { ...this.state, ...next };
    for (const listener of this.listeners) listener();
  }

  private forgetIfIdle() {
    const key = this.key;
    if (this.listeners.size === 0 && !this.state.busy && key && sessions.get(key) === this) sessions.delete(key);
  }

  private nextId() {
    return `live-${++this.seq}`;
  }

  private push(item: Item) {
    this.set((s) => ({ items: [...s.items, item] }));
  }

  async load(chatId: string) {
    this.set({ loading: true });
    try {
      const [loaded, messages] = await Promise.all([
        api<AnalyticsChat>(`/api/v1/analytics/chats/${chatId}`),
        apiPaged<AnalyticsChatMessage>(messagesPath(chatId, 1)),
      ]);
      this.set({ chat: loaded, items: fromMessages(messages.data), hasEarlier: messages.pagination.has_next });
    } catch (e) {
      this.set({ error: e instanceof Error ? e.message : "Could not open this chat" });
    } finally {
      this.set({ loading: false });
    }
  }

  async loadEarlier() {
    const { chat, page } = this.state;
    if (!chat) return;
    const res = await apiPaged<AnalyticsChatMessage>(messagesPath(chat.id, page + 1));
    this.set((s) => {
      const seen = new Set(s.items.map((i) => i.id));
      return {
        items: [...fromMessages(res.data).filter((i) => !seen.has(i.id)), ...s.items],
        hasEarlier: res.pagination.has_next,
        page: page + 1,
      };
    });
  }

  private async ensureChat(title: string): Promise<AnalyticsChat> {
    if (this.state.chat) return this.state.chat;
    const created = await api<AnalyticsChat>("/api/v1/analytics/chats", {
      method: "POST",
      body: { title },
    });
    this.resumed = true;
    this.key = created.id;
    sessions.set(created.id, this);
    this.set({ chat: created });
    window.history.replaceState(null, "", chatHref(created.id));
    return created;
  }

  private async store(chatId: string, messages: Stored[]) {
    await api(`/api/v1/analytics/chats/${chatId}/messages`, {
      method: "POST",
      body: { messages },
    });
    chatsChanged();
  }

  async send(message: string, displayAs?: string) {
    const text = message.trim();
    if (!text || this.state.busy) return;
    const shown = displayAs ?? text;
    const history = this.resumed ? undefined : storedTurns(this.state.items);
    this.set({ error: null, busy: true });
    this.push({ kind: "user", id: this.nextId(), text: shown });

    let current: AnalyticsChat;
    try {
      current = await this.ensureChat(shown);
      await this.store(current.id, [{ role: "user", text: shown }]);
    } catch (e) {
      this.set({ error: e instanceof Error ? e.message : "Could not save this chat", busy: false });
      return;
    }

    let answerId = this.nextId();
    let answer = "";
    this.running = streamTurn({
      action: ACTION,
      siteId: this.siteId,
      message: text,
      sessionId: current.sdkSessionId,
      history,
      onText: (chunk) => {
        answer += chunk;
        const text = answer.trimStart();
        if (!text) return;
        this.set((s) => {
          const last = s.items[s.items.length - 1];
          if (last?.kind === "assistant" && last.id === answerId) {
            return { items: [...s.items.slice(0, -1), { ...last, text }] };
          }
          return { items: [...s.items, { kind: "assistant", id: answerId, text }] };
        });
      },
      onTool: (name) => {
        answerId = this.nextId();
        answer = "";
        this.push({ kind: "tool", id: this.nextId(), text: name });
      },
      onEvent: (m) => {
        if (m.event === "permission" && typeof m.data.requestId === "string") {
          this.push({
            kind: "permission",
            id: this.nextId(),
            requestId: m.data.requestId,
            tool: String(m.data.tool ?? "this action"),
            input: (m.data.input as Record<string, unknown>) ?? {},
          });
        }
      },
    });
    const result = await this.running.result;
    this.running = null;
    this.resumed = true;
    if (!result.ok && result.error) this.set({ error: result.error });
    try {
      if (result.sessionId && result.sessionId !== current.sdkSessionId) {
        const updated = await api<AnalyticsChat>(`/api/v1/analytics/chats/${current.id}`, {
          method: "PUT",
          body: { sdkSessionId: result.sessionId },
        });
        this.set({ chat: updated });
      }
      if (answer.trim()) await this.store(current.id, [{ role: "assistant", text: answer.trim() }]);
    } catch (e) {
      this.set({ error: e instanceof Error ? e.message : "Could not save the answer" });
    }
    this.set({ busy: false });
    this.forgetIfIdle();
  }

  stop() {
    this.running?.abort();
  }

  async answer(requestId: string, decision: Decision) {
    this.set((s) => ({
      items: s.items.map((i) =>
        i.kind === "permission" && i.requestId === requestId ? { ...i, answered: decision } : i,
      ),
    }));
    await bridge()?.respondPermission?.(requestId, decision);
  }
}
