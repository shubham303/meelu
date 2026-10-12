import type { AiCrawlerVerdict } from "./types";

type Rule = { allow: boolean; pattern: string };
type Group = { agents: string[]; rules: Rule[] };

export function parseRobots(text: string): Group[] {
  const groups: Group[] = [];
  let current: Group | null = null;

  for (const raw of text.split(/\r?\n/)) {
    const line = raw.split("#")[0].trim();
    const colon = line.indexOf(":");
    if (colon < 0) continue;
    const field = line.slice(0, colon).trim().toLowerCase();
    const value = line.slice(colon + 1).trim();

    if (field === "user-agent") {
      if (current === null || current.rules.length > 0) {
        current = { agents: [], rules: [] };
        groups.push(current);
      }
      if (value) current.agents.push(value.toLowerCase());
      continue;
    }
    if (field !== "allow" && field !== "disallow") continue;
    if (current === null) continue;
    current.rules.push({ allow: field === "allow", pattern: value });
  }

  return groups;
}

/** The most specific user-agent group wins, exactly as the crawlers read it. */
function rulesFor(groups: Group[], agent: string): Rule[] {
  const needle = agent.toLowerCase();
  let best = 0;
  for (const group of groups) {
    for (const named of group.agents) {
      if (named !== "*" && needle.startsWith(named) && named.length > best) {
        best = named.length;
      }
    }
  }
  const matches = (named: string) =>
    best === 0 ? named === "*" : named.length === best && needle.startsWith(named);

  return groups.filter((g) => g.agents.some(matches)).flatMap((g) => g.rules);
}

function pathMatcher(pattern: string): RegExp {
  const anchored = pattern.endsWith("$");
  const body = anchored ? pattern.slice(0, -1) : pattern;
  let escaped = "";
  for (const ch of body) {
    if (ch === "*") escaped += ".*";
    else if (".+?^${}()|[]\\".includes(ch)) escaped += `\\${ch}`;
    else escaped += ch;
  }
  return new RegExp(`^${escaped}${anchored ? "$" : ""}`);
}

/** Longest matching pattern wins; a tie goes to Allow, as Google documents. */
export function robotsAllows(robotsTxt: string, agent: string, path = "/"): boolean {
  const rules = rulesFor(parseRobots(robotsTxt), agent);
  let strongest = -1;
  let allowed = true;

  for (const rule of rules) {
    if (!rule.pattern) continue;
    if (!pathMatcher(rule.pattern).test(path)) continue;
    const weight = rule.pattern.length;
    if (weight > strongest || (weight === strongest && rule.allow)) {
      strongest = weight;
      allowed = rule.allow;
    }
  }

  return strongest === -1 ? true : allowed;
}

export function sitemapsIn(robotsTxt: string): string[] {
  const out: string[] = [];
  for (const raw of robotsTxt.split(/\r?\n/)) {
    const line = raw.split("#")[0].trim();
    const match = /^sitemap\s*:\s*(\S+)$/i.exec(line);
    if (match) out.push(match[1]);
  }
  return [...new Set(out)];
}

const ASSET_DISALLOW = /^\s*disallow:\s*(\S+)/i;
const ASSET_PATH = /(\.css|\.js|\.jpe?g|\.png|\.gif|\.webp|\.svg|\/wp-content|\/assets|\/static)/i;

export function disallowsAssets(robotsTxt: string): boolean {
  for (const line of robotsTxt.split("\n")) {
    const match = ASSET_DISALLOW.exec(line);
    const path = match?.[1];
    if (path && path !== "/" && ASSET_PATH.test(path)) return true;
  }
  return false;
}

export const AI_CRAWLERS: Array<Omit<AiCrawlerVerdict, "allowed">> = [
  { operator: "OpenAI", agent: "OAI-SearchBot", job: "search" },
  { operator: "OpenAI", agent: "ChatGPT-User", job: "fetch" },
  { operator: "OpenAI", agent: "GPTBot", job: "training" },
  { operator: "Anthropic", agent: "Claude-SearchBot", job: "search" },
  { operator: "Anthropic", agent: "Claude-User", job: "fetch" },
  { operator: "Anthropic", agent: "ClaudeBot", job: "training" },
  { operator: "Perplexity", agent: "PerplexityBot", job: "search" },
  { operator: "Perplexity", agent: "Perplexity-User", job: "fetch" },
  { operator: "Google", agent: "Google-Extended", job: "training" },
  { operator: "Apple", agent: "Applebot", job: "search" },
  { operator: "Apple", agent: "Applebot-Extended", job: "training" },
  { operator: "Amazon", agent: "Amazonbot", job: "search" },
  { operator: "Meta", agent: "Meta-ExternalAgent", job: "training" },
  { operator: "Common Crawl", agent: "CCBot", job: "training" },
];

export function aiCrawlerVerdicts(robotsTxt: string | null): AiCrawlerVerdict[] {
  return AI_CRAWLERS.map((crawler) => ({
    ...crawler,
    allowed: robotsTxt ? robotsAllows(robotsTxt, crawler.agent, "/") : true,
  }));
}
