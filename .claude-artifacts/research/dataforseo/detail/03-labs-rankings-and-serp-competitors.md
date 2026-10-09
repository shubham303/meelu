# DataForSEO Labs API (Google): rankings, SERP competitors and historical SERPs

Research date: 2026-10-06. Every statement below comes from the official DataForSEO docs, pricing page or help center pages fetched on that date. Where the docs say nothing, this file says "not stated in docs". Observations taken from the docs' own example responses are marked "(doc example)".

Scope: the Labs Google endpoints that relate keywords to ranking URLs, domains and SERPs. Domain-only metric endpoints are out of scope: `domain_rank_overview` (`POST /v3/dataforseo_labs/google/domain_rank_overview/live`) and `historical_rank_overview` (`POST /v3/dataforseo_labs/google/historical_rank_overview/live`) exist in the same group and return domain-level ranking distributions.

---

## 0. Shared rules for all Labs endpoints

Sources:
- https://docs.dataforseo.com/v3/dataforseo_labs/overview/
- https://docs.dataforseo.com/v3/dataforseo_labs/filters/
- https://docs.dataforseo.com/v3/dataforseo_labs/status/
- https://dataforseo.com/pricing/dataforseo-labs/dataforseo-google-api

### Method and rate limits
- Labs supports **only the Live method**. One POST returns the result. There is no task_post / task_get pair.
- Up to **2000 API calls per minute**. Each Live call can hold **one task** only.
- At most **30 simultaneous requests**.
- Body is JSON (UTF-8). It is an array of task objects, with one object per call.
- Data comes from DataForSEO's **in-house databases**. It is not a live fetch of Google.
- Most of the ranking endpoints say: "data is updated weekly, the latest update time is available in the Status endpoint." This line appears on ranked_keywords, competitors_domain, domain_intersection, page_intersection, relevant_pages and subdomains. It does not appear on serp_competitors, historical_serps, bulk_traffic_estimation or historical_bulk_traffic_estimation (for those: not stated in docs).

### Status endpoint (free)
`GET https://api.dataforseo.com/v3/dataforseo_labs/status`. The result has `google.date_update`, `bing.date_update` and `amazon.date_update` (format `yyyy-mm-dd`). This is the last date the Labs Google database was refreshed. You can use it as the "as of" date for any snapshot you store.

### Envelope (same on every endpoint)
Top level: `version`, `status_code`, `status_message`, `time`, `cost` (USD float), `tasks_count`, `tasks_error`, `tasks[]`.
Each task: `id` (UUID), `status_code` (10000–60000), `status_message`, `time`, `cost`, `result_count`, `path`, `data` (echo of the request, including `tag`), `result[]`.

### Common request fields
- `location_name` / `location_code`, `language_name` / `language_code`. The list comes from `https://api.dataforseo.com/v3/dataforseo_labs/locations_and_languages`. Some endpoints make these fields required. Others make them optional, and if you leave them out you get "all available locations/languages". Each endpoint section says which.
- `tag` (string, ≤255 chars). It is echoed back in `data`.

### filters syntax
- Up to **8 filters** per request. You join conditions with `"and"` / `"or"` and can nest them.
- Basic shape: `[field_path, operator, value]`, for example `["keyword_data.keyword_info.search_volume", ">=", 50]`.
- Field paths are dot paths into the result item, for example `ranked_serp_element.serp_item.rank_group`, `metrics.organic.pos_1`, `intersection_result.1.rank_absolute`.
- Operators by field type:
  - bool: `=`, `<>`
  - num: `<`, `<=`, `>`, `>=`, `=`, `<>`, `in`, `not_in`
  - str: `match`, `not_match`, `like`, `not_like`, `ilike`, `not_ilike`, `in`, `not_in`, `=`, `<>`, `regex`, `not_regex`
  - array.str / array.num: `has`, `has_not`
  - time: `<`, `>`. Time format is `"yyyy-mm-dd hh-mm-ss +00:00"`.
- `in` / `not_in` take an array value, for example `["keyword_info.search_volume","in",[10,1000]]`.
- `regex` / `not_regex` use RE2 syntax, with at most 1000 characters.
- `like` / `ilike` need `%` wildcards.
- `match` / `not_match` are full-text word matches.
- Field-to-field comparison: Page Intersection, Ranked Keywords, Subdomains, Relevant Pages, Competitors Domain, Categories For Domain and Domain Intersection also accept `["metrics.organic.pos_1", ">", "$item->metrics.organic.pos_2_3"]`. Both sides must have the same type.
- The full list of filterable fields comes from `GET https://api.dataforseo.com/v3/dataforseo_labs/available_filters`, which is free.

### order_by syntax
- An array of `"field,asc|desc"` strings, with **at most 3 rules**, for example `["keyword_data.keyword_info.search_volume,desc","keyword_data.keyword_info.cpc,desc"]`.
- Fields of type `array.str` / `array.num` cannot be used in `order_by`.

### item_types behaviour (endpoints that take it)
- Default is `["organic","paid"]`.
- If `item_types` has any type other than `organic`, results are **ordered by the first type in the array**. You also **cannot sort or filter by item types you did not request**.

### Pricing (Labs Google, from the pricing page)

| Endpoint group | Price per task | Price per item |
|---|---|---|
| "All other endpoints" (ranked_keywords, serp_competitors, competitors_domain, domain_intersection, page_intersection, relevant_pages, subdomains, bulk_traffic_estimation) | $0.012 | $0.00012 |
| Historical SERPs | none listed | **$0.00012 per SERP**. One item is one monthly snapshot. |
| Historical Bulk Traffic Estimation (and Domain Metrics by Categories) | $0.12 | $0.0012 per domain |
| Historical Rank (historical_rank_overview) | $0.12 | $0.0012 per item (one item is one month) |

