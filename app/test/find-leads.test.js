import assert from "node:assert/strict";
import test from "node:test";
import { itemsOf, judgeVerdicts } from "../src/main/find-leads/judge.js";
import { needsPlan, plansByBrief } from "../src/main/find-leads/plan.js";
import { candidateOf, contactPages, emailIn, webResults } from "../src/main/find-leads/web.js";

test("a brief needs a plan only for the sources it uses", () => {
  assert.equal(needsPlan({ sources: ["posts"], plan: { keywords: ["a b", "c d"] } }), false);
  assert.equal(needsPlan({ sources: ["posts"], plan: { keywords: ["a b"] } }), true);
  assert.equal(needsPlan({ sources: ["linkedin"], plan: { keywords: [] } }), true);
  assert.equal(
    needsPlan({ sources: ["linkedin"], plan: { linkedin: { query: "shop owner" } } }),
    false,
  );
  assert.equal(needsPlan({ sources: ["web"], plan: { web: ["agencies on Clutch"] } }), false);
});

test("plans keep two cleaned keywords and a tidy linkedin search per known brief", () => {
  const briefs = [{ id: "a" }, { id: "b" }, { id: "c" }];
  const out = plansByBrief(
    {
      briefs: [
        {
          id: "a",
          keywords: ["Traffic  Dropped", "lost rankings", "third"],
          linkedin: {
            query: " Shopify  store owner ",
            titles: ["Owner", "Owner", "Founder", "CEO", "Extra"],
            locations: ["Austin", "Texas", "USA"],
          },
        },
        { id: "b", keywords: ["same", "SAME"] },
        { id: "c", keywords: ["x y", "z w"], linkedin: { query: "" } },
        { id: "zzz", keywords: ["x y", "z w"] },
      ],
    },
    briefs,
  );
  assert.deepEqual([...out.keys()], ["a", "c"]);
  assert.deepEqual(out.get("a"), {
    keywords: ["traffic dropped", "lost rankings"],
    linkedin: {
      query: "Shopify store owner",
      titles: ["Owner", "Founder", "CEO"],
      locations: ["Austin", "Texas"],
    },
  });
  assert.deepEqual(out.get("c"), { keywords: ["x y", "z w"] });
});

test("judge verdicts map evidence numbers to the lead's own items", () => {
  const lead = {
    id: "l0",
    evidence: [{ url: "https://r.com/p1", quote: "traffic halved", at: "2026-10-10T00:00:00Z" }],
    activity: [
      { url: "https://r.com/p1", text: "duplicate", at: null, kind: "post" },
      { url: "https://r.com/c2", text: "which pages lost rankings?", at: "2026-10-12", kind: "comment" },
    ],
  };
  assert.equal(itemsOf(lead).length, 2);
  const out = judgeVerdicts(
    {
      results: [
        { i: 0, worth: true, why: " Asked twice ", angle: "Offer the list", evidence: [1, 0, 1, 7, "x"] },
        { i: 1, worth: false, why: "Agency" },
      ],
    },
    [lead, { id: "l1" }],
  );
  assert.deepEqual(out, [
    {
      id: "l0",
      keep: true,
      reason: "Asked twice",
      angle: "Offer the list",
      evidence: [
        { url: "https://r.com/c2", quote: "which pages lost rankings?", at: "2026-10-12" },
        { url: "https://r.com/p1", quote: "traffic halved", at: "2026-10-10T00:00:00Z" },
      ],
    },
    { id: "l1", keep: false },
  ]);
});

test("email extraction prefers mailto and skips placeholders and file names", () => {
  assert.equal(
    emailIn('<a href="mailto:Hello@CandlesByDana.com?subject=hi">Write</a> also bob@shop.io'),
    "hello@candlesbydana.com",
  );
  assert.equal(emailIn("logo@2x.png noreply@shop.io you@example.com"), null);
  assert.equal(emailIn("Contact: owner@rise-bakery.co.uk."), "owner@rise-bakery.co.uk");
  assert.equal(emailIn("<p>no email here</p>"), null);
});

