import assert from "node:assert/strict";
import fs from "node:fs";
import { register } from "node:module";
import os from "node:os";
import path from "node:path";
import { after, before, test } from "node:test";
import { CATALOG, meeluTools, startLlm, startMcp, startScopeApi, systemText } from "./fakes.mjs";

register("./electron-loader.mjs", import.meta.url);

let scopeApi;
let mcp;
let llm;
let runner;
let cwd;

before(async () => {
  [scopeApi, mcp, llm] = await Promise.all([startScopeApi(), startMcp(), startLlm()]);
  process.env.MEELU_BASE_URL = scopeApi.url;
  process.env.MEELU_AGENT_MCP_URL = mcp.url;
  process.env.MEELU_API_KEY = "emcp_test_key";
  process.env.MEELU_LLM_BASE_URL = llm.url;
  process.env.MEELU_LLM_API_KEY = "test";
  process.env.MEELU_LLM_MODEL = "claude-haiku-4-5-20251001";
  cwd = fs.mkdtempSync(path.join(os.tmpdir(), "meelu-runner-test-"));
  runner = await import("../../src/main/agent/runner.js");
});

after(() => {
  runner?.closeAgentSessions();
  scopeApi?.close();
  mcp?.close();
  llm?.close();
});

async function turn(message, sessionId, { action = "ask-pages", askPermission = async () => "allow", history } = {}) {
  const events = [];
  let sid = sessionId;
  await runner.runAgentTurn(
    { action, siteId: "site_test", message, sessionId, form: {}, history },
    (event, data) => {
      events.push([event, data]);
      if (event === "session") sid = data.sessionId;
    },
    { cwd, abortController: new AbortController(), askPermission },
  );
  const done = events.find(([e]) => e === "done")?.[1];
  return { sessionId: sid, done, events };
}

const PAGES_TOOLS = ["delete_note", "find_plans", "get_plan", "run_sql", "save_note", "search_page", "update_note"];
const CONTENT_TOOLS = [...PAGES_TOOLS, "content_create_piece", "content_update_piece"].sort();

test("one task reads the catalog once across three turns, and sends only its own desk's tools", async () => {
  llm.script.push({ text: "one" }, { text: "two" }, { text: "three" });
  const first = await turn("turn one");
  assert.equal(first.done.ok, true, first.done.error);
  assert.ok(first.sessionId);
  const second = await turn("turn two", first.sessionId);
  const third = await turn("turn three", first.sessionId);
  assert.equal(second.done.ok, true);
  assert.equal(third.done.ok, true);

  assert.equal(llm.requests.length, 3);
  assert.equal(mcp.counts["tools/list"], 1, "the app reads the catalog once; the CLI lists the runner's server");
  assert.equal(mcp.counts.initialize, 1, "no connection to the agent server until a tool is called");

  for (const req of llm.requests) {
    assert.deepEqual(meeluTools(req), PAGES_TOOLS);
    assert.ok(!req.tools.some((t) => t.name === "mcp__meelu__cluster"), "analytics engine hidden on pages");
    assert.ok(req.tools.some((t) => t.name === "mcp__desks__add_desk"), "add_desk offered");
  }
  assert.equal(scopeApi.calls.length, 1, "scope fetched once per task, not per turn");
});

test("the system prompt sent to the model is the scope prompt plus the runner blocks", async () => {
  const req = llm.requests[0];
  const sys = systemText(req);
  assert.ok(sys.includes("PAGES DESK PROMPT. Answer about the site's pages."));
  assert.ok(sys.includes("## The database"));
  assert.ok(sys.includes("## You can read the open web"));
  assert.ok(sys.includes("## Delegating bulk reads"));
  assert.ok(sys.includes("## The website this task is about"));
  assert.ok(sys.includes("site_id = 'site_test'"));
  assert.ok(sys.includes("## What this task may write"));
  assert.ok(sys.includes("`save_note`"));
  assert.ok(sys.includes("## Other desks (load on demand)"));
  assert.ok(sys.includes("- content: content desk"));
  assert.ok(sys.includes("- analytics: analytics desk"));
  assert.ok(!sys.includes("- pages:"), "the loaded desk is not offered again");
  for (const hidden of CATALOG.filter((t) => t.desk && t.desk !== "pages")) {
    assert.ok(!sys.includes(hidden.name), `${hidden.name} leaked into the prompt`);
  }
  const text = sys.split("\n").filter((l) => l.trim()).join("\n");
  assert.equal(sys, systemText(llm.requests[2]), "prompt is stable across turns of one task");
  assert.ok(text.length > 0);
});

test("add_desk sends the desk's tools on the next model call without a new handshake", async () => {
  const before = { ...mcp.counts };
  llm.script.push({ tool: "mcp__desks__add_desk", input: { desk: "content" } }, { text: "after add" });
  const start = llm.requests.length;
  const res = await turn("write a page");
  assert.equal(res.done.ok, true, res.done.error);
  const [beforeAdd, afterAdd] = llm.requests.slice(start);
  assert.deepEqual(meeluTools(beforeAdd), PAGES_TOOLS);
  assert.deepEqual(meeluTools(afterAdd), CONTENT_TOOLS);
  assert.ok(!afterAdd.tools.some((t) => t.name === "mcp__meelu__cluster"), "analytics still hidden");

  const last = afterAdd.messages.at(-1).content;
  const result = last.find((b) => b.type === "tool_result");
  const resultText = typeof result.content === "string" ? result.content : result.content.map((c) => c.text).join("");
  assert.ok(resultText.includes("BRIEF FOR CONTENT"), "the desk brief comes back as the tool result");

  assert.equal(mcp.counts["tools/list"] - before["tools/list"], 0, "new task: catalog cached, no agent server listing");
  assert.equal(scopeApi.calls.at(-1).desks, "content", "scope refetched with the added desk");
  assert.equal(scopeApi.calls.length, 3);
});

