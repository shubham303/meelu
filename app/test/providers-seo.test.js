import assert from "node:assert/strict";
import { test } from "node:test";
import { AmbiguousProviderError, NotSupportedError, ProviderError } from "../src/main/providers/errors.js";
import { SeoDataAdapter, SEO_CAPABILITIES } from "../src/main/providers/seo-data/adapter.js";
import { SeoDataProvider } from "../src/main/providers/seo-data/provider.js";
import { toolNames } from "../src/main/providers/tools.js";

class FakeAdapter extends SeoDataAdapter {
  static id = "fake";
  static name_ = "Fake";

  static get capabilities() {
    return new Set(SEO_CAPABILITIES);
  }

  constructor() {
    super();
    this.log = [];
  }

  async keywordOverview(keywords) {
    this.log.push(["keywordOverview", keywords]);
    return {
      endpoint: "/overview",
      costMicros: 1200,
      items: keywords.map((keyword) => ({
        keyword,
        keyword_info: { search_volume: 100, competition: 0.42, competition_level: "LOW", cpc: 1.5 },
        keyword_properties: { keyword_difficulty: 33 },
        search_intent_info: { main_intent: "informational" },
      })),
    };
  }

  async serpOrganic(keyword, locale, opts) {
    this.log.push(["serpOrganic", keyword, opts]);
    return {
      endpoint: "/serp",
      costMicros: 2000,
      item: {
        check_url: "https://google.com/?q=" + keyword,
        item_types: ["organic", "people_also_ask"],
        items: [
          { type: "organic", rank_group: 1, rank_absolute: 1, domain: "other.com", url: "https://other.com/a" },
          { type: "organic", rank_group: 3, rank_absolute: 4, domain: "www.example.com", url: "https://example.com/p" },
        ],
      },
    };
  }
}

class NarrowAdapter extends SeoDataAdapter {
  static id = "narrow";
  static name_ = "Narrow";

  static get capabilities() {
    return new Set(["keywords.volume"]);
  }
}

function build({ adapters = [new FakeAdapter()], defaultFor = null } = {}) {
  const store = {
    connected: (id) => (adapters.some((a) => a.id === id) ? { login: "x" } : null),
    defaultFor: () => defaultFor,
  };
  const seo = new SeoDataProvider({ adapters, store, meelu: null });
  return { seo, adapter: adapters[0] };
}

test("registers the seo tool set", () => {
  const names = toolNames(SeoDataProvider);
  assert.ok(names.includes("seo_keyword_facts"));
  assert.ok(names.includes("seo_serp_snapshot"));
  assert.ok(names.every((n) => n.startsWith("seo_")));
});

test("keyword facts come straight from the vendor, shaped and lower-cased", async () => {
  const { seo, adapter } = build();
  const out = await seo.keywordFacts({ keywords: [" Blue Shoes ", "red shoes"] });
  assert.deepEqual(adapter.log[0], ["keywordOverview", ["blue shoes", "red shoes"]]);
  assert.equal(out.facts.length, 2);
  assert.equal(out.facts[0].keyword, "blue shoes");
  assert.equal(out.facts[0].volume, 100);
  assert.equal(out.facts[0].difficulty, 33);
  assert.equal(out.facts[0].intent, "informational");
});

test("serp snapshot reports features and results in rank order", async () => {
  const { seo, adapter } = build();
  const out = await seo.serpSnapshot({ keyword: "Blue Shoes", device: "mobile", stopOnDomain: "https://www.example.com" });
  assert.equal(adapter.log[0][1], "blue shoes");
  assert.equal(adapter.log[0][2].stopOnDomain, "example.com");
  assert.equal(out.snapshot.peopleAlsoAsk, true);
  assert.equal(out.snapshot.aiOverview, false);
  assert.equal(out.snapshot.organicCount, 2);
  assert.equal(out.snapshot.results[1].url, "https://example.com/p");
  assert.equal(out.costMicros, 2000);
});

test("ambiguous and unsupported providers surface as ProviderError", async () => {
  const ambiguous = build({ adapters: [new FakeAdapter(), new NarrowAdapter()] });
  await assert.rejects(
    () => ambiguous.seo.keywordFacts({ keywords: ["a"] }),
    (err) => err instanceof ProviderError && err instanceof AmbiguousProviderError && err.code === "ambiguous_provider",
  );

  const narrow = build({ adapters: [new NarrowAdapter()] });
  await assert.rejects(
    () => narrow.seo.keywordFacts({ keywords: ["a"] }),
    (err) => err instanceof ProviderError && err instanceof NotSupportedError && err.capability === "keywords.overview",
  );
  await assert.rejects(
    () => narrow.seo.serpSnapshot({ keyword: "a" }),
    (err) => err instanceof NotSupportedError && err.capability === "serp.organic",
  );
});
