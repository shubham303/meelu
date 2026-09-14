import { connectorValues, providerDefault, setProviderDefault } from "../connector-config.js";
import { PROVIDER_CATALOG, PROVIDER_DOMAINS, providerEntry, secretKeys } from "./catalog.js";
import { errorPayload } from "./errors.js";
import { MeeluApi } from "./meelu.js";
import { DataForSeoAdapter } from "./seo-data/dataforseo.js";
import { SeoDataProvider } from "./seo-data/provider.js";
import { PostproxyAdapter } from "./social/postproxy.js";
import { SocialMediaScheduler } from "./social/scheduler.js";
import { toolHandlers } from "./tools.js";

export { PROVIDER_CATALOG, PROVIDER_DOMAINS, providerEntry, secretKeys, setProviderDefault };
export { providersMcpServer, providerToolNames, PROVIDERS_SERVER } from "./mcp.js";

const store = {
  connected: (id) => connectorValues(id),
  defaultFor: (domain) => providerDefault(domain),
};

export function createProviders({ cookieHeader = "" } = {}) {
  const meelu = new MeeluApi({ cookieHeader });
  const seo = new SeoDataProvider({ adapters: [new DataForSeoAdapter()], store, meelu });
  const social = new SocialMediaScheduler({ adapters: [new PostproxyAdapter()], store, meelu });
  return { seo, social, facades: [seo, social] };
}

export function providersStatus(providers) {
  return Object.fromEntries(providers.facades.map((f) => [f.domain, f.status()]));
}

export async function callProviderTool(providers, toolName, input) {
  for (const facade of providers.facades) {
    const handler = toolHandlers(facade).get(toolName);
    if (!handler) continue;
    try {
      return { ok: true, result: await handler(input ?? {}) };
    } catch (err) {
      return { ok: false, error: errorPayload(err) };
    }
  }
  return { ok: false, error: { code: "unknown_tool", message: `No provider tool named ${toolName}.` } };
}
