import { createSdkMcpServer } from "@anthropic-ai/claude-agent-sdk";
import { mcpTools, toolNames } from "./tools.js";

export const PROVIDERS_SERVER = "providers";

export function providerToolNames(facades, domains) {
  const names = [];
  for (const facade of facades) {
    if (!domains.includes(facade.domain)) continue;
    names.push(...toolNames(facade.constructor));
  }
  return names;
}

export function providersMcpServer(facades, { domains = [], siteId = null, only = null } = {}) {
  const allowed = new Set(providerToolNames(facades, domains).filter((n) => !only || only.includes(n)));
  if (allowed.size === 0) return null;
  const tools = facades.flatMap((facade) => mcpTools(facade, { allowed, siteId }));
  return { server: createSdkMcpServer({ name: PROVIDERS_SERVER, version: "1.0.0", tools }), allowed };
}
