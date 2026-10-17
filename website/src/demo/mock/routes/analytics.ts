import type {
  AnalyticsChat,
  AnalyticsChatMessage,
  AnalyticsChatSummary,
  Report,
  ReportDesk,
  ReportSummary,
} from "@demo/lib/types";
import { REPORT_DESKS } from "@demo/lib/types";
import * as siteData from "../data/site";
import * as analytics from "../data/analytics";
import { b, MockHttpError, newId, now, ok, paginate, type Route } from "../core";

export const analyticsState = {
  chats: analytics.CHATS.map((c) => ({ ...c })) as AnalyticsChat[],
  messages: Object.fromEntries(
    Object.entries(analytics.MESSAGES).map(([id, list]) => [id, list.map((m) => ({ ...m }))]),
  ) as Record<string, AnalyticsChatMessage[]>,
  reports: analytics.REPORTS.map((r) => ({ ...r })) as Report[],
};
const state = analyticsState;

const CHAT_TITLE_MAX = 80;

function required(value: unknown, field: string): string {
  const text = (value == null ? "" : String(value)).trim();
  if (!text) throw new MockHttpError(422, `\`${field}\` is required.`);
  return text;
}

function chatTitle(value: unknown): string {
  const text = required(value, "title").split(/\s+/).join(" ");
  return text.length <= CHAT_TITLE_MAX ? text : `${text.slice(0, CHAT_TITLE_MAX - 1).trimEnd()}…`;
}

function findChat(id: string): AnalyticsChat {
  const chat = state.chats.find((c) => c.id === id);
  if (!chat) throw new MockHttpError(404, "Not found");
  return chat;
}

function findReport(id: string): Report {
  const report = state.reports.find((r) => r.id === id);
  if (!report) throw new MockHttpError(404, "Not found");
  return report;
}

function summary({ html, ...r }: Report): ReportSummary {
  return { ...r, htmlBytes: new TextEncoder().encode(html).length };
}

export function createChat(title: string): AnalyticsChat {
  const at = now();
  const chat: AnalyticsChat = { id: newId("ch"), siteId: siteData.SITE_ID, title: chatTitle(title), createdAt: at, updatedAt: at };
  state.chats.unshift(chat);
  state.messages[chat.id] = [];
  return chat;
}

export function appendChatMessage(chatId: string, role: "user" | "assistant", text: string): AnalyticsChatMessage {
  const chat = findChat(chatId);
  const message: AnalyticsChatMessage = { id: newId("msg"), role, text: required(text, "text"), createdAt: now() };
  (state.messages[chatId] ??= []).push(message);
  chat.updatedAt = message.createdAt;
  return message;
}

export function lastAssistantMessage(chatId: string): AnalyticsChatMessage | null {
  const list = state.messages[chatId] ?? [];
  for (let i = list.length - 1; i >= 0; i--) if (list[i].role === "assistant") return list[i];
  return null;
}

export function addReport(title: string, html: string, createdBy: "agent" | "user" = "agent", desk: ReportDesk = "analytics"): Report {
  const at = now();
  const report: Report = { id: newId("rp"), createdAt: at, updatedAt: at, siteId: siteData.SITE_ID, desk, title: required(title, "title"), html: required(html, "html"), createdBy };
  state.reports.unshift(report);
  return report;
}

export function addReportFromAnswer(title: string, answer: string): Report {
  return addReport(title, analytics.reportHtmlFromAnswer(title, answer));
}

function reportDesk(value: unknown): ReportDesk {
  if ((REPORT_DESKS as readonly unknown[]).includes(value)) return value as ReportDesk;
  throw new MockHttpError(422, `desk must be one of ${REPORT_DESKS.join(", ")}.`);
}

const byNewest = (a: { updatedAt: string }, c: { updatedAt: string }) => c.updatedAt.localeCompare(a.updatedAt);

