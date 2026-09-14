import assert from "node:assert/strict";
import { test } from "node:test";
import { compare } from "@meelu/similarity";
import { markdownParagraphs, pageParagraphs } from "../src/main/text-checks/prose.js";
import { checkSimilarity } from "../src/main/text-checks/similarity.js";

const COPIED =
  "Search engines reward pages that answer the question quickly, so put the answer in the first paragraph and the evidence below it where a reader who wants it can find it.";
const FRESH =
  "A slow cooker turns cheap cuts tender by holding them just under a simmer for hours, which is why the collagen melts instead of tightening.";

test("markdownParagraphs keeps raw slices anchored in the source", () => {
  const md = `# Title\n\nFirst para line one\nline two.\n\n- a list item\n\n\`\`\`js\ncode();\n\`\`\`\n\nLast one.`;
  const paras = markdownParagraphs(md);
  assert.deepEqual(
    paras.map((p) => p.text),
    ["Title", "First para line one line two.", "a list item", "Last one."],
  );
  for (const p of paras) assert.equal(md.slice(p.start, p.end), p.raw);
});

test("pageParagraphs strips crawler block markers", () => {
  assert.deepEqual(pageParagraphs("# Heading\n- item\n| cell\nplain\n\n"), ["Heading", "item", "cell", "plain"]);
});

test("compare flags a paraphrase and clears unrelated text", () => {
  assert.ok(compare(COPIED, COPIED.replace("quickly", "fast")).overall >= 60);
  assert.equal(compare(COPIED, FRESH).overall, 0);
});

test("checkSimilarity reports paragraph matches per page and skips excluded pages", async () => {
  const pages = [
    { id: "p1", url: "https://x.test/a", title: "Answer first", bodyText: `# Answer first\n${COPIED}\nother stuff here that is long enough to count as a paragraph on its own.` },
    { id: "p2", url: "https://x.test/b", title: "Soup", bodyText: FRESH },
    { id: "p3", url: "https://x.test/c", title: "Copy", bodyText: COPIED },
  ];
  const loadPages = async () => pages;
  const text = `Intro\n\n${COPIED}\n\n${FRESH}\n\nA totally new paragraph about pricing tiers, refunds, invoices and the small print that nobody reads until it matters.`;
  const result = await checkSimilarity(text, { siteId: "s", excludePageIds: ["p3"] }, { loadPages });
  assert.equal(result.summary.pagesChecked, 2);
  assert.equal(result.summary.flagged, 2);
  assert.equal(result.issues.length, 2);
  assert.ok(result.issues.every((i) => i.code === "duplicate_paragraph"));
  assert.ok(result.issues.every((i) => text.includes(i.anchorText)));
  assert.deepEqual(new Set(result.issues.map((i) => i.detail.includes("https://x.test/"))), new Set([true]));
});

test("checkAiDetect flags windows and anchors them in the body", async () => {
  const { checkAiDetect } = await import("../src/main/text-checks/ai-detect.js");
  const para =
    "Furthermore, it is important to note that search engines play a crucial role in the digital landscape. Moreover, businesses must leverage robust strategies to navigate the realm of content.";
  const body = Array.from({ length: 8 }, () => para).join("\n\n");
  const result = await checkAiDetect(body, {}, { scoreChunks: async (chunks) => chunks.map(() => 0.92) });
  assert.equal(result.summary.verdict, "ai");
  assert.equal(result.issues[0].code, "ai_ai");
  const passages = result.issues.filter((i) => i.code === "ai_passage");
  assert.ok(passages.length >= 1);
  for (const issue of result.issues) {
    if (issue.anchorText !== null) assert.ok(body.includes(issue.anchorText));
  }
  const short = await checkAiDetect("Too short.", {}, { scoreChunks: async () => [] });
  assert.equal(short.summary.verdict, "too-short");
  assert.deepEqual(short.issues, []);
});
