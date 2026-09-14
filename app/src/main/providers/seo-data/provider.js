import { z } from "zod";
import { ProviderError } from "../errors.js";
import { ProviderFacade } from "../registry.js";
import { defineTools } from "../tools.js";
import {
  byMentionsDesc,
  chunk,
  citedUrls,
  factFromOverview,
  ideaOf,
  localeOf,
  normalizeKeywords,
  ownDomain,
  pick,
  promptOf,
  roundValue,
} from "./shape.js";

const MAX_BRAND_EXCLUSIONS = 8;
const FEATURE_TYPES = ["ai_overview", "featured_snippet", "people_also_ask", "local_pack"];
const KEYWORDS_PER_REQUEST = 1000;
const SEEDS_PER_REQUEST = 200;
const TRENDS_PER_REQUEST = 5;
const SERP_COMPETITOR_KEYWORDS = 100;

export class SeoDataConflict extends ProviderError {
  constructor(message) {
    super("conflict", message);
  }
}

function brandFilters(terms) {
  const filters = [];
  for (const term of terms) {
    if (filters.length) filters.push("and");
    filters.push(["keyword_data.keyword", "not_ilike", `%${term}%`]);
  }
  return filters;
}

function rankedRow(item, domain) {
  const keyword = String(item.keyword_data?.keyword ?? "")
    .trim()
    .toLowerCase();
  const serp = item.ranked_serp_element?.serp_item ?? null;
  if (!keyword || !serp) return null;
  return {
    domain,
    keyword,
    rankGroup: Math.trunc(serp.rank_group ?? 0),
    rankAbsolute: Math.trunc(serp.rank_absolute ?? 0),
    url: serp.url ?? null,
    etv: pick(serp.etv),
  };
}

function trendPoints(graph, keyword, seat) {
  const order = (graph.keywords ?? []).map((k) => String(k ?? "").trim().toLowerCase());
  const column = order.includes(keyword) ? order.indexOf(keyword) : seat;
  const points = [];
  for (const point of graph.data ?? []) {
    const day = String(point?.date_from ?? "").slice(0, 10);
    if (day.length !== 10 || Number.isNaN(new Date(day).getTime())) continue;
    const values = point.values ?? [];
    const raw = column < values.length ? values[column] : null;
    points.push({ day, interest: Math.trunc(raw ?? 0) });
  }
  return points;
}

export class SeoDataProvider extends ProviderFacade {
  constructor(opts) {
    super({ domain: "seo-data", label: "search data", ...opts });
  }

  async keywordFacts({ keywords, locationCode, languageCode, provider = null }) {
    const locale = localeOf({ locationCode, languageCode });
    const wanted = normalizeKeywords(keywords);
    if (!wanted.length) return { facts: [] };
    const adapter = this.require("keywords.overview", provider);
    const at = new Date().toISOString();
    const facts = [];
    for (const part of chunk(wanted, KEYWORDS_PER_REQUEST)) {
      const result = await adapter.keywordOverview(part, locale);
      facts.push(...result.items.filter((i) => i?.keyword).map((i) => factFromOverview(i, at)));
    }
    return { facts };
  }

  async keywordIdeas({ seeds, limit = 200, locationCode, languageCode, provider = null }) {
    const locale = localeOf({ locationCode, languageCode });
    const wanted = normalizeKeywords(seeds);
    if (!wanted.length) return { ideas: [] };
    const adapter = this.require("keywords.ideas", provider);
    const found = new Map();
    for (const part of chunk(wanted, SEEDS_PER_REQUEST)) {
      if (found.size >= limit) break;
      const result = await adapter.keywordIdeas(part, locale, limit);
      for (const item of result.items.filter((i) => i?.keyword)) {
        const idea = ideaOf(item);
        if (!found.has(idea.keyword)) found.set(idea.keyword, idea);
      }
    }
    return { ideas: [...found.values()].slice(0, limit) };
  }

  async rankedKeywords({ domain, limit = 100, excludeBrandTerms = [], locationCode, languageCode, provider = null }) {
    const locale = localeOf({ locationCode, languageCode });
    const target = ownDomain(domain);
    if (!target) return { rankings: [] };
    const exclude = normalizeKeywords(excludeBrandTerms);
    if (exclude.length > MAX_BRAND_EXCLUSIONS) {
      throw new SeoDataConflict(
        `At most ${MAX_BRAND_EXCLUSIONS} brand terms can be excluded per pull — the vendor caps a request at ` +
          `${MAX_BRAND_EXCLUSIONS} filter conditions and ${exclude.length} were given.`,
      );
    }
    const adapter = this.require("domains.ranked_keywords", provider);
    const result = await adapter.rankedKeywords(target, locale, limit, exclude.length ? brandFilters(exclude) : null);
    const rankings = result.items
      .map((i) => rankedRow(i, target))
      .filter(Boolean)
      .sort((a, b) => a.rankGroup - b.rankGroup)
      .slice(0, limit);
    return { rankings, fetchedAt: new Date().toISOString() };
  }

