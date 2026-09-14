import { fetch as pooledFetch, FormData } from "undici";
import { ProviderRequestError } from "./errors.js";

const ATTEMPTS = 3;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function backoff(attempt) {
  const base = Math.min(500 * 2 ** attempt, 8000);
  return base + Math.random() * base * 0.5;
}

async function readBody(res) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function withQuery(url, query) {
  if (!query) return url;
  const u = new URL(url);
  for (const [k, v] of Object.entries(query)) {
    if (v !== undefined && v !== null) u.searchParams.set(k, String(v));
  }
  return u.toString();
}

export async function vendorRequest(
  providerId,
  url,
  { method = "GET", headers = {}, json, form, query, timeoutMs = 30_000 } = {},
) {
  const target = withQuery(url, query);
  let body;
  const sendHeaders = { ...headers };
  if (form) {
    body = form instanceof FormData ? form : buildForm(form);
  } else if (json !== undefined) {
    body = JSON.stringify(json);
    sendHeaders["content-type"] = "application/json";
  }

  let last;
  for (let attempt = 0; attempt < ATTEMPTS; attempt += 1) {
    let res;
    try {
      res = await pooledFetch(target, {
        method,
        headers: sendHeaders,
        body,
        signal: AbortSignal.timeout(timeoutMs),
      });
    } catch (err) {
      last = new ProviderRequestError(
        providerId,
        null,
        `${providerId} is unreachable: ${err instanceof Error ? err.message : err}`,
      );
      if (attempt + 1 < ATTEMPTS) await sleep(backoff(attempt));
      continue;
    }
    const parsed = await readBody(res);
    if (res.status === 429 || res.status >= 500) {
      last = new ProviderRequestError(
        providerId,
        res.status,
        `${providerId} answered ${res.status}`,
        parsed,
      );
      if (attempt + 1 < ATTEMPTS) await sleep(backoff(attempt));
      continue;
    }
    if (res.status >= 400) {
      throw new ProviderRequestError(
        providerId,
        res.status,
        `${providerId} answered ${res.status}`,
        parsed,
      );
    }
    return parsed;
  }
  throw last;
}

export function buildForm(fields) {
  const form = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    if (value === undefined || value === null) continue;
    if (Array.isArray(value)) {
      for (const one of value) form.append(key, String(one));
    } else if (value && typeof value === "object" && value.data instanceof Uint8Array) {
      form.append(key, new Blob([value.data], { type: value.contentType }), value.filename);
    } else {
      form.append(key, String(value));
    }
  }
  return form;
}
