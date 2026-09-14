import { ProviderRequestError } from "../errors.js";
import { vendorRequest } from "../vendor-http.js";
import { SeoDataAdapter, SEO_CAPABILITIES } from "./adapter.js";

export const ENDPOINTS = {
  search_volume: "/v3/keywords_data/google_ads/search_volume/live",
  difficulty: "/v3/dataforseo_labs/google/bulk_keyword_difficulty/live",
  intent: "/v3/dataforseo_labs/google/search_intent/live",
  ideas: "/v3/dataforseo_labs/google/keyword_ideas/live",
  ranked_keywords: "/v3/dataforseo_labs/google/ranked_keywords/live",
  competitors: "/v3/dataforseo_labs/google/competitors_domain/live",
  serp: "/v3/serp/google/organic/live/advanced",
  trends: "/v3/keywords_data/google_trends/explore/live",
  related_keywords: "/v3/dataforseo_labs/google/related_keywords/live",
  suggestions: "/v3/dataforseo_labs/google/keyword_suggestions/live",
  keyword_overview: "/v3/dataforseo_labs/google/keyword_overview/live",
  domain_overview: "/v3/dataforseo_labs/google/domain_rank_overview/live",
  serp_competitors: "/v3/dataforseo_labs/google/serp_competitors/live",
  relevant_pages: "/v3/dataforseo_labs/google/relevant_pages/live",
  lighthouse: "/v3/on_page/lighthouse/live/json",
  llm_mentions: "/v3/ai_optimization/llm_mentions/search/live",
  llm_mention_totals: "/v3/ai_optimization/llm_mentions/aggregated_metrics/live",
  llm_top_pages: "/v3/ai_optimization/llm_mentions/top_pages/live",
  llm_share_of_voice: "/v3/ai_optimization/llm_mentions/cross_aggregated_metrics/live",
};

export const LIMITS = {
  keywordsPerRequest: 1000,
  seedsPerRequest: 200,
  trendsPerRequest: 5,
  ideasPerRequest: 1000,
  serpCompetitorKeywords: 100,
  llmTargetGroups: 10,
};

const OK = 20000;

function clamp(limit, cap) {
  return Math.min(Math.max(Number(limit) || 1, 1), cap);
}

function micros(cost) {
  return typeof cost === "number" && Number.isFinite(cost) ? Math.round(cost * 1_000_000) : 0;
}

function localeFields(locale) {
  return { location_code: locale.locationCode, language_code: locale.languageCode };
}

function envelopeCost(envelope) {
  if (typeof envelope.cost === "number") return micros(envelope.cost);
  return (envelope.tasks ?? []).reduce((sum, t) => sum + micros(t?.cost), 0);
}

function results(envelope) {
  return (envelope.tasks ?? []).flatMap((t) => t?.result ?? []);
}

function bundleItems(envelope) {
  return results(envelope).flatMap((r) => (r && typeof r === "object" ? (r.items ?? []) : []));
}

function llmDomainTarget(domain) {
  return { domain, include_subdomains: true, search_filter: "include", search_scope: ["any"] };
}

function llmKeywordTarget(keyword) {
  return { keyword, search_filter: "include", search_scope: ["any"], match_type: "word_match" };
}

export function llmTarget(target) {
  return target.domain ? llmDomainTarget(target.domain) : llmKeywordTarget(target.keyword);
}

export class DataForSeoAdapter extends SeoDataAdapter {
  static id = "dataforseo";
  static name_ = "DataForSEO";

  static get capabilities() {
    return new Set(SEO_CAPABILITIES);
  }

  baseUrl() {
    return (this.credentials?.baseUrl || "https://api.dataforseo.com").replace(/\/$/, "");
  }

  headers() {
    const login = (this.credentials?.login ?? "").trim();
    const password = (this.credentials?.password ?? "").trim();
    return { authorization: `Basic ${Buffer.from(`${login}:${password}`).toString("base64")}` };
  }

  async post(endpoint, task) {
    const path = ENDPOINTS[endpoint];
    let body;
    try {
      body = await vendorRequest(this.id, `${this.baseUrl()}${path}`, {
        method: "POST",
        headers: this.headers(),
        json: [task],
        timeoutMs: 120_000,
      });
    } catch (err) {
      throw this.describe(path, err);
    }
    if (!body || typeof body !== "object") {
      throw new ProviderRequestError(this.id, 502, `DataForSEO returned non-JSON from ${path}`, body);
    }
    if (body.status_code != null && body.status_code !== OK) {
      throw new ProviderRequestError(
        this.id,
        502,
        `DataForSEO refused ${path} (${body.status_code}): ${body.status_message || "no message"}`,
        body,
      );
    }
    const failed = (body.tasks ?? []).find((t) => t?.status_code !== OK);
    if (failed) {
      throw new ProviderRequestError(
        this.id,
        502,
        `DataForSEO task failed on ${path} (${failed.status_code}): ${failed.status_message || "no message"}`,
        body,
      );
    }
    return { envelope: body, endpoint: path, costMicros: envelopeCost(body) };
  }

