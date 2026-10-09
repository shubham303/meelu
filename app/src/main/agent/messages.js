const ANTHROPIC_BASE_URL = "https://api.anthropic.com";
const API_VERSION = "2023-06-01";
const MAX_TOKENS = 2048;
const TIMEOUT_MS = 120_000;
const ATTEMPTS = 4;
const RETRYABLE = new Set([408, 409, 429, 500, 502, 503, 504, 529]);

export function messagesEndpoint(gateway, anthropicKey) {
  if (gateway) {
    return {
      url: `${gateway.baseUrl.replace(/\/+$/, "")}/v1/messages`,
      headers: { authorization: `Bearer ${gateway.apiKey}` },
    };
  }
  const baseUrl = (process.env.ANTHROPIC_BASE_URL || ANTHROPIC_BASE_URL).replace(/\/+$/, "");
  const key = anthropicKey || process.env.ANTHROPIC_API_KEY;
  if (key) return { url: `${baseUrl}/v1/messages`, headers: { "x-api-key": key } };
  const token = process.env.ANTHROPIC_AUTH_TOKEN;
  if (token) return { url: `${baseUrl}/v1/messages`, headers: { authorization: `Bearer ${token}` } };
  return null;
}

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function retryDelay(res, attempt) {
  const after = Number(res?.headers.get("retry-after"));
  if (Number.isFinite(after) && after > 0) return Math.min(after * 1000, 30_000);
  return Math.min(1000 * 2 ** attempt, 15_000) + Math.random() * 500;
}

async function errorMessage(res) {
  const payload = await res.json().catch(() => null);
  return payload?.error?.message ?? `the model endpoint answered ${res.status}`;
}

export function messagesJudge({ endpoint, model, system, limits }) {
  const maxTokens = Math.min(MAX_TOKENS, limits?.output ?? MAX_TOKENS);
  return async (prompt) => {
    const body = JSON.stringify({
      model,
      max_tokens: maxTokens,
      system,
      messages: [{ role: "user", content: prompt }],
    });
    for (let attempt = 0; ; attempt += 1) {
      let res;
      try {
        res = await fetch(endpoint.url, {
          method: "POST",
          headers: {
            ...endpoint.headers,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
          },
          body,
          signal: AbortSignal.timeout(TIMEOUT_MS),
        });
      } catch (err) {
        if (attempt + 1 >= ATTEMPTS) throw err;
        await sleep(retryDelay(null, attempt));
        continue;
      }
      if (res.ok) {
        const payload = await res.json();
        return (payload.content ?? [])
          .filter((block) => block.type === "text")
          .map((block) => block.text)
          .join("");
      }
      if (!RETRYABLE.has(res.status) || attempt + 1 >= ATTEMPTS) {
        throw new Error(await errorMessage(res));
      }
      await sleep(retryDelay(res, attempt));
    }
  };
}
