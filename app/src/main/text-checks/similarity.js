import { compare, contentTokens, tokenise } from "@meelu/similarity";
import { markdownParagraphs, pageParagraphs } from "./prose.js";
import { sitePageTexts } from "./pages.js";

const MIN_PARAGRAPH_WORDS = 12;
const CANDIDATE_DICE = 0.3;
const REPORT_CONTAINMENT = 30;
const DUPLICATE_CONTAINMENT = 60;
const MAX_PAGES_PER_PARAGRAPH = 3;
const MAX_ISSUES = 40;

function fingerprint(text) {
  const tokens = tokenise(text).map((t) => t.text);
  return { words: tokens.length, content: new Set(contentTokens(tokens)) };
}

function dice(a, b) {
  if (a.size === 0 || b.size === 0) return 0;
  const [small, large] = a.size <= b.size ? [a, b] : [b, a];
  let shared = 0;
  for (const term of small) if (large.has(term)) shared += 1;
  return (2 * shared) / (a.size + b.size);
}

function pageLabel(page) {
  const title = (page.title ?? "").trim();
  return title || page.url;
}

function quote(text, max = 140) {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max - 1)}…` : flat;
}

function bestMatch(paragraph, page) {
  let best = null;
  for (const candidate of page.paragraphs) {
    if (dice(paragraph.print.content, candidate.print.content) < CANDIDATE_DICE) continue;
    const result = compare(paragraph.text, candidate.text);
    const score = result.a.containment;
    if (score < REPORT_CONTAINMENT) continue;
    if (!best || score > best.score) {
      best = {
        score,
        passage: result.passages[0]?.text ?? null,
        exact: result.exactSentences,
        near: result.nearSentences,
        pageText: candidate.text,
      };
    }
  }
  return best;
}

function issueFor(paragraph, page, match) {
  const duplicate = match.score >= DUPLICATE_CONTAINMENT;
  const where = `${pageLabel(page)} (${page.url})`;
  const evidence = match.passage
    ? `Shared wording: "${quote(match.passage)}"`
    : `Closest passage there: "${quote(match.pageText)}"`;
  return {
    code: duplicate ? "duplicate_paragraph" : "similar_paragraph",
    title: duplicate
      ? `${match.score}% of this paragraph already lives on ${pageLabel(page)}`
      : `Paragraph overlaps ${match.score}% with ${pageLabel(page)}`,
    detail: `${evidence}. Found on ${where}. ${
      duplicate
        ? "Two pages saying the same thing split the ranking between them — rewrite this so it adds something, or link to that page instead."
        : "Rephrase the shared sentences or fold in a point that page does not make."
    }`,
    anchorText: paragraph.raw,
    suggestion: null,
  };
}

export async function checkSimilarity(text, context = {}, { loadPages = sitePageTexts } = {}) {
  const { siteId, cookieHeader = "", excludePageIds = [], excludeUrls = [] } = context;
  const paragraphs = markdownParagraphs(text)
    .map((p) => ({ ...p, print: fingerprint(p.text) }))
    .filter((p) => p.print.words >= MIN_PARAGRAPH_WORDS);
  const empty = { pagesChecked: 0, paragraphsChecked: paragraphs.length, flagged: 0, maxScore: 0 };
  if (!paragraphs.length) return { summary: empty, issues: [] };

  const skipIds = new Set(excludePageIds);
  const skipUrls = new Set(excludeUrls.map((u) => String(u).replace(/\/$/, "")));
  const pages = (await loadPages({ siteId, cookieHeader }))
    .filter((page) => !skipIds.has(page.id) && !skipUrls.has(page.url.replace(/\/$/, "")))
    .map((page) => ({
      ...page,
      paragraphs: pageParagraphs(page.bodyText)
        .map((t) => ({ text: t, print: fingerprint(t) }))
        .filter((p) => p.print.words >= MIN_PARAGRAPH_WORDS),
    }))
    .filter((page) => page.paragraphs.length > 0);

  const issues = [];
  let maxScore = 0;
  let flagged = 0;
  for (const paragraph of paragraphs) {
    const hits = [];
    for (const page of pages) {
      const match = bestMatch(paragraph, page);
      if (match) hits.push({ page, match });
    }
    if (!hits.length) continue;
    flagged += 1;
    hits.sort((x, y) => y.match.score - x.match.score);
    for (const { page, match } of hits.slice(0, MAX_PAGES_PER_PARAGRAPH)) {
      maxScore = Math.max(maxScore, match.score);
      issues.push(issueFor(paragraph, page, match));
    }
  }

  issues.sort((x, y) => (x.code === y.code ? 0 : x.code === "duplicate_paragraph" ? -1 : 1));
  return {
    summary: { pagesChecked: pages.length, paragraphsChecked: paragraphs.length, flagged, maxScore },
    issues: issues.slice(0, MAX_ISSUES),
  };
}
