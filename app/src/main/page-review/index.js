import { ENV_DEFAULTS, meeluAuthHeaders } from "../config.js";
import { apiFetch } from "../net.js";
import { resolveLlm } from "../agent/runner.js";
import { jsonCall } from "../social-signals/llm.js";

export const LLM_PAGE_EXTRACTION_MODEL = "claude-haiku-4-5-20251001";

const ENABLED = process.env.MEELU_PAGE_REVIEW !== "0";
const TICK_MS = Number(process.env.MEELU_PAGE_REVIEW_TICK_MS ?? 10 * 60 * 1000);
const FIRST_TICK_MS = Number(process.env.MEELU_PAGE_REVIEW_FIRST_TICK_MS ?? 2 * 60 * 1000);
const QUEUE_LIMIT = 100;

const SYSTEM =
  "You classify one web page. Decide from what the page offers or does, not from how it is worded. Answer with one JSON object and nothing else.";

let running = false;
let timer = null;
let firstTick = null;

function api(path, { method = "GET", body, siteId, cookieHeader } = {}) {
  const headers = {
    ...meeluAuthHeaders(cookieHeader),
    ...(body ? { "content-type": "application/json" } : {}),
    ...(siteId ? { "x-meelu-site": siteId } : {}),
  };
  return apiFetch(`${ENV_DEFAULTS.meeluBaseUrl}/api/v1${path}`, {
    method,
    headers,
    ...(body ? { body: JSON.stringify(body) } : {}),
  }).then(async (res) => {
    const json = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(json?.error?.message ?? `${method} ${path} failed (${res.status})`);
    }
    return json?.data ?? json;
  });
}

export async function pageExtractionLlm(llm, cookieHeader) {
  const target = { llm, cookieHeader, purpose: "page_review" };
  if (llm?.provider === "anthropic") {
    return {
      target: { ...target, llm: { ...llm, model: LLM_PAGE_EXTRACTION_MODEL } },
      model: LLM_PAGE_EXTRACTION_MODEL,
    };
  }
  const { model } = await resolveLlm(target);
  return { target: { ...target, model }, model };
}

function reviewPrompt(page, questions) {
  const asked = Object.entries(questions).map(([key, q]) => {
    const options = Object.entries(q.criteria)
      .map(([value, meaning]) => `  - ${value}: ${meaning}`)
      .join("\n");
    return `"${key}": ${q.instructions}\n${options}`;
  });
  const shape = Object.keys(questions)
    .map((key) => `"${key}": "<one option>"`)
    .join(", ");
  return [
    `URL: ${page.url}`,
    `Title: ${page.title ?? ""}`,
    `H1: ${(page.h1 ?? []).join(" | ")}`,
    `Meta description: ${page.metaDescription ?? ""}`,
    `Body text:\n${page.bodyText}`,
    "",
    "Answer every question with exactly one of its options.",
    "",
    asked.join("\n\n"),
    "",
    `Reply as {${shape}}.`,
  ].join("\n");
}

async function reviewSite(site, cookie, target, log) {
  const queue = await api(`/site/page-llm-extractions/review-queue?limit=${QUEUE_LIMIT}`, {
    siteId: site.id,
    cookieHeader: cookie,
  });
  const pages = Array.isArray(queue?.pages) ? queue.pages : [];
  let reviewed = 0;
  for (const page of pages) {
    try {
      const answers = await jsonCall(SYSTEM, reviewPrompt(page, queue.questions), {
        ...target.target,
        siteId: site.id,
      });
      await api(`/site/page-llm-extractions/by-page/${page.pageId}/review`, {
        method: "POST",
        siteId: site.id,
        cookieHeader: cookie,
        body: { contentHash: page.contentHash, model: target.model, answers },
      });
      reviewed += 1;
    } catch (err) {
      log(`page-review ${page.url} failed:`, err instanceof Error ? err.message : err);
    }
  }
  if (pages.length) log(`page-review ${site.domain}: ${reviewed}/${pages.length} page(s) reviewed`);
}

async function tick({ cookieHeader, llm, log }) {
  if (running) return;
  const cookie = await cookieHeader().catch(() => "");
  if (!cookie && !ENV_DEFAULTS.meeluApiKey) return;
  running = true;
  try {
    const sites = await api("/sites?page_size=100", { cookieHeader: cookie });
    if (!Array.isArray(sites) || !sites.length) return;
    const target = await pageExtractionLlm(llm(), cookie);
    for (const site of sites) {
      if (!site?.id) continue;
      try {
        await reviewSite(site, cookie, target, log);
      } catch (err) {
        log(`page-review ${site.domain} failed:`, err instanceof Error ? err.message : err);
      }
    }
  } catch (err) {
    log("page-review failed:", err instanceof Error ? err.message : err);
  } finally {
    running = false;
  }
}

export function startPageReviewSchedule(deps) {
  if (!ENABLED || timer || firstTick) return;
  const run = () => void tick(deps);
  firstTick = setTimeout(() => {
    firstTick = null;
    run();
    timer = setInterval(run, TICK_MS);
  }, FIRST_TICK_MS);
}
