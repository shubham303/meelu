const LLM_TELLS = [
  "delve",
  "leverage",
  "in today's landscape",
  "in today's fast-paced",
  "game-changer",
  "game changer",
  "unlock",
  "supercharge",
  "dive into",
  "elevate your",
  "it's not just",
  "it is not just",
  "in the ever-evolving",
  "seamlessly",
  "a testament to",
];

const MARKETING = ["don't miss out", "act now", "limited offer", "revolutionary", "next-level", "cutting-edge", "world-class"];

const RHETORICAL_OPENERS = ["ever wondered", "have you ever", "what if i told you", "did you know"];

const LONG_FORM_WORDS = 300;
const PARAGRAPH_MAX = 700;

function paragraphs(text) {
  return text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

function prose(text) {
  return paragraphs(text).filter((p) => !/^\s{0,3}(#{1,6}\s|[-*+]\s|\d+\.\s|!\[|>|\|)/.test(p));
}

function wordCount(text) {
  return text.split(/\s+/).filter(Boolean).length;
}

function findAllPhrases(text, phrases) {
  const lower = text.toLowerCase();
  const hits = [];
  for (const phrase of phrases) {
    const at = lower.indexOf(phrase.toLowerCase());
    if (at >= 0) hits.push(text.slice(at, at + phrase.length));
  }
  return hits;
}

function issue(code, title, detail, anchorText = null, suggestion = null) {
  return { code, title, detail, anchorText, suggestion };
}

function phrases(code, title, detail, list) {
  return (text) => {
    const hits = findAllPhrases(text, list);
    if (!hits.length) return null;
    const named = hits.length === 1 ? `"${hits[0]}"` : hits.map((h) => `"${h}"`).join(", ");
    return issue(code, `${title}: ${named}`, detail, hits[0]);
  };
}

const RULES = [
  (text) => {
    if (/^\s{0,3}#{2,3}\s+\S/m.test(text)) return null;
    if (wordCount(text) < LONG_FORM_WORDS) return null;
    return issue("no_headings", "No H2/H3 headings", "A page is scanned before it is read. Break it into sections with headings.");
  },
  (text) => {
    if (/\]\(\/[^)]*\)/.test(text)) return null;
    if (wordCount(text) < LONG_FORM_WORDS) return null;
    return issue("no_internal_links", "No links to other pages on the site", "Link related pages by path so the page sits inside the site rather than beside it.");
  },
  (text) => {
    const wall = prose(text).find((p) => p.length > PARAGRAPH_MAX);
    if (!wall) return null;
    return issue("wall_of_text", `A paragraph runs ${wall.length} characters`, "Short paragraphs, one idea each. Break this one up.", wall);
  },
  (text) => {
    const first = prose(text)[0] ?? "";
    const opening = (/^(.*?[.!?])(\s|$)/.exec(first)?.[1] ?? first).trim();
    if (!opening.endsWith("?")) return null;
    if (!findAllPhrases(opening, RHETORICAL_OPENERS).length) return null;
    return issue("rhetorical_opener", "Opens with a rhetorical question", "The first paragraph should answer what the reader searched for. Say it instead of asking.", opening);
  },
  phrases("llm_tells", "Reads as machine-written", "These phrases are the tells readers have learned to skip. Say the specific thing instead.", LLM_TELLS),
  phrases("marketing_cadence", "Marketing cadence", "Advertising copy reads as filler on an article. Plain and specific wins.", MARKETING),
];

export async function checkPageRules(text) {
  const body = String(text ?? "").replace(/\r\n/g, "\n").trim();
  const issues = RULES.map((check) => check(body)).filter(Boolean);
  return { summary: { rulesChecked: RULES.length, flagged: issues.length }, issues };
}
