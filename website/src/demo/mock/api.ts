import { ROUTES as ACCOUNT } from "./routes/account";
import { ROUTES as SITE } from "./routes/site";
import { ROUTES as SEO } from "./routes/seo";
import { ROUTES as CONTENT } from "./routes/content";
import { ROUTES as SOCIAL } from "./routes/social";
import { ROUTES as ANALYTICS } from "./routes/analytics";
import { ROUTES as AGENT } from "./routes/agent";
import { MockHttpError, type Route } from "./core";

export { issuesCsv, markCrawled } from "./routes/site";

const ROUTES: Route[] = [...ACCOUNT, ...SITE, ...SEO, ...CONTENT, ...SOCIAL, ...ANALYTICS, ...AGENT];

export interface MockResponse {
  status: number;
  payload: unknown;
}

export function route(method: string, path: string, body?: unknown): MockResponse {
  const url = new URL(path, "http://demo.local");
  const pathname = url.pathname.replace(/\/$/, "") || "/";
  for (const [m, re, handler] of ROUTES) {
    if (m !== method.toUpperCase()) continue;
    const match = pathname.match(re);
    if (!match) continue;
    try {
      const payload = handler(match, url.searchParams, (body ?? {}) as Record<string, unknown>);
      return { status: 200, payload };
    } catch (e) {
      if (e instanceof MockHttpError) return { status: e.status, payload: { error: { message: e.message, ...e.extra } } };
      throw e;
    }
  }
  return { status: 404, payload: { error: { message: `The demo has no data for ${method} ${pathname}.` } } };
}

export async function mockFetch(method: string, path: string, body?: unknown): Promise<MockResponse> {
  const wait = 90 + Math.random() * 160;
  await new Promise((r) => setTimeout(r, wait));
  return route(method, path, body);
}