  describe(path, err) {
    if (!(err instanceof ProviderRequestError)) return err;
    if (err.status === 401) {
      return new ProviderRequestError(
        this.id,
        502,
        "DataForSEO rejected the credentials (401). Check the login and password on the Connections screen.",
        err.body,
      );
    }
    if (err.status === 402) {
      return new ProviderRequestError(
        this.id,
        502,
        "DataForSEO returned 402 Payment Required — the account balance does not cover this call.",
        err.body,
      );
    }
    if (err.status === 403) {
      return new ProviderRequestError(
        this.id,
        502,
        "DataForSEO returned 403 — the account is not allowed to call this endpoint.",
        err.body,
      );
    }
    if (err.body && typeof err.body === "object" && err.body.status_code != null && err.body.status_code !== OK) {
      return new ProviderRequestError(
        this.id,
        502,
        `DataForSEO refused ${path} (${err.body.status_code}): ${err.body.status_message || "no message"}`,
        err.body,
      );
    }
    if (err.status == null) return err;
    return new ProviderRequestError(
      this.id,
      502,
      `DataForSEO ${err.status} on ${path}: ${String(err.body ?? "").slice(0, 200)}`,
      err.body,
    );
  }

  async items(endpoint, task, { bundles = true } = {}) {
    const { envelope, costMicros, endpoint: path } = await this.post(endpoint, task);
    return { items: bundles ? bundleItems(envelope) : results(envelope), costMicros, endpoint: path };
  }

  async first(endpoint, task, { bundles = false } = {}) {
    const { envelope, costMicros, endpoint: path } = await this.post(endpoint, task);
    const rows = bundles ? bundleItems(envelope) : results(envelope);
    return { item: rows[0] ?? null, costMicros, endpoint: path };
  }

  searchVolume(keywords, locale) {
    return this.items("search_volume", { keywords, ...localeFields(locale) }, { bundles: false });
  }

  bulkDifficulty(keywords, locale) {
    return this.items("difficulty", { keywords, ...localeFields(locale) });
  }

  searchIntent(keywords, locale) {
    return this.items("intent", { keywords, ...localeFields(locale) });
  }

  keywordOverview(keywords, locale) {
    return this.items("keyword_overview", {
      keywords: keywords.slice(0, LIMITS.keywordsPerRequest),
      ...localeFields(locale),
    });
  }

  keywordIdeas(seeds, locale, limit) {
    return this.items("ideas", {
      keywords: seeds.slice(0, LIMITS.seedsPerRequest),
      limit: clamp(limit, LIMITS.ideasPerRequest),
      ...localeFields(locale),
    });
  }

  async relatedKeywords(seed, locale, limit) {
    const out = await this.items("related_keywords", {
      keyword: seed,
      limit: clamp(limit, LIMITS.ideasPerRequest),
      depth: 3,
      ...localeFields(locale),
    });
    return {
      ...out,
      items: out.items.map((row) => row?.keyword_data).filter((k) => k && k.keyword),
    };
  }

  keywordSuggestions(seed, locale, limit) {
    return this.items("suggestions", {
      keyword: seed,
      limit: clamp(limit, LIMITS.ideasPerRequest),
      include_seed_keyword: true,
      ignore_synonyms: false,
      exact_match: false,
      ...localeFields(locale),
    });
  }

  trendsExplore(keywords, locale) {
    return this.items("trends", {
      keywords: keywords.slice(0, LIMITS.trendsPerRequest),
      type: "web",
      ...localeFields(locale),
    });
  }

  rankedKeywords(target, locale, limit, filters = null) {
    return this.items("ranked_keywords", {
      target,
      limit: clamp(limit, 1000),
      ...(filters && filters.length ? { filters } : {}),
      ...localeFields(locale),
    });
  }

  competitorsDomain(target, locale, limit) {
    return this.items("competitors", { target, limit: clamp(limit, 1000), ...localeFields(locale) });
  }

  domainRankOverview(target, locale) {
    return this.first("domain_overview", { target, limit: 1, ...localeFields(locale) }, { bundles: true });
  }

  relevantPages(target, locale, limit) {
    return this.items("relevant_pages", {
      target,
      limit: clamp(limit, 1000),
      order_by: ["metrics.organic.etv,desc"],
      ...localeFields(locale),
    });
  }

  serpCompetitors(keywords, locale, limit) {
    return this.items("serp_competitors", {
      keywords: keywords.slice(0, LIMITS.serpCompetitorKeywords),
      limit: clamp(limit, 100),
      ...localeFields(locale),
    });
  }

  serpOrganic(keyword, locale, { depth = 10, device = "desktop", stopOnDomain = null } = {}) {
    return this.first("serp", {
      keyword,
      device,
      depth,
      ...(stopOnDomain
        ? {
            stop_crawl_on_match: [{ match_value: stopOnDomain, match_type: "with_subdomains" }],
            find_targets_in: ["organic"],
          }
        : {}),
      ...localeFields(locale),
    });
  }

  lighthouse(url, forMobile) {
    return this.first("lighthouse", {
      url,
      for_mobile: forMobile,
      categories: ["performance", "accessibility", "best_practices", "seo"],
    });
  }

  llmMentions(targets, platform, locale, limit) {
    return this.items("llm_mentions", {
      target: targets.map(llmTarget),
      platform,
      limit: clamp(limit, 1000),
      ...localeFields(locale),
    });
  }

  llmMentionTotals(targets, platform, locale) {
    return this.first("llm_mention_totals", {
      target: targets.map(llmTarget),
      platform,
      internal_list_limit: 20,
      ...localeFields(locale),
    });
  }

  llmTopPages(targets, platform, locale) {
    return this.items("llm_top_pages", {
      target: targets.map(llmTarget),
      platform,
      links_scope: "sources",
      items_list_limit: 10,
      internal_list_limit: 5,
      ...localeFields(locale),
    });
  }

  llmShareOfVoice(groups, platform, locale) {
    return this.items("llm_share_of_voice", {
      targets: groups.slice(0, LIMITS.llmTargetGroups).map((g) => ({
        aggregation_key: g.key,
        target: g.targets.map(llmTarget),
      })),
      platform,
      internal_list_limit: 10,
      ...localeFields(locale),
    });
  }
}
