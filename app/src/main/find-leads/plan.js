import { jsonCall } from "../social-signals/llm.js";

export const KEYWORDS_PER_BRIEF = 2;
const MAX_TITLES = 3;
const MAX_LOCATIONS = 2;
export const WEB_ANGLES = 3;

const SYSTEM = `You turn briefs a founder wrote, each describing the kind of people they want to contact about their product, into searches.
Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"briefs":[{"id":"...","keywords":["...","..."],"linkedin":{"query":"...","titles":["..."],"locations":["..."]},"web":["...","...","..."]}]}

- One entry per brief, with the brief's id exactly as given.
- keywords: exactly ${KEYWORDS_PER_BRIEF} short phrases, two or three words each, that such a person would actually write in a social post about their problem. They run against literal keyword search, so write what the person says, not what the founder sells.
- linkedin.query: a short LinkedIn people-search query for who these people are (a role or business type), not their problem.
- linkedin.titles: up to ${MAX_TITLES} job titles these people hold. Empty if the brief does not imply one.
- linkedin.locations: up to ${MAX_LOCATIONS} places, ONLY when the brief names a place. Otherwise empty.
- web: exactly ${WEB_ANGLES} different web search angles for finding these people, each a short instruction naming who to look for and where, taken from the brief. Cover different places they show up: their own sites, directories and marketplaces, and posts they write. When the brief names more than one kind of person, give each kind its own angle.

Use the description of the founder's site to read ambiguous words the way their customers would. Never invent people or places the brief does not support.`;

function phrase(value) {
  return String(value ?? "").toLowerCase().split(/\s+/).filter(Boolean).join(" ");
}

function list(values, max) {
  const out = [];
  for (const v of Array.isArray(values) ? values : []) {
    const clean = String(v ?? "").split(/\s+/).filter(Boolean).join(" ");
    if (clean && !out.includes(clean)) out.push(clean);
  }
  return out.slice(0, max);
}

export function needsPlan(brief) {
  const sources = brief?.sources ?? [];
  const plan = brief?.plan ?? {};
  if (sources.includes("posts") && (plan.keywords ?? []).length !== KEYWORDS_PER_BRIEF) return true;
  if (sources.includes("linkedin") && !plan.linkedin?.query) return true;
  if (sources.includes("web") && (plan.web ?? []).length === 0) return true;
  return false;
}

export function plansByBrief(parsed, briefs) {
  const ids = new Set(briefs.map((b) => b.id));
  const out = new Map();
  for (const entry of Array.isArray(parsed?.briefs) ? parsed.briefs : []) {
    if (!ids.has(entry?.id)) continue;
    const keywords = [...new Set((entry.keywords ?? []).map(phrase).filter(Boolean))];
    const web = list(entry.web, WEB_ANGLES);
    if (keywords.length < KEYWORDS_PER_BRIEF && web.length === 0) continue;
    const query = String(entry.linkedin?.query ?? "").split(/\s+/).filter(Boolean).join(" ");
    out.set(entry.id, {
      keywords: keywords.length >= KEYWORDS_PER_BRIEF ? keywords.slice(0, KEYWORDS_PER_BRIEF) : [],
      ...(web.length ? { web } : {}),
      ...(query
        ? {
            linkedin: {
              query,
              titles: list(entry.linkedin?.titles, MAX_TITLES),
              locations: list(entry.linkedin?.locations, MAX_LOCATIONS),
            },
          }
        : {}),
    });
  }
  return out;
}

export async function planBriefs({ briefs, siteContext }, target) {
  if (briefs.length === 0) return new Map();
  const prompt = [
    `The briefs:\n${briefs.map((b) => JSON.stringify({ id: b.id, brief: b.text })).join("\n")}`,
    siteContext ? `The founder's site:\n${siteContext}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
  return plansByBrief(await jsonCall(SYSTEM, prompt, target), briefs);
}

const MORE_SYSTEM = `You help a founder find more people to contact. Earlier searches for each brief already ran, so every new search must differ from the ones listed as used.
Reply with ONLY a JSON object, no prose and no code fences, of this exact shape:
{"briefs":[{"id":"...","keywords":["...","..."],"web":["...","...","..."]}]}

- One entry per brief, with the brief's id exactly as given.
- keywords: only when the brief's sources include posts, exactly ${KEYWORDS_PER_BRIEF} new short phrases, two or three words each, that such a person would write in a social post. Never repeat or lightly reword a used one: pick other words, other problems, other ways people describe it.
- web: only when the brief's sources include web, exactly ${WEB_ANGLES} new search angles that reach people the used angles would not: other directories, marketplaces, communities, niches, regions or kinds of business. Never repeat a used angle.

Never invent people or places the brief does not support.`;

export async function morePlans({ briefs, siteContext }, target) {
  if (briefs.length === 0) return new Map();
  const prompt = [
    `The briefs:\n${briefs
      .map((b) =>
        JSON.stringify({
          id: b.id,
          brief: b.text,
          sources: b.sources,
          usedKeywords: b.usedKeywords,
          usedWebAngles: b.usedWeb,
        }),
      )
      .join("\n")}`,
    siteContext ? `The founder's site:\n${siteContext}` : "",
  ]
    .filter(Boolean)
    .join("\n\n");
  return freshPlans(await jsonCall(MORE_SYSTEM, prompt, target), briefs);
}

export function freshPlans(parsed, briefs) {
  const plans = plansByBrief(parsed, briefs);
  const byId = new Map(briefs.map((b) => [b.id, b]));
  for (const [id, plan] of plans) {
    const brief = byId.get(id);
    const usedKeywords = new Set((brief.usedKeywords ?? []).map(phrase));
    const usedWeb = new Set((brief.usedWeb ?? []).map((w) => w.toLowerCase()));
    const keywords = plan.keywords.filter((k) => !usedKeywords.has(k));
    const web = (plan.web ?? []).filter((w) => !usedWeb.has(w.toLowerCase()));
    plans.set(id, {
      keywords: keywords.length === KEYWORDS_PER_BRIEF ? keywords : [],
      web,
    });
  }
  return plans;
}
