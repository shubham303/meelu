/**
 * Only the URL mode needs a server. When both boxes hold pasted text nothing is
 * sent here at all — the comparison runs in the browser. This endpoint exists to
 * fetch a page and hand back the readable text, because a browser cannot fetch
 * somebody else's site without their CORS headers saying so.
 */

import { extractPageText } from "@/lib/page-text/extract";
import { fetchUrl, looksLikeBotChallenge } from "@/lib/seo-audit/net";
import { clientKey } from "@/lib/seo-audit/rate-limit";
import { parseInput } from "@/lib/seo-audit/url";
import { MAX_WORDS } from "@/lib/similarity/compare";
import { countWords, limitWords } from "@/lib/limits";
import { FETCH_LIMITS, takeFetchSlot } from "@/lib/similarity/rate-limit";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;

const RATE_MESSAGES: Record<string, { message: string; hint: string }> = {
  hourly: {
    message: `That is ${FETCH_LIMITS.perHour} pages fetched this hour, which is the limit.`,
    hint: "Fetching is the only part of this tool that touches our server, so the rate is capped. Paste the text instead and the comparison runs straight away.",
  },
  daily: {
    message: `That is ${FETCH_LIMITS.perDay} pages fetched today, which is the limit.`,
    hint: "The cap resets on a rolling twenty-four hours. Pasting text is never rate-limited.",
  },
  busy: {
    message: "Too many pages are being fetched at once.",
    hint: "Give it twenty seconds and try again, or paste the text instead.",
  },
};

type Side = "a" | "b";

type Document = {
  url: string;
  finalUrl: string;
  title: string | null;
  text: string;
  words: number;
  truncated: boolean;
};

type Failure = { error: string; hint?: string; code: string };

async function readPage(raw: string, signal: AbortSignal): Promise<Document | Failure> {
  const parsed = parseInput(raw);
  if (!parsed) {
    return {
      error: "That does not look like a web address.",
      hint: "Try something like example.com/blog/post — or paste the text itself instead.",
      code: "invalid-url",
    };
  }

  const result = await fetchUrl(parsed.toString(), { timeoutMs: 15_000, signal });

  if (result.blockedReason) {
    return { error: result.blockedReason, code: "unreachable" };
  }
  if (result.error) {
    return {
      error: `${parsed.hostname} could not be reached.`,
      hint: "Check the address, or copy the text off the page and paste it in.",
      code: "unreachable",
    };
  }
  if (result.status && result.status >= 400) {
    return {
      error: `${parsed.hostname} answered ${result.status}.`,
      hint:
        result.status === 403 || result.status === 401 || result.status === 429
          ? "The site refuses automated requests. Copy the text off the page and paste it in instead."
          : "The page may have moved or been removed.",
      code: result.status >= 500 ? "unreachable" : "http-refused",
    };
  }
  if (!result.html) {
    return {
      error: `${parsed.hostname} did not return a web page.`,
      hint: "PDFs, documents and images cannot be read. Paste the text instead.",
      code: "not-html",
    };
  }
  if (looksLikeBotChallenge(result.html)) {
    return {
      error: `${parsed.hostname} served a bot challenge instead of the page.`,
      hint: "Cloudflare and similar do this to anything that is not a browser. Paste the text instead.",
      code: "bot-protection",
    };
  }

  // extractBlocks, not the audit's extract(): the audit keeps navigation,
  // headers and footers because it is checking them, and it counts a <li>
  // wrapping a <p> twice. Comparing a fetched page against pasted prose has to
  // see the same thing a reader copies, or the shared navigation on two pages
  // from one site reads as similarity between the articles.
  const page = extractPageText(result.html);
  const full = page.text.trim();
  if (full.length < 40) {
    return {
      error: `Almost no readable text was found on ${parsed.hostname}.`,
      hint: "The page may build its content with JavaScript, which this fetch does not run. Paste the text instead.",
      code: "empty",
    };
  }

  const capped = limitWords(full, MAX_WORDS);
  return {
    url: parsed.toString(),
    finalUrl: result.finalUrl ?? parsed.toString(),
    title: page.title,
    text: capped.text,
    // The words actually being compared, not the page's total: the card says
    // "N words" next to a result built from exactly those words.
    words: countWords(capped.text),
    truncated: capped.truncated,
  };
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as {
    a?: unknown;
    b?: unknown;
  } | null;

  const wanted: Array<[Side, string]> = [];
  for (const side of ["a", "b"] as const) {
    const value = body?.[side];
    if (typeof value === "string" && value.trim()) wanted.push([side, value.trim()]);
  }

  if (wanted.length === 0) {
    return Response.json(
      {
        error: "No URL was given to fetch.",
        hint: "Send one or both sides as a URL. Pasted text is compared in the browser and never reaches this endpoint.",
        code: "invalid-url",
      },
      { status: 400 },
    );
  }

  const slot = takeFetchSlot(clientKey(request.headers));
  if (!slot.ok) {
    const copy = RATE_MESSAGES[slot.reason];
    return Response.json(
      {
        error: copy.message,
        hint: copy.hint,
        code: slot.reason === "busy" ? "busy" : "rate-limited",
        retryAfterSeconds: slot.retryAfterSeconds,
      },
      { status: 429, headers: { "retry-after": String(slot.retryAfterSeconds) } },
    );
  }

  try {
    const results = await Promise.all(
      wanted.map(async ([side, url]) => [side, await readPage(url, request.signal)] as const),
    );

    const documents: Partial<Record<Side, Document>> = {};
    const errors: Partial<Record<Side, Failure>> = {};
    for (const [side, result] of results) {
      if ("error" in result) errors[side] = result;
      else documents[side] = result;
    }

    return Response.json(
      { documents, errors },
      { headers: { "cache-control": "no-store" } },
    );
  } catch {
    return Response.json(
      {
        error: "The page could not be fetched.",
        hint: "Try again, or copy the text off the page and paste it in.",
        code: "unreachable",
      },
      { status: 502 },
    );
  } finally {
    slot.release();
  }
}
