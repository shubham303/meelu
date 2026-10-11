const listeners = new Set<() => void>();

export const CHATS_PAGE_SIZE = 5;
export const MESSAGES_PAGE_SIZE = 20;

export function chatHref(id: string): string {
  return `/dashboard/analytics/chat/${id}`;
}

export function chatsChanged(): void {
  for (const listener of listeners) listener();
}

export function onChatsChanged(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

const newChatListeners = new Set<() => void>();

export function startNewChat(): void {
  for (const listener of newChatListeners) listener();
}

export function onNewChat(listener: () => void): () => void {
  newChatListeners.add(listener);
  return () => {
    newChatListeners.delete(listener);
  };
}
