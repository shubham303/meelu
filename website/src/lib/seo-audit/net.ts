import dns from "node:dns/promises";
import net from "node:net";
import { Agent, fetch, type Response } from "undici";
import { normalise } from "./url";

export const USER_AGENT =
  "MeeluSEOAudit/1.0 (+https://meelu.dev/tools/seo-audit; free technical SEO audit tool)";

/**
 * Some servers answer a plain crawler with 403 and a real browser with 200.
 * Used only as a second opinion before calling somebody's link dead.
 */
export const BROWSER_USER_AGENT =
  "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36";

export const MAX_HTML_BYTES = 3_000_000;
const REDIRECT_STATUS = new Set([301, 302, 303, 307, 308]);
const MAX_HOPS = 5;

function isPrivateIpv4(ip: string): boolean {
  const [a, b, c] = ip.split(".").map(Number);
  if (a === 0 || a === 10 || a === 127) return true;
  if (a === 169 && b === 254) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  // Only the /24s RFC 6890 reserves, not the whole of 192.0.0.0/16 —
  // 192.0.78.0/24 is WordPress.com and very much on the public internet.
  if (a === 192 && b === 0 && (c === 0 || c === 2)) return true;
  if (a === 198 && (b === 18 || b === 19)) return true;
  if (a === 198 && b === 51 && c === 100) return true;
  if (a === 203 && b === 0 && c === 113) return true;
  if (a === 100 && b >= 64 && b <= 127) return true;
  if (a >= 224) return true;
  return false;
}

function ipv6Hextets(ip: string): number[] | null {
  let text = ip.toLowerCase().split("%")[0];
  const tail = text.match(/(\d+\.\d+\.\d+\.\d+)$/);
  if (tail) {
    const [a, b, c, d] = tail[1].split(".").map(Number);
    text = `${text.slice(0, -tail[1].length)}${((a << 8) | b).toString(16)}:${((c << 8) | d).toString(16)}`;
  }
  const [head, rest] = text.split("::");
  const left = head ? head.split(":") : [];
  const right = rest === undefined ? [] : rest ? rest.split(":") : [];
  const missing = 8 - left.length - right.length;
  if (rest === undefined ? left.length !== 8 : missing < 0) return null;
  const words = [...left, ...Array(rest === undefined ? 0 : missing).fill("0"), ...right];
  const parsed = words.map((w) => parseInt(w, 16));
  return parsed.length === 8 && parsed.every((n) => n >= 0 && n <= 0xffff) ? parsed : null;
}

function embeddedIpv4(words: number[]): string {
  return [words[6] >> 8, words[6] & 0xff, words[7] >> 8, words[7] & 0xff].join(".");
}

function isPrivateIpv6(ip: string): boolean {
  const w = ipv6Hextets(ip);
  if (!w) return true;
  const zeroUntil = (n: number) => w.slice(0, n).every((x) => x === 0);
  if (zeroUntil(5) && w[5] === 0xffff) return isPrivateIpv4(embeddedIpv4(w));
  if (zeroUntil(6)) return true;
  if ((w[0] & 0xffc0) === 0xfe80 || (w[0] & 0xffc0) === 0xfec0) return true;
  if ((w[0] & 0xfe00) === 0xfc00) return true;
  if ((w[0] & 0xff00) === 0xff00) return true;
  if (w[0] === 0x64 && w[1] === 0xff9b) return true;
  if (w[0] === 0x2002) return true;
  if (w[0] === 0x2001 && (w[1] === 0 || w[1] === 0xdb8)) return true;
  if (w[0] === 0x100 && w[1] === 0 && w[2] === 0 && w[3] === 0) return true;
  return false;
}

/** Ranges no public website lives on, and that a server must never be talked into fetching. */
export function isPrivateAddress(ip: string): boolean {
  const version = net.isIP(ip);
  if (version === 4) return isPrivateIpv4(ip);
  if (version === 6) return isPrivateIpv6(ip);
  return true;
}

const PRIVATE_TARGET = "EPRIVATETARGET";

type LookupCallback = (
  err: NodeJS.ErrnoException | null,
  address: string | Array<{ address: string; family: number }>,
  family?: number,
) => void;

function publicOnlyLookup(hostname: string, options: { all?: boolean }, callback: LookupCallback) {
  dns.lookup(hostname, { all: true }).then(
    (records) => {
      if (records.length === 0 || records.some((r) => isPrivateAddress(r.address))) {
        const err: NodeJS.ErrnoException = new Error(`${hostname} points at a private network address.`);
        err.code = PRIVATE_TARGET;
        callback(err, "");
        return;
      }
      if (options.all) callback(null, records);
      else callback(null, records[0].address, records[0].family);
    },
    (err: NodeJS.ErrnoException) => callback(err, ""),
  );
}

const publicAgent = new Agent({ connect: { lookup: publicOnlyLookup } });

function blockedByLookup(error: unknown): boolean {
  for (let e = error; e instanceof Error; e = e.cause) {
    if ((e as NodeJS.ErrnoException).code === PRIVATE_TARGET) return true;
  }
  return false;
}

const BLOCKED_HOSTS = /(^|\.)(localhost|local|internal|intranet|lan|home|test|invalid|example)$/i;

export type UrlVerdict = { ok: true } | { ok: false; reason: string };

/**
 * Resolves the host before any request goes out. A public tool that fetches a
 * URL on demand is one careless hop from reading the machine it runs on.
 */
