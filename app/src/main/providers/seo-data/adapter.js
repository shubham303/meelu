import { ProviderAdapter } from "../registry.js";

export const SEO_CAPABILITIES = [
  "keywords.volume",
  "keywords.difficulty",
  "keywords.intent",
  "keywords.overview",
  "keywords.ideas",
  "keywords.related",
  "keywords.suggestions",
  "keywords.trends",
  "domains.ranked_keywords",
  "domains.competitors",
  "domains.overview",
  "domains.relevant_pages",
  "serp.organic",
  "serp.competitors",
  "pages.lighthouse",
  "llm.mentions",
  "llm.mention_totals",
  "llm.top_pages",
  "llm.share_of_voice",
];

export const DEFAULT_LOCALE = { locationCode: 2840, languageCode: "en" };

export class SeoDataAdapter extends ProviderAdapter {
  async searchVolume() {
    throw this.unsupported("keywords.volume");
  }

  async bulkDifficulty() {
    throw this.unsupported("keywords.difficulty");
  }

  async searchIntent() {
    throw this.unsupported("keywords.intent");
  }

  async keywordOverview() {
    throw this.unsupported("keywords.overview");
  }

  async keywordIdeas() {
    throw this.unsupported("keywords.ideas");
  }

  async relatedKeywords() {
    throw this.unsupported("keywords.related");
  }

  async keywordSuggestions() {
    throw this.unsupported("keywords.suggestions");
  }

  async trendsExplore() {
    throw this.unsupported("keywords.trends");
  }

  async rankedKeywords() {
    throw this.unsupported("domains.ranked_keywords");
  }

  async competitorsDomain() {
    throw this.unsupported("domains.competitors");
  }

  async domainRankOverview() {
    throw this.unsupported("domains.overview");
  }

  async relevantPages() {
    throw this.unsupported("domains.relevant_pages");
  }

  async serpOrganic() {
    throw this.unsupported("serp.organic");
  }

  async serpCompetitors() {
    throw this.unsupported("serp.competitors");
  }

  async lighthouse() {
    throw this.unsupported("pages.lighthouse");
  }

  async llmMentions() {
    throw this.unsupported("llm.mentions");
  }

  async llmMentionTotals() {
    throw this.unsupported("llm.mention_totals");
  }

  async llmTopPages() {
    throw this.unsupported("llm.top_pages");
  }

  async llmShareOfVoice() {
    throw this.unsupported("llm.share_of_voice");
  }
}
