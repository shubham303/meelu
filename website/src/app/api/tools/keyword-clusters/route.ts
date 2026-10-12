import { clientKey } from "@/lib/seo-audit/rate-limit";
import { claimDailyRun } from "@/lib/keyword-clusters/daily-limit";
import { CLUSTER_LIMITS, LANGUAGES, LOCATIONS } from "@/lib/keyword-clusters/limits";
import { takeClusterSlot } from "@/lib/keyword-clusters/rate-limit";
import { RUN_STEPS, cleanSeeds, runClustering } from "@/lib/keyword-clusters/run";
import type { ClusterError, ClusterStreamEvent } from "@/lib/keyword-clusters/types";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 150;

const encoder = new TextEncoder();

function fail(error: ClusterError, status: number, retryAfterSeconds?: number) {
  return Response.json(
    { error: error.message, hint: error.hint, code: error.code, retryAfterSeconds },
    {
      status,
      headers: retryAfterSeconds ? { "retry-after": String(retryAfterSeconds) } : undefined,
    },
  );
}

function hours(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.ceil((seconds % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m} minutes`;
}

export async function POST(request: Request) {
  const body = (await request.json().catch(() => null)) as {
    seeds?: unknown;
    locationCode?: unknown;
    languageCode?: unknown;
    minVolume?: unknown;
  } | null;

  const rawSeeds = Array.isArray(body?.seeds)
    ? body.seeds.filter((s): s is string => typeof s === "string")
    : typeof body?.seeds === "string"
      ? body.seeds.split(/[\n,]/)
      : [];
  const seeds = cleanSeeds(rawSeeds);
  const location =
    LOCATIONS.find((l) => l.code === Number(body?.locationCode)) ?? LOCATIONS[0];
  const language =
    LANGUAGES.find((l) => l.code === body?.languageCode)?.code ?? location.language;
  const minVolumeRaw = Number(body?.minVolume);
  const minVolume = Number.isFinite(minVolumeRaw)
    ? Math.min(Math.max(Math.floor(minVolumeRaw), 0), 100_000)
    : CLUSTER_LIMITS.defaultMinVolume;

  if (seeds.length === 0) {
    return fail(
      {
        code: "invalid-input",
        message: "Enter at least one seed keyword.",
        hint: "One per line, for example: blue light glasses.",
      },
      400,
    );
  }

  const slot = takeClusterSlot(clientKey(request.headers));
  if (!slot.ok) {
    return fail(
      slot.reason === "busy"
        ? {
            code: "busy",
            message: "You already have a clustering run going.",
            hint: "Wait for it to finish, then start the next one.",
          }
        : {
            code: "rate-limited",
            message: "That is the limit of runs from one visitor for now.",
            hint: "Each run calls paid keyword and search APIs, so the rate is capped. Try again later.",
          },
      429,
      slot.retryAfterSeconds,
    );
  }

  const claim = await claimDailyRun();
  if (!claim.ok) {
    slot.release();
    if (claim.reason === "exhausted") {
      return fail(
        {
          code: "daily-limit",
          message: `The tool has run ${claim.limit} times today, which is the daily limit for everyone.`,
          hint: `It resets at midnight UTC, in about ${hours(claim.retryAfterSeconds)}.`,
        },
        429,
        claim.retryAfterSeconds,
      );
    }
    console.error("keyword-clusters: daily counter unavailable", claim.detail);
    return fail(
      {
        code: "not-configured",
        message: "The tool cannot check its daily limit right now, so it is paused.",
        hint: "Try again in a few minutes.",
      },
      503,
    );
  }

  const stream = new ReadableStream<Uint8Array>({
    async start(controller) {
      let closed = false;
      const send = (event: ClusterStreamEvent) => {
        if (closed) return;
        try {
          controller.enqueue(encoder.encode(`${JSON.stringify(event)}\n`));
        } catch {
          closed = true;
        }
      };

      try {
        const outcome = await runClustering(
          {
            seeds,
            locationCode: location.code,
            languageCode: language,
            minVolume,
          },
          {
            signal: request.signal,
            dailyRuns: { used: claim.used, limit: claim.limit },
            onPhase: (message, step) => send({ type: "phase", message, step, steps: RUN_STEPS }),
          },
        );
        if (outcome.ok) {
          console.info("keyword-clusters: run cost", outcome.result.costUsd);
          send({ type: "done", result: outcome.result });
        } else {
          send({ type: "error", error: outcome.error });
        }
      } catch (e) {
        console.error("keyword-clusters: run failed", e);
        send({
          type: "error",
          error: {
            code: "provider-failed",
            message: "The run stopped unexpectedly.",
            hint: e instanceof Error ? e.message : String(e),
          },
        });
      } finally {
        slot.release();
        closed = true;
        try {
          controller.close();
        } catch {}
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
