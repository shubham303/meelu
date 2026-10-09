# DataForSEO: a map of the Labs and SERP APIs

What each API does, what goes in, what comes out, and how they overlap. Only the parameters and fields that matter. Researched 2026-10-06 from docs.dataforseo.com/v3.

Scope for Meelu v1: DataForSEO Labs and the SERP API only. Out of scope: the Keywords Data API (Google Ads, Bing, Clickstream, Trends), AI Optimization / LLM APIs, Backlinks, On-Page, Domain Analytics, Business Data, Merchant, App Data.

---

## 1. The two families

The two families differ in **where the data comes from**, and that difference explains most of their behaviour.

| Family | Where the data comes from | Shape of a call | Freshness | Pricing model |
|---|---|---|---|---|
| **DataForSEO Labs** | DataForSEO's **own database**: about 7 billion keywords and the Google SERPs they have collected for them | You ask a question (keywords for a seed, keywords a domain ranks for, competitors…) and page through rows | Keyword metrics monthly, rankings weekly, each SERP every 30–90 days | Per task + per returned row |
| **SERP API** | A **live fetch of Google** for one keyword | You give one keyword, you get the whole results page parsed into items | Live, at request time | Per 10 results |

A rough way to hold it in your head:

- **Labs**: "search DataForSEO's index of keywords and rankings." It is the only family that can go from a **domain** to its keywords, or from a keyword to its **neighbours**.
- **SERP API**: "what does Google show right now for this keyword?"

Two practical constraints:
- **Labs is countries only, and Live only.** The SERP API goes down to city or postcode, and has a cheaper queued mode.
- **Labs only knows keywords already in its database.** `keyword_overview` silently skips unknown keywords, so long-tail queries (for example from Search Console) will often have no volume. The SERP API works for any keyword but returns no volume.

---

## 2. The things the data describes

Both families return some mix of these seven things. Think of these as the nouns. The endpoints are different ways of getting them.

| Thing | Identified by | Changes |
|---|---|---|
| **Keyword** | keyword × location × language | never (it is just the text in a market) |
| **Keyword metrics**: volume, CPC, competition, ad bids, keyword difficulty, intent, which SERP features appear | the keyword | monthly; each group has its own "last updated" time |
| **Monthly volume series** | keyword × year × month, per volume variant | monthly; Google sometimes rewrites past months |
| **SERP snapshot**: the whole results page for one search | keyword × location × language × device × time fetched | every fetch |
| **SERP item**: one block on the page (an organic result, an ad, People Also Ask, an AI Overview, a local pack…) | snapshot × position | every fetch |
| **Ranking**: a URL holding a position for a keyword | keyword × URL (× item type) at a date | weekly in Labs, per fetch in the SERP API |
| **AI Overview citation**: a URL cited as a source in an AI Overview | the AI Overview × URL | very volatile, can change daily |

The same thing often comes from several endpoints. Section 8 lists the overlaps.

---

## 3. Labs, keyword side: discovery and keyword records

All under `/v3/dataforseo_labs/google/...`. Live only, about 2 s. $0.012 per call + $0.00012 per returned row, **doubled if you ask for clickstream data**. Max 1000 rows per call; page with `offset` or `offset_token`. Every list endpoint takes `filters` (up to 8 conditions on any field) and `order_by`.

### The keyword record

Almost every Labs keyword endpoint returns the same record per keyword. Learn it once:

| Block | What's in it | Updated |
|---|---|---|
| `keyword_info` | Google Ads volume, last 12 months of volume, CPC, competition, bid range, Google product categories, % change month/quarter/year | monthly |
| `keyword_properties` | **keyword difficulty** (0–100), **core_keyword** (the head of its synonym group), detected language, word count | not stated |
| `serp_info` *(opt-in, free)* | which SERP features appear for the keyword (including `ai_overview`), result count, when the SERP was last crawled | every 30–90 days |
| `avg_backlinks_info` | average backlinks / referring domains / rank of the current top 10 | with the SERP |
| `search_intent_info` | main intent (informational / navigational / commercial / transactional) + secondary intents | rarely; can be a year old |
| `clickstream_keyword_info` *(opt-in, ×2 price)* | clickstream volume, gender and age split, monthly series | not stated |
| `keyword_info_normalized_with_bing` / `_with_clickstream` | Google's volume split back into individual keywords using Bing or clickstream data | monthly |

So for one keyword and month you can hold **up to four different volumes**: Google Ads, clickstream, Bing-normalised and clickstream-normalised.

