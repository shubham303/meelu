# DataForSEO Labs API (Google): keyword research endpoints

Reference for designing Meelu's Postgres keyword storage. Everything below was read from the live DataForSEO v3 docs and pricing pages on 2026-10-06. Where the docs say nothing, this file says "not stated in docs". Where a statement comes from a response example instead of the field table, it is marked "(from example)".

Base URL for every call: `https://api.dataforseo.com/v3/`. Auth is HTTP Basic (login + API password).

---

## 0. General rules for all Labs endpoints

Sources:
- https://docs.dataforseo.com/v3/dataforseo_labs/overview/
- https://docs.dataforseo.com/v3/dataforseo_labs/google/overview/
- https://dataforseo.com/pricing/dataforseo-labs/dataforseo-google-api

- **Live only.** Labs supports only the Live method. One POST returns the result. There is no task_post / tasks_ready / task_get flow.
- **One task per call.** "Each Live API call can contain only one task." The body is still a JSON array with one object.
- **Rate limits.** Up to 2000 API calls per minute. At most 30 simultaneous requests.
- **Data source.** Labs reads DataForSEO's own databases (Keyword Database, SERPs Database), not Google Ads in real time.
- **Search engines in Labs.** The Labs overview lists Google, Amazon, Google Play and App Store.
  - **Amazon** has its own keyword endpoints (Bulk Search Volume, Related Keywords, Ranked Keywords, and product endpoints). https://docs.dataforseo.com/v3/dataforseo_labs/amazon/overview/
  - **Bing** pages still resolve (for example https://docs.dataforseo.com/v3/dataforseo_labs/bing/overview/), but Bing is no longer in the Labs navigation or the Labs overview list. The Bing overview lists Related Keywords, Ranked Keywords, Bulk Keyword Difficulty and domain endpoints. It does not list Keyword Suggestions, Keyword Ideas or Keywords For Site (`/bing/keyword_suggestions/live/` returns 404). The Locations endpoint says Bing and Amazon are limited to US/English.
  - This file covers Google only.
- **Response envelope (every endpoint):**
  ```
  { version, status_code, status_message, time, cost, tasks_count, tasks_error,
    tasks: [ { id (UUID), status_code (10000-60000), status_message, time, cost,
               result_count, path[], data{echo of request}, result: [ ... ] } ] }
  ```
  `cost` is in USD at both the top level and per task. Success is `status_code` 20000.
- **`tag`** (string, max 255 chars) is an optional request field on every POST endpoint. It is echoed back in `data`.
- **Keyword normalisation.** Every endpoint says input keywords "will be converted to lowercase format". Response keywords are returned "with decoded %## (plus character '+' will be decoded to a space character)".

### 0.1 Pricing (Google Labs)

Source: https://dataforseo.com/pricing/dataforseo-labs/dataforseo-google-api (fetched 2026-10-06)

| Group | Price per task | Price per item |
|---|---|---|
| Search Intent | $0.012 | $0.00012 per keyword |
| **All other endpoints** (covers every keyword research endpoint in this file) | $0.012 | $0.00012 per returned item |
| Historical Rank Overview | $0.12 | $0.0012 per item (month) |
| Historical SERPs | — | $0.00012 per SERP |
| Historical Bulk Traffic Estimation / Domain Metrics by Categories | $0.12 | $0.0012 per domain |

- **Clickstream flag:** "if you set `include_clickstream_data` to `true`, the cost of the request is multiplied by 2." Each endpoint that has this flag also says "you will be charged double the price for the request".
- The pricing page's worked example for "all other endpoints" is: 1,000 tasks × $0.012 + 1,000,000 items × $0.00012 = $132 per 1M keywords.
- **Discrepancy.** Most response examples in the endpoint docs show older costs: `0.0101` for 1 item, which is $0.01 + $0.0001 per item. The pricing page is the current source. Categories for Keywords shows `0.00103` for 3 items in its example, which is 10× lower than the other endpoints. The pricing page does not list it separately.
- Keyword Overview and Historical Keyword Data: "you will not be charged for the keywords omitted in the results".
- The help center confirms the per-item model for Keyword Ideas: "$0.012 for the request and then $0.00012 per every keyword in the results array" (https://dataforseo.com/help-center/dataforseo-labs-api-vs-google-ads-api).

### 0.2 Filters and order_by syntax

Source: https://docs.dataforseo.com/v3/dataforseo_labs/filters/ (GET `https://api.dataforseo.com/v3/dataforseo_labs/available_filters`, free)

- **`filters`** is an array of up to **8** conditions. Conditions are joined with `"and"` / `"or"`, and groups can be nested:
  ```json
  [["keyword_info.search_volume","in",[0,1000]], "and", ["keyword_info.competition_level","=","LOW"]]
  ```
- A single condition has the shape `[field_path, operator, value]`. The field path is relative to the item, for example `keyword_info.search_volume`. On Related Keywords, items wrap the data in `keyword_data`, so the path becomes `keyword_data.keyword_info.search_volume`.
- **Operators by field type:**
  - num: `<`, `<=`, `>`, `>=`, `=`, `<>`, `in`, `not_in`
  - str: `match`, `not_match` (full-text word match), `like`, `not_like`, `ilike`, `not_ilike` (`%` wildcard), `in`, `not_in`, `=`, `<>`, `regex`, `not_regex` (RE2 syntax, max 1000 chars)
  - bool: `=`, `<>`
  - array.str / array.num: `has`, `has_not`
  - time: `<`, `>`. The value format is `"yyyy-mm-dd hh-mm-ss +00:00"`.
  - `in` / `not_in` take an array as the value.
- **`order_by`** is an array of up to **3** strings of the form `"field,asc|desc"`, for example `["keyword_info.search_volume,desc","keyword_info.cpc,desc"]`. Fields of type `array.str` and `array.num` cannot be used for sorting.
- **`relevance`** is the default sort on Keyword Ideas and Keywords For Site (`["relevance,desc"]`). It is an internal score. It cannot be used as a filter and is not returned in the results.
- **Filterable keyword fields (Related Keywords list, `keyword_data.` prefix).** The `available_filters` response lists these with their types:
  - **keyword_info**: `keyword` (str); `last_updated_time` (time); `competition`, `cpc`, `search_volume`, `low_top_of_page_bid`, `high_top_of_page_bid` (num); `competition_level` (str); `categories` (array.num); `search_volume_trend.monthly`, `.quarterly`, `.yearly` (num).
  - **clickstream_keyword_info**: `search_volume`; `last_updated_time`; `gender_distribution.female`, `.male`; `age_distribution.18-24` … `.55-64`.
  - **keyword_properties**: `core_keyword` (str), `synonym_clustering_algorithm` (str), `keyword_difficulty` (num), `detected_language` (str), `is_another_language` (bool).
  - **serp_info**: `check_url` (str), `serp_item_types` (array.str), `se_results_count` (num), `last_updated_time`, `previous_updated_time` (time).
  - **avg_backlinks_info**: every numeric field plus `last_updated_time`.
  - **search_intent_info**: `main_intent` (str), `foreign_intent` (array.str), `last_updated_time`.
  - **keyword_info_normalized_with_bing** and **keyword_info_normalized_with_clickstream**: `search_volume`, `last_updated_time`, `is_normalized`.
  - **Related Keywords only**: `depth` (num).
  - Monthly series (`monthly_searches`) are not filterable.

### 0.3 Pagination

- **`limit`** sets the page size. Defaults differ per endpoint (see each endpoint). The maximum is 1000 on every paginated keyword endpoint.
- **`offset`** is an integer, default 0. The docs recommend it "only when retrieving up to 10,000 results".
- **`offset_token`** is a string returned in each `result[0].offset_token`. Send it back to get the next page. "If the offset_token is specified in the request, all other parameters except limit will not be taken into account." Tokens are unique per subsequent task. Use tokens to go past 10,000 rows without timeouts.
- **Support per endpoint:**
  - Keyword Suggestions, Keyword Ideas, Keywords For Site, Keywords For Categories and Top Searches support `offset_token`.
  - Related Keywords supports `offset` only. The `offset_token` param is not listed and the result has no `offset_token` field.

---

## 1. The shared keyword_data object

Sources (each endpoint repeats this table):
- https://docs.dataforseo.com/v3/dataforseo_labs/google/keyword_suggestions/live/
- https://docs.dataforseo.com/v3/dataforseo_labs/google/keyword_ideas/live/
- https://docs.dataforseo.com/v3/dataforseo_labs/google/keyword_overview/live/

Every list endpoint returns items with the same shape. Related Keywords puts this object under `items[].keyword_data`. The others put these fields directly on `items[]`. In the response JSON, all the sub-objects below are **siblings**. Some doc tables indent `serp_info` and the objects after it under `keyword_properties`, but the JSON examples show them at the same level.

```
{
  se_type: "google",
  keyword: string,
  location_code: int,
  language_code: string,
  search_partners: bool,              // Keyword Overview only
  keyword_info: {...},
  clickstream_keyword_info: {...}|null,
  keyword_properties: {...},
  serp_info: {...}|null,
  avg_backlinks_info: {...}|null,
  search_intent_info: {...}|null,
  keyword_info_normalized_with_bing: {...}|null,
  keyword_info_normalized_with_clickstream: {...}|null
}
```

### 1.1 Identity fields

| Field | Type | Meaning |
|---|---|---|
| `se_type` | string | Search engine type. Always `"google"` here. |
| `keyword` | string | The keyword, lowercased. |
| `location_code` | integer | Location code from the request (country level only in Labs, see 4.1). |
| `language_code` | string | Language code from the request (ISO 639-1). |
| `search_partners` | boolean | **Keyword Overview only.** `true` means the data covers Google plus partner sites that host Google search. `false` means Google search sites only. |

### 1.2 `keyword_info`: Google Ads-derived metrics

| Field | Type | Meaning |
|---|---|---|
| `se_type` | string | Search engine type. |
| `last_updated_time` | string | When the keyword data was updated. UTC, `"yyyy-mm-dd hh-mm-ss +00:00"`. |
| `competition` | float | Relative amount of paid competition, from Google Ads data, 0 to 1 inclusive. Can be `null` (from example, Top Searches). |
| `competition_level` | string | Paid-SERP competition level: `LOW`, `MEDIUM`, `HIGH`. `null` if unknown. |
| `cpc` | float | Average cost per click (USD) historically paid for the keyword. |
| `search_volume` | integer | Average monthly search volume (approximate searches on google.com). |
| `low_top_of_page_bid` | float | Minimum bid for a top-of-first-page ad. It is "greater than about 20% of the lowest bids for which ads were displayed". It can differ by location. |
| `high_top_of_page_bid` | float | Maximum bid for a top-of-first-page ad, "greater than about 80% of the lowest bids". It can differ by location. |
| `categories` | array of int | Google product and service category codes (see 4.2). |
| `monthly_searches` | array | Approximate searches for each of the past 12 months for the location. Items: `{year: int, month: int, search_volume: int}`, newest first (from example). |
| `search_volume_trend` | object | Percent change in search volume versus the previous period. |
| `search_volume_trend.monthly` | integer | Percent change versus the previous month. |
| `search_volume_trend.quarterly` | integer | Percent change versus the previous quarter. |
| `search_volume_trend.yearly` | integer | Percent change versus the previous year. |

### 1.3 `clickstream_keyword_info`

This object is returned only when `include_clickstream_data: true`, which doubles the price. Otherwise it is `null`.

| Field | Type | Meaning |
|---|---|---|
| `search_volume` | integer | Monthly average clickstream search volume. |
| `last_updated_time` | string | When the clickstream dataset was updated (UTC). |
| `gender_distribution.female` | integer | Docs: "number of female users in the relevant clickstream dataset". |
| `gender_distribution.male` | integer | Docs: "number of male users". The example shows 51 / 49, which looks like a percent split. The docs do not say it is a percent. |
| `age_distribution.18-24` … `55-64` | integer | Five age buckets: `18-24`, `25-34`, `35-44`, `45-54`, `55-64`. Docs: "number of users … that fall within the … age range". The example sums to 100. |
| `monthly_searches` | array | `{year, month, search_volume}` clickstream volume per month. The number of months is not stated in docs. |

### 1.4 `keyword_properties`

| Field | Type | Meaning |
|---|---|---|
| `se_type` | string | Search engine type. |
| `core_keyword` | string | The main keyword of the synonym group this keyword belongs to. `null` means the database holds no keywords that the algorithm treats as synonyms of this one. |
| `synonym_clustering_algorithm` | string | The algorithm that grouped the synonyms: `keyword_metrics` (based on keyword_info values) or `text_processing` (text-based). `null` means the same as for `core_keyword`. |
| `keyword_difficulty` | integer | Chance of reaching the top-10 organic results, on a logarithmic 0–100 scale. It is calculated from, among other things, the link profiles of the top-10 pages. |
| `detected_language` | string | The keyword's language as DataForSEO detects it. Can be `null` (from example). |
| `is_another_language` | boolean | `true` when the detected language differs from the language in the request. |
| `words_count` | integer | Number of words in the keyword. **Documented on** Keyword Suggestions, Keyword Ideas, Keywords For Site, Keywords For Categories and Top Searches. **Absent from** the Related Keywords and Keyword Overview tables and examples. |

### 1.5 `serp_info`

This object is returned only when `include_serp_info: true`. It is also `null` when the database has no SERP for the keyword.

| Field | Type | Meaning |
|---|---|---|
| `se_type` | string | Search engine type. |
| `check_url` | string | Direct Google URL for the SERP, so you can verify the data. |
| `serp_item_types` | array of string | SERP feature types present on the page. Possible values: answer_box, app, carousel, multi_carousel, featured_snippet, google_flights, google_reviews, third_party_reviews, google_posts, images, jobs, knowledge_graph, local_pack, hotels_pack, map, organic, paid, people_also_ask, related_searches, people_also_search, shopping, top_stories, twitter, video, events, mention_carousel, recipes, top_sights, scholarly_articles, popular_products, podcasts, questions_and_answers, find_results_on, stocks_box, visual_stories, commercial_units, local_services, google_hotels, math_solver, currency_box, product_considerations, found_on_web, short_videos, refine_products, explore_brands, perspectives, discussions_and_forums, compare_sites, courses, ai_overview. |
| `se_results_count` | string / integer | Number of search results Google reports. The doc tables say `string` on some endpoints and `integer` on others. The JSON examples show an integer (for example `19880000000`, which needs a bigint). |
| `last_updated_time` | string | When the SERP was last crawled (UTC). |
| `previous_updated_time` | string | The crawl before the latest one (UTC). Not listed in the Top Searches table. |

### 1.6 `avg_backlinks_info`

Averages across the top-10 pages that rank organically for the keyword.

| Field | Type | Meaning |
|---|---|---|
| `se_type` | string | Search engine type. |
| `backlinks` | float | Average number of backlinks. |
| `dofollow` | float | Average number of dofollow links. |
| `referring_pages` | float | Average number of referring pages. |
| `referring_domains` | float | Average number of referring domains. |
| `referring_main_domains` | float | Average number of referring main domains. |
| `rank` | float | Average page rank (DataForSEO's backlink rank metric). |
| `main_domain_rank` | float | Average main domain rank. |
| `last_updated_time` | string | When the backlink data was updated (UTC). |

### 1.7 `search_intent_info`

| Field | Type | Meaning |
|---|---|---|
| `se_type` | string | Possible value: `google`. |
| `main_intent` | string | `informational`, `navigational`, `commercial` or `transactional`. |
| `foreign_intent` | array of string | Supplementary intents, using the same four values. Can be `null`. |
| `last_updated_time` | string | When the intent was last computed (UTC). The examples show dates more than a year older than `keyword_info`, so intent is refreshed less often. |

### 1.8 `keyword_info_normalized_with_bing` / `keyword_info_normalized_with_clickstream`

Both objects have the same shape. The docs say these, together with `clickstream_keyword_info`, are returned when `include_clickstream_data: true`. However, the Keyword Suggestions and Top Searches examples show them populated without the flag, so do not rely on them being absent.

| Field | Type | Meaning |
|---|---|---|
| `last_updated_time` | string | When the dataset was updated (UTC). |
| `search_volume` | integer | Current search volume, normalised with Bing Ads data or with clickstream data. |
| `is_normalized` | boolean | `true` if the values were actually normalised. |
| `monthly_searches` | array | `{year, month, search_volume}`. The examples show 12 or 13 months. |

**What "normalised" means.** Source: https://dataforseo.com/help-center/how-to-get-precise-search-volume-for-keywords-with-the-dataforseo-search-volume-endpoint

Google Ads merges close variants and misspellings into one volume. DataForSEO calls its fix the "DataForSEO Search Volume". The steps are:
1. Fetch the Google Ads volume.
2. Find the Google Ads "keyword group" that the keyword belongs to.
3. Split the group's merged volume across the keywords in the group, using either Bing Ads volume per keyword or clickstream event counts per keyword.
4. Calculate 12 months of values this way.

### 1.9 `impressions_info`

Not present in the current docs for any Google keyword research endpoint in this file. No field table or example on these pages contains it. Do not plan storage for it.

---

## 2. Endpoints

### 2.1 Keyword Suggestions

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/keyword_suggestions/live/

`POST /v3/dataforseo_labs/google/keyword_suggestions/live`

- **What it returns.** Full-text matches: long-tail keywords that **contain** the seed, with extra words before, after or inside it. The word order can differ from the seed.
- **Data source:** DataForSEO Keyword Database.

**Request**

| Param | Type | Notes |
|---|---|---|
| `keyword` | string | Required. One seed. |
| `location_name` / `location_code` | string / int | **Optional.** "Ignore this field to get the results for all available locations." |
| `language_name` / `language_code` | string | Optional. If omitted, the language with the most keyword records in the location is used. See `available_languages.keywords` in Locations and Languages. |
| `include_seed_keyword` | bool | Default `false`. If `true`, the seed's data is returned in `seed_keyword_data`. |
| `include_serp_info` | bool | Default `false`. |
| `include_clickstream_data` | bool | Default `false`. Doubles the price. |
| `exact_match` | bool | Default `false`. If `true`, results contain the exact seed phrase, with words allowed only before or after it. |
| `ignore_synonyms` | bool | Default `false`. If `true`, only core keywords are returned and highly similar keywords are dropped. |
| `filters` | array | Up to 8 conditions. |
| `order_by` | array | Up to 3 rules. Default `["keyword_info.search_volume,desc"]`. |
| `limit` | int | Default **100**, max **1000**. |
| `offset` | int | Default 0. Use up to 10k rows. |
| `offset_token` | string | Use beyond 10k rows. |
| `tag` | string | Optional. |

**Response** `tasks[0].result[0]`:
```
{ se_type, seed_keyword, seed_keyword_data{same shape as an item}|null,
  location_code, language_code, total_count, items_count, offset, offset_token,
  items: [ keyword_data shape (section 1) ] }
```
- `total_count` is the total number of matches in the database.
- **Pricing:** $0.012 per task + $0.00012 per returned item. ×2 with clickstream.

### 2.2 Keyword Ideas

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/keyword_ideas/live/

`POST /v3/dataforseo_labs/google/keyword_ideas/live`

- **What it returns.** Relevance-based search for keywords in the **same product/service categories** as the seeds.
- **Data source:** DataForSEO Keyword Database segmented by product categories.

**Request**

| Param | Type | Notes |
|---|---|---|
| `keywords` | array | Required. Up to **200** seeds. |
| `location_name` / `location_code` | | **Required** (one of them). |
| `language_name` / `language_code` | | Optional. The default rule is the same as Keyword Suggestions. |
| `closely_variants` | bool | Default `false`. `true` uses phrase-match, `false` uses broad-match. |
| `ignore_synonyms` | bool | Default `false`. |
| `include_serp_info` | bool | Default `false`. |
| `include_clickstream_data` | bool | Default `false`. ×2 price. |
| `limit` | int | Default **700**, max **1000**. |
| `offset`, `offset_token` | | As in 0.3. |
| `filters` | array | Up to 8. You cannot filter by relevance. |
| `order_by` | array | Default `["relevance,desc"]`. Up to 3 rules. |
| `tag` | string | |

**Response** `result[0]`:
```
{ se_type, seed_keywords[], location_code, language_code, total_count,
  items_count, offset, offset_token, items: [ keyword_data shape ] }
```
- There is no `seed_keyword_data`.
- The intro text mentions "minimum, maximum and average values of clicks and CPC". No such fields appear in the field table or the example.
- **Pricing:** $0.012 per task + $0.00012 per item. ×2 with clickstream.

### 2.3 Related Keywords

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/related_keywords/live/

`POST /v3/dataforseo_labs/google/related_keywords/live`

- **What it returns.** Keywords from Google's "Searches related to" SERP block, found by a depth-first walk.
- **Data source:** DataForSEO SERPs Database.

**Request**

| Param | Type | Notes |
|---|---|---|
| `keyword` | string | Required. |
| `location_name` / `location_code` | | **Required** (one). |
| `language_name` / `language_code` | | **Required** (one). |
| `depth` | int | 0–4, default **1**. Approximate maximum keywords per level: 0 = only the seed, 1 = 8, 2 = 72, 3 = 584, 4 = 4680. |
| `include_seed_keyword` | bool | Default `false`. |
| `include_serp_info` | bool | Default `false`. |
| `include_clickstream_data` | bool | Listed, but **the description cell is empty in the docs**. |
| `ignore_synonyms` | bool | Listed, but **the description cell is empty in the docs**. |
| `replace_with_core_keyword` | bool | Default `false`. If `true`, `serp_info` and `related_keywords` are returned for the **core keyword** of the seed's synonym group instead of the seed itself. |
| `filters` | array | Up to 8. Paths are prefixed `keyword_data.` (for example `["keyword_data.keyword_info.search_volume",">",0]`). `depth` is also filterable. |
| `order_by` | array | Default `["keyword_data.keyword_info.search_volume,desc"]`. |
| `limit` | int | Default **100**, max **1000**. |
| `offset` | int | Default 0. **No `offset_token`.** |
| `tag` | string | |

**Response** `result[0]`:
```
{ se_type, seed_keyword, seed_keyword_data|null, location_code, language_code,
  total_count, items_count,
  items: [ { se_type,
             keyword_data: { keyword_data shape (section 1) },
             depth: int,                     // depth level at which this keyword was found
             related_keywords: [string] } ] }   // that keyword's own related searches
```
- `related_keywords` is a list of plain strings. These are graph edges, with no metrics attached.
- The `keyword_properties` table and example here have no `words_count`.
- **Pricing:** $0.012 per task + $0.00012 per item. The `include_clickstream_data` description is empty here, so its pricing effect on this endpoint is not stated in the docs. The pricing page says the flag doubles the request in general.

### 2.4 Keywords For Site

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/keywords_for_site/live/

`POST /v3/dataforseo_labs/google/keywords_for_site/live`

- **What it returns.** Keywords relevant to a domain, subdomain or page. These are **relevance-based, not rankings**. Ranked Keywords is the separate endpoint for actual rankings and is outside this file's scope.
- **Data source:** DataForSEO Keyword Database segmented by relevant domains/pages from the Google Ads API, supplemented by the SERP Database.
- **Freshness:** "data is updated weekly, the latest update time is available in the Status endpoint."

**Request**

| Param | Type | Notes |
|---|---|---|
| `target` | string | Required. Give a domain without `https://` and without `www.`. Give a subdomain without `https://`. Give a page with `https://` or `www.`. A page URL without those prefixes is treated as the whole domain. |
| `location_name` / `location_code` | | **Required** (one). |
| `language_name` / `language_code` | | Optional. |
| `include_serp_info` | bool | Default `false`. |
| `include_subdomains` | bool | Default **`true`**. |
| `include_clickstream_data` | bool | Default `false`. ×2 price. |
| `limit` | int | Default **100**, max **1000**. |
| `offset`, `offset_token` | | |
| `filters` | array | Up to 8. You cannot filter by relevance. |
| `order_by` | array | Default `["relevance,desc"]`. |
| `tag` | string | |

**Response** `result[0]`:
```
{ se_type, target, location_code, language_code, total_count, items_count,
  offset, offset_token, items: [ keyword_data shape ] }
```
- **Pricing:** $0.012 per task + $0.00012 per item. ×2 with clickstream.

### 2.5 Keyword Overview

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/keyword_overview/live/

`POST /v3/dataforseo_labs/google/keyword_overview/live`

- **What it returns.** A lookup: the full keyword data for keywords **you name**. There is no discovery, no filters, no sort and no pagination.
- **Data source:** the Google Ads API. "We update keyword metrics once a month after the data source completes its updates. Note that sometimes Google tends to rewrite search volume values for a given month, and we update the values in this endpoint respectively."

**Request**

| Param | Type | Notes |
|---|---|---|
| `keywords` | array | Required. Max **700** keywords. Each keyword: max 80 characters, max 10 words. |
| `location_name` / `location_code` | | **Required** (one). |
| `language_name` / `language_code` | | **Required** (one). |
| `include_serp_info` | bool | Default `false`. |
| `include_clickstream_data` | bool | Default `false`. ×2 price. |
| `tag` | string | |

- Keywords the database does not have are left out of the results and are **not charged**.

**Response** `result[0]`:
```
{ se_type, location_code, language_code, items_count,
  items: [ { se_type, keyword, location_code, language_code, search_partners,
             keyword_info, keyword_info_normalized_with_bing,
             keyword_info_normalized_with_clickstream, clickstream_keyword_info,
             keyword_properties, serp_info, avg_backlinks_info, search_intent_info } ] }
```
- There is no `total_count` and no `words_count`. `search_partners` appears only on this endpoint.
- **Pricing:** $0.012 per task + $0.00012 per returned keyword. ×2 with clickstream. The example with clickstream shows cost `0.0201` for 1 keyword.

### 2.6 Bulk Keyword Difficulty

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/bulk_keyword_difficulty/live/

`POST /v3/dataforseo_labs/google/bulk_keyword_difficulty/live`

**Request**

| Param | Type | Notes |
|---|---|---|
| `keywords` | array | Required. Max **1000**. |
| `location_name` / `location_code` | | **Required** (one). |
| `language_name` / `language_code` | | **Required** (one). |
| `tag` | string | |

**Response** `result[0]`:
```
{ se_type, location_code, language_code, total_count, items_count,
  items: [ { se_type, keyword, keyword_difficulty: int } ] }
```
- `keyword_difficulty` uses the same 0–100 logarithmic metric as `keyword_properties.keyword_difficulty`.
- There is no timestamp for when KD was computed.
- **Pricing:** $0.012 per task + $0.00012 per item. The example shows `0.0103` for 3 keywords at the older rate.

### 2.7 Search Intent

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/search_intent/live/

`POST /v3/dataforseo_labs/google/search_intent/live`

- **Method.** A machine-learning classifier trained on keyword and SERP data. It returns four classes: informational, navigational, commercial, transactional.

**Request**

| Param | Type | Notes |
|---|---|---|
| `keywords` | array | Required. Max **1000**. |
| `tag` | string | |

- **No location or language parameter is documented.**

**Response** `result[0]`:
```
{ items_count,
  items: [ { keyword,
             keyword_intent: { label: string, probability: float },        // 1 = highest
             secondary_keyword_intents: [ { label, probability } ] | null } ] }
```
- There is no `se_type`, `location_code`, `language_code` or timestamp in the result.
- **Differs from `search_intent_info`.** This endpoint returns **probabilities**. `search_intent_info` inside keyword_data returns only labels (`main_intent`, `foreign_intent`) with a `last_updated_time`.
- **Pricing:** $0.012 per task + $0.00012 per keyword. The example shows `0.01248` for 4 keywords, which matches the current pricing page.

### 2.8 Historical Keyword Data

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/historical_keyword_data/live/

`POST /v3/dataforseo_labs/google/historical_keyword_data/live`

- **What it returns.** Past monthly **snapshots** of `keyword_info`, available since **August 2021**, depending on the keyword, location and language.
- **Data source:** the Google Ads API, updated monthly. Google sometimes rewrites past months, and the endpoint follows those rewrites.

**Request**

| Param | Type | Notes |
|---|---|---|
| `keywords` | array | Required. Max **700**. Each keyword: max 80 characters, max 10 words. |
| `location_name` / `location_code` | | **Required** (one). |
| `language_name` / `language_code` | | **Required** (one). |
| `tag` | string | |

- There is no date-range parameter. Omitted keywords are not charged.

**Response** `result[0]`:
```
{ se_type, location_code, language_code, items_count,
  items: [ { se_type, keyword, location_code, language_code,
             history: [ { year, month,
                          keyword_info: { se_type, last_updated_time, competition,
                            competition_level, cpc, search_volume, low_top_of_page_bid,
                            high_top_of_page_bid, categories[], monthly_searches[12],
                            search_volume_trend{monthly,quarterly,yearly} } } ] } ] }
```
- **Each `history` entry is a full `keyword_info` snapshot as it was in that month.** The snapshot includes its own trailing 12-month `monthly_searches` array, so the monthly volumes overlap heavily from one snapshot to the next. The example returns 44 history entries for one keyword, newest first (2025-02 back to 2021).
- No keyword_properties, SERP, backlink, intent or clickstream data is returned.
- **Pricing:** $0.012 per task + $0.00012 per item. The example charges `0.0101` for 1 keyword with 44 months, so billing appears to be per keyword, not per month (from example; not stated explicitly).

### 2.9 Categories for Keywords

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/categories_for_keywords/live/

`POST /v3/dataforseo_labs/google/categories_for_keywords/live`

**Request**

| Param | Type | Notes |
|---|---|---|
| `keywords` | array | Required. Max **1000**. |
| `language_name` / `language_code` | | **Required** (one). The supported list comes from Languages for Categories for Keywords (2.10). |
| `tag` | string | |

- **There is no location parameter.**

**Response** `result[0]`:
```
{ language_code, total_count, items_count,
  items: [ { keyword, categories: [int] } ] }
```
- **Pricing:** covered by "all other endpoints" on the pricing page. The example shows `0.00103` for 3 keywords, which is 10× cheaper than the other examples. Treat the exact rate as unconfirmed.

### 2.10 Languages for Categories for Keywords

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/categories_for_keywords/languages/

`GET /v3/dataforseo_labs/google/categories_for_keywords/languages`

- **Cost:** free.
- **Result:** `[ { language_name, language_code } ]`.

### 2.11 Keywords For Categories

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/keywords_for_categories/live/

`POST /v3/dataforseo_labs/google/keywords_for_categories/live`

This endpoint is still present in the docs.

**Request**

| Param | Type | Notes |
|---|---|---|
| `category_codes` | array of int | Required. Max **20**. |
| `location_name` / `location_code` | | **Required** (one). |
| `language_name` / `language_code` | | **Required** (one). |
| `category_intersection` | bool | Default **`true`**. `true` returns keywords in **all** the given categories. `false` returns keywords in **any** of them. |
| `include_serp_info`, `include_clickstream_data`, `ignore_synonyms` | bool | Default `false`. Clickstream ×2. |
| `limit` | int | Default **100**, max **1000**. |
| `offset`, `offset_token` | | |
| `filters`, `order_by` | | Same syntax as 0.2. |
| `tag` | string | |

**Response** `result[0]`:
```
{ se_type, seed_categories[], location_code, language_code, total_count,
  items_count, offset, offset_token, items: [ keyword_data shape ] }
```
- **Pricing:** $0.012 per task + $0.00012 per item. ×2 with clickstream.

### 2.12 Top Searches

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/top_searches/live/

`POST /v3/dataforseo_labs/google/top_searches/live`

- **What it is.** A bulk dump of the DataForSEO Keyword Database for one location and language. The docs say "over 7 billion keywords".
- **How to page.** The first call sets the parameters. Each later call sends only the returned `offset_token` (and `limit`) to get the next batch of up to 1000.

**Request**

| Param | Type | Notes |
|---|---|---|
| `location_name` / `location_code` | | **Required** (one). |
| `language_name` / `language_code` | | **Required** (one). |
| `include_serp_info`, `include_clickstream_data`, `ignore_synonyms` | bool | Default `false`. Clickstream ×2. |
| `filters`, `order_by` | | Same syntax as 0.2. |
| `limit` | int | Default **1000**, max **1000**. |
| `offset`, `offset_token` | | |
| `tag` | string | |

- There is no seed keyword.

**Response** `result[0]`:
```
{ se_type, location_code, language_code, total_count, items_count, offset,
  offset_token, items: [ keyword_data shape ] }
```
- The `serp_info` table here does not list `previous_updated_time`.
- **Pricing:** $0.012 per task + $0.00012 per item. ×2 with clickstream.

---

## 3. Shared helper endpoints

### 3.1 Locations and Languages

Source: https://docs.dataforseo.com/v3/dataforseo_labs/locations_and_languages/

`GET /v3/dataforseo_labs/locations_and_languages`

- **Cost:** free.
- A CSV version is also offered (last updated 2026-09-01).
- **Result item:**
  ```
  { location_code, location_name, location_code_parent (always null),
    country_iso_code, location_type ("Country" only),
    available_languages: [ { available_sources: ["google","bing","amazon"],
                             language_name, language_code (ISO 639-1),
                             keywords: int,   // keyword count for this location+language
                             serps: int } ] } // SERP count
  ```
- **Only countries are supported in Labs.** There are no cities or regions.
- Russia and Belarus are not supported.
- Bing and Amazon are limited to US/English.

### 3.2 Categories list

Source: https://docs.dataforseo.com/v3/dataforseo_labs/categories_list/

`GET /v3/dataforseo_labs/categories`

- **Cost:** free. A CSV download is also available.
- **Result:** `[ { category_code: int, category_name: string, category_code_parent: int|null } ]`.
- The categories are Google's product and service taxonomy, arranged as a tree through `category_code_parent`. For example, 10178 "Apparel Accessories" has parent 10021 "Apparel", which has parent `null`.

### 3.3 Available filters

Source: https://docs.dataforseo.com/v3/dataforseo_labs/filters/

`GET /v3/dataforseo_labs/available_filters`

- **Cost:** free.
- Returns every filterable field and its type, grouped by endpoint. Section 0.2 lists the keyword fields.

### 3.4 Status

Source: https://docs.dataforseo.com/v3/dataforseo_labs/status/

`GET /v3/dataforseo_labs/status`

- **Cost:** free.
- **Result:** `[ { google: {date_update: "yyyy-mm-dd"}, bing: {date_update}, amazon: {date_update} } ]`. Each value is the last date the Labs data for that engine was updated.

### 3.5 Available History

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/available_history/live/

`GET /v3/dataforseo_labs/google/available_history`

- **Cost:** free.
- **Result:** `[ { date: "yyyy-mm-01" } ]`. These are the months you can use in Domain Metrics by Categories. It is not used by the keyword endpoints.

### 3.6 ID List (appendix)

Source: https://docs.dataforseo.com/v3/appendix/id_list/

`POST /v3/dataforseo_labs/id_list`

- **Cost:** free. Limit: 10 calls per minute.
- **What it returns.** Task IDs, and optionally the request metadata, for tasks created in a date range.
- **Request fields:**
  - `datetime_from` and `datetime_to`: required. The window can reach back up to 6 months, or up to 1 month when `include_metadata` is set.
  - `limit`: up to 1000.
  - `offset`
  - `sort`: `asc` / `desc`
  - `include_metadata`
- Useful for auditing spend. It does not return keyword data.

---

## 4. Data freshness and Labs vs Keywords Data API

### 4.1 How Labs data is updated

Sources:
- https://dataforseo.com/help-center/dataforseo-labs-api-update-time
- the Keyword Overview, Historical Keyword Data and Keywords For Site pages
- https://docs.dataforseo.com/v3/dataforseo_labs/status/

- **The underlying databases.** Labs reads the in-house Keyword Database and the SERPs Database. The help article (2021) quotes over 3.5 billion keywords and 660 million SERPs. The Top Searches page now says over 7 billion keywords.
- **Keyword metrics** (search volume, CPC, competition) are updated **monthly, following the Google Ads cycle**. "Generally, in the middle of the month, you can get fresh data for the previous month."
- **Google can rewrite past months.** "Sometimes Google tends to rewrite search volume values for a given month, and we update the values." So a stored month value is **not final**.
- **SERP data** (`serp_info`, and the inputs to `avg_backlinks_info` and KD) is refreshed on a cycle that depends on search volume and location:
  - about 30 days for high-volume keywords in popular locations;
  - up to 60 or 90 days for low-volume keywords and less popular locations.
- **Keywords For Site** is updated weekly.
- **Every sub-object carries its own `last_updated_time`.** keyword_info, clickstream, serp_info, avg_backlinks_info, search_intent_info and both normalised objects each have one. They differ in practice: in the examples, intent is often a year older than keyword_info.
- **Status endpoint.** Use it to detect a new Labs update before re-pulling.

### 4.2 Labs vs Keywords Data API (Google Ads)

Sources:
- https://docs.dataforseo.com/v3/keywords_data/google_ads/overview/
- https://docs.dataforseo.com/v3/keywords_data/google_ads/search_volume/live/
- https://dataforseo.com/help-center/sv-update-time
- https://dataforseo.com/help-center/dataforseo-labs-api-vs-google-ads-api
- https://dataforseo.com/help-center/how-to-get-precise-search-volume-for-keywords-with-the-dataforseo-search-volume-endpoint

| Aspect | Labs (Google) | Keywords Data API, Google Ads |
|---|---|---|
| Source | DataForSEO's own Keyword and SERP databases, refreshed monthly from Google Ads. | Google Ads API, called for your request. |
| Methods | Live only, up to about 2 seconds. | Standard (task_post/task_get) or Live. Live is limited to 12 requests per minute per account. |
| Locations | Countries only. | Google Geo Targeting: worldwide, country, region and city, plus `location_coordinate`. |
| Volume semantics | `keyword_info.search_volume` is the Google Ads value. Labs adds `keyword_info_normalized_with_bing` / `_with_clickstream`, which split Google's merged close-variant volume per keyword. | Google merges close variants and misspellings into one volume, so similar keywords get the same number. |
| History | 12 months in `monthly_searches`. Snapshots since Aug 2021 via Historical Keyword Data. | `date_from` / `date_to`, up to 4 years back. |
| Competition | `competition` is a float 0–1 and `competition_level` is LOW/MEDIUM/HIGH. | `competition` is a string (LOW/MEDIUM/HIGH) and `competition_index` is an integer. |
| Extra fields | KD, SERP features, average backlinks, intent, core_keyword/synonym clustering, clickstream demographics. | `spell` (corrected spelling) and `search_partners`. Optional `include_adult_keywords`, `sort_by`. |
| Restrictions | Not stated in docs. | Google Ads policy: no data for weapons, tobacco, drugs and similar categories. |
| Pricing model | Per task + per returned item, so you pay for what you return. | Per request regardless of keyword count (up to 1000 keywords per request). The help center quotes Keywords For Keywords at $0.06 standard / $0.09 live. |
| Update cycle | Monthly. Labs follows Google Ads, around mid-month. | Google updates mid-month; check the Google Ads Status endpoint. |

**Practical consequence.** The same keyword, location and month can carry three different volumes:
- Google Ads `search_volume`;
- `keyword_info_normalized_with_bing.search_volume`;
- `keyword_info_normalized_with_clickstream.search_volume`.

Store them as separate columns with their source. Do not overwrite one with another.

---

## 5. Data grain and identity notes

### 5.1 What identifies a keyword record

- **Natural key: `(keyword, location_code, language_code)`**, with `se_type = google` implied.
  - `keyword` is lowercased by the API and returned decoded.
  - `location_code` is always a country in Labs.
  - `language_code` is ISO 639-1.
- **Default language when omitted.** When `language_*` is omitted (Suggestions, Ideas, Keywords For Site), the API picks the language with the most keywords in that location. Always store the `language_code` echoed in the response, not the request value.
- **Keyword Suggestions without a location.** Keyword Suggestions allows omitting location ("all available locations"). The docs do not say what `location_code` comes back in that case. Avoid that mode for stored data, or treat a null location as its own key.
- **`search_partners`** (Keyword Overview only) changes what the volume means. Today the Labs request has no `search_partners` switch, and the example returns `false`. Store it so the volume is not misread.
- **Category data has a coarser key.** Categories for Keywords is keyed by `(keyword, language_code)` only, with no location. In the list endpoints, `keyword_info.categories` arrives per `(keyword, location, language)`.
- **Search Intent endpoint has the coarsest key.** It is keyed by `keyword` only, with no location or language documented. `search_intent_info` inside keyword_data arrives per `(keyword, location, language)`.

### 5.2 Per-keyword vs per-keyword-per-month

**Per keyword (one row per keyword × location × language), current snapshot:**
- `keyword_info`: `search_volume`, `cpc`, `competition`, `competition_level`, `low_top_of_page_bid`, `high_top_of_page_bid`, `categories[]`, `search_volume_trend{monthly,quarterly,yearly}`, `last_updated_time`
- `keyword_properties`: `core_keyword`, `synonym_clustering_algorithm`, `keyword_difficulty`, `detected_language`, `is_another_language`, `words_count`
- `serp_info`: `serp_item_types[]`, `se_results_count`, `check_url`, `last_updated_time`, `previous_updated_time`
- `avg_backlinks_info`: 7 averages + `last_updated_time`
- `search_intent_info`: `main_intent`, `foreign_intent[]`, `last_updated_time`
- `clickstream_keyword_info`: `search_volume`, `gender_distribution`, `age_distribution`, `last_updated_time`
- the normalised objects: `search_volume`, `is_normalized`, `last_updated_time`

**Per keyword per month (one row per keyword × location × language × year × month):**
- `keyword_info.monthly_searches[]`: Google Ads volume, trailing 12 months.
- `clickstream_keyword_info.monthly_searches[]`: clickstream volume.
- `keyword_info_normalized_with_bing.monthly_searches[]`
- `keyword_info_normalized_with_clickstream.monthly_searches[]`
- **Historical Keyword Data `history[]`.** Each `(year, month)` entry is a full `keyword_info` snapshot (cpc, competition, bids, volume, categories, trend), plus a nested trailing 12-month array. Snapshot-level fields like `cpc` exist **only** at this monthly grain through this endpoint. Elsewhere you only get the current value.
- Monthly volumes are **re-stated by Google**. An upsert on `(keyword, location, language, year, month)` that overwrites the value is the right model. Insert-once is wrong.

### 5.3 Stable vs time-varying fields

- **Effectively stable** (derived from the text; change only if DataForSEO re-processes):
  - `words_count`
  - `detected_language`
  - `is_another_language`
  - `core_keyword` / `synonym_clustering_algorithm` (can change as the database grows)
  - `categories` (no update cadence stated in docs)
- **Changes monthly** (Google Ads cycle): everything in `keyword_info` and the `monthly_searches` series.
- **Changes on the SERP cycle (30–90 days)**: `serp_info`, `avg_backlinks_info`, and probably `keyword_difficulty`. KD is calculated from top-10 link profiles, but the docs do not state its refresh cadence, and KD has no timestamp of its own.
- **Changes rarely** (examples show timestamps 1–2 years old): `search_intent_info`.
- **Clickstream**: has its own `last_updated_time`. The cadence is not stated in the Labs docs.
- **Rule:** keep each sub-object's `last_updated_time` alongside its fields, because one keyword row mixes data of different ages.

### 5.4 Overlap between endpoints (avoid storing twice)

| Data | Returned by |
|---|---|
| Full keyword_data (keyword_info + properties + serp + backlinks + intent + clickstream + normalised) | Keyword Suggestions, Keyword Ideas, Related Keywords (under `keyword_data`), Keywords For Site, Keywords For Categories, Top Searches, Keyword Overview |
| `keyword_info` only, as monthly snapshots | Historical Keyword Data |
| `keyword_difficulty` only | Bulk Keyword Difficulty (same metric as `keyword_properties.keyword_difficulty`) |
| Intent with probabilities | Search Intent. A different shape from `search_intent_info` (labels only). If you store both, keep them in separate columns or tables. |
| `categories` only | Categories for Keywords (keyed without location). The same codes appear in `keyword_info.categories`. |
| Related-search graph edges (`related_keywords[]`, `depth`) | Related Keywords only. These are not keyword metrics; store them as an edge list. |
| Discovery context (`seed_keyword(s)`, `target`, `seed_categories`, `relevance` ordering, `total_count`) | One per list endpoint. This is per-request, not per-keyword. It describes why a keyword was found, not the keyword itself. |

**Design implications drawn from the above:**
1. Keep **one keyword-metrics table** keyed by `(keyword, location_code, language_code)`. Every list endpoint and Keyword Overview fill the same table, so a keyword found by both Suggestions and Ideas is stored once.
2. Keep **one monthly-volume table** keyed by `(keyword, location_code, language_code, year, month)`. Give it separate columns for Google Ads, Bing-normalised, clickstream-normalised and raw clickstream volume. Historical Keyword Data snapshots (cpc, competition, bids per month) can widen the same table or sit beside it.
3. Store **discovery links** (seed or target → keyword, endpoint, depth) separately from metrics.
4. The two `include_*` flags change which objects are null. A null `serp_info` or `clickstream_keyword_info` can mean "not requested" as well as "no data". Record what was requested so a null is not read as "no data".
5. `se_results_count` needs `bigint`. The API returns values around 2×10^10.
