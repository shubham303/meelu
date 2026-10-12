import { site } from "@/lib/site";
import { ProviderError, type Spend } from "./dataforseo";

const BASE_URL = "https://openrouter.ai/api";
export const DEFAULT_LLM_MODEL = "deepseek/deepseek-v4-flash";
const DEFAULT_JEV_MODEL = "~typesafe/jev-latest";

function apiKey(): string {
  const key = process.env.OPENROUTER_API_KEY?.trim();
  if (!key) throw new ProviderError("openrouter", "OPENROUTER_API_KEY is not set");
  return key;
}

export function llmModel(): string {
  return process.env.OPENROUTER_LLM_MODEL?.trim() || DEFAULT_LLM_MODEL;
}

function headers(): Record<string, string> {
  return {
    authorization: `Bearer ${apiKey()}`,
    "content-type": "application/json",
    "x-title": "Meelu",
    "http-referer": `${site.url}/tools/keyword-clustering-tool`,
  };
}

function timeout(signal: AbortSignal | undefined, ms: number): AbortSignal {
  return signal ? AbortSignal.any([signal, AbortSignal.timeout(ms)]) : AbortSignal.timeout(ms);
}

async function postJson(path: string, body: unknown, ms: number, signal?: AbortSignal) {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      method: "POST",
      headers: headers(),
      body: JSON.stringify(body),
      signal: timeout(signal, ms),
      cache: "no-store",
    });
  } catch (error) {
    throw new ProviderError("openrouter", `${path}: ${error instanceof Error ? error.message : error}`);
  }
  const json = (await response.json().catch(() => null)) as Record<string, unknown> | null;
  if (!response.ok || !json) {
    const detail = json?.error ? JSON.stringify(json.error).slice(0, 200) : "";
    throw new ProviderError("openrouter", `${path}: HTTP ${response.status} ${detail}`);
  }
  return json;
}

export type ChoiceQuestion = {
  type: "choice";
  instructions: string;
  criteria: Record<string, string>;
};

export type ChoiceAnswer = {
  choice: string;
  probabilities: Record<string, number>;
  confidence: number;
};

export async function decide(
  state: unknown,
  questions: Record<string, ChoiceQuestion>,
  spend: Spend,
  signal?: AbortSignal,
): Promise<Record<string, ChoiceAnswer>> {
  const body = await postJson(
    "/alpha/decisions",
    {
      model: process.env.OPENROUTER_JEV_MODEL?.trim() || DEFAULT_JEV_MODEL,
      state,
      questions,
    },
    60_000,
    signal,
  );
  const usage = body.usage as { cost?: number } | undefined;
  if (typeof usage?.cost === "number") spend.openrouter += usage.cost;
  const answers = body.answers as Record<string, ChoiceAnswer> | undefined;
  if (!answers || typeof answers !== "object") {
    throw new ProviderError("openrouter", "Jev returned no answers");
  }
  return answers;
}

export async function structuredChat<T>(
  system: string,
  user: string,
  schemaName: string,
  schema: Record<string, unknown>,
  spend: Spend,
  signal?: AbortSignal,
): Promise<T> {
  const body = await postJson(
    "/v1/chat/completions",
    {
      model: llmModel(),
      messages: [
        { role: "system", content: system },
        { role: "user", content: user },
      ],
      response_format: {
        type: "json_schema",
        json_schema: { name: schemaName, strict: true, schema },
      },
      reasoning: { effort: "low" },
      temperature: 0,
      usage: { include: true },
    },
    90_000,
    signal,
  );
  const usage = body.usage as { cost?: number } | undefined;
  if (typeof usage?.cost === "number") spend.openrouter += usage.cost;
  const choices = body.choices as Array<{ message?: { content?: string | null } }> | undefined;
  const content = choices?.[0]?.message?.content;
  if (!content) throw new ProviderError("openrouter", "the model returned no content");
  try {
    return JSON.parse(content) as T;
  } catch {
    throw new ProviderError("openrouter", "the model returned invalid JSON");
  }
}
