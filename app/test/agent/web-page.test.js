import assert from "node:assert/strict";
import { test } from "node:test";
import { firstWords, readWebPage, webPageMcpServer } from "../../src/main/agent/web-page.js";

test("the body is cut at the word cap on a line boundary and flagged", () => {
  const body = ["# Espresso machines", "one two three four", "five six seven eight"].join("\n");
  assert.deepEqual(firstWords(body, 100), { bodyText: body, truncated: false });
  assert.deepEqual(firstWords(body, 5), {
    bodyText: "# Espresso machines\none two",
    truncated: true,
  });
});

test("the tool is registered only for a scope that lists it", () => {
  assert.equal(webPageMcpServer(["review_link_suggestions"]), null);
  assert.equal(webPageMcpServer(undefined), null);
  assert.deepEqual([...webPageMcpServer(["read_web_page"]).allowed], ["read_web_page"]);
});

test("private and non-web addresses are refused before anything is fetched", async () => {
  for (const url of ["http://127.0.0.1/admin", "file:///etc/passwd", "not a url"]) {
    assert.match(await readWebPage(url), /Only public http\(s\) pages/);
  }
});
