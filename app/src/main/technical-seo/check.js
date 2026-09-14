import { query } from "@anthropic-ai/claude-agent-sdk";
import { llmEnv, resolveLlm } from "../agent/runner.js";

const MAX_BODY_CHARS = 6000;
const MAX_LIST_ITEMS = 40;
const MAX_TEXT_FILE_CHARS = 4000;

const SYSTEM = `You verify one technical SEO finding that a deterministic rule raised against one website or page.
The rule is a heuristic and can be wrong. Decide from the evidence whether the finding really applies.
Reply with ONLY a JSON object — no prose, no code fences — of this exact shape:
{"verdict":"keep"|"update"|"delete","issue":"...","reason":"..."}

- keep: the finding is correct and the explanation fits the evidence as written. Leave "issue" empty.
- update: the finding is correct but the explanation should be more specific to this evidence. Put the full replacement text in "issue": same tone, two to four sentences, naming what you saw and what to do.
- delete: the finding does not apply — the evidence shows the rule fired on something deliberate, harmless, or misread.
- reason: one sentence for the log.

Be conservative: delete only when the evidence clearly contradicts the finding. When unsure, keep.`;

const PAGE_FIELDS = {
  "soft-404": ["status", "title", "h1", "wordCount", "bodyText"],
  "thin-content": ["kind", "title", "wordCount", "headings", "bodyText"],
  "stale-content": ["kind", "title", "publishedAt", "modifiedAt", "contentChangedAt", "lastCrawledAt", "bodyText"],
  "date-inflation": ["kind", "title", "publishedAt", "modifiedAt", "contentChangedAt", "lastCrawledAt", "headings"],
  "heading-hierarchy-skip": ["title", "h1", "headings"],
  "image-missing-alt": ["title", "images"],
  "url-hygiene": ["title", "kind"],
  "url-stop-words": ["title", "kind"],
  "url-dated": ["title", "kind", "publishedAt"],
  "home-missing-contact-link": ["title", "outLinks", "externalLinks", "headings"],
  "home-missing-social-links": ["title", "externalLinks", "schemaNodes"],
  "home-missing-terms-link": ["title", "outLinks", "externalLinks"],
  "restrictive-snippet": ["title", "kind", "robotsDirectives", "xRobotsTag", "metaDescription"],
};

const SCHEMA_FIELDS = ["title", "kind", "schemaTypes", "schemaNodes", "headings"];

const SITE_FIELDS = {
  "robots-blocks-assets": ["robotsTxt", "robotsStatus"],
  "ai-permissions-inconsistent": ["robotsTxt", "robotsStatus", "crawlerAccess"],
  "host-variant-distinct": ["domain", "hostVariants"],
  "host-variant-elsewhere": ["domain", "hostVariants"],
};

function trimValue(key, value) {
  if (value == null) return null;
  if (key === "bodyText") return String(value).slice(0, MAX_BODY_CHARS);
  if (key === "robotsTxt" || key === "llmsTxt") return String(value).slice(0, MAX_TEXT_FILE_CHARS);
  if (Array.isArray(value)) return value.slice(0, MAX_LIST_ITEMS);
  return value;
}

function pick(record, keys) {
  const out = {};
  for (const key of keys) {
    const value = trimValue(key, record?.[key]);
    if (value !== null && value !== undefined && value !== "") out[key] = value;
  }
  return out;
}

export function pageFieldsFor(kind) {
  if (kind.startsWith("schema-")) return SCHEMA_FIELDS;
  return PAGE_FIELDS[kind] ?? ["title", "kind", "headings", "bodyText"];
}

export function siteFieldsFor(kind) {
  return SITE_FIELDS[kind] ?? ["domain", "robotsTxt", "hostVariants"];
}

function prompt(issue, subjectLabel, subject) {
  return [
    `Rule: ${issue.kind}`,
    `Severity: ${issue.severity}`,
    `Finding as written:\n${issue.issue}`,
    `${subjectLabel}:\n${JSON.stringify(subject, null, 1)}`,
  ].join("\n\n");
}

export function pagePrompt(issue, page) {
  return prompt(issue, "Page evidence", { url: page.url, ...pick(page, pageFieldsFor(issue.kind)) });
}

export function sitePrompt(issue, site) {
  return prompt(issue, "Site evidence", pick(site, siteFieldsFor(issue.kind)));
}

export function parseVerdict(text) {
  const raw = String(text ?? "").trim();
  const start = raw.indexOf("{");
  const end = raw.lastIndexOf("}");
  if (start === -1 || end <= start) throw new Error("The model returned no JSON object.");
  const parsed = JSON.parse(raw.slice(start, end + 1));
  const verdict = String(parsed.verdict ?? "").trim().toLowerCase();
  if (!["keep", "update", "delete"].includes(verdict)) {
    throw new Error(`The model returned an unknown verdict: ${verdict || "(empty)"}.`);
  }
  const issue = typeof parsed.issue === "string" ? parsed.issue.trim() : "";
  if (verdict === "update" && !issue) return { verdict: "keep", issue: null, reason: "update without text" };
  return {
    verdict,
    issue: verdict === "update" ? issue : null,
    reason: typeof parsed.reason === "string" ? parsed.reason.trim() : "",
  };
}

export async function judge(promptText, llm) {
  const { gateway, model, anthropicKey, limits } = await resolveLlm(llm);
  const q = query({
    prompt: promptText,
    options: {
      model,
      systemPrompt: SYSTEM,
      tools: [],
      allowedTools: [],
      permissionMode: "default",
      settingSources: [],
      maxTurns: 1,
      env: llmEnv(gateway, anthropicKey, limits),
    },
  });
  let output = null;
  for await (const m of q) {
    if (m.type === "result") {
      if (m.subtype !== "success" || m.is_error) {
        throw new Error(m.result || m.subtype || "The check run failed.");
      }
      output = m.result;
    }
  }
  if (output === null) throw new Error("The check run produced no result.");
  return { ...parseVerdict(output), model };
}
