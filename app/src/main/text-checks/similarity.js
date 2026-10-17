import { bandFor, compare, contentTokens, intersectionSize, SHINGLE_K, shingles, tokenise } from "@meelu/similarity";
import { markdownParagraphs, pageParagraphs } from "./prose.js";
import { sitePageTexts } from "./pages.js";

const MIN_PARAGRAPH_WORDS = 12;
const CANDIDATE_DICE = 0.3;
const REPORT_CONTAINMENT = 30;
const DUPLICATE_CONTAINMENT = 60;
const MAX_PAGES_PER_PARAGRAPH = 3;
const MAX_ISSUES = 40;

const MIN_PAGE_WORDS = 50;
const PAGE_VOCABULARY_FLOOR = 0.35;
const PAGE_VERBATIM_FLOOR = 0.2;
const MAX_PAGES_COMPARED = 20;
const MAX_DUPLICATE_PAGES = 5;

function fingerprint(text) {
  const tokens = tokenise(text).map((t) => t.text);
  return { tokens, words: tokens.length, content: new Set(contentTokens(tokens)) };
}

function documentPrint(paragraphPrints) {
  const tokens = paragraphPrints.flatMap((p) => p.tokens);
  const content = new Set();
  for (const p of paragraphPrints) for (const term of p.content) content.add(term);
  return { words: tokens.length, content, shingles: shingles(tokens, SHINGLE_K) };
}

function pageLabel(page) {
  const title = (page.title ?? "").trim();
  return title || page.url;
}

function quote(text, max = 140) {
  const flat = text.replace(/\s+/g, " ").trim();
  return flat.length > max ? `${flat.slice(0, max - 1)}…` : flat;
}

function share(shared, size) {
  return size > 0 ? shared / size : 0;
}

function pageGate(draft, page) {
  const sharedTerms = intersectionSize(draft.content, page.print.content);
  const vocabulary = Math.max(share(sharedTerms, draft.content.size), share(sharedTerms, page.print.content.size));
  const sharedShingles = intersectionSize(draft.shingles, page.print.shingles);
  const verbatim = Math.max(share(sharedShingles, draft.shingles.size), share(sharedShingles, page.print.shingles.size));
  return { vocabulary, verbatim, passes: vocabulary >= PAGE_VOCABULARY_FLOOR || verbatim >= PAGE_VERBATIM_FLOOR };
}

function duplicatePages(draftText, draft, pages) {
  if (draft.words < MIN_PAGE_WORDS) return { screened: 0, compared: 0, hits: [] };
  const candidates = [];
  let screened = 0;
  for (const page of pages) {
    if (page.print.words < MIN_PAGE_WORDS) continue;
    screened += 1;
    const gate = pageGate(draft, page);
    if (gate.passes) candidates.push({ page, rank: Math.max(gate.vocabulary, gate.verbatim * 2) });
  }
  candidates.sort((x, y) => y.rank - x.rank);
  const compared = candidates.slice(0, MAX_PAGES_COMPARED);
  const hits = [];
  for (const { page } of compared) {
    const result = compare(draftText, page.bodyText);
    if (bandFor(result.overall) === "high") hits.push({ page, result });
  }
  hits.sort((x, y) => y.result.overall - x.result.overall);
  return { screened, compared: compared.length, hits: hits.slice(0, MAX_DUPLICATE_PAGES) };
}

function pageIssue({ page, result }) {
  const passage = result.passages[0]?.text;
  const evidence = passage ? ` Longest shared run: "${quote(passage)}".` : "";
  return {
    code: "duplicate_page",
    title: `This draft is ${result.overall}% the same as ${pageLabel(page)}`,
    detail:
      `${result.a.containment}% of this draft already appears on ${page.url}, and ${result.b.containment}% of that page appears here.${evidence} ` +
      "Two pages on the same thing split the ranking between them. Consider improving that page instead, or make this one cover what it does not.",
    anchorText: null,
    suggestion: null,
  };
}

function paragraphIndex(pages) {
  const entries = [];
  const byTerm = new Map();
  for (const page of pages) {
    for (const paragraph of page.paragraphs) {
      const slot = entries.length;
      entries.push({ page, paragraph });
      for (const term of paragraph.print.content) {
        const list = byTerm.get(term);
        if (list) list.push(slot);
        else byTerm.set(term, [slot]);
      }
    }
  }
  return { entries, byTerm };
}