export const ROUTES: Route[] = [
  ["GET", /^\/api\/v1\/reports$/, (_m, q) => {
    const search = q.get("q")?.trim().toLowerCase();
    const desk = q.get("desk");
    const rows = state.reports
      .filter((r) => !desk || r.desk === desk)
      .filter((r) => !search || r.title.toLowerCase().includes(search))
      .sort((a, c) => c.createdAt.localeCompare(a.createdAt))
      .map(summary);
    return paginate(rows, q);
  }],
  ["POST", /^\/api\/v1\/reports$/, (_m, _q, body) =>
    ok(summary(addReport(String(b(body, "title") ?? ""), String(b(body, "html") ?? ""), b(body, "createdBy") === "user" ? "user" : "agent", reportDesk(b(body, "desk")))))],
  ["GET", /^\/api\/v1\/reports\/([^/]+)$/, (m) => ok(findReport(m[1]))],
  ["PUT", /^\/api\/v1\/reports\/([^/]+)$/, (m, _q, body) => {
    const report = findReport(m[1]);
    const title = b(body, "title");
    const html = b(body, "html");
    if (title != null) report.title = required(title, "title");
    if (html != null) report.html = required(html, "html");
    report.updatedAt = now();
    return ok(summary(report));
  }],
  ["DELETE", /^\/api\/v1\/reports\/([^/]+)$/, (m) => {
    const report = findReport(m[1]);
    state.reports = state.reports.filter((r) => r.id !== report.id);
    return ok({ id: report.id, deleted: true });
  }],
  ["GET", /^\/api\/v1\/analytics\/chats$/, (_m, q) => {
    const rows: AnalyticsChatSummary[] = [...state.chats].sort(byNewest).map(({ id, title, updatedAt }) => ({ id, title, updatedAt }));
    return paginate(rows, q);
  }],
  ["POST", /^\/api\/v1\/analytics\/chats$/, (_m, _q, body) => ok(createChat(String(b(body, "title") ?? "")))],
  ["GET", /^\/api\/v1\/analytics\/chats\/([^/]+)$/, (m) => ok(findChat(m[1]))],
  ["PUT", /^\/api\/v1\/analytics\/chats\/([^/]+)$/, (m, _q, body) => {
    const chat = findChat(m[1]);
    const title = b(body, "title");
    const sdkSessionId = b(body, "sdkSessionId");
    if (title == null && sdkSessionId == null) {
      throw new MockHttpError(400, "Nothing to update — send `title` and/or `sdkSessionId`.");
    }
    if (title != null) chat.title = chatTitle(title);
    if (sdkSessionId != null) chat.sdkSessionId = String(sdkSessionId);
    chat.updatedAt = now();
    return ok(chat);
  }],
  ["DELETE", /^\/api\/v1\/analytics\/chats\/([^/]+)$/, (m) => {
    const chat = findChat(m[1]);
    state.chats = state.chats.filter((c) => c.id !== chat.id);
    delete state.messages[chat.id];
    return ok({ id: chat.id, deleted: true });
  }],
  ["GET", /^\/api\/v1\/analytics\/chats\/([^/]+)\/messages$/, (m, q) => {
    const chat = findChat(m[1]);
    return paginate([...(state.messages[chat.id] ?? [])].reverse(), q);
  }],
  ["POST", /^\/api\/v1\/analytics\/chats\/([^/]+)\/messages$/, (m, _q, body) => {
    const chat = findChat(m[1]);
    const input = b(body, "messages");
    if (!Array.isArray(input) || input.length === 0) throw new MockHttpError(422, "`messages` needs at least one message.");
    const added = input.map((raw) => {
      const msg = (raw ?? {}) as Record<string, unknown>;
      const role = msg.role === "assistant" ? "assistant" : msg.role === "user" ? "user" : null;
      if (!role) throw new MockHttpError(422, "`role` must be user or assistant.");
      return appendChatMessage(chat.id, role, String(msg.text ?? ""));
    });
    return ok(added);
  }],
];
