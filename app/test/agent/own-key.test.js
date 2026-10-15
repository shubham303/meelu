import assert from "node:assert/strict";
import fs from "node:fs";
import { register } from "node:module";
import os from "node:os";
import path from "node:path";
import { after, before, beforeEach, test } from "node:test";
import { OWN_ANTHROPIC_KEY, TEST_MODEL, startLlm, startMcp, startScopeApi } from "./fakes.mjs";

register("./electron-loader.mjs", import.meta.url);

let scopeApi;
let mcp;
let llm;
let runner;
let ownKey;
let messages;
let cwd;

before(async () => {
  const electron = await import("electron");
  const userData = fs.mkdtempSync(path.join(os.tmpdir(), "meelu-own-key-"));
  electron.app.getPath = () => userData;
  electron.safeStorage.isEncryptionAvailable = () => true;
  electron.safeStorage.encryptString = (s) => Buffer.from(`enc:${s}`);
  electron.safeStorage.decryptString = (b) => b.toString().replace(/^enc:/, "");

  llm = await startLlm();
  [scopeApi, mcp] = await Promise.all([startScopeApi(llm.url), startMcp()]);
  process.env.MEELU_BASE_URL = scopeApi.url;
  process.env.MEELU_AGENT_MCP_URL = mcp.url;
  process.env.MEELU_API_KEY = "emcp_test_key";
  process.env.MEELU_ANTHROPIC_BASE_URL = llm.url;
  cwd = fs.mkdtempSync(path.join(os.tmpdir(), "meelu-own-key-cwd-"));
  runner = await import("../../src/main/agent/runner.js");
  ownKey = await import("../../src/main/integrations/llm/own-key.js");
  messages = await import("../../src/main/agent/messages.js");
});

after(() => {
  runner?.closeAgentSessions();
  scopeApi?.close();
  mcp?.close();
  llm?.close();
});

beforeEach(async () => {
  await ownKey.saveOwnAnthropic({ apiKey: "" });
  llm.headers.length = 0;
  scopeApi.llmHeaders.length = 0;
});

async function turn(message, model) {
  const events = [];
  await runner.runAgentTurn(
    { action: "ask-pages", siteId: "site_test", message, form: {}, model },
    (event, data) => events.push([event, data]),
    { cwd, abortController: new AbortController(), askPermission: async () => "allow" },
  );
  return events.find(([e]) => e === "done")?.[1];
}

test("a key Anthropic rejects is not saved", async () => {
  await assert.rejects(
    ownKey.saveOwnAnthropic({ apiKey: "sk-ant-wrong" }),
    /did not accept this API key/,
  );
  assert.deepEqual(ownKey.describeOwnKeys(), { anthropic: { saved: false, defaultModel: "" } });
});

test("a saved key is encrypted on disk and defaults to a Haiku model", async () => {
  await ownKey.saveOwnAnthropic({ apiKey: OWN_ANTHROPIC_KEY });
  assert.deepEqual(ownKey.describeOwnKeys(), {
    anthropic: { saved: true, defaultModel: "claude-haiku-test" },
  });
  const onDisk = fs.readFileSync(path.join((await import("electron")).app.getPath(), "llm-keys.json"), "utf8");
  assert.ok(!onDisk.includes(OWN_ANTHROPIC_KEY), "the key is not stored in plain text");
  assert.deepEqual(
    (await ownKey.ownAnthropicModels()).map((m) => m.id),
    ["claude-sonnet-test", "claude-haiku-test"],
  );

  await ownKey.saveOwnAnthropic({ defaultModel: "claude-sonnet-test" });
  assert.equal(ownKey.describeOwnKeys().anthropic.defaultModel, "claude-sonnet-test");
});

test("with a key saved, a task on the default model goes straight to Anthropic with the key", async () => {
  await ownKey.saveOwnAnthropic({ apiKey: OWN_ANTHROPIC_KEY });
  llm.script.push({ text: "from my key" });

  const done = await turn("hello");

  assert.equal(done.ok, true, done.error);
  assert.equal(scopeApi.llmHeaders.length, 0, "nothing went through the Meelu gateway");
  const sent = llm.headers.find((h) => h["x-api-key"]);
  assert.equal(sent["x-api-key"], OWN_ANTHROPIC_KEY);
  assert.ok(!String(sent.authorization ?? "").includes("emcp_"), "no Meelu key sent to Anthropic");
  assert.equal(llm.requests.at(-1).model, "claude-haiku-test");
});

test("an own-key model picked for the task uses that model", async () => {
  await ownKey.saveOwnAnthropic({ apiKey: OWN_ANTHROPIC_KEY });
  llm.script.push({ text: "sonnet" });

  const done = await turn("hello", ownKey.ownModelId("claude-sonnet-test"));

  assert.equal(done.ok, true, done.error);
  assert.equal(llm.requests.at(-1).model, "claude-sonnet-test");
  assert.equal(scopeApi.llmHeaders.length, 0);
});

test("a Meelu model picked for the task still runs on Meelu credits", async () => {
  await ownKey.saveOwnAnthropic({ apiKey: OWN_ANTHROPIC_KEY });
  llm.script.push({ text: "credits" });

  const done = await turn("hello", TEST_MODEL);

  assert.equal(done.ok, true, done.error);
  assert.ok(scopeApi.llmHeaders.length > 0, "the call went through the Meelu gateway");
  assert.ok(!llm.headers.some((h) => h["x-api-key"] === OWN_ANTHROPIC_KEY));
});

test("without a key, the default runs on Meelu credits and an own-key model is refused", async () => {
  llm.script.push({ text: "credits" });
  const done = await turn("hello");
  assert.equal(done.ok, true, done.error);
  assert.ok(scopeApi.llmHeaders.length > 0);

  await assert.rejects(
    runner.resolveLlm({ model: ownKey.ownModelId("claude-haiku-test"), purpose: "agent" }),
    /no key is saved/,
  );
});

test("the one-shot judge endpoint uses the key against Anthropic", async () => {
  await ownKey.saveOwnAnthropic({ apiKey: OWN_ANTHROPIC_KEY });
  const { gateway, model } = await runner.resolveLlm({ purpose: "page_review" });
  const endpoint = messages.messagesEndpoint(gateway);
  assert.equal(endpoint.url, `${llm.url}/v1/messages`);
  assert.deepEqual(endpoint.headers, { "x-api-key": OWN_ANTHROPIC_KEY });

  const answer = await messages.messagesJudge({ endpoint, model, system: "You answer with one JSON object and nothing else." })(
    "judge this",
  );
  assert.match(answer, /verdict/);
  assert.equal(llm.judgeRequests.at(-1).model, "claude-haiku-test");
});