### Endpoints

| Endpoint | In | Out | Use it for |
|---|---|---|---|
| `keyword_overview` | up to 700 keywords you name | the full keyword record for each | Enriching keywords you already have. Unknown keywords are skipped and not billed |
| `historical_keyword_data` | up to 700 keywords | one `keyword_info` snapshot per month back to Aug 2021 (volume, CPC, competition as they were then) | Long-term trend, CPC history |
| `bulk_keyword_difficulty` | up to 1000 keywords | KD only | Cheap KD refresh |
| `search_intent` | up to 1000 keywords (no location) | intent labels **with probabilities** | Intent when you need confidence scores |
| `keyword_suggestions` | one seed | keywords that **contain** the seed (long tail) | Expanding one term |
| `keyword_ideas` | up to 200 seeds | keywords in the **same product categories** as the seeds, ranked by relevance | Broad topic discovery |
| `related_keywords` | one seed + depth 0–4 | a walk through Google's "related searches" box, up to ~4,700 keywords at depth 4, each with its own related list | Building a topic graph (seed → related edges) |
| `keywords_for_site` | a domain or page | keywords **relevant** to it (not ones it ranks for) | Ideas for a site |
| `keywords_for_categories` / `categories_for_keywords` | category codes / keywords | keywords in a Google product category / the categories of a keyword | Category-based grouping |
| `top_searches` | a country + language | the whole keyword database, page by page, filterable | Bulk pulls ("all keywords with volume > 1000 containing X") |

---

## 4. Labs, ranking side: who ranks for what

Same pricing and rules as section 3. The keyword record from section 3 is embedded in each row. Rankings are refreshed weekly (the `status` endpoint gives the date). Only five SERP item types are tracked: `organic`, `paid`, `featured_snippet`, `local_pack`, `ai_overview_reference`.