export async function checkPublicUrl(raw: string): Promise<UrlVerdict> {
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return { ok: false, reason: "That is not a URL we can read." };
  }
  if (url.protocol !== "http:" && url.protocol !== "https:") {
    return { ok: false, reason: "Only http and https addresses can be audited." };
  }
  if (url.username || url.password) {
    return { ok: false, reason: "URLs carrying credentials are not audited." };
  }
  const host = url.hostname.replace(/^\[|\]$/g, "");
  if (BLOCKED_HOSTS.test(host)) {
    return { ok: false, reason: "That host is not reachable from the public internet." };
  }
  if (net.isIP(host)) {
    return isPrivateAddress(host)
      ? { ok: false, reason: "That address is on a private network." }
      : { ok: true };
  }
  let records: Array<{ address: string }>;
  try {
    records = await dns.lookup(host, { all: true });
  } catch {
    return { ok: false, reason: `${host} does not resolve — check the spelling.` };
  }
  if (records.length === 0) {
    return { ok: false, reason: `${host} does not resolve — check the spelling.` };
  }
  if (records.some((r) => isPrivateAddress(r.address))) {
    return { ok: false, reason: "That host points at a private network address." };
  }
  return { ok: true };
}

async function readCapped(res: Response, cap: number): Promise<string> {
  const reader = res.body?.getReader();
  if (!reader) return "";
  const decoder = new TextDecoder("utf-8", { fatal: false });
  let out = "";
  let seen = 0;
  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      seen += value.byteLength;
      out += decoder.decode(value, { stream: true });
      if (seen >= cap) {
        await reader.cancel().catch(() => undefined);
        break;
      }
    }
  } catch {
    // A truncated body still tells us most of what the checks need.
  }
  return out + decoder.decode();
}

export type FetchResult = {
  url: string;
  finalUrl?: string;
  status?: number;
  html?: string;
  text?: string;
  contentType: string | null;
  bytes: number | null;
  responseMs: number | null;
  xRobotsTag: string | null;
  chain: Array<{ from: string; status: number; to: string }>;
  error?: string;
  blockedReason?: string;
  loop?: boolean;
  tooManyHops?: boolean;
};

const EMPTY = {
  contentType: null,
  bytes: null,
  responseMs: null,
  xRobotsTag: null,
};

export type FetchOptions = {
  method?: "GET" | "HEAD";
  timeoutMs?: number;
  userAgent?: string;
  accept?: string;
  /** Set false for robots.txt and sitemaps, where a non-HTML body is the point. */
  htmlOnly?: boolean;
  signal?: AbortSignal;
};

/** Follows redirects by hand so every hop is recorded and re-checked. */
export async function fetchUrl(
  url: string,
  options: FetchOptions = {},
): Promise<FetchResult> {
  const {
    method = "GET",
    timeoutMs = 15_000,
    userAgent = USER_AGENT,
    accept = "text/html,application/xhtml+xml",
    htmlOnly = true,
    signal,
  } = options;

  const chain: FetchResult["chain"] = [];
  let current = url;

  for (let hop = 0; hop <= MAX_HOPS; hop++) {
    const verdict = await checkPublicUrl(current);
    if (!verdict.ok) {
      return { url, chain, ...EMPTY, blockedReason: verdict.reason };
    }

    const startedAt = Date.now();
    let res: Response;
    try {
      res = await fetch(current, {
        dispatcher: publicAgent,
        method,
        headers: { "user-agent": userAgent, accept },
        redirect: "manual",
        signal: signal
          ? AbortSignal.any([signal, AbortSignal.timeout(timeoutMs)])
          : AbortSignal.timeout(timeoutMs),
      });
    } catch (e) {
      if (blockedByLookup(e)) {
        return { url, chain, ...EMPTY, blockedReason: "That host points at a private network address." };
      }
      const message = e instanceof Error ? e.message : String(e);
      return { url, chain, ...EMPTY, error: message };
    }
    const responseMs = Date.now() - startedAt;

    const location = res.headers.get("location");
    if (REDIRECT_STATUS.has(res.status) && location) {
      await res.body?.cancel().catch(() => undefined);
      let next: string;
      try {
        next = normalise(new URL(location, current).toString());
      } catch {
        return { url, chain, ...EMPTY, status: res.status, error: "broken redirect target" };
      }
      chain.push({ from: current, status: res.status, to: next });
      if (chain.some((h) => h.from === next)) {
        return { url, chain, ...EMPTY, loop: true };
      }
      current = next;
      continue;
    }

    const contentType = res.headers.get("content-type");
    const isHtml = contentType?.includes("html") ?? false;
    const wanted = method === "HEAD" ? false : htmlOnly ? isHtml : true;
    const body = wanted ? await readCapped(res, MAX_HTML_BYTES) : undefined;
    if (body === undefined) await res.body?.cancel().catch(() => undefined);

    return {
      url,
      finalUrl: current,
      status: res.status,
      html: isHtml ? body : undefined,
      text: body,
      contentType,
      bytes: body === undefined ? null : Buffer.byteLength(body),
      responseMs,
      xRobotsTag: res.headers.get("x-robots-tag"),
      chain,
    };
  }

  return { url, chain, ...EMPTY, tooManyHops: true };
}

/** Runs `work` over `items` with at most `limit` in flight. */
export async function pool<T, R>(
  items: T[],
  limit: number,
  work: (item: T) => Promise<R>,
): Promise<R[]> {
  const out: R[] = new Array(items.length);
  let next = 0;
  const runners = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const index = next++;
      out[index] = await work(items[index]);
    }
  });
  await Promise.all(runners);
  return out;
}

export const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

const CHALLENGE =
  /(just a moment|checking your browser|enable javascript and cookies|cf[-_]browser[-_]verification|cf[-_]chl|attention required|access denied|request unsuccessful|are you a robot|verifying you are human)/i;

export function looksLikeBotChallenge(html: string | undefined): boolean {
  return html !== undefined && CHALLENGE.test(html.slice(0, 6000));
}