function candidateParagraphs(paragraph, index) {
  const shared = new Map();
  for (const term of paragraph.print.content) {
    for (const slot of index.byTerm.get(term) ?? []) shared.set(slot, (shared.get(slot) ?? 0) + 1);
  }
  const size = paragraph.print.content.size;
  const out = [];
  for (const [slot, count] of shared) {
    const entry = index.entries[slot];
    const dice = (2 * count) / (size + entry.paragraph.print.content.size);
    if (dice >= CANDIDATE_DICE) out.push(entry);
  }
  return out;
}

function paragraphHits(paragraph, index) {
  const best = new Map();
  for (const { page, paragraph: candidate } of candidateParagraphs(paragraph, index)) {
    const result = compare(paragraph.text, candidate.text);
    const score = result.a.containment;
    if (score < REPORT_CONTAINMENT) continue;
    const current = best.get(page.id);
    if (!current || score > current.match.score) {
      best.set(page.id, {
        page,
        match: {
          score,
          passage: result.passages[0]?.text ?? null,
          exact: result.exactSentences,
          near: result.nearSentences,
          pageText: candidate.text,
        },
      });
    }
  }
  return Array.from(best.values());
}

function paragraphIssue(paragraph, page, match) {
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

const ISSUE_ORDER = { duplicate_page: 0, duplicate_paragraph: 1, similar_paragraph: 2 };

export async function checkSimilarity(text, context = {}, { loadPages = sitePageTexts } = {}) {
  const { siteId, cookieHeader = "", excludePageIds = [], excludeUrls = [] } = context;
  const draftParagraphs = markdownParagraphs(text).map((p) => ({ ...p, print: fingerprint(p.text) }));
  const draftText = draftParagraphs.map((p) => p.text).join("\n");
  const draft = documentPrint(draftParagraphs.map((p) => p.print));
  const paragraphs = draftParagraphs.filter((p) => p.print.words >= MIN_PARAGRAPH_WORDS);
  const empty = {
    pagesChecked: 0,
    pagesScreened: 0,
    pagesCompared: 0,
    duplicatePages: 0,
    paragraphsChecked: paragraphs.length,
    flagged: 0,
    maxScore: 0,
  };
  if (!paragraphs.length && draft.words < MIN_PAGE_WORDS) return { summary: empty, issues: [] };

  const skipIds = new Set(excludePageIds);
  const skipUrls = new Set(excludeUrls.map((u) => String(u).replace(/\/$/, "")));
  const pages = (await loadPages({ siteId, cookieHeader }))
    .filter((page) => !skipIds.has(page.id) && !skipUrls.has(page.url.replace(/\/$/, "")))
    .map((page) => {
      const all = pageParagraphs(page.bodyText).map((t) => ({ text: t, print: fingerprint(t) }));
      return {
        ...page,
        print: documentPrint(all.map((p) => p.print)),
        paragraphs: all.filter((p) => p.print.words >= MIN_PARAGRAPH_WORDS),
      };
    })
    .filter((page) => page.print.words > 0);

  const whole = duplicatePages(draftText, draft, pages);
  const issues = whole.hits.map(pageIssue);
  let maxScore = whole.hits.reduce((max, hit) => Math.max(max, hit.result.overall), 0);

  const index = paragraphIndex(pages);
  let flagged = 0;
  for (const paragraph of paragraphs) {
    const hits = paragraphHits(paragraph, index);
    if (!hits.length) continue;
    flagged += 1;
    hits.sort((x, y) => y.match.score - x.match.score);
    for (const { page, match } of hits.slice(0, MAX_PAGES_PER_PARAGRAPH)) {
      maxScore = Math.max(maxScore, match.score);
      issues.push(paragraphIssue(paragraph, page, match));
    }
  }

  issues.sort((x, y) => ISSUE_ORDER[x.code] - ISSUE_ORDER[y.code]);
  return {
    summary: {
      pagesChecked: pages.length,
      pagesScreened: whole.screened,
      pagesCompared: whole.compared,
      duplicatePages: whole.hits.length,
      paragraphsChecked: paragraphs.length,
      flagged,
      maxScore,
    },
    issues: issues.slice(0, MAX_ISSUES),
  };
}
