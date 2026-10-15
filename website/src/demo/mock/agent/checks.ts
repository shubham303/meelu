import { PAGES } from "../data/site";
import { sleep } from "./channel";

export interface CheckIssue {
  code: string;
  title: string;
  detail: string | null;
  anchorText: string | null;
  suggestion: string | null;
}

export interface CheckResult {
  summary: Record<string, unknown> | null;
  issues: CheckIssue[];
}

export const AVAILABLE_CHECKS = ["readability", "similarity", "ai_detector", "page_rules"];

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
  "seamlessly",
  "a testament to",
];
const MARKETING = ["don't miss out", "act now", "limited offer", "revolutionary", "next-level", "cutting-edge", "world-class"];
const RHETORICAL = ["ever wondered", "have you ever", "what if i told you", "did you know"];

function paragraphs(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((p) => p.trim())
    .filter(Boolean);
}

function prose(text: string): string[] {
  return paragraphs(text).filter((p) => !/^\s{0,3}(#{1,6}\s|[-*+]\s|\d+\.\s|!\[|>|\|)/.test(p));
}

function sentences(text: string): string[] {
  return prose(text)
    .flatMap((p) => p.split(/(?<=[.!?])\s+/))
    .map((s) => s.trim())
    .filter((s) => s.length > 0);
}

function words(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

function syllables(word: string): number {
  const w = word.toLowerCase().replace(/[^a-z]/g, "");
  if (!w) return 0;
  const groups = w.replace(/e$/, "").match(/[aeiouy]+/g);
  return Math.max(1, groups?.length ?? 1);
}

function findPhrase(text: string, list: string[]): { phrase: string; at: string } | null {
  const lower = text.toLowerCase();
  for (const phrase of list) {
    const i = lower.indexOf(phrase);
    if (i >= 0) {
      const sentence = sentences(text).find((s) => s.toLowerCase().includes(phrase));
      return { phrase: text.slice(i, i + phrase.length), at: sentence ?? text.slice(i, i + phrase.length) };
    }
  }
  return null;
}

function readability(text: string): CheckResult {
  const list = sentences(text);
  const wordList = prose(text).join(" ").split(/\s+/).filter(Boolean);
  if (wordList.length < 30) return { summary: null, issues: [] };
  const syl = wordList.reduce((n, w) => n + syllables(w), 0);
  const wps = wordList.length / Math.max(1, list.length);
  const spw = syl / wordList.length;
  const grade = Math.round((0.39 * wps + 11.8 * spw - 15.59) * 10) / 10;
  const flesch = Math.round(206.835 - 1.015 * wps - 84.6 * spw);
  const issues: CheckIssue[] = list
    .filter((s) => words(s) > 30)
    .slice(0, 4)
    .map((s) => ({
      code: "long_sentence",
      title: `Sentence runs to ${words(s)} words`,
      detail: "Readers skim on screen. Split it where the idea turns.",
      anchorText: s,
      suggestion: null,
    }));
  const passive = list.find((s) => /\b(is|are|was|were|be|been|being)\s+\w+ed\b/i.test(s) && words(s) > 12);
  if (passive) {
    issues.push({
      code: "passive_voice",
      title: "Passive voice hides who does what",
      detail: "Name the person or the product doing the action.",
      anchorText: passive,
      suggestion: null,
    });
  }
  return {
    summary: { grade, gradeLabel: grade <= 8 ? "Easy" : grade <= 11 ? "Plain" : "Dense", flesch, reliable: wordList.length >= 100 },
    issues,
  };
}

function similarity(text: string): CheckResult {
  const issues: CheckIssue[] = [];
  const lower = text.toLowerCase();
  if (lower.includes("net 30") || lower.includes("payment terms")) {
    const paragraph = prose(text).find((p) => /net 30|payment terms/i.test(p));
    const page = PAGES.find((p) => p.url.endsWith("/blog/invoice-payment-terms"));
    if (paragraph && page) {
      issues.push({
        code: "similar_paragraph",
        title: `Paragraph overlaps 41% with "${page.title}"`,
        detail: `Closest passage there: "Net 30 is the default, but net 15 gets you paid a week and a half sooner on average…". Found on ${page.url}. Rephrase the shared sentences or fold in a point that page does not make.`,
        anchorText: paragraph,
        suggestion: null,
      });
    }
  }
  return { summary: { pagesCompared: PAGES.filter((p) => p.status === 200).length, flagged: issues.length }, issues };
}

function aiDetector(text: string): CheckResult {
  const total = words(text);
  if (total < 80) return { summary: { verdict: "too-short", verdictLabel: "Too short to judge", words: total }, issues: [] };
  const tell = findPhrase(text, LLM_TELLS);
  const score = tell ? 62 : 14;
  const verdict = tell ? "mixed" : "human";
  const issues: CheckIssue[] = [];
  if (tell) {
    issues.push({
      code: "ai_mixed",
      title: `Partly machine-like — ${score}% (moderate confidence)`,
      detail: "Some passages read like generated text. Break the rhythm with a concrete detail or an opinion.",
      anchorText: null,
      suggestion: null,
    });
    issues.push({
      code: "ai_signal_stock_phrases",
      title: `Stock phrasing: "${tell.phrase}"`,
      detail: "Words models reach for and people rarely say. Say the plain thing.",
      anchorText: tell.at,
      suggestion: null,
    });
  }
  return {
    summary: {
      verdict,
      verdictLabel: tell ? "Mixed" : "Reads human",
      score,
      confidenceLabel: "Moderate",
      words: total,
      windows: Math.max(1, Math.round(total / 120)),
    },
    issues,
  };
}

function pageRules(text: string): CheckResult {
  const issues: CheckIssue[] = [];
  const tell = findPhrase(text, LLM_TELLS);
  if (tell) {
    issues.push({ code: "llm_tells", title: `LLM tells: ${tell.phrase}`, detail: "Readers spot these and stop trusting the page.", anchorText: tell.at, suggestion: null });
  }
  const marketing = findPhrase(text, MARKETING);
  if (marketing) {
    issues.push({ code: "marketing_cadence", title: `Marketing cadence: ${marketing.phrase}`, detail: "Advertising copy reads as filler on an article. Plain and specific wins.", anchorText: marketing.at, suggestion: null });
  }
  const opener = findPhrase(text, RHETORICAL);
  if (opener) {
    issues.push({ code: "rhetorical_opener", title: `Rhetorical opener: ${opener.phrase}`, detail: "Open with the answer, not a question the reader did not ask.", anchorText: opener.at, suggestion: null });
  }
  const long = prose(text).find((p) => p.length > 700);
  if (long) {
    issues.push({ code: "long_paragraph", title: `Paragraph of ${long.length} characters`, detail: "Past about 700 characters a paragraph reads as a wall on mobile. Split it.", anchorText: long, suggestion: null });
  }
  if (words(text) >= 300 && !/^#{2,3}\s/m.test(text)) {
    issues.push({ code: "no_subheadings", title: "No H2 or H3 in a long page", detail: "Readers and search engines both use subheadings to find their place.", anchorText: null, suggestion: null });
  }
  return { summary: { rulesChecked: 9, flagged: issues.length }, issues };
}

const CHECKS: Record<string, (text: string) => CheckResult> = {
  readability,
  similarity,
  ai_detector: aiDetector,
  page_rules: pageRules,
};

export async function checkContent(payload: { text: string; tools?: string[] }) {
  await sleep(1100 + Math.random() * 700);
  const wanted = payload.tools?.length ? payload.tools : AVAILABLE_CHECKS;
  const unknown = wanted.filter((t) => !CHECKS[t]);
  if (unknown.length) return { error: `Unknown check: ${unknown.join(", ")}` };
  const text = String(payload.text ?? "");
  const results: Record<string, CheckResult> = {};
  for (const tool of wanted) results[tool] = CHECKS[tool](text);
  return { results };
}
