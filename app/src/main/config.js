import path from "node:path";
import { fileURLToPath } from "node:url";
import dotenv from "dotenv";

const here = path.dirname(fileURLToPath(import.meta.url));

export const APP_ROOT = path.resolve(here, "../..");
export const REPO_ROOT = path.resolve(APP_ROOT, "..");

dotenv.config({ path: path.join(APP_ROOT, ".env"), quiet: true });

export const GSC_OAUTH_CLIENT = {
  clientId: process.env.MEELU_GSC_CLIENT_ID ?? "",
  clientSecret: process.env.MEELU_GSC_CLIENT_SECRET ?? "",
};

export const GA_OAUTH_CLIENT = {
  clientId: process.env.MEELU_GA_CLIENT_ID ?? "",
  clientSecret: process.env.MEELU_GA_CLIENT_SECRET ?? "",
};

export const OPENROUTER_BASE_URL = "https://openrouter.ai/api";

export const LLAMACPP_BASE_URL = "http://127.0.0.1:8080";

export const ENV_DEFAULTS = {
  meeluApiKey: process.env.MEELU_API_KEY ?? "",
  meeluBaseUrl: (process.env.MEELU_BASE_URL ?? "http://localhost:3000").replace(/\/$/, ""),
  agentMcpUrl: (process.env.MEELU_AGENT_MCP_URL ?? "http://127.0.0.1:8484/mcp/").replace(/\/?$/, "/"),
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
