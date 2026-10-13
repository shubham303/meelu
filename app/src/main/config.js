import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";
import { app } from "electron";

const here = path.dirname(fileURLToPath(import.meta.url));

export const APP_ROOT = path.resolve(here, "../..");
export const REPO_ROOT = path.resolve(APP_ROOT, "..");

if (!app.isPackaged) dotenv.config({ path: path.join(APP_ROOT, ".env"), quiet: true });

const env = app.isPackaged ? {} : process.env;

const PACKAGED_ENDPOINTS = {
  prod: { meeluBaseUrl: "https://ui.meelu.tech", agentMcpUrl: "https://agent.meelu.tech/mcp/" },
  test: { meeluBaseUrl: "https://test-ui.meelu.tech", agentMcpUrl: "https://test-agent.meelu.tech/mcp/" },
};

function buildFlavour() {
  const pkg = JSON.parse(fs.readFileSync(path.join(APP_ROOT, "package.json"), "utf8"));
  return pkg.meeluFlavour === "test" ? "test" : "prod";
}

export const BUILD_FLAVOUR = buildFlavour();

export const INSTALLED_FROM_STORE = Boolean(process.windowsStore);

function updateManifestUrl() {
  if (INSTALLED_FROM_STORE) return "";
  if (!app.isPackaged) return env.MEELU_UPDATE_MANIFEST_URL ?? "";
  return `https://downloads.meelu.tech/${BUILD_FLAVOUR === "test" ? "test/" : ""}version.json`;
}

export const UPDATE_MANIFEST_URL = updateManifestUrl();

function bundledOauthClient() {
  try {
    return JSON.parse(fs.readFileSync(path.join(APP_ROOT, "oauth-client.json"), "utf8"));
  } catch {
    return {};
  }
}

const bundled = bundledOauthClient();

export const GSC_OAUTH_CLIENT = {
  clientId: env.MEELU_GSC_CLIENT_ID || bundled.clientId || "",
  clientSecret: env.MEELU_GSC_CLIENT_SECRET || bundled.clientSecret || "",
};

export const GA_OAUTH_CLIENT = {
  clientId: env.MEELU_GA_CLIENT_ID || bundled.clientId || "",
  clientSecret: env.MEELU_GA_CLIENT_SECRET || bundled.clientSecret || "",
};

export const ENV_DEFAULTS = app.isPackaged
  ? { meeluApiKey: "", ...PACKAGED_ENDPOINTS[BUILD_FLAVOUR] }
  : {
      meeluApiKey: env.MEELU_API_KEY ?? "",
      meeluBaseUrl: (env.MEELU_BASE_URL ?? "http://localhost:3000").replace(/\/$/, ""),
      agentMcpUrl: (env.MEELU_AGENT_MCP_URL ?? "http://127.0.0.1:8484/mcp/").replace(/\/?$/, "/"),
    };

export function meeluAuthHeaders(cookieHeader) {
  if (cookieHeader) return { Cookie: cookieHeader };
  if (ENV_DEFAULTS.meeluApiKey) return { "x-api-key": ENV_DEFAULTS.meeluApiKey };
  throw new Error(
    "Not signed in to Meelu — this window has no session, and there is no " +
      "MEELU_API_KEY to fall back on. Sign in in the app; if you are running " +
      "a script outside it, set MEELU_API_KEY (Dashboard → Settings → API keys).",
  );
}
