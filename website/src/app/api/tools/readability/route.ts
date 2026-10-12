/**
 * Only the URL mode needs a server. Pasted text is scored in the browser and
 * never leaves the tab. This endpoint exists because a browser cannot fetch
 * somebody else's page without their CORS headers saying so — it fetches the
 * page, strips the markup and hands back the readable blocks. The scoring still
 * happens in the browser, on the blocks this returns. Nothing is stored.
 */

import { extractPageText } from "@/lib/page-text/extract";
import { MAX_BLOCKS } from "@/lib/page-text/types";
import { fetchUrl, looksLikeBotChallenge } from "@/lib/seo-audit/net";
import { clientKey } from "@/lib/seo-audit/rate-limit";
import { parseInput } from "@/lib/seo-audit/url";
import { FETCH_LIMITS, takeFetchSlot } from "@/lib/similarity/rate-limit";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 30;

const TIMEOUT_MS = 15_000;

const RATE_MESSAGES: Record<string, { message: string; hint: string }> = {
  hourly: {
    message: `That is ${FETCH_LIMITS.perHour} pages fetched this hour, which is the limit.`,
    hint: "Fetching is the only part of this tool that touches our server, so the rate is capped. Paste the text instead and the scores appear straight away.",
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

function fail(error: string, code: string, hint?: string, status = 400) {
  return Response.json(
    { error, code, ...(hint ? { hint } : {}) },
    { status, headers: { "cache-control": "no-store" } },
  );
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as { url?: unknown } | null;
  const raw = typeof body?.url === "string" ? body.url.trim() : "";

  if (!raw) {
    return fail("Enter the address of the page you want to score.", "invalid-url");
  }

  const parsed = parseInput(raw);
  if (!parsed) {
    return fail(
      "That does not look like a web address.",
      "invalid-url",
      "Try something like example.com/blog/post — or paste the text itself instead.",
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
    // fetchUrl resolves the host before every hop, so a URL pointing at a
    // private or loopback address never gets a request sent to it.
    const result = await fetchUrl(parsed.toString(), {
      timeoutMs: TIMEOUT_MS,
      signal: request.signal,
    });

    if (result.blockedReason) {
      return fail(result.blockedReason, "blocked");
    }
    if (result.loop) {
      return fail(`${parsed.hostname} redirects in a loop.`, "unreachable");
    }
    if (result.tooManyHops) {
      return fail(`${parsed.hostname} redirects too many times.`, "unreachable");
    }
    if (result.error) {
      const timedOut = /timeout|abort|timed out/i.test(result.error);
      return fail(
        timedOut
          ? `${parsed.hostname} took longer than ${TIMEOUT_MS / 1000} seconds to answer.`
          : `${parsed.hostname} could not be reached.`,
        timedOut ? "timeout" : "unreachable",
        "Check the address, or copy the text off the page and paste it in.",
        504,
      );
    }
    if (result.status && result.status >= 400) {
      return fail(
        `${parsed.hostname} answered ${result.status}.`,
        result.status >= 500 ? "unreachable" : "http-refused",
        result.status === 403 || result.status === 401 || result.status === 429
          ? "The site refuses automated requests. Copy the text off the page and paste it in instead."
          : "The page may have moved or been removed.",
        502,
      );
    }
    if (!result.html) {
      return fail(
        `${parsed.hostname} did not return a web page.`,
        "not-html",
        `The address served ${result.contentType ?? "something that is not HTML"}. PDFs, documents and images cannot be read — paste the text instead.`,
        415,
      );
    }
    if (looksLikeBotChallenge(result.html)) {
      return fail(
        `${parsed.hostname} served a bot challenge instead of the page.`,
        "bot-protection",
        "Cloudflare and similar do this to anything that is not a browser. Paste the text instead.",
        502,
      );
    }

    const page = extractPageText(result.html);
    if (page.text.trim().length < 40) {
      return fail(
        `Almost no readable text was found on ${parsed.hostname}.`,
        "empty",
        "The page may build its content with JavaScript, which this fetch does not run. Paste the text instead.",
        422,
      );
    }

    return Response.json(
      {
        page: {
          url: parsed.toString(),
          finalUrl: result.finalUrl ?? parsed.toString(),
          title: page.title,
          blocks: page.blocks,
          text: page.text,
          words: page.words,
          // True when the page ran past the block or character cap, so the UI
          // can say the scores cover the first part of a very long page.
          truncated: page.truncated,
          // True when the page had no paragraph markup and the passages were
          // split on line breaks instead, which makes them coarser.
          usedFallback: page.usedFallback,
          maxBlocks: MAX_BLOCKS,
        },
      },
      { headers: { "cache-control": "no-store" } },
    );
  } catch {
    return fail(
      "The page could not be fetched.",
      "unreachable",
      "Try again, or copy the text off the page and paste it in.",
      502,
    );
  } finally {
    slot.release();
  }
}