  async rivalDomains({ domain, limit = 10, locationCode, languageCode, provider = null }) {
    const locale = localeOf({ locationCode, languageCode });
    const target = ownDomain(domain);
    if (!target) return { rivals: [] };
    const adapter = this.require("domains.competitors", provider);
    const result = await adapter.competitorsDomain(target, locale, limit);
    const rivals = result.items
      .filter((i) => i?.domain && i.domain !== target)
      .map((i) => ({ domain: i.domain, intersections: pick(i.intersections), avgPosition: pick(i.avg_position) }))
      .slice(0, limit);
    return { rivals };
  }

  async serpSnapshot({ keyword, device = "desktop", depth = 10, stopOnDomain = null, locationCode, languageCode, provider = null }) {
    const locale = localeOf({ locationCode, languageCode });
    const adapter = this.require("serp.organic", provider);
    const term = keyword.trim().toLowerCase();
    const result = await adapter.serpOrganic(term, locale, {
      device,
      depth,
      stopOnDomain: stopOnDomain ? ownDomain(stopOnDomain) : null,
    });
    const block = result.item ?? null;
    const itemTypes = [...(block?.item_types ?? [])];
    const items = block?.items ?? [];
    const cited = citedUrls(items);
    const results = items
      .filter((item) => item?.rank_absolute != null)
      .map((item) => ({
        rankGroup: Math.trunc(item.rank_group ?? 0),
        rankAbsolute: Math.trunc(item.rank_absolute ?? 0),
        type: item.type,
        domain: item.domain ?? null,
        url: item.url ?? null,
        title: item.title ?? null,
        description: item.description ?? null,
        citedByAiOverview: Boolean(item.url && cited.has(item.url)),
      }));
    const features = Object.fromEntries(FEATURE_TYPES.map((name) => [name, itemTypes.includes(name)]));
    return {
      snapshot: {
        keyword: term,
        locationCode: locale.locationCode,
        languageCode: locale.languageCode,
        device,
        capturedAt: new Date().toISOString(),
        itemTypes,
        aiOverview: features.ai_overview,
        featuredSnippet: features.featured_snippet,
        peopleAlsoAsk: features.people_also_ask,
        localPack: features.local_pack,
        organicCount: results.filter((r) => r.type === "organic").length,
        checkUrl: block?.check_url ?? null,
        results,
      },
      costMicros: result.costMicros,
    };
  }

  async trend({ keywords, locationCode, languageCode, provider = null }) {
    const locale = localeOf({ locationCode, languageCode });
    const wanted = normalizeKeywords(keywords);
    const trends = {};
    if (!wanted.length) return { trends };
    const adapter = this.require("keywords.trends", provider);
    for (const part of chunk(wanted, TRENDS_PER_REQUEST)) {
      const result = await adapter.trendsExplore(part, locale);
      const graph = result.items.find((i) => i?.type === "google_trends_graph");
      if (!graph) continue;
      for (const [seat, keyword] of part.entries()) trends[keyword] = trendPoints(graph, keyword, seat);
    }
    return { trends };
  }

  async domainOverview({ domain, locationCode, languageCode, provider = null }) {
    const locale = localeOf({ locationCode, languageCode });
    const target = ownDomain(domain);
    const adapter = this.require("domains.overview", provider);
    const out = await adapter.domainRankOverview(target, locale);
    const organic = out.item?.metrics?.organic ?? null;
    if (!organic) return { domain: target, overview: null };
    return {
      domain: target,
      overview: {
        organicTraffic: roundValue(organic.etv),
        organicKeywords: roundValue(organic.count),
        fetchedAt: new Date().toISOString(),
      },
    };
  }

  async serpCompetitors({ keywords, limit = 10, locationCode, languageCode, provider = null }) {
    const locale = localeOf({ locationCode, languageCode });
    const sampled = normalizeKeywords(keywords).slice(0, SERP_COMPETITOR_KEYWORDS);
    if (!sampled.length) throw new SeoDataConflict("Pass at least one keyword to sample the results pages with.");
    const adapter = this.require("serp.competitors", provider);
    const result = await adapter.serpCompetitors(sampled, locale, limit);
    const competitors = result.items
      .map((i) => ({
        domain: ownDomain(i?.domain),
        visibility: pick(i?.visibility),
        avgPosition: pick(i?.avg_position),
        medianPosition: pick(i?.median_position),
        keywordsCount: pick(i?.keywords_count),
        etv: pick(i?.etv),
      }))
      .filter((r) => r.domain)
      .sort((a, b) => (b.visibility ?? 0) - (a.visibility ?? 0))
      .slice(0, limit);
    return { sampled: sampled.length, competitors };
  }

