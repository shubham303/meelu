import { checkReadability } from "@meelu/readability";
import { checkAiDetect } from "./ai-detect.js";
import { checkChannelRules } from "./channel-rules.js";
import { checkSimilarity } from "./similarity.js";

const CHECKS = {
  readability: async (text) => {
    const result = checkReadability(text);
    return {
      summary: result.grade === null ? null : { grade: result.grade, gradeLabel: result.gradeLabel, flesch: result.flesch, reliable: result.reliable },
      issues: result.issues,
    };
  },
  similarity: checkSimilarity,
  ai_detector: checkAiDetect,
  channel_rules: checkChannelRules,
};

export const AVAILABLE_CHECKS = Object.keys(CHECKS);

export async function runTextChecks({ text, tools, siteId, excludePageIds, excludeUrls, channelKey, hasMedia } = {}, { cookieHeader = "", modelDir = null } = {}) {
  const body = typeof text === "string" ? text : "";
  const wanted = Array.isArray(tools) && tools.length ? tools : AVAILABLE_CHECKS;
  const unknown = wanted.filter((t) => !CHECKS[t]);
  if (unknown.length) throw new Error(`Unknown check: ${unknown.join(", ")}`);
  const context = {
    siteId,
    cookieHeader,
    modelDir,
    channelKey: typeof channelKey === "string" ? channelKey : null,
    hasMedia: !!hasMedia,
    excludePageIds: Array.isArray(excludePageIds) ? excludePageIds : [],
    excludeUrls: Array.isArray(excludeUrls) ? excludeUrls : [],
  };
  const results = {};
  for (const tool of wanted) results[tool] = await CHECKS[tool](body, context);
  return results;
}