- `include_clickstream_data: true` **doubles** the cost of the request.
- The pricing page's own worked examples are not consistent with its table. For example, the Historical Bulk Traffic note says "$0.1 per task, $0.001 per domain" but then calculates with $0.12 / $0.0012. Cost figures in older doc examples are also lower: a ranked_keywords example shows `cost: 0.011`, a help-center example shows `0.0102` for 2 items, and a historical_serps example shows `0.0005`. Use the `cost` field in each response as the source of truth.
- "All other endpoints" are limited to **1000 items per response**. Getting 1M rows takes 1000 requests.

---

## 1. Ranked Keywords

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live/

`POST https://api.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live`

Purpose: the keywords that a domain, subdomain or single page ranks for. For each keyword you get keyword metrics plus the target's SERP element (the ranking URL, its position and more). Data is updated weekly.

### Request

| Field | Type | Required | Default / limits | Notes |
|---|---|---|---|---|
| `target` | string | yes | — | Domain without `https://` or `www.`. Subdomain without `https://`. **Page URL must include `https://` or `www.`**. If you send a page URL without either, you get results for the whole domain. |
| `location_name` / `location_code` | string / int | no | — | Leave both out to get results for **all available locations**. |
| `language_name` / `language_code` | string / string | no | — | Leave both out to get results for all languages. |
| `ignore_synonyms` | bool | no | `false` | If `true`, only core keywords are returned and "highly similar keywords" are excluded. |
| `item_types` | array | no | `["organic","paid"]` | Allowed: `organic`, `paid`, `featured_snippet`, `local_pack`, `ai_overview_reference`. The ordering and filtering rule from section 0 applies. |
| `include_clickstream_data` | bool | no | `false` | Adds `clickstream_keyword_info`, `clickstream_etv`, gender/age distributions, `keyword_info_normalized_with_clickstream` and `keyword_info_normalized_with_bing`. Doubles the price. |
| `limit` | int | no | 100, max **1000** | Number of keywords returned. |
| `offset` | int | no | 0 | Offset into the result list. |
| `load_rank_absolute` | bool | no | `false` | If `true`, the response also has `metrics_absolute`: the distribution by `rank_absolute` instead of `rank_group`. |
| `historical_serp_mode` | string | no | `live` | `live`: keywords where the target ranks now. `lost`: keywords where the target ranked before but not at the last check. `all`: both. |
| `filters` | array | no | max 8 | Operators: `regex, not_regex, <, <=, >, >=, =, <>, in, not_in, match, not_match, ilike, not_ilike, like, not_like`. For one page's keywords, set `target` to the page URL or filter `["ranked_serp_element.serp_item.relative_url","=","/apis/rank-tracker-api"]`. |
| `order_by` | array | no | default `["ranked_serp_element.serp_item.rank_group,asc"]`, max 3 rules | |
| `tag` | string | no | ≤255 | |

There is no `date_from` / `date_to` parameter. The endpoint returns the current database state only.

### Response: result[] (one object per task)

| Field | Type | Meaning |
|---|---|---|
| `se_type` | string | Search engine type ("google"). |
| `target` | string | The target from the request. |
| `location_code`, `language_code` | int / string | From the request. `null` if none was given. |
| `total_count` | int | Total matching keywords in the database. Use it for paging. |
| `items_count` | int | Number of items in this response. |
| `metrics` | object | Ranking distribution of the target by **`rank_group`**, one sub-object per item type. |
| `metrics_absolute` | object | Same distribution by **`rank_absolute`**. Only present when `load_rank_absolute=true`. |
| `items` | array | One entry per ranked keyword (see below). |

#### metrics / metrics_absolute sub-objects
Keys: `organic`, `paid`, `featured_snippet`, `local_pack`, `ai_overview_reference`. A type you did not request comes back as `null` (doc example: with `item_types:["ai_overview_reference"]`, `organic`, `paid`, `featured_snippet` and `local_pack` are `null`).

Fields in each sub-object (per docs listing):

| Field | Type | Meaning |
|---|---|---|
| `pos_1`, `pos_2_3`, `pos_4_10`, `pos_11_20`, `pos_21_30`, `pos_31_40`, `pos_41_50`, `pos_51_60`, `pos_61_70`, `pos_71_80`, `pos_81_90`, `pos_91_100` | int | Number of SERPs where the target ranks in that bucket. |
| `etv` | float | Estimated monthly traffic: CTR × search volume, summed over all keywords. |
| `count` | int | Total SERPs of that type that contain the target. |
| `estimated_paid_traffic_cost` | float | Organic: etv × CPC, the cost of buying that traffic. Paid: cost of the paid traffic. |
| `is_new` | int | Number of newly found ranked elements. |
| `is_up` | int | Number of ranked elements that moved up. |
| `is_down` | int | Number of ranked elements that moved down. |
| `is_lost` | int | Number of elements present before but not found at the last check. |
| `clickstream_etv` | int | Only with `include_clickstream_data`. |
| `clickstream_gender_distribution` {`female`,`male`} | object | Only with clickstream. |
| `clickstream_age_distribution` {`18-24`,`25-34`,`35-44`,`45-54`,`55-64`} | object | Only with clickstream. |

Doc quirks, reported exactly as the docs show them:
- In `metrics.local_pack` the docs do not list `is_lost`. The `metrics_absolute.local_pack` listing does include it.
- In `metrics_absolute`, the docs list no `etv`, `count` or `estimated_paid_traffic_cost` for `organic` and `paid`. They do list them for `featured_snippet`, `local_pack` and `ai_overview_reference`.
- `ai_overview_reference.count` is described as "total count of featured snippet items that contain the target". This looks like a copy-paste error in the docs.

#### items[] (one ranked keyword)

```
items[i]
├── se_type
├── keyword_data            (keyword-level data, embedded)
└── ranked_serp_element     (the target's SERP element for this keyword)
```

