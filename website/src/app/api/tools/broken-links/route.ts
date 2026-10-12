import { MAX_LINKS, runLinkCheck } from "@/lib/link-check/run";
import { LIMITS, clientKey, takeSlot } from "@/lib/seo-audit/rate-limit";
import { parseInput } from "@/lib/seo-audit/url";
import type { StreamEvent } from "@/lib/seo-audit/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 150;

const encoder = new TextEncoder();

const RATE_MESSAGES: Record<string, { message: string; hint: string }> = {
  hourly: {
    message: `That is ${LIMITS.perHour} scans this hour, which is the limit.`,
    hint: "The tool is free and each run crawls a site and checks hundreds of links, so the rate is capped. Try again shortly.",
  },
  daily: {
    message: `That is ${LIMITS.perDay} scans today, which is the limit.`,
    hint: "The cap resets on a rolling twenty-four hours.",
  },
  busy: {
    message: "Three scans are already running.",
    hint: "Give it half a minute and try again.",
  },
  global: {
    message: "The tool is at capacity right now.",
    hint: "Too many scans are running across everyone using it. Try again in a few minutes.",
  },
};

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as {
    url?: unknown;
    scope?: unknown;
    includeImages?: unknown;
  } | null;

  const url = typeof body?.url === "string" ? body.url.trim() : "";
  const scope = body?.scope === "page" ? "page" : "auto";
  const includeImages = body?.includeImages !== false;

  if (!url) {
    return Response.json({ error: "Enter a website, page or sitemap URL." }, { status: 400 });
  }
  if (!parseInput(url)) {
    return Response.json(
      {
        error: "That does not look like a website address.",
        hint: "Try something like example.com, https://example.com/blog/post or https://example.com/sitemap.xml.",
        code: "invalid-url",
      },
      { status: 400 },
    );
  }

  const slot = takeSlot(clientKey(request.headers));
  if (!slot.ok) {
    const copy = RATE_MESSAGES[slot.reason];
    return Response.json(
      {
        error: copy.message,
        hint: copy.hint,
        code: slot.reason === "busy" || slot.reason === "global" ? "busy" : "rate-limited",
        retryAfterSeconds: slot.retryAfterSeconds,
      },
      { status: 429, headers: { "retry-after": String(slot.retryAfterSeconds) } },
    );
  }

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let closed = false;
      const send = (event: StreamEvent | Record<string, unknown>) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(`${JSON.stringify(event)}\n`));
        } catch {
          closed = true;
        }
      };

      try {
        const outcome = await runLinkCheck(url, {
          scope,
          includeImages,
          maxLinks: MAX_LINKS,
          signal: request.signal,
          onEvent: send,
        });

        if (outcome.ok) {
          send({ type: "done", result: outcome.result });
        } else {
          send({ type: "error", error: outcome.error });
        }
      } catch (e) {
        send({
          type: "error",
          error: {
            code: "unreachable",
            message: "The scan stopped unexpectedly.",
            hint: e instanceof Error ? e.message : String(e),
          },
        });
      } finally {
        slot.release();
        closed = true;
        try {
          controller.close();
        } catch {
          // Already closed because the visitor navigated away.
        }
      }
    },
  });

  return new Response(stream, {
    headers: {
      "content-type": "application/x-ndjson; charset=utf-8",
      "cache-control": "no-store, no-transform",
      "x-accel-buffering": "no",
    },
  });
}
