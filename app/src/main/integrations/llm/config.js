import fs from "node:fs";
import { safeStorage } from "electron";
import { LLAMACPP_BASE_URL, OPENROUTER_BASE_URL } from "../../config.js";
import { appFile } from "../../paths.js";

const PROVIDERS = new Set(["anthropic", "openrouter", "llamacpp", "custom"]);

function configFile() {
  return appFile("llm-config.json");
}

function named(value) {
  return PROVIDERS.has(value) ? value : "anthropic";
}

function urlFor(provider, stored) {
  if (provider === "openrouter") return OPENROUTER_BASE_URL;
  if (provider === "llamacpp") return stored || LLAMACPP_BASE_URL;
  return stored ?? "";
}

export function loadLlmConfig() {
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(configFile(), "utf8"));
  } catch {
    return null;
  }
  let apiKey = "";
  if (raw.apiKeyEnc) {
    try {
      apiKey = safeStorage.decryptString(Buffer.from(raw.apiKeyEnc, "base64"));
    } catch {
      apiKey = "";
    }
  }
  const provider = named(raw.provider);
  return {
    provider,
    model: raw.model ?? "",
    baseUrl: urlFor(provider, raw.baseUrl),
    apiKey,
  };
}

export function saveLlmConfig({ provider, model, baseUrl, apiKey }) {
  const prev = loadLlmConfig();
  const key = apiKey === undefined ? (prev?.apiKey ?? "") : apiKey.trim();
  const record = {
    provider: named(provider),
    model: (model ?? "").trim(),
    baseUrl: (baseUrl ?? "").trim().replace(/\/+$/, ""),
  };
  if (record.provider === "custom" && !record.baseUrl) {
    throw new Error("A custom provider needs a base URL (e.g. http://localhost:11434).");
  }
  if (record.provider === "openrouter") {
    record.baseUrl = "";
    if (!key) {
      throw new Error("OpenRouter needs an API key — create one at openrouter.ai/keys.");
    }
    if (!record.model) {
      throw new Error(
        "OpenRouter needs a model id, written provider-first (e.g. anthropic/claude-sonnet-5).",
      );
    }
  }
  if (key) {
    if (!safeStorage.isEncryptionAvailable()) {
      throw new Error("Secure storage is unavailable on this machine, so the key was not saved.");
    }
    record.apiKeyEnc = safeStorage.encryptString(key).toString("base64");
  }
  fs.writeFileSync(configFile(), JSON.stringify(record, null, 2));
}

export function describeLlmConfig() {
  const cfg = loadLlmConfig();
  if (!cfg) return { saved: false, provider: "anthropic", model: "", baseUrl: "", hasApiKey: false };
  return {
    saved: true,
    provider: cfg.provider,
    model: cfg.model,
    baseUrl: cfg.baseUrl,
    hasApiKey: cfg.apiKey !== "",
  };
}
