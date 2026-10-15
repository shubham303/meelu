import fs from "node:fs";
import { safeStorage } from "electron";
import { appFile, writeSecretFile } from "../../paths.js";

export function anthropicBaseUrl() {
  return process.env.MEELU_ANTHROPIC_BASE_URL || "https://api.anthropic.com";
}

export const ANTHROPIC_VERSION = "2023-06-01";
const OWN_ANTHROPIC_PREFIX = "own:anthropic/";
const MODEL_LIST_MS = 6 * 60 * 60 * 1000;

let modelList = { at: 0, key: "", models: [] };

function keysFile() {
  return appFile("llm-keys.json");
}

function readRecord() {
  try {
    return JSON.parse(fs.readFileSync(keysFile(), "utf8"));
  } catch {
    return {};
  }
}

export function ownModelId(model) {
  return `${OWN_ANTHROPIC_PREFIX}${model}`;
}

export function ownModelOf(value) {
  return typeof value === "string" && value.startsWith(OWN_ANTHROPIC_PREFIX)
    ? value.slice(OWN_ANTHROPIC_PREFIX.length)
    : null;
}

export function ownAnthropic() {
  const saved = readRecord().anthropic;
  if (!saved?.keyEnc) return null;
  try {
    const apiKey = safeStorage.decryptString(Buffer.from(saved.keyEnc, "base64"));
    return apiKey ? { apiKey, defaultModel: saved.defaultModel ?? "" } : null;
  } catch {
    return null;
  }
}

async function fetchAnthropicModels(apiKey) {
  const res = await fetch(`${anthropicBaseUrl()}/v1/models?limit=100`, {
    headers: { "x-api-key": apiKey, "anthropic-version": ANTHROPIC_VERSION },
    signal: AbortSignal.timeout(15_000),
  });
  if (res.status === 401 || res.status === 403) {
    throw new Error("Anthropic did not accept this API key.");
  }
  if (!res.ok) throw new Error(`Anthropic answered ${res.status} when listing models.`);
  const payload = await res.json();
  return (payload.data ?? []).map((m) => ({ id: m.id, name: m.display_name ?? m.id }));
}

export async function ownAnthropicModels() {
  const own = ownAnthropic();
  if (!own) return [];
  const fresh = modelList.key === own.apiKey && Date.now() - modelList.at < MODEL_LIST_MS;
  if (!fresh) {
    modelList = { at: Date.now(), key: own.apiKey, models: await fetchAnthropicModels(own.apiKey) };
  }
  return modelList.models;
}

function pickDefault(models, wanted) {
  if (wanted && models.some((m) => m.id === wanted)) return wanted;
  return (models.find((m) => m.id.includes("haiku")) ?? models[0])?.id ?? "";
}

export async function saveOwnAnthropic({ apiKey, defaultModel }) {
  const record = readRecord();
  if (apiKey === "") {
    delete record.anthropic;
    modelList = { at: 0, key: "", models: [] };
    writeSecretFile(keysFile(), JSON.stringify(record, null, 2));
    return;
  }
  const key = apiKey?.trim() || ownAnthropic()?.apiKey;
  if (!key) throw new Error("Paste an Anthropic API key first.");
  const models = await fetchAnthropicModels(key);
  if (!safeStorage.isEncryptionAvailable()) {
    throw new Error("Secure storage is unavailable on this machine, so the key was not saved.");
  }
  record.anthropic = {
    keyEnc: safeStorage.encryptString(key).toString("base64"),
    defaultModel: pickDefault(models, defaultModel ?? record.anthropic?.defaultModel),
  };
  modelList = { at: Date.now(), key, models };
  writeSecretFile(keysFile(), JSON.stringify(record, null, 2));
}

export function describeOwnKeys() {
  const own = ownAnthropic();
  return { anthropic: own ? { saved: true, defaultModel: own.defaultModel } : { saved: false, defaultModel: "" } };
}
