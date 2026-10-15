import type { LinkSuggestion, PillarSuggestion } from "@demo/lib/types";
import { addLinkSuggestions as insertLinkSuggestions, addPillarSuggestions as insertPillarSuggestions } from "../routes/site";
import * as seo from "../routes/seo";
import { chargeCredits, setSiteSummary, siteSummary as accountSiteSummary } from "../routes/account";
import * as analyticsRoutes from "../routes/analytics";
import { route } from "../api";

interface AnalyticsHooks {
  analyticsState?: { chats: Array<{ id: string; sdkSessionId?: string; updatedAt: string }> };
  lastAssistantMessage?: (chatId: string) => { text: string } | null;
  addReportFromAnswer?: (title: string, answer: string) => { id: string; title: string };
}

const analytics = analyticsRoutes as unknown as AnalyticsHooks;

export function syncEvent(event: string, data: Record<string, unknown>): void {
  seo.syncEvent(event, data);
}

export function inspectedUrl(url: string): void {
  seo.inspectedUrl(url);
}

export function addLinkSuggestions(rows: LinkSuggestion[]): boolean {
  insertLinkSuggestions(rows);
  return true;
}

export function addPillarSuggestions(rows: PillarSuggestion[]): boolean {
  insertPillarSuggestions(rows);
  return true;
}

export function addKeywordClusters(source: string, topic: string | null): number {
  return seo.addKeywordClusters(source, topic);
}

export function trackKeywords(keywords: string[]): void {
  seo.trackKeywords(keywords);
}

export function chargeTurn(costUsd: number): void {
  chargeCredits("usage", "llm/anthropic/claude-haiku-5.5", -costUsd);
}

export function writeSiteSummary(siteId: string, summary: string): void {
  setSiteSummary(siteId, summary);
}

export function siteSummary(siteId: string): string | undefined {
  return accountSiteSummary(siteId);
}

export function lastAnalyticsAnswer(sessionId: string | undefined): string | null {
  const chats = analytics.analyticsState?.chats ?? [];
  const chat =
    chats.find((c) => sessionId && c.sdkSessionId === sessionId) ??
    [...chats].sort((a, c) => c.updatedAt.localeCompare(a.updatedAt))[0];
  if (!chat) return null;
  return analytics.lastAssistantMessage?.(chat.id)?.text ?? null;
}

export function saveAnalyticsReport(title: string, answer: string): { id: string; title: string } | null {
  return analytics.addReportFromAnswer?.(title, answer) ?? null;
}

export function call<T = unknown>(method: string, path: string, body?: unknown): T | null {
  const res = route(method, path, body);
  if (res.status >= 400) return null;
  const payload = res.payload as { data?: T } | null;
  return (payload?.data ?? null) as T | null;
}

export function callPaged<T = unknown>(path: string): T[] {
  const res = route("GET", path);
  if (res.status >= 400) return [];
  const payload = res.payload as { data?: T[] } | null;
  return Array.isArray(payload?.data) ? payload.data : [];
}