  async relevantPages({ domain, limit = 100, locationCode, languageCode, provider = null }) {
    const locale = localeOf({ locationCode, languageCode });
    const target = ownDomain(domain);
    const adapter = this.require("domains.relevant_pages", provider);
    const result = await adapter.relevantPages(target, locale, limit);
    const pages = result.items
      .filter((i) => i?.page_address)
      .map((i) => ({
        url: String(i.page_address),
        organicKeywords: pick(i.metrics?.organic?.count),
        organicEtv: pick(i.metrics?.organic?.etv),
      }))
      .sort((a, b) => (b.organicEtv ?? 0) - (a.organicEtv ?? 0));
    return { domain: target, pages };
  }

  async lighthouse({ url, strategy = "mobile", provider = null }) {
    const adapter = this.require("pages.lighthouse", provider);
    const out = await adapter.lighthouse(url, strategy === "mobile");
    return { url, strategy, report: out.item ?? null, costMicros: out.costMicros };
  }

  async llmMentions({ targets, platform = "google", limit = 300, locationCode, languageCode, provider = null }) {
    const locale = localeOf({ locationCode, languageCode });
    const adapter = this.require("llm.mentions", provider);
    const clean = (targets ?? []).filter((t) => t && (t.domain || t.keyword));
    if (!clean.length) throw new SeoDataConflict("Pass at least one target: a domain or a keyword.");
    const result = await adapter.llmMentions(clean, platform, locale, limit);
    const prompts = result.items.map((i) => promptOf(i, platform)).filter((p) => p.question);
    prompts.sort((a, b) => byMentionsDesc(a.aiSearchVolume, b.aiSearchVolume));
    return { platform, prompts };
  }
}

const provider = z.string().optional().describe("Force one connected provider");
const locale = {
  locationCode: z.number().optional(),
  languageCode: z.string().optional(),
};

defineTools(SeoDataProvider, [
  {
    name: "seo_keyword_facts",
    description: "Search volume, difficulty, cpc and intent for keywords, straight from the vendor. One unit per keyword.",
    input: z.object({ keywords: z.array(z.string()), ...locale, provider }),
    method: "keywordFacts",
  },
  {
    name: "seo_keyword_ideas",
    description: "Keyword ideas grown from seed keywords, with volume, difficulty and intent. One unit per seed.",
    input: z.object({ seeds: z.array(z.string()), limit: z.number().optional(), ...locale, provider }),
    method: "keywordIdeas",
  },
  {
    name: "seo_ranked_keywords",
    description: "Keywords a domain ranks for. excludeBrandTerms drops keywords containing those terms (at most eight).",
    input: z.object({
      domain: z.string(),
      limit: z.number().optional(),
      excludeBrandTerms: z.array(z.string()).optional(),
      ...locale,
      provider,
    }),
    method: "rankedKeywords",
  },
  {
    name: "seo_rival_domains",
    description: "Domains that rank for the same keywords as the given domain, with intersections and average position.",
    input: z.object({ domain: z.string(), limit: z.number().optional(), ...locale, provider }),
    method: "rivalDomains",
  },
  {
    name: "seo_serp_snapshot",
    description: "The live results page for one keyword: organic results, features and AI-overview citations. One unit per call.",
    input: z.object({
      keyword: z.string(),
      device: z.enum(["desktop", "mobile"]).optional(),
      depth: z.number().optional(),
      stopOnDomain: z.string().optional(),
      ...locale,
      provider,
    }),
    method: "serpSnapshot",
  },
  {
    name: "seo_trend",
    description: "Daily interest over time for keywords. Five keywords per vendor call.",
    input: z.object({ keywords: z.array(z.string()), ...locale, provider }),
    method: "trend",
  },
  {
    name: "seo_domain_overview",
    description: "Organic traffic estimate and ranking-keyword count for a domain. One unit per call.",
    input: z.object({ domain: z.string(), ...locale, provider }),
    method: "domainOverview",
  },
  {
    name: "seo_serp_competitors",
    description: "Domains that appear most on the results pages of the given keywords (up to 100), ranked by visibility.",
    input: z.object({ keywords: z.array(z.string()), limit: z.number().optional(), ...locale, provider }),
    method: "serpCompetitors",
  },
  {
    name: "seo_relevant_pages",
    description: "A domain's pages ordered by organic traffic, with the keyword count each one ranks for.",
    input: z.object({ domain: z.string(), limit: z.number().optional(), ...locale, provider }),
    method: "relevantPages",
  },
  {
    name: "seo_lighthouse",
    description: "Run Lighthouse on one URL for mobile or desktop and return the raw report. One unit per call.",
    input: z.object({ url: z.string(), strategy: z.enum(["mobile", "desktop"]).optional(), provider }),
    method: "lighthouse",
  },
  {
    name: "seo_llm_mentions",
    description:
      "Prompts on an AI platform whose answers mention a domain or keyword, with cited URLs and co-mentioned brands. Platform is chat_gpt or google.",
    input: z.object({
      targets: z.array(z.object({ domain: z.string().optional(), keyword: z.string().optional() })),
      platform: z.enum(["chat_gpt", "google"]).optional(),
      limit: z.number().optional(),
      ...locale,
      provider,
    }),
    method: "llmMentions",
  },
]);
