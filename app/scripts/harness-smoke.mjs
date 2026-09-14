import { runAgentTurn } from "../src/main/agent/runner.js";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

const cwd = fs.mkdtempSync(path.join(os.tmpdir(), "meelu-harness-"));
const abortController = new AbortController();
const events = [];

await runAgentTurn(
  {
    action: "profile-setup",
    siteId: null,
    message: "In one short sentence: what exactly can you do in this task? Create nothing.",
    form: {},
  },
  (event, data) => {
    events.push(event);
    if (event === "text") process.stdout.write(data.text);
    if (event === "done") {
      console.log(`\n[done ok=${data.ok} cost=$${(data.costUsd ?? 0).toFixed(4)} error=${data.error ?? "none"}]`);
    }
  },
  { cwd, abortController },
);

const ok = events.includes("session") && events.includes("text") && events.includes("done");
console.log(ok ? "HARNESS_SMOKE_PASS" : `HARNESS_SMOKE_FAIL events=${events.join(",")}`);
process.exit(ok ? 0 : 1);
