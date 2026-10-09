import assert from "node:assert/strict";
import { register } from "node:module";
import { test } from "node:test";

register("../agent/electron-loader.mjs", import.meta.url);

const { LLM_PAGE_EXTRACTION_MODEL, pageExtractionLlm } = await import(
  "../../src/main/page-review/index.js"
);

test("claude connections review pages with haiku", async () => {
  const saved = { provider: "anthropic", model: "claude-opus-5-5", baseUrl: "", apiKey: "k" };
  const target = await pageExtractionLlm(saved);
  assert.equal(target.model, LLM_PAGE_EXTRACTION_MODEL);
  assert.equal(target.llm.model, LLM_PAGE_EXTRACTION_MODEL);
  assert.equal(target.llm.apiKey, "k");
});

test("a gateway connection reviews pages with its own model", async () => {
  const saved = { provider: "custom", model: "qwen3-32b", baseUrl: "http://localhost:11434", apiKey: "" };
  const target = await pageExtractionLlm(saved);
  assert.equal(target.model, "qwen3-32b");
  assert.equal(target.llm, saved);
});