Every ranking row carries:
- **position**: `rank_group` (position among results of the same type, e.g. organic #3) and `rank_absolute` (position counting every block on the page)
- the **ranking URL**: full URL, `relative_url` (the path) and domain
- **etv**: estimated monthly traffic, which is volume × CTR at that position
- **rank_changes**: new / up / down / previous position, compared with the previous crawl

Domain-level endpoints also return a **metrics** summary: how many keywords sit in positions 1, 2–3, 4–10, 11–20 … 91–100, plus total etv and how many are new, up, down or lost.

| Endpoint | In | Out | Use it for |
|---|---|---|---|
| `ranked_keywords` | a domain, subdomain or page | every keyword it ranks for, with position, URL, etv and rank change. `historical_serp_mode: lost` gives keywords it **lost**. Also the **only** Labs source of AI Overview citations (section 6) | "What does my site rank for?" |
| `relevant_pages` | a domain | its pages, each with a ranking-position summary and etv | "Which of my pages bring traffic?" |
| `subdomains` | a domain | the same summary per subdomain | |
| `competitors_domain` | a domain | domains that rank for the same keywords, with overlap count and both sides' metrics on the shared keywords | "Who are my organic competitors?" |
| `serp_competitors` | up to 200 keywords | the domains ranking for that keyword set, with average/median position, visibility and etv. Domain-level only, no URLs | "Who owns this topic?" |
| `domain_intersection` | two domains | keywords where both rank (with both URLs and positions), or with `intersections: false`, where the first ranks and the second doesn't | Keyword gap between two domains |
| `page_intersection` | up to 20 page URLs or URL patterns (+ pages to exclude) | keywords where all of them (or any) rank, with each page's position | Gap / cannibalisation between specific pages |
| `historical_serps` | one keyword | roughly **one full SERP per month for the last 12 months**, every item type included (AI Overviews too). $0.00012 per snapshot | "What did Google show for this keyword in March?" |
| `bulk_traffic_estimation` | up to 1000 domains or pages | etv and keyword count per target | Quick traffic estimate |
| `historical_bulk_traffic_estimation` | up to 1000 domains | etv per month back to Oct 2020. $0.12 + $0.0012 per domain | Traffic trend |

---

## 5. SERP API: the live results page

`/v3/serp/google/organic/...`. Give one keyword, location, language and device; get the parsed results page.

### Modes and price (per 10 results)

| Mode | Speed | Price |
|---|---|---|
| Standard queue (`task_post`, then `task_get` or a webhook) | ~5 min | $0.0006 |
| Standard, high priority | ~1 min | $0.0012 |
| Live | ~6 s | $0.002 |

A queued result can be fetched for 30 days. Three output formats from the same task:
- **regular**: organic, ads and featured snippet only
- **advanced**: every block on the page, fully parsed. This is the one to use.
- **html**: raw HTML

### Parameters that matter

| Parameter | What it does |
|---|---|
| `keyword`, `location_code`, `language_code` | the search. Location can be anything down to a city or coordinates |
| `device` / `os` | desktop (default) or mobile. Results differ |
| `depth` | how many results; default 10, up to 200 live / 700 queued. Each extra 10 costs more |
| `load_async_ai_overview` | waits for an AI Overview that Google loads late. Without it, those come back `null`. Costs one extra base price, refunded if no late-loading overview appears |
| `people_also_ask_click_depth` | 1–4: opens People Also Ask questions to load more. $0.00015 per click |
| `target` / `stop_crawl_on_match` | return only results for a domain, or stop paging once it is found. Useful for rank checking |
| `group_organic_results` | whether a second result from the same domain is nested or counted separately. Changes organic positions; keep it fixed |

### What comes back

One snapshot header (keyword, location, language, fetch time, Google's result count, spelling correction, the list of item types present) plus a flat list of **items in page order**. Each item has `type`, `rank_group`, `rank_absolute`, and type-specific fields. About 45 item types, in families:

| Family | Item types | Has URLs to match against your pages? |
|---|---|---|
| Web results | `organic` (with sitelinks), `paid`, `featured_snippet`, `answer_box` | yes |
| Questions | `people_also_ask` (each question has an answer URL, or an AI-generated answer), `related_searches` and `people_also_search` (just strings), `discussions_and_forums`, `perspectives`, `questions_and_answers` | yes, except the string lists |
| AI | `ai_overview` | yes (citations) |
| Knowledge | `knowledge_graph` (with many sub-parts) | some |
| Media | `top_stories`, `video`, `short_videos`, `images`, `twitter`, `carousel` | mostly |
| Local and travel | `local_pack` (one item per business), `map`, `local_services`, `hotels_pack`, `google_reviews`, `events`, `jobs`, `recipes`… | yes |
| Shopping | `shopping`, `popular_products`, `commercial_units`, `product_considerations`, `refine_products` | mostly |
| Utility | `stocks_box`, `currency_box`, `math_solver` | no |

Nested lists inside an item (sitelinks, People Also Ask answers, AI Overview citations) have no position of their own; their order in the array is the only order.

### Other SERP endpoints (one line each)

- **Autocomplete**: keyword → Google's autocomplete suggestions. Good for discovery.
- **Maps / Local Finder**: local business listings with address, rating, category, place ID.
- **News / Images**: the News and Images tabs.
- **Bing organic / YouTube organic**: the same idea for those engines.

---

## 6. AI Overview: where it lives

Google's AI Overview shows up in six places across these APIs:

| Where | What you get | Good for |
|---|---|---|
| SERP API, `ai_overview` item | The full overview: answer text (markdown), its sections, and the **cited sources** | Live check per keyword |
| SERP API, inside `people_also_ask` and `knowledge_graph` | Smaller AI answers nested in those blocks, same shape | Extra citations |
| SERP API, **Google AI Mode** (`/v3/serp/google/ai_mode/...`) | The separate AI Mode chat-style answer and its sources. Cites different sources from AI Overview for the same query. $0.0012 queued / $0.004 live | Comparing the two AI surfaces |
| Labs `ranked_keywords` with `item_types: ["ai_overview_reference"]` | Every keyword where a **domain or page is cited** in an AI Overview, with the cited URL, its position among citations, etv and change since the last crawl | "Where is my site cited?" across all keywords at once |
| Labs `serp_info.serp_item_types` | Only a yes/no: this keyword's SERP had an AI Overview at the last crawl | Filtering keywords by AI Overview presence |
| Labs `historical_serps` | Full past AI Overviews inside the monthly snapshots | History |

### Shape of one AI Overview

```
ai_overview
├── markdown                  the whole answer
├── asynchronous_ai_overview  whether it loaded late
├── items[]                   the sections of the answer
│   ├── ai_overview_element           title, text, links, images, references[]
│   ├── ai_overview_table_element     a table, references[]
│   ├── ai_overview_video_element     a video (no references)
│   └── ai_overview_expanded_element  "show more" parts, each with references[]
└── references[]              sources cited for the overview as a whole
```

Each reference is just `url`, `domain`, `title`, `source` (site name) and `text` (the snippet Google quoted). The same URL can appear at several levels.

### Things to know

- **A late-loading overview reads as "no overview" unless you ask for it.** Without `load_async_ai_overview`, a late-loading AI Overview comes back as `null`.
- **Very volatile.** DataForSEO says the same query can have an overview one day, none the next, and different sources the day after. They suggest daily checks for tracking.
- **Citation and ranking are separate signals.** A page can be cited while ranking badly, or rank well and never be cited.
- **Citation order is undocumented.** The SERP API gives no position for a reference. Labs gives one, but doesn't define what it means.

---

## 7. Which API answers which question

| Question | Best source | Alternatives |
|---|---|---|
| How many searches does this keyword get? | Labs `keyword_overview` (volume + everything else) | any Labs list endpoint, which returns the same record |
| How has its volume or CPC changed over the years? | Labs `historical_keyword_data` (back to Aug 2021) | |
| Is it seasonal? | 12-month series and `search_volume_trend` in the keyword record | |
| How hard is it to rank? | `keyword_difficulty` in the keyword record | `bulk_keyword_difficulty` |
| What does the searcher want? | `search_intent_info` in the keyword record | `search_intent` (with probabilities) |
| What other keywords exist around this topic? | `keyword_suggestions` (contains the seed), `keyword_ideas` (same category), `related_keywords` (Google's related searches) | `keywords_for_site`, `top_searches`; SERP `autocomplete`, `people_also_ask`, `related_searches` |
| Which keywords are near-duplicates of each other? | `core_keyword` in the keyword record | |
| What does my site rank for, and on which page? | Labs `ranked_keywords` | SERP API with `target` for specific keywords |
| Which of my pages get traffic? | Labs `relevant_pages` | |
| What keywords did I lose? | `ranked_keywords` with `historical_serp_mode: lost` | |
| Who are my competitors? | Labs `competitors_domain` (by domain), `serp_competitors` (by keyword set) | |
| What do they rank for that I don't? | Labs `domain_intersection` (`intersections: false`), `page_intersection` | |
| What does Google show right now for this keyword? | SERP API advanced | Labs `serp_info` (only which features appear, up to 90 days old) |
| What did Google show months ago? | Labs `historical_serps` | |
| Does this keyword trigger an AI Overview, and who is cited? | SERP API with `load_async_ai_overview` | Labs `serp_info` for presence only |
| Where is my site cited in AI Overviews? | Labs `ranked_keywords` with `ai_overview_reference` | Daily SERP API checks for a tracked set |

---

## 8. Overlaps: same data, several sources

| Data | Comes from |
|---|---|
| Search volume + monthly series | Labs keyword record (4 variants: Google Ads, clickstream, Bing-normalised, clickstream-normalised), Labs historical keyword data |
| CPC / competition / bids | Labs keyword record, Labs historical keyword data |
| Keyword difficulty | Labs keyword record, Labs bulk KD, also echoed in Labs ranking rows |
| Intent | Labs keyword record (labels), Labs `search_intent` (labels + probabilities) |
| Which SERP features appear | Labs `serp_info` (stored crawl), SERP API `item_types` (live), Labs historical SERPs |
| Who ranks where | SERP API (live, any keyword, full page), Labs `ranked_keywords` / intersections (weekly, 5 item types, adds etv and change), Labs historical SERPs (monthly) |
| AI Overview citations | SERP API (live, per keyword), Labs `ranked_keywords` (per domain/page, with etv), Labs historical SERPs |

The keyword record from section 3 is embedded in nearly every Labs response, including the ranking endpoints. A call to `ranked_keywords` therefore also refreshes the volume, KD and intent for every keyword it returns.

---

## 9. What Meelu calls today

From `api/src/providers/seo_data/dataforseo.py`:

- **Labs keyword side:** `keyword_ideas`, `keyword_overview` (with clickstream, so double price), `historical_keyword_data`
- **Labs ranking side:** `ranked_keywords`, `competitors_domain`, `serp_competitors`, `relevant_pages`, `historical_serps`, `bulk_traffic_estimation`
- **SERP API:** Google organic **live** advanced
- **Keywords Data (out of v1 scope):** Google Trends explore. Drop it for v1.

Not used yet, and worth knowing about:
- `keyword_suggestions` and `related_keywords`: discovery
- `bulk_keyword_difficulty`: a cheap KD refresh
- `domain_intersection` / `page_intersection`: keyword gaps
- the SERP API **standard queue**: about 3× cheaper than live, if a few minutes' wait is fine
- `load_async_ai_overview`: without it, some AI Overviews come back `null`
- Google AI Mode