**keyword_data** (embedded keyword record):
- `se_type`, `keyword`, `location_code`, `language_code`
- `keyword_info`: `se_type`, `last_updated_time`, `competition` (0–1), `competition_level` (LOW/MEDIUM/HIGH/null), `cpc` (USD), `search_volume`, `low_top_of_page_bid`, `high_top_of_page_bid`, `categories[]`, `monthly_searches[] {year, month, search_volume}`, `search_volume_trend {monthly, quarterly, yearly}` (percent change)
- `keyword_info_normalized_with_bing`, `keyword_info_normalized_with_clickstream`: `last_updated_time`, `search_volume`, `is_normalized`, `monthly_searches`. Clickstream only.
- `clickstream_keyword_info`: `search_volume`, `last_updated_time`, `gender_distribution`, `age_distribution`, `monthly_searches[]`. Clickstream only.
- `keyword_properties`: `se_type`, `core_keyword`, `synonym_clustering_algorithm`, `keyword_difficulty` (0–100), `detected_language`, `is_another_language`
- `serp_info`: `se_type`, `check_url`, `serp_item_types[]`, `se_results_count`, `last_updated_time`, `previous_updated_time`
- `avg_backlinks_info`: `se_type`, `backlinks`, `dofollow`, `referring_pages`, `referring_domains`, `referring_main_domains`, `rank`, `main_domain_rank`, `last_updated_time` (averages over the SERP's ranking pages)
- `search_intent_info`: `se_type`, `main_intent`, `foreign_intent[]`, `last_updated_time`

**ranked_serp_element**:

| Field | Type | Meaning |
|---|---|---|
| `se_type` | string | |
| `serp_item` | object | The target's element. Its shape depends on `type` (see below). |
| `check_url` | string | Direct Google URL for the SERP. In doc examples it contains `num=100`. |
| `serp_item_types` | array | All element types seen in the SERP: answer_box, app, carousel, multi_carousel, featured_snippet, google_flights, google_reviews, third_party_reviews, google_posts, images, jobs, knowledge_graph, local_pack, hotels_pack, map, organic, paid, people_also_ask, related_searches, people_also_search, shopping, top_stories, twitter, video, events, mention_carousel, recipes, top_sights, scholarly_articles, popular_products, podcasts, questions_and_answers, find_results_on, stocks_box, visual_stories, commercial_units, local_services, google_hotels, math_solver, currency_box, product_considerations, found_on_web, short_videos, refine_products, explore_brands, perspectives, discussions_and_forums, compare_sites, courses, ai_overview. **Results are returned only for organic, paid, featured_snippet, local_pack and ai_overview_reference.** |
| `se_results_count` | string | Number of Google results. |
| `keyword_difficulty` | int | 0–100. |
| `is_lost` | bool | The result no longer appears in the SERP. Relevant with `historical_serp_mode` `lost`/`all`. |
| `last_updated_time` | string | When the SERP was last checked (`yyyy-mm-dd hh-mm-ss +00:00`). |
| `previous_updated_time` | string | The check before that. `rank_changes` compares against this check. |

**serp_item when `type = "organic"`**:
`se_type`, `type`, `rank_group` (position among elements of the same type), `rank_absolute` (position among all SERP elements), `position` (`left`/`right`), `xpath`, `domain` (the subdomain as shown in the SERP), `title`, `url`, `breadcrumb`, `website_name`, `is_image`, `is_video`, `is_featured_snippet`, `is_malicious` (these four are flagged in the docs as "this check no longer appears in SERP"), `checks[]` (properties that are true: `is_image`, `is_video`, `is_featured_snippet`, `amp_version`, `is_malicious`, `is_web_story`, `is_highly_cited`; `null` if none), `description`, `pre_snippet`, `extended_snippet`, `amp_version`, `rating {rating_type (Max5/Percents/CustomMax), value, votes_count, rating_max}`, `highlighted[]`, `links[] {type='link_element', title, description, url}` (sitelinks), `about_this_result {type, url, source, source_info, source_url, language, location, search_terms[], related_terms[]}`, `main_domain`, `relative_url` (path without scheme and host), `etv` (CTR × this keyword's volume), `estimated_paid_traffic_cost` (etv × CPC), `clickstream_etv`, `rank_changes {previous_rank_absolute (null if new), is_new, is_up, is_down}`, `backlinks_info {referring_domains, referring_main_domains, referring_pages, dofollow, backlinks, time_update}` (for the ranking page URL), `rank_info {page_rank, main_domain_rank}`.

**serp_item when `type = "paid"`**:
`type`, `rank_group`, `rank_absolute`, `position`, `xpath`, `title`, `domain`, `description`, `breadcrumb`, `url`, `highlighted[]`, `extra {ad_aclk}`, `description_rows[]`, `links[] {type='ad_link_element', title, description, url, ad_aclk}`, `main_domain`, `relative_url`, `etv`, `estimated_paid_traffic_cost`, `rank_changes{…}`, `backlinks_info{…}`, `rank_info{…}`, `clickstream_etv`.

**serp_item when `type = "local_pack"`**:
`type`, `rank_group`, `rank_absolute`, `position`, `xpath`, `title`, `description`, `domain`, `phone`, `url`, `is_paid`, `rating{…}`, `main_domain`, `relative_url`, `etv`, `estimated_paid_traffic_cost`, `rank_changes{…}`, `backlinks_info{…}`, `rank_info{…}`, `clickstream_etv`.

**serp_item when `type = "featured_snippet"`**:
`type`, `rank_group`, `rank_absolute`, `position`, `xpath`, `domain`, `title`, `featured_title` (title of the source page), `description`, `url`, `table {table_header[], table_content[]}` (null if none), `main_domain`, `relative_url`, `etv`, `estimated_paid_traffic_cost`, `rank_changes{…}`, `backlinks_info{…}`, `rank_info{…}`.

**serp_item when `type = "ai_overview_reference"`**: see section 11.

### Limits and pricing
- `limit` max 1000 per call. Use `offset` to page past that, with `total_count` as the total.
- Price: $0.012 per task + $0.00012 per returned item. Clickstream doubles it.

### Behaviour that is not stated in docs
- Whether a domain target with two ranking URLs for the same keyword yields one item or two: not stated in docs. In the doc example with mixed `item_types`, each keyword appears once with one `serp_item` (some keywords `organic`, one `ai_overview_reference`). This is not stated as a rule.
- Device (desktop/mobile): not stated in docs. There is no device parameter.
- SERP depth: the bucket fields go up to `pos_91_100`, and the doc example `check_url` contains `num=100`. A crawl depth is not stated explicitly.

---

## 2. SERP Competitors

Sources:
- https://docs.dataforseo.com/v3/dataforseo_labs/google/serp_competitors/live/
- https://dataforseo.com/help-center/rating-and-visibility-of-serp-competitors-endpoint

`POST https://api.dataforseo.com/v3/dataforseo_labs/google/serp_competitors/live`

Purpose: domains that rank for a set of keywords you give, with positions, rating, ETV and visibility for those keywords. Data update frequency: not stated on this page.

### Request

| Field | Type | Required | Default / limits | Notes |
|---|---|---|---|---|
| `keywords` | array | yes | max **200** | Converted to lowercase. |
| `location_name` / `location_code` | | **yes** (one of them) | | |
| `language_name` / `language_code` | | **yes** (one of them) | | |
| `include_subdomains` | bool | no | `true` | If `false`, subdomains are ignored. |
| `item_types` | array | no | `["organic","paid"]` | Allowed: `organic`, `paid`, `featured_snippet`, `local_pack`. **No `ai_overview_reference` here.** |
| `limit` | int | no | 100, max 1000 | Number of domains. |
| `offset` | int | no | 0 | |
| `filters` | array | no | max 8 | For example `[["median_position","in",[1,10]],"and",["domain","not_like","%wikipedia.org%"]]`. |
| `order_by` | array | no | default `["rating,desc"]`, max 3 | |
| `tag` | string | no | | |

There is no `ignore_synonyms`, `historical_serp_mode` or date range.

### Response
`result[]`: `se_type`, `seed_keywords[]`, `location_code`, `language_code`, `total_count`, `items_count`, `items[]`.

`items[]` (one row per competing domain):

| Field | Type | Meaning |
|---|---|---|
| `se_type` | string | |
| `domain` | string | Competitor domain. In the doc example these are hosts such as `play.google.com` and `www.phone.com`. |
| `avg_position` | int | Mean of the values in `keywords_positions`. |
| `median_position` | int | Median of the values in `keywords_positions`. |
| `rating` | int | `sum(100 - position)` over the given keywords. |
| `etv` | float | Σ(search volume × CTR at position) over the given keywords. |
| `keywords_count` | int | How many of the given keywords the domain ranks for. |
| `visibility` | float | Positions 1–10 map to 1.0 down to 0.1. Positions 11–20 score 0.05. Positions 20–100 score 0. The values are summed. |
| `relevant_serp_items` | int | Number of SERP elements relevant to the domain. |
| `keywords_positions` | object | Keyword → array of positions. Doc example: `{"phone": [1]}`. A keyword holds an array because a domain can hold more than one position. |

There is no per-URL output. This endpoint is at domain grain only.

Pricing: $0.012/task + $0.00012/item.

---

## 3. Competitors Domain

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/competitors_domain/live/

`POST https://api.dataforseo.com/v3/dataforseo_labs/google/competitors_domain/live`

Purpose: competitor domains of a target, with full-domain metrics and metrics restricted to the keywords both domains share. Data is updated weekly.

### Request

| Field | Type | Required | Default / limits | Notes |
|---|---|---|---|---|
| `target` | string | yes | | Domain without `https://`/`www.`. A page URL is accepted, but results are for its domain. |
| location / language | | **yes** | | |
| `item_types` | array | no | `["organic","paid"]` | Allowed: `organic`, `paid`, `featured_snippet`, `local_pack`. |
| `include_clickstream_data` | bool | no | false | Doubles the price. |
| `filters` | array | no | max 8 | Operators: `regex, not_regex, <, <=, >, >=, =, <>, in, not_in`. |
| `order_by` | array | no | default `["metrics.organic.count,desc"]`, max 3 | |
| `limit` | int | no | 100, max 1000 | |
| `offset` | int | no | 0 | |
| `max_rank_group` | int | no | 100 | Only SERP results up to this `rank_group` count. For example, 10 means top 10 only. |
| `exclude_top_domains` | bool | no | false | Excludes wikipedia.org, pinterest.com, amazon.com, google.com, facebook.com, wordpress.com, medium.com, quora.com, reddit.com, youtube.com, ebay.com, uol.com.br, instagram.com, olx.com, twitter.com, linkedin.com and slideshare.net. |
| `exclude_domains` | array | no | up to 1000 | |
| `intersecting_domains` | array | no | up to 20 | Metrics are then based on SERPs where the target **and** these domains appear. |
| `ignore_synonyms` | bool | no | false | |
| `tag` | string | no | | |

### Response
`result[]`: `se_type`, `target`, `location_code`, `language_code`, `total_count`, `items_count`, `items[]`.

`items[]`:
- `se_type`, `domain`
- `avg_position` (float): average position, calculated **on intersecting keywords only**. It changes depending on which target it is paired with.
- `sum_position` (int)
- `intersections` (int): number of shared keywords
- `full_domain_metrics`: all keywords of that domain. Sub-objects `organic`, `paid`, `local_pack`, `featured_snippet`, each with `pos_1` … `pos_91_100`, `etv`, `count`, `estimated_paid_traffic_cost`, `is_new`, `is_up`, `is_down`, `is_lost` and the clickstream fields.
- `metrics`: same shape. These are the **target's** metrics on the keywords it shares with this competitor.
- `competitor_metrics`: same shape. These are the **competitor's** metrics on the shared keywords.

There is no ai_overview_reference sub-object here.

Pricing: $0.012/task + $0.00012/item.

---

## 4. Domain Intersection

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/domain_intersection/live/

`POST https://api.dataforseo.com/v3/dataforseo_labs/google/domain_intersection/live`

Purpose: keywords where two domains both rank in the same SERP, or with `intersections:false`, where target1 ranks and target2 does not. Each item carries both domains' SERP elements. Data is updated weekly.

### Request

| Field | Type | Required | Default / limits | Notes |
|---|---|---|---|---|
| `target1`, `target2` | string | yes | | Domains without `https://`/`www.`. |
| location / language | | **yes** | | |
| `intersections` | bool | no | `true` | `true`: both rank in the same SERP. `false`: target1 ranks and target2 does not; only target1's element is returned. No results if intersecting keywords exceed **10 million**. |
| `item_types` | array | no | `["organic","paid"]` | Allowed: `organic`, `paid`, `featured_snippet`, `local_pack`. |
| `include_serp_info` | bool | no | false | Adds `serp_info` per keyword. |
| `include_clickstream_data` | bool | no | false | Doubles the price. |
| `limit` | int | no | 100, max 1000 | |
| `offset` | int | no | 0 | |
| `filters` | array | no | max 8 | Full operator set including `match`/`like`. Fields such as `first_domain_serp_element.etv` and `second_domain_serp_element.type`. |
| `order_by` | array | no | default `["keyword_data.keyword_info.search_volume,desc"]`, max 3 | |
| `tag` | string | no | | |

`ignore_synonyms` and `historical_serp_mode` are not documented for this endpoint.

### Response
`result[]`: `se_type`, `target1`, `target2`, `location_code`, `language_code`, `total_count`, `items_count`, `items[]`.

`items[]`:
- `se_type`
- `keyword_data`: same embedded keyword record as Ranked Keywords. `serp_info` here notes that actual results are returned only for organic, paid, featured_snippet and local_pack.
- `first_domain_serp_element`: target1's element.
- `second_domain_serp_element`: target2's element. It has the same per-type shapes as the Ranked Keywords `serp_item` for organic, paid, local_pack and featured_snippet, including `rank_group`, `rank_absolute`, `url`, `relative_url`, `main_domain`, `etv`, `estimated_paid_traffic_cost`, `clickstream_etv`, `rank_changes`, `backlinks_info` and `rank_info`.

Doc quirks: the docs list `rank_changes` and `rating` as "array" type here, but as "object" in Ranked Keywords.

Pricing: $0.012/task + $0.00012/item.

---

## 5. Page Intersection

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/page_intersection/live/

`POST https://api.dataforseo.com/v3/dataforseo_labs/google/page_intersection/live`

Purpose: keywords where a set of pages (URLs or URL patterns) rank together. With `exclude_pages`, you get keywords that some pages rank for and other pages do not. Data is updated weekly.

### Request

| Field | Type | Required | Default / limits | Notes |
|---|---|---|---|---|
| `pages` | object | yes | up to **20** | Keys `"1"`..`"20"` → absolute URL with `http(s)://`. A trailing `*` after `/` is a prefix wildcard (`https://example.com/eng/*`). A wildcard directly after the host is not allowed. No results if intersecting keywords exceed 10 million. |
| `exclude_pages` | array | no | up to **10** | Wildcards are allowed. Keywords where `pages` rank but these do not. |
| location / language | | **yes** | | |
| `item_types` | array | no | `["organic","paid"]` | Allowed: `organic`, `paid`, `featured_snippet`, `local_pack`. |
| `limit` | int | no | 100, max 1000 | |
| `offset` | int | no | 0 | |
| `include_subdomains` | bool | no | true | |
| `intersection_mode` | string | no | `intersect` if only `pages` is given; `union` if `exclude_pages` is given | `union`: any page ranks. `intersect`: all pages rank in the same SERP. |
| `include_serp_info` | bool | no | false | |
| `include_clickstream_data` | bool | no | false | Doubles the price. |
| `ignore_synonyms` | bool | no | false | |
| `filters` | array | no | max 8 | To filter on one page's element, use its index: `["intersection_result.1.rank_absolute","=",1]`, `["intersection_result.3.type","=","organic"]`. |
| `order_by` | array | no | default `["keyword_data.keyword_info.search_volume,desc"]`, max 3 | For example `["intersection_result.1.rank_group,asc"]`. |
| `tag` | string | no | | |

### Response
`result[]`: `se_type`, `pages` (echo), `exclude_pages`, `location_code`, `language_code`, `total_count`, `items_count`, `items[]`.

`items[]`:
- `se_type`
- `keyword_data`: embedded keyword record, as above.
- `intersection_result`: an object with keys `"1"`..`"20"` matching the `pages` keys. Each value is that page's SERP element: `organic`, `paid`, `featured_snippet` or `local_pack`, with the same fields as the Ranked Keywords `serp_item` (`type`, `rank_group`, `rank_absolute`, `position`, `xpath`, `domain`, `title`, `url`, `relative_url`, `main_domain`, `etv`, `estimated_paid_traffic_cost`, `clickstream_etv`, `rank_changes`, `backlinks_info`, `rank_info`, …).

Pricing: $0.012/task + $0.00012/item.

---

## 6. Relevant Pages

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/relevant_pages/live/

`POST https://api.dataforseo.com/v3/dataforseo_labs/google/relevant_pages/live`

Purpose: the pages of a domain, each with its ranking distribution and ETV. It is the page-level rollup of Ranked Keywords. Data is updated weekly.

### Request

| Field | Type | Required | Default / limits | Notes |
|---|---|---|---|---|
| `target` | string | yes | | Domain without `https://`/`www.`. |
| location / language | | no | | Leave out to get all locations/languages. |
| `item_types` | array | no | `["organic","paid"]` | Allowed: `organic`, `paid`, `featured_snippet`, `local_pack`. |
| `include_clickstream_data` | bool | no | false | |
| `limit` | int | no | 100, max 1000 | Number of pages. |
| `offset` | int | no | 0 | |
| `historical_serp_mode` | string | no | `live` | `live`, `lost` or `all`. These apply to the SERPs counted in the metrics. |
| `ignore_synonyms` | bool | no | false | |
| `filters` | array | no | max 8 | Operators `regex, not_regex, <, <=, >, >=, =, <>, in, not_in`. |
| `order_by` | array | no | default `["metrics.organic.count,desc"]`, max 3 | |
| `tag` | string | no | | |

There is no `load_rank_absolute` parameter.

### Response
`result[]`: `se_type`, `target`, `location_code`, `language_code`, `total_count`, `items_count`, `items[]`.

`items[]`: `se_type`, `page_address` (absolute URL), and `metrics` with sub-objects `organic`, `paid`, `featured_snippet`, `local_pack`. Each has `pos_1`…`pos_91_100`, `etv`, `count`, `estimated_paid_traffic_cost`, `is_new`, `is_up`, `is_down`, `is_lost` and the clickstream fields.

Pricing: $0.012/task + $0.00012/item.

---

## 7. Historical SERPs

Sources:
- https://docs.dataforseo.com/v3/dataforseo_labs/google/historical_serps/live/
- Pricing: https://dataforseo.com/pricing/dataforseo-labs/dataforseo-google-api

`POST https://api.dataforseo.com/v3/dataforseo_labs/google/historical_serps/live`

Purpose: full Google SERPs for one keyword over a past time range, including all SERP features. "Historical data is available for 12 months."

### Request

| Field | Type | Required | Default / limits | Notes |
|---|---|---|---|---|
| `keyword` | string | yes | ≤700 chars | `%##` is decoded. Use `%25` for a literal `%` and `%2B` for `+`. |
| `date_from` | string `yyyy-mm-dd` | no | Leave out to get all SERPs from the last 365 days. | Earliest value: 365 days before now. |
| `date_to` | string `yyyy-mm-dd` | no | today | |
| location / language | | **yes** | | |
| `tag` | string | no | | |

There are **no** `limit`, `offset`, `filters`, `order_by`, `item_types`, `depth` or device parameters.

### Response
`result[]`: "the array includes objects with SERPs for each month within the specified time frame".
- `se_type`, `keyword`, `location_code`, `language_code`, `total_count`, `items_count`
- `items[]`: **one entry per SERP snapshot**. The pricing page calls each one "a monthly snapshot of search results". (Doc example: 2 snapshots with `datetime` `2021-08-01 08:05:11 +00:00` and `2021-10-01 03:37:47 +00:00`. The month in between is absent, so not every month is guaranteed to have a snapshot.)
  - `se_type`, `keyword`, `type`, `se_domain`, `location_code`, `language_code`
  - `check_url` (doc example contains `num=100`)
  - `datetime`: when the SERP was collected (`yyyy-mm-dd hh-mm-ss +00:00`)
  - `spell {keyword, type: did_you_mean | showing_results_for | no_results_found_for}`
  - `item_types[]`: types present in this SERP
  - `se_results_count`, `items_count`
  - `items[]`: **every SERP element in the snapshot** (doc example: snapshots with 96 and 106 elements, max `rank_absolute` 69 in that example).

#### SERP element types documented in Historical SERPs, with their top-level fields
- **organic**: se_type, type, rank_group, rank_absolute, position, xpath, domain, title, url, breadcrumb, is_image, is_video, is_featured_snippet, is_malicious, checks, description, pre_snippet, extended_snippet, amp_version, rating, highlighted, links, about_this_result, main_domain, relative_url, etv, estimated_paid_traffic_cost, rank_changes, backlinks_info, rank_info
- **paid**: se_type, type, rank_group, rank_absolute, position, xpath, title, domain, description, breadcrumb, url, highlighted, extra, description_rows, links, main_domain, relative_url, etv, estimated_paid_traffic_cost, rank_changes
- **local_pack**: se_type, type, rank_group, rank_absolute, position, xpath, title, description, domain, phone, url, is_paid, rating, main_domain, relative_url, etv, estimated_paid_traffic_cost, rank_changes
- **featured_snippet**: se_type, type, rank_group, rank_absolute, position, xpath, domain, title, featured_title, description, url, table, main_domain, relative_url, etv, estimated_paid_traffic_cost, rank_changes
- **ai_overview**: type, rank_group, rank_absolute, page, position, xpath, asynchronous_ai_overview, markdown, items, references, rectangle. See section 11 for the nested structure.
- Other feature blocks. These have position fields (`type, rank_group, rank_absolute, position, xpath`) plus a nested `items[]` or type-specific fields, but **no etv or rank_changes**: carousel, multi_carousel, answer_box (text, links), related_searches, people_also_search, hotels_pack (date_from, date_to), knowledge_graph (title, sub_title, description, card_id, url, image_url, logo_url, cid, items), top_stories, twitter, map, google_flights, google_reviews (reviews_count, rating, place_id, feature, cid), google_posts, video, people_also_ask, images, shopping, jobs, events, mention_carousel, recipes, top_sights, scholarly_articles, popular_products, podcasts, questions_and_answers, find_results_on, stocks_box, visual_stories, commercial_units, local_services, google_hotels (no rank_absolute listed), math_solver.

`rank_changes` in Historical SERPs: "ranking changes of the SERP element compared to the preceding month. Note: the changes are calculated even if the preceding month is not included in a POST request". Fields: `previous_rank_absolute` (null if new), `is_new`, `is_up`, `is_down`.

In Historical SERPs the docs list `backlinks_info` and `rank_info` **only on organic**. They are not listed on paid, local_pack or featured_snippet.

### Pricing
$0.00012 **per SERP** (per monthly snapshot returned). No per-task fee is listed. Pricing page example: 1000 keywords × 10 months = $1.20.

---

## 8. Subdomains (brief)

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/subdomains/live/

`POST https://api.dataforseo.com/v3/dataforseo_labs/google/subdomains/live`. Data is updated weekly.
- Request: `target` (domain without `https://`/`www.`, required); location/language optional (leave out for all); `item_types` (`organic`, `paid`, `featured_snippet`, `local_pack`; default organic+paid); `include_clickstream_data`; `historical_serp_mode` (`live` default / `lost` / `all`); `ignore_synonyms`; `filters` (max 8); `order_by` (default `["metrics.organic.count,desc"]`); `limit` (100, max 1000); `offset`; `tag`.
- Response `items[]`: `se_type`, `subdomain`, `metrics.{organic, paid, featured_snippet, local_pack}` with `pos_*` buckets, `etv`, `count`, `estimated_paid_traffic_cost`, `is_new`, `is_up`, `is_down`, `is_lost` and the clickstream fields.
- Pricing: $0.012/task + $0.00012/item.

## 9. Bulk Traffic Estimation (brief)

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/bulk_traffic_estimation/live/

`POST https://api.dataforseo.com/v3/dataforseo_labs/google/bulk_traffic_estimation/live`
- Request: `targets[]` (up to **1000** domains, subdomains or pages; pages with `https://`); location/language optional (leave out for all); `item_types` (`organic`, `paid`, `featured_snippet`, `local_pack`); `ignore_synonyms`; `tag`. There are no filters, limit or offset.
- Response `items[]`: `se_type`, `target`, `metrics.{organic, paid, featured_snippet, local_pack}`, each with only `etv` and `count`.
- Pricing: $0.012/task + $0.00012/item.

## 10. Historical Bulk Traffic Estimation (brief)

Source: https://docs.dataforseo.com/v3/dataforseo_labs/google/historical_bulk_traffic_estimation/live/

`POST https://api.dataforseo.com/v3/dataforseo_labs/google/historical_bulk_traffic_estimation/live`
- Request: `targets[]` (up to 1000 domains or subdomains; **pages are not listed**); location/language optional; `date_from` (`yyyy-mm-dd`, minimum `2020-10-01`, default is the previous 12 months); `date_to` (default today); `ignore_synonyms`; `item_types` (`organic`, `paid`, `featured_snippet`, `local_pack`); `tag`.
- Response `items[]`: `se_type`, `target`, `metrics.{organic, paid, featured_snippet, local_pack}`. Each is an **array** of `{year, month, etv, count}`.
- Pricing: $0.12/task + $0.0012 per domain.

---

## 11. How `ai_overview_reference` appears in Labs

Sources:
- https://docs.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live/
- https://dataforseo.com/update/aio-references-in-ranked-keywords-api (24 June 2025)
- https://dataforseo.com/help-center/how-to-get-keywords-that-a-website-ranks-for-in-google-ai-overview
- https://dataforseo.com/help-center/how-to-pull-ranked-keywords-from-ai-overviews
- https://docs.dataforseo.com/v3/dataforseo_labs/google/historical_serps/live/

### Where it is supported
- **Ranked Keywords is the only endpoint in this set where `ai_overview_reference` is an allowed `item_types` value and a `metrics` key.** serp_competitors, competitors_domain, domain_intersection, page_intersection, relevant_pages, subdomains and the two bulk traffic endpoints list only `organic`, `paid`, `featured_snippet` and `local_pack`.
- Historical SERPs does not "rank" anything. It returns the raw `ai_overview` block, with `ai_overview_reference` objects nested inside it.

### Ranked Keywords: how to request it
- It is **not in the default** `item_types` (`["organic","paid"]`). You must request it explicitly: `"item_types": ["ai_overview_reference"]`, alone or with other types. The help center says an unset `item_types` "gives you zero AI Overview data even when citations exist".
- The June 2025 update note says `"item_types": ["ai_overview"]`. The endpoint doc and both help-center articles use `"ai_overview_reference"`. The doc's list of allowed values contains only `ai_overview_reference`.
- If `ai_overview_reference` is first in `item_types`, results are ordered by it, and you can only sort or filter by the types you requested.
- Meaning, from the help center: the target page "was used as source material" (cited) in the AI Overview for that keyword. "A page can get cited in an AI Overview for a query where its organic rank is mediocre, and it can hold a strong organic rank without ever getting cited." The two signals are separate.

### The ranked `serp_item` for `type = "ai_overview_reference"` (fields per docs)

| Field | Type | Meaning |
|---|---|---|
| `se_type` | string | |
| `type` | string | `"ai_overview_reference"` |
| `rank_group` | int | Position among elements of the same type. For this type it is the order among AI Overview references. The help center calls it "its position within the overview". |
| `rank_absolute` | int | Position among all SERP elements. Doc example: `rank_group 1`, `rank_absolute 3`. |
| `position` | string | `left` / `right` |
| `source` | string | Reference source name or title (for example "Medium") |
| `domain` | string | Domain of the reference |
| `title` | string | Reference page title |
| `url` | string | Cited page URL |
| `text` | string | Snippet from the page that was used to generate the AI Overview element |
| `main_domain` | string | |
| `relative_url` | string | |
| `etv` | float | Estimated traffic. Doc text: CTR × search volume of the keyword. |
| `estimated_paid_traffic_cost` | float | `null` in both doc examples |
| `clickstream_etv` | int | Only with clickstream |
| `rank_changes` | object | `previous_rank_absolute`, `is_new`, `is_up`, `is_down` |
| `backlinks_info` | object | `null` in both doc examples |
| `rank_info` | object | `page_rank`, `main_domain_rank` |

Compared with organic, this type has no `xpath`, `description`, `breadcrumb`, `checks` or `is_*` flags.

The surrounding `ranked_serp_element` keeps its usual fields: `check_url`, `serp_item_types` (which includes `"ai_overview"`), `se_results_count`, `keyword_difficulty`, `is_lost`, `last_updated_time` and `previous_updated_time`.

### `metrics.ai_overview_reference` (aggregate)
It has the same shape as the other metric types: `pos_1`…`pos_91_100`, `etv`, `count`, `estimated_paid_traffic_cost`, `is_new`, `is_up`, `is_down`, `is_lost` and the clickstream fields. The docs describe the buckets as "number of ai_overview references where the target ranks #N". Help-center example for medium.com (US/en): `count 986598`, `pos_1 59249`, …, `etv 22972498.8`.

Which rank the buckets use: `metrics` uses `rank_group` and `metrics_absolute` uses `rank_absolute`, as for every other type. So in `metrics`, the `pos_*` buckets for AI Overview references reflect the order among references. This is how the docs define rank_group. The docs do not say this specifically for AIO.

### Inside Historical SERPs (`ai_overview` element)
- Top level: `type='ai_overview'`, `rank_group`, `rank_absolute`, `page`, `position`, `xpath`, `asynchronous_ai_overview` (bool: loaded asynchronously, or `false` = from cache), `markdown`, `items[]`, `references[]`, `rectangle`.
- `items[]` can be any of these:
  - `ai_overview_element`: title, text, markdown, `links[]`, `images[]`, `references[]`
  - `ai_overview_video_element`
  - `ai_overview_table_element`: markdown, table, `references[]`
  - `ai_overview_expanded_element`: `components[]`, each with its own `links` and `references`
- Each reference: `{type:'ai_overview_reference', source, domain, url, title, text}`. The nested references in Historical SERPs carry **no rank, etv or rank_changes**. The ranked fields exist only in the Ranked Keywords projection.

---

## 12. Data grain and identity notes

### Natural keys (what identifies one row)

| Data | Natural key | Source endpoint |
|---|---|---|
| Ranking of a target on a keyword | `keyword × location_code × language_code × item type (serp_item.type) × url` at a database snapshot. Use `ranked_serp_element.last_updated_time` (the SERP check time) or the Labs status `google.date_update` as the time key. | ranked_keywords |
| Page-level ranking rollup | `page_address × location × language × item type` at a snapshot | relevant_pages |
| Subdomain rollup | `subdomain × location × language × item type` at a snapshot | subdomains |
| Domain vs keyword-set competitor row | `sorted seed keyword set × location × language × domain` (plus `include_subdomains` and `item_types`, which change the numbers) | serp_competitors |
| Competitor pair | `target × competitor domain × location × language` (plus `max_rank_group`, `intersecting_domains` and `item_types`, which change the numbers) | competitors_domain |
| Shared keyword of two domains | `target1 × target2 × keyword × location × language` | domain_intersection |
| Shared keyword of a page set | `page set (ordered keys 1..20) × keyword × location × language` | page_intersection |
| Historical SERP snapshot | `keyword × location_code × language_code × datetime`. Roughly one per month. | historical_serps |
| Element inside a snapshot | `snapshot × rank_absolute`. `type` + `rank_group` is also unique within a snapshot, by definition of rank_group. | historical_serps |
| Monthly traffic estimate | `target × location × language × item type × year × month` | historical_bulk_traffic_estimation |

Notes:
- `location_code` / `language_code` can be `null` in the result when the request left them out on endpoints where they are optional (ranked_keywords, relevant_pages, subdomains, bulk). The data is then "all available locations/languages". That is a different grain from a single location, and a key must keep the two apart.
- `domain` in an organic `serp_item` is the **host as shown in the SERP** (the docs say "subdomain in SERP"). `main_domain` is the registrable domain. `relative_url` is the path without scheme and host. `url` is the full URL.
- Whether one keyword can return more than one item for the same domain target (two URLs ranking, or organic plus featured snippet): not stated in docs.
- `rank_group` counts within one element type. `rank_absolute` counts across all elements. Store both. The `metrics` buckets use `rank_group`, and `metrics_absolute` uses `rank_absolute`.

### What changes over time
- Per ranking: `rank_group`, `rank_absolute`, `url` (the ranking URL for a keyword can change), `title`, `description`, `etv`, `estimated_paid_traffic_cost`, `rank_changes.*`, `is_lost`, `backlinks_info.*` (has its own `time_update`), `rank_info.*`.
- Per keyword (embedded `keyword_data`): `search_volume`, `monthly_searches`, `cpc`, `competition`, `keyword_difficulty`, `search_intent_info` and `avg_backlinks_info`. Each block has its own `last_updated_time`, and these times are often different from the SERP check time. In a help-center example, keyword_info is from 2025-07-17, the SERP from 2025-07-09 and search intent from 2023-03-03.
- `rank_changes` in Ranked Keywords compares to `previous_updated_time` (the previous SERP check). In Historical SERPs it compares to the preceding month. The `metrics.*.is_new/is_up/is_down/is_lost` counts are aggregates of the same comparison.
- Aggregates (`metrics`, `etv`, `count`) are recomputed by DataForSEO each time the database updates. The docs give no per-snapshot ID other than the timestamps.

### Labs ranking data vs a live SERP API fetch

| Aspect | Labs (ranked_keywords, historical_serps, …) | SERP API (`/v3/serp/google/organic/live/advanced`) |
|---|---|---|
| Source | DataForSEO's in-house database, built from SERPs it collected earlier (Labs overview) | A live query to Google at request time |
| Freshness | Database "updated weekly" (status endpoint gives the date). Each keyword's SERP has its own `last_updated_time`, and the gap between checks can be weeks (doc example: previous check 2025-05-26, last check 2025-07-09). Historical SERPs: roughly monthly snapshots, 12 months back. | Current at request time |
| Keyword coverage | Only keywords in DataForSEO's database. You cannot ask Labs for a keyword it has not tracked. Exception: historical_serps takes any keyword string, but returns only what is stored. | Any keyword |
| Depth | Buckets go to position 100 and doc `check_url`s contain `num=100`. An explicit depth is not stated in docs. No depth parameter. | `depth` parameter: default 10, max 200 (billed per 10 results) |
| Device | Not stated in docs. No device parameter. | `device`: desktop (default) / mobile |
| Element types returned | ranked_keywords: only `organic`, `paid`, `featured_snippet`, `local_pack`, `ai_overview_reference` (others appear only as names in `serp_item_types`). Other Labs ranking endpoints: only organic, paid, featured_snippet, local_pack. historical_serps: the full SERP, about 40 element types including `ai_overview`. | Full SERP element set, including `ai_overview` with references. AI Overviews that load asynchronously need `load_async_ai_overview` (extra $0.002). |
| Extra fields | Labs adds `etv`, `estimated_paid_traffic_cost`, `rank_changes`, `backlinks_info`, `rank_info` and embedded keyword metrics | Raw SERP fields. No etv or rank_changes. |
| Query shape | Target-centric (domain/page → keywords) or keyword-set-centric (serp_competitors) | Keyword-centric (keyword → SERP) |
| Cost model | $0.012/task + $0.00012/item (up to 1000 items per call); historical SERPs $0.00012/snapshot | Per SERP of up to 10 results (see SERP API pricing) |

SERP API facts above come from https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/.
