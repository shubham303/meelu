import { crawlFetch, withOutboundSlot } from "../net.js";
import { domainOf } from "./dedupe.js";

const EMAIL_RE = /[a-z0-9][a-z0-9._%+-]*@[a-z0-9][a-z0-9.-]*\.[a-z]{2,}/gi;
const SKIP_SUFFIXES = [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".css", ".js"];
const SKIP_LOCALS = ["noreply", "no-reply", "donotreply", "example", "sentry", "wixpress"];
const MAX_BYTES = 300_000;

async function fetchText(url) {
  try {
    return await withOutboundSlot(async () => {
      const res = await crawlFetch(url, { redirect: "follow" });
      if (!res.ok) return null;
      const type = String(res.headers.get("content-type") ?? "");
      if (type && !type.includes("html") && !type.includes("text")) return null;
      const text = await res.text();
      return text.slice(0, MAX_BYTES);
    });
  } catch {
    return null;
  }
}

function emailsIn(html) {
  const decoded = String(html ?? "").replace(/&#64;|%40/g, "@");
  const found = decoded.match(EMAIL_RE) ?? [];
  const out = [];
  for (const raw of found) {
    const email = raw.toLowerCase();
    if (SKIP_SUFFIXES.some((s) => email.endsWith(s))) continue;
    const local = email.split("@")[0];
    if (SKIP_LOCALS.some((s) => local.includes(s))) continue;
    if (!out.includes(email)) out.push(email);
  }
  return out;
}

function pick(emails, siteDomain) {
  if (emails.length === 0) return null;
  if (siteDomain) {
    const own = emails.find((e) => e.split("@")[1] === siteDomain);
    if (own) return own;
  }
  return emails[0];
}

export async function enrichEmail(lead) {
  if (lead.email || !lead.website) return lead;
  const siteDomain = domainOf(lead.website);
  const pages = [lead.website];
  try {
    pages.push(new URL("/contact", lead.website).toString());
  } catch {}
  for (const page of pages) {
    const html = await fetchText(page);
    if (!html) continue;
    const email = pick(emailsIn(html), siteDomain);
    if (email) return { ...lead, email, emailVerified: true };
  }
  return lead;
}
