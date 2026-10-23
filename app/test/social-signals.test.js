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
        { i: 0, why: "Asks for help", angle: "Answer first" },
        { i: 1, why: " ", angle: "" },
        { i: 7, why: "out of range" },
      ],
    },
    posts,
  );
  assert.deepEqual(out[0].verdict, { why: "Asks for help", angle: "Answer first" });
  assert.deepEqual(out[1].verdict, { why: null, angle: null });
  assert.equal(out[2].verdict, null);
});

test("lines searched on the web in the last 12 hours are skipped", async () => {
  const { recentLines } = await import("../src/main/social-signals/web.js");
  const now = Date.parse("2026-10-23T12:00:00Z");
  const lines = [{ text: "Cancel  Ahrefs" }, { text: "seo is too slow" }];
  const out = recentLines(
    lines,
    [
      { query: "cancel ahrefs", searchedAt: "2026-10-23T05:00:00Z" },
      { query: "seo is too slow", searchedAt: "2026-10-22T20:00:00Z" },
    ],
    now,
  );
  assert.deepEqual(out.fresh, [{ text: "seo is too slow" }]);
  assert.deepEqual(out.skippedQueries, [{ query: "Cancel  Ahrefs", searchedAt: "2026-10-23T05:00:00Z" }]);
});

test("streamed answers are read from their text deltas", async () => {
  const { sseEvents, jsonOfText } = await import("../src/main/social-signals/llm.js");
  const frames =
    'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"{\\"a\\":"}}\n\n' +
    'event: content_block_delta\ndata: {"type":"content_block_delta","delta":{"type":"text_delta","text":"1}"}}\n\nevent: ping\ndata: {"ty';
  const { events, rest } = sseEvents(frames);
  assert.equal(events.length, 2);
  assert.equal(rest, 'event: ping\ndata: {"ty');
  assert.deepEqual(jsonOfText(events.map((e) => e.delta.text).join("")), { a: 1 });
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

test("web posts need a real url, a title or text and a date from the last 30 days, and skip hosts searched on their own", async () => {
  const { skippedHosts, webPosts } = await import("../src/main/social-signals/web.js");
  const now = Date.parse("2026-10-20T00:00:00Z");
  const skipped = skippedHosts(["reddit", "hackernews", "web"]);
  assert.deepEqual(skipped, ["reddit.com", "redd.it", "news.ycombinator.com"]);
  const posts = webPosts(
    {
      posts: [
        { url: "forum.example.org/t/slow/1", title: "Site got slow", text: " help ", author: "ana", published: "2026-10-12" },
        { url: "https://old.reddit.com/r/seo/comments/abc", title: "Reddit", published: "2026-10-12" },
        { url: "https://q.example.net/9", title: "Old", published: "2026-08-01" },
        { url: "https://q.example.net/10", title: "Undated" },
        { url: "https://q.example.net/11", published: "2026-10-18" },
        { url: "javascript:alert(1)", title: "Bad", published: "2026-10-18" },
      ],
    },
    skipped,
    now,
  );
  assert.deepEqual(posts, [
    {
      url: "https://forum.example.org/t/slow/1",
      title: "Site got slow",
      text: "help",
      authorName: "ana",
      postedAt: "2026-10-12T00:00:00.000Z",
    },
  ]);
});