test("silent writes of an approved job skip the permission prompt", async () => {
  const asked = [];
  const askPermission = async ({ tool }) => {
    asked.push(tool);
    return "allow";
  };
  llm.script.push(
    { tool: "mcp__meelu__start_structure_job", input: { q: "link related articles" } },
    { tool: "mcp__meelu__screen_link_suggestions", input: { job_id: "sjob_1" } },
    { tool: "mcp__meelu__rank_link_suggestions", input: { job_id: "sjob_1" } },
    { tool: "mcp__meelu__rank_link_suggestions", input: { job_id: "sjob_2" } },
    { text: "done" },
  );
  const res = await turn("link related articles", undefined, { action: "ask-site", askPermission });
  assert.equal(res.done.ok, true, res.done.error);
  assert.deepEqual(asked, ["start_structure_job", "screen_link_suggestions", "rank_link_suggestions"]);
});

test("the local review tool judges every suggestion and returns counts, not rows", async () => {
  llm.script.push(
    {
      tool: "mcp__review__review_link_suggestions",
      input: { job_id: "sjob_9", prompt: "Highest return" },
    },
    { text: "done" },
  );
  llm.judge.answer = (text) =>
    text.includes("cold brew")
      ? '```json\n{"verdict": "review_rejected", "reason": "too thin"}\n```'
      : '{"verdict": "review_approved", "reason": "worth it"}';
  const before = llm.judgeRequests.length;
  const res = await turn("review the drafts", undefined, { action: "ask-site" });
  assert.equal(res.done.ok, true, res.done.error);

  assert.equal(llm.judgeRequests.length - before, 2, "one model call per suggestion");
  const steps = scopeApi.reviewCalls.map((c) => c.step);
  assert.deepEqual(steps, ["review-inputs", "verdicts"]);
  assert.equal(scopeApi.reviewCalls[0].body.jobId, "sjob_9");
  assert.equal(scopeApi.reviewCalls[0].body.prompt, "Highest return");
  assert.deepEqual(scopeApi.reviewCalls[1].body.verdicts, [
    { id: "sug_1", verdict: "review_approved" },
    { id: "sug_2", verdict: "review_rejected" },
  ]);

  const toolResult = JSON.stringify(llm.requests.at(-1).messages);
  assert.ok(!toolResult.includes("cold brew"), "no suggestion data reaches the main model");
  assert.ok(toolResult.includes("worth it"), "sample reasons come back");
});

test("a live session refuses a turn sent for another website", async () => {
  llm.script.push({ text: "pinned" });
  const first = await turn("turn one");
  await assert.rejects(
    () =>
      runner.runAgentTurn(
        { action: "ask-pages", siteId: "site_other", message: "again", sessionId: first.sessionId, form: {} },
        () => {},
        { cwd, abortController: new AbortController(), askPermission: async () => "allow" },
      ),
    /pinned to another website/,
  );
});

test("a desk that works only on database data refuses attached files", async () => {
  await assert.rejects(
    () =>
      runner.runAgentTurn(
        {
          action: "ask-analytics",
          siteId: "site_test",
          message: "use this",
          form: {},
          files: [{ name: "data.csv", type: "text/csv", data: Buffer.from("a,b").toString("base64") }],
        },
        () => {},
        { cwd, abortController: new AbortController(), askPermission: async () => "allow" },
      ),
    /does not take attached files/,
  );
});

test("text after a tool call starts on a new paragraph, so a fenced block opens on its own line", async () => {
  llm.script.push(
    { tool: "mcp__desks__add_desk", input: { desk: "content" }, text: "Here is the chart:" },
    { text: "```chart\n<svg></svg>\n```" },
  );
  const res = await turn("chart it");
  assert.equal(res.done.ok, true, res.done.error);
  const streamed = res.events.filter(([e]) => e === "text").map(([, d]) => d.text).join("");
  assert.equal(streamed, "Here is the chart:\n\n```chart\n<svg></svg>\n```");
});

test("a chat whose transcript is gone starts a new session that opens with the stored turns", async () => {
  llm.script.push({ text: "continued" });
  const start = llm.requests.length;
  const res = await turn("and on mobile?", "0b9d5a8e-0000-4000-8000-000000000000", {
    history: [
      { role: "user", text: "Which country grew?" },
      { role: "assistant", text: "India, by 40%." },
    ],
  });
  assert.equal(res.done.ok, true, res.done.error);
  assert.notEqual(res.sessionId, "0b9d5a8e-0000-4000-8000-000000000000");
  const sent = JSON.stringify(llm.requests[start].messages.at(-1).content);
  assert.ok(sent.includes("[assistant]: India, by 40%."), sent);
  assert.ok(sent.includes("and on mobile?"));
});

test("a chat whose transcript is on disk resumes it without the stored turns", async () => {
  llm.script.push({ text: "first" });
  const first = await turn("first question");
  runner.closeAgentSessions();
  llm.script.push({ text: "second" });
  const start = llm.requests.length;
  const res = await turn("follow up", first.sessionId, { history: [{ role: "user", text: "NOT SENT" }] });
  assert.equal(res.done.ok, true, res.done.error);
  const sent = JSON.stringify(llm.requests[start].messages);
  assert.ok(sent.includes("first question"), "the resumed transcript carries the earlier turn");
  assert.ok(!sent.includes("NOT SENT"));
});