test("web results need a name, a real url, their own website and a page from the last 30 days, and candidates carry the page as evidence", () => {
  const now = Date.parse("2026-10-18T12:00:00Z");
  const results = webResults(
    {
      results: [
        { name: "Rise Bakery", headline: "Bakery", website: "risebakery.com", url: "https://x.com/a", kind: "post", published: "2026-10-10", why: "Blog stopped ranking" },
        { name: "", url: "https://x.com/b", published: "2026-10-10" },
        { name: "No url", url: "javascript:alert(1)", published: "2026-10-10" },
        { name: "Forum poster", url: "https://forum.example/t/1", published: "2026-10-10", why: "lost traffic" },
        { name: "Old Shop", website: "oldshop.com", url: "https://oldshop.com/blog", kind: "post", published: "2019-04-02" },
        { name: "Undated Post", website: "undated.com", url: "https://undated.com/blog", kind: "post" },
        { name: "Studio Site", website: "studio.example", url: "https://studio.example/", kind: "site" },
      ],
    },
    now,
  );
  assert.deepEqual(results.map((r) => r.name), ["Rise Bakery", "Studio Site"]);
  assert.equal(results[1].published, null);
  assert.equal(results[0].website, "https://risebakery.com/");
  assert.deepEqual(contactPages(results[0]), [
    "https://x.com/a",
    "https://risebakery.com/contact",
    "https://risebakery.com/about",
  ]);
  const c = candidateOf({ id: "b1" }, results[0], { email: null, emailSourceUrl: null });
  assert.deepEqual(c.evidence, [
    { url: "https://x.com/a", quote: "Blog stopped ranking", at: "2026-10-10T00:00:00.000Z" },
  ]);
  assert.equal(c.profileUrl, "https://x.com/a");
  assert.equal(c.snippet, "Bakery · Blog stopped ranking");
});

test("web angles come from the plan, and results are de-duplicated by website", async () => {
  const { searchAngles, distinctResults } = await import("../src/main/find-leads/web.js");
  const { needsPlan, plansByBrief } = await import("../src/main/find-leads/plan.js");
  assert.deepEqual(searchAngles({ text: "agencies", plan: {} }), ["agencies"]);
  assert.deepEqual(searchAngles({ text: "agencies", plan: { web: ["a", " ", "b"] } }), ["a", "b"]);
  const merged = distinctResults([
    [{ name: "A", website: "https://www.a.com/" }],
    [{ name: "A again", website: "https://a.com/about" }, { name: "B", website: "https://b.com/" }],
  ]);
  assert.deepEqual(merged.map((r) => r.name), ["A", "B"]);
  assert.equal(needsPlan({ sources: ["web"], plan: {} }), true);
  assert.equal(needsPlan({ sources: ["web"], plan: { web: ["x"] } }), false);
  const plans = plansByBrief(
    { briefs: [{ id: "b1", keywords: [], web: ["freelance marketers", "small agencies on Clutch", "x", "y"] }] },
    [{ id: "b1" }],
  );
  assert.deepEqual(plans.get("b1").web, ["freelance marketers", "small agencies on Clutch", "x"]);
});

test("later rounds keep only searches that were not used before", async () => {
  const { freshPlans } = await import("../src/main/find-leads/plan.js");
  const { targetOf } = await import("../src/main/find-leads/pipeline.js");
  const briefs = [
    { id: "b1", usedKeywords: ["traffic dropped", "lost rankings"], usedWeb: ["Agencies on Clutch"] },
    { id: "b2", usedKeywords: [], usedWeb: [] },
  ];
  const plans = freshPlans(
    {
      briefs: [
        { id: "b1", keywords: ["Traffic Dropped", "seo help"], web: ["agencies on clutch", "freelancers on Upwork"] },
        { id: "b2", keywords: ["site slow", "page speed"], web: [] },
      ],
    },
    briefs,
  );
  assert.deepEqual(plans.get("b1"), { keywords: [], web: ["freelancers on Upwork"] });
  assert.deepEqual(plans.get("b2"), { keywords: ["site slow", "page speed"], web: [] });
  assert.equal(targetOf(undefined), 20);
  assert.equal(targetOf("0"), 20);
  assert.equal(targetOf(35.7), 35);
  assert.equal(targetOf(500), 100);
});
