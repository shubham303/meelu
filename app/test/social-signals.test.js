import assert from "node:assert/strict";
import test from "node:test";
import { verdictsFor } from "../src/main/social-signals/classify.js";
import { keywordsByLine } from "../src/main/social-signals/expand.js";
import { headersFor, jsonOf } from "../src/main/social-signals/llm.js";

test("expansion keeps exactly two cleaned keywords per known line", () => {
  const lines = [{ id: "a" }, { id: "b" }, { id: "c" }];
  const out = keywordsByLine(
    {
      lines: [
        { id: "a", keywords: ["Slow  WordPress", "site speed", "extra"] },
        { id: "b", keywords: ["same", "SAME"] },
        { id: "zzz", keywords: ["x y", "z w"] },
      ],
    },
    lines,
  );
  assert.deepEqual([...out], [["a", ["slow wordpress", "site speed"]]]);
});

test("verdicts leave unanswered posts without a verdict", () => {
  const posts = [{ id: "p0" }, { id: "p1" }, { id: "p2" }];
  const out = verdictsFor(
    {
      results: [
        { i: 0, fits: true, why: "Asks for help", angle: "Answer first" },
        { i: 1, fits: false, why: "Job ad", angle: "ignored" },
        { i: 2, why: "no fits field" },
      ],
    },
    posts,
  );
  assert.deepEqual(out[0].verdict, { fits: true, why: "Asks for help", angle: "Answer first" });
  assert.deepEqual(out[1].verdict, { fits: false, why: "Job ad", angle: null });
  assert.equal(out[2].verdict, null);
});

test("gateway calls send a bearer token and the meelu headers", () => {
  const headers = headersFor({
    apiKey: "mk_1",
    headers: { "x-meelu-purpose": "social_listening", "x-meelu-site": "site_1" },
  });
  assert.equal(headers.authorization, "Bearer mk_1");
  assert.equal(headers["x-meelu-purpose"], "social_listening");
  assert.equal(headers["x-api-key"], undefined);
});

test("own key calls go straight to Anthropic with x-api-key", () => {
  const headers = headersFor({ ownKey: true, apiKey: "sk-ant", headers: {} });
  assert.equal(headers["x-api-key"], "sk-ant");
  assert.equal(headers.authorization, undefined);
  assert.equal(headers["anthropic-version"], "2023-06-01");
});

test("the JSON object is read out of the text blocks", () => {
  const payload = { content: [{ type: "text", text: 'Sure:\n{"results":[]}\n' }] };
  assert.deepEqual(jsonOf(payload), { results: [] });
  assert.throws(() => jsonOf({ content: [] }), /no JSON object/);
});
