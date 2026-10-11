import fs from "node:fs";
import { safeStorage } from "electron";
import { appFile, writeSecretFile } from "../../paths.js";

const PROVIDERS = new Set(["meelu", "anthropic"]);

function configFile() {
  return appFile("llm-config.json");
}

function named(value) {
  return PROVIDERS.has(value) ? value : "meelu";
}

export function loadLlmConfig() {
  let raw;
  try {
    raw = JSON.parse(fs.readFileSync(configFile(), "utf8"));
  } catch {
    return { provider: "meelu", model: "", apiKey: "" };
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
    model: provider === "anthropic" ? (raw.model ?? "") : "",
    apiKey: provider === "anthropic" ? apiKey : "",
  };
}

export function saveLlmConfig({ provider, model, apiKey }) {
  const prev = loadLlmConfig();
  const record = { provider: named(provider) };
  if (record.provider === "anthropic") {
    record.model = (model ?? "").trim();
    const key = apiKey === undefined ? (prev.provider === "anthropic" ? prev.apiKey : "") : apiKey.trim();
    if (key) {
      if (!safeStorage.isEncryptionAvailable()) {
        throw new Error("Secure storage is unavailable on this machine, so the key was not saved.");
      }
      record.apiKeyEnc = safeStorage.encryptString(key).toString("base64");
    }
  }
  writeSecretFile(configFile(), JSON.stringify(record, null, 2));
}

export function describeLlmConfig() {
  const cfg = loadLlmConfig();
  return { provider: cfg.provider, model: cfg.model, hasApiKey: cfg.apiKey !== "" };
}
