import { createSdkMcpServer, query, tool as sdkTool } from "@anthropic-ai/claude-agent-sdk";
import { z } from "zod";
import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";

export const REVIEW_SERVER = "review";

const CONCURRENCY = 4;

const PIPELINES = {
  review_link_suggestions: {
    description:
      "Read every screening_approved link suggestion of a job one by one against your prompt and settle each: review_approved shows it to the user, review_rejected hides it. Run it after screening and before ranking. It returns counts, never the suggestions.",
    inputs: "/site/structure/link-suggestions/review-inputs",
    verdicts: "/site/structure/link-suggestions/verdicts",
    fields: [],
  },
  review_pillar_suggestions: {
    description:
      "Read every screening_approved pillar suggestion of a job one by one against your prompt and settle each: review_approved (writing the page title and the brief the user acts on) shows it to the user, review_rejected hides it. Run it after screening and before ranking. It returns counts, never the suggestions.",
    inputs: "/site/structure/pillar-suggestions/review-inputs",
    verdicts: "/site/structure/pillar-suggestions/verdicts",
    fields: ["title", "suggestion"],
  },
};

export const reviewToolNames = Object.keys(PIPELINES);

async function meelu(path, { body, cookieHeader, siteId }) {
  const res = await apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1${path}`, {
    method: "POST",
    headers: {
      ...meeluAuthHeaders(cookieHeader),
      "content-type": "application/json",
      ...(siteId ? { "x-meelu-site": siteId } : {}),
    },
    body: JSON.stringify(body),
  });
  const payload = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(payload?.error?.message ?? `${path} failed (${res.status})`);
  return payload.data;
}

function parseVerdict(text) {
  const fenced = text.match(/```(?:json)?\s*([\s\S]*?)```/);
  const body = (fenced ? fenced[1] : text).trim();
  const start = body.indexOf("{");
  const end = body.lastIndexOf("}");
  if (start === -1 || end <= start) return null;
  try {
    const parsed = JSON.parse(body.slice(start, end + 1));
    return parsed && typeof parsed === "object" ? parsed : null;
  } catch {
    return null;
  }
}

async function judgeOne({ instructions, schema, item, judge }) {
  const prompt = [
    instructions,
    "",
    "The item to judge, as JSON:",
    JSON.stringify(item.state),
    "",
    `Answer with one JSON object and nothing else, matching this schema: ${JSON.stringify(schema)}`,
  ].join("\n");
  const text = await judge(prompt);
  return parseVerdict(text ?? "");
}

async function mapLimited(items, limit, run, onSettled) {
  const out = new Array(items.length);
  let next = 0;
  let settled = 0;
  const workers = Array.from({ length: Math.min(limit, items.length) }, async () => {
    while (next < items.length) {
      const index = next++;
      out[index] = await run(items[index]);
      settled += 1;
      onSettled?.(settled);
    }
  });
  await Promise.all(workers);
  return out;
}

function summarise(name, batch, result, reasons, error = null) {
  const lines = [
    `${name}: ${JSON.stringify(result)}`,
    `${batch.items.length} judged${batch.needsSerp?.length ? `, ${batch.needsSerp.length} skipped for a missing search snapshot` : ""}.`,
  ];
  if (error) lines.push(`The model call failed at least once: ${error}`);
  if (reasons.length > 0) {
    lines.push("Sample reasons:");
    lines.push(...reasons.slice(0, 3).map((r) => `- ${r}`));
  }
  return lines.join("\n");
}

async function runPipeline(name, pipeline, input, { cookieHeader, siteId, judge, progress }) {
  const batch = await meelu(pipeline.inputs, {
    cookieHeader,
    siteId,
    body: {
      prompt: input.prompt,
      jobId: input.job_id ?? null,
      ids: input.ids ?? null,
      ...(input.limit ? { limit: input.limit } : {}),
    },
  });
  if (batch.items.length === 0) {
    return summarise(name, batch, { reviewed: 0 }, []);
  }
  const total = batch.items.length;
  progress?.({ tool: name, done: 0, total });
  const answers = await mapLimited(
    batch.items,
    CONCURRENCY,
    (item) =>
      judgeOne({ instructions: batch.instructions, schema: batch.schema, item, judge }).then(
        (answer) => ({ item, answer }),
        (err) => ({ item, answer: null, error: err instanceof Error ? err.message : String(err) }),
      ),
    (done) => progress?.({ tool: name, done, total }),
  );
  const verdicts = [];
  const reasons = [];
  for (const { item, answer } of answers) {
    if (!answer?.verdict) continue;
    const verdict = { id: item.id, verdict: String(answer.verdict) };
    for (const field of pipeline.fields) {
      if (typeof answer[field] === "string") verdict[field] = answer[field];
    }
    verdicts.push(verdict);
    if (typeof answer.reason === "string") reasons.push(answer.reason);
  }
  const result = await meelu(pipeline.verdicts, { cookieHeader, siteId, body: { verdicts } });
  const unanswered = batch.items.length - verdicts.length;
  if (unanswered > 0) result.failed = (result.failed ?? 0) + unanswered;
  const error = answers.find((a) => a.error)?.error ?? null;
  return summarise(name, batch, result, reasons, error);
}

export function reviewMcpServer(names, context) {
  const wanted = (names ?? []).filter((n) => PIPELINES[n]);
  if (wanted.length === 0) return null;
  const tools = wanted.map((name) =>
    sdkTool(
      name,
      PIPELINES[name].description,
      {
        job_id: z.string().describe("Job whose drafts to review"),
        prompt: z.string().describe("The strategy the run is following, as the user wrote it"),
        ids: z.array(z.string()).optional().describe("Only these suggestion ids"),
        limit: z.number().int().positive().optional().describe("Most rows to read"),
      },
      async (input) => {
        const text = await runPipeline(name, PIPELINES[name], input, context);
        return { content: [{ type: "text", text }] };
      },
    ),
  );
  return {
    server: createSdkMcpServer({ name: REVIEW_SERVER, version: "1.0.0", tools }),
    allowed: new Set(wanted),
  };
}
