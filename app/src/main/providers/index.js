import { errorPayload } from "./errors.js";
import { MeeluApi } from "./meelu.js";
import { ProspectSourcesClient } from "./prospect_sources.js";
import { SocialListeningClient } from "./social_listening.js";
import { toolHandlers } from "./tools.js";

export { providersMcpServer, providerToolNames, PROVIDERS_SERVER } from "./mcp.js";

export function createProviders({ cookieHeader = "" } = {}) {
  const meelu = new MeeluApi({ cookieHeader });
  const listening = new SocialListeningClient({ meelu });
  const prospects = new ProspectSourcesClient({ meelu });
  return { listening, prospects, facades: [] };
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
