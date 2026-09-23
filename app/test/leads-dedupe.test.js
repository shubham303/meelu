import assert from "node:assert/strict";
import { test } from "node:test";
import { dedupeKeysOf, dedupeProspects } from "../src/main/leads/dedupe.js";
import { toApiLead } from "../src/main/leads/store.js";

test("dedupe keys cover email, domain and handles", () => {
  const keys = dedupeKeysOf({
    name: "pg",
    email: "pg@example.com",
    website: "https://www.example.com/about",
    channelHandles: { hackernews: "pg" },
  });
  assert.ok(keys.includes("pg@example.com"));
  assert.ok(keys.includes("example.com"));
  assert.ok(keys.includes("hackernews:pg"));
});

test("local dedupe drops overlapping prospects", () => {
  const a = { name: "Acme", website: "https://acme.io", source: "web-search", channelHandles: {} };
  const b = {
    name: "Acme founder",
    website: "https://www.acme.io/blog",
    channelHandles: { hackernews: "acme" },
    source: "hackernews",
  };
  const c = { name: "Other", website: "https://other.dev", source: "web-search", channelHandles: {} };
  const out = dedupeProspects([a, b, c]);
  assert.deepEqual(out.map((p) => p.name), ["Acme", "Other"]);
});

test("toApiLead maps the normalized shape to camelCase", () => {
  const lead = toApiLead({
    name: "Jane",
    email: "jane@acme.io",
    emailVerified: true,
    website: "https://acme.io/",
    source: "apify:linkedin",
    sourceUrl: "https://linkedin.com/in/jane",
    channelHandles: { linkedin: "jane" },
    fitScore: 0.8,
    fitReason: "Fits",
    evidence: [{ quote: "q", url: "u" }],
  });
  assert.equal(lead.emailVerified, true);
  assert.equal(lead.fitScore, 0.8);
  assert.equal(lead.company, null);
  assert.deepEqual(lead.evidence, [{ quote: "q", url: "u" }]);
});
