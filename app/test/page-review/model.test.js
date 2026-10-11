import assert from "node:assert/strict";
import { register } from "node:module";
import { test } from "node:test";

register("../agent/electron-loader.mjs", import.meta.url);

const { LLM_PAGE_EXTRACTION_MODEL, pageExtractionLlm } = await import(
  "../../src/main/page-review/index.js"
);

test("claude connections review pages with haiku", async () => {
  const saved = { provider: "anthropic", model: "claude-opus-5-5", apiKey: "k" };
  const { target, model } = await pageExtractionLlm(saved, "");
  assert.equal(model, LLM_PAGE_EXTRACTION_MODEL);
  assert.equal(target.llm.model, LLM_PAGE_EXTRACTION_MODEL);
  assert.equal(target.llm.apiKey, "k");
  assert.equal(target.purpose, "page_review");
});
