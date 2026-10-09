# DataForSEO v3 — Keywords Data API reference (for Meelu keyword storage design)

Researched 2026-10-06 from the live pages at https://docs.dataforseo.com/v3/ and the pricing pages at https://dataforseo.com/pricing/keywords-data/*. Everything below comes from those pages. Where a page does not say something, this file says "not stated in docs".

Scope: Google Ads, Bing Ads, Clickstream Data, Google Trends, DataForSEO Trends. AI Optimization / LLM APIs and DataForSEO Labs are out of scope.

---

## 0. Things common to every endpoint

### 0.1 Base URL, auth, request shape

- Base: `https://api.dataforseo.com/v3/keywords_data/...`
- Auth: HTTP Basic with the API login and password from `https://app.dataforseo.com/api-access`.
- POST bodies are JSON (UTF-8). The body is an **array of task objects**. Each task object carries the parameters listed under each endpoint.
- Every task accepts `tag` (string, optional, max 255 chars). It is echoed back in `tasks[].data`.

### 0.2 Two methods: Live and Standard

| | Live | Standard |
|---|---|---|
| Endpoints | `.../live` (one POST returns data) | `.../task_post` (POST), `.../tasks_ready` (GET), `.../task_get/$id` (GET) |
| Tasks per call | 1 task per Live call | up to 100 tasks per POST; tasks above 100 return error `40006` |
| Billing | charged per request | charged only when the task is set; `task_get` is free |
| Price | higher | lower ("more affordable") |
| Callbacks | none | `postback_url` (POSTs gzip results) or `pingback_url` (GET notification). `$id` and `$tag` placeholders are substituted. If your server does not answer in 10 s, the task goes to the `tasks_ready` list. |

Standard-method rules (same on every endpoint checked: Google Ads, Bing, Google Trends):

- `tasks_ready`: free, up to **20 calls per minute**, returns up to **1000 tasks** completed in the **previous three days** that were not yet collected. A task with a `postback_url` only appears here if the postback failed (your server returned HTTP <200 or >300). Docs recommend pingback/postback above 1000 tasks/minute.
- `task_get/$id`: free; results stay retrievable for **30 days**.
- Each `tasks_ready` item: `id` (UUID), `se` (search engine), `function`, `date_posted` (UTC), `endpoint` (URL to collect).

Clickstream Data and DataForSEO Trends are **Live only**.

### 0.3 Response envelope (same on every endpoint)

```
version (string), status_code (int), status_message (string), time (string, seconds),
cost (float, USD, total), tasks_count (int), tasks_error (int),
tasks[]:
  id (UUID string), status_code (int, 10000–60000), status_message, time, cost (float USD),
  result_count (int), path (array), data (object: the POST params echoed back),
  result (array; null on task_post responses)
```

The per-endpoint sections below only list what is inside `tasks[].result[]`.

### 0.4 Global limits and caveats

- **2000 API calls per minute** per account (all Keywords Data endpoints). Can be raised on request.
- **Google Ads Live endpoints: max 12 requests per minute per account.** Clickstream `dataforseo_search_volume` has the same 12/min cap.
- Clickstream `global_search_volume`, `bulk_search_volume` and all DataForSEO Trends endpoints: max **30 simultaneous** requests.
- Google Trends Live: limit errors possible above **250 Live tasks per minute**; DataForSEO's whole platform is capped at **500K Google Trends requests per day across all users**.
- **Restricted categories**: Google Ads and Bing data follow Google Advertising Policy / Microsoft Advertising policies. No data for keywords in categories such as weapons, tobacco, drugs, violence, terrorism. **If one keyword in a batch falls into such a category, no data is returned for the whole batch** (stated on the Keywords Data overview and the Bing overview).
- Russia and Belarus locations are not supported anywhere.
- Keywords are lowercased by the API on every endpoint that documents it.

### 0.5 Pricing summary (from https://dataforseo.com/pricing/keywords-data/*)

| API | Standard (per task) | Live (per task) | Notes |
|---|---|---|---|
| Google Ads | $0.06 | $0.09 | Same per-task price for 1 or 1000 keywords. Pricing page gives one price for "Google Ads API"; it does not list separate prices for search_volume / keywords_for_site / keywords_for_keywords / ad_traffic_by_keywords. Standard turnaround "1 to 3 hours depending on the load"; Live "up to 7 seconds on average". |
| Bing Ads | $0.06 | $0.09 | Pricing page says "bulk of up to 200 keywords" per task (endpoint docs allow 1000 for search_volume). Per-endpoint prices not listed separately. Standard "up to 45 minutes"; Live "up to 7 seconds". |
| Google Trends Explore | $0.0027 | $0.011 | Up to 5 keywords per task. Standard "up to 45 minutes"; Live "up to 32 seconds". |
| Clickstream `bulk_search_volume` | — | $0.012 per request **+ $0.00012 per item** | Live only. "~$132 per 1M keywords". |
| Clickstream `global_search_volume` | — | $0.18 per task | Live only. |
| Clickstream `dataforseo_search_volume` | — | $0.18 per task | Live only. |
| DataForSEO Trends Explore | — | $0.0012 per task | Live only. |
| DataForSEO Trends Subregion Interests / Demography | — | $0.0024 per task | Live only. |
| DataForSEO Trends Merged Data | — | $0.006 per task | Live only. |

All `locations`, `languages`, `status`, `categories`, `tasks_ready` and `task_get` endpoints are free.
DataForSEO also reports the actual cost in `cost` on every response; Meelu should trust that number over this table.

---

## 1. Google Ads

Overview: https://docs.dataforseo.com/v3/keywords_data/google_ads/overview/

- Source: Google Ads API (Keyword Planner). Locations match Google Geographical Targeting.
- "Generally, Google updates keyword data in the middle of the month." Check the Status endpoint.
- Migration note (https://docs.dataforseo.com/v3/keywords_data/google_ads/migration_guide/): the old Google AdWords API endpoints (`keywords_data/google/...`) are replaced by `keywords_data/google_ads/...`. The guide lists `cpc` and `categories` as deprecated response fields for search_volume / keywords_for_site / keywords_for_keywords, but the **current endpoint pages still list `cpc`** in the response. Treat `cpc` as possibly null.
- Help Center (https://dataforseo.com/help-center/what-are-similarity-keywords-and-how-can-you-identify-them-in-google-ads-api): Google Ads groups "too similar" keywords and aggregates their metrics under the **first keyword of the group**; other members get no data. The article mentions a `return_close_variants` flag and a `close_variants` array; **these fields are not listed on the current Google Ads search_volume endpoint pages**, so their availability there is not stated in the endpoint docs.
- Volume rounding / bucketing: **not stated in docs.** The docs only say Google "provides combined search volume values for groups of similar keywords" and recommends sending similar keywords in separate requests.

### 1.1 Google Ads Status

https://docs.dataforseo.com/v3/keywords_data/google_ads/status/

- `GET https://api.dataforseo.com/v3/keywords_data/google_ads/status` — free.
- Result fields:

| Field | Type | Meaning |
|---|---|---|
| `actual_data` | boolean | true = Google has published last month's data |
| `date_update` | string (yyyy-mm-dd) | date of the latest Google Ads data update |
| `last_year_in_monthly_searches` | integer | latest year present in `monthly_searches` |
| `last_month_in_monthly_searches` | integer | latest month present in `monthly_searches` |

- Use: if `actual_data` is false, `date_from` may only be the month before last or earlier; if true, last month or earlier. Good trigger for a monthly refresh job.

### 1.2 Google Ads Locations

https://docs.dataforseo.com/v3/keywords_data/google_ads/locations/

- `GET .../google_ads/locations` and `GET .../google_ads/locations/$country` (filter by country ISO code). Free. CSV download also offered (last updated 2026-09-01).
- Any Google target type is allowed except "Okrug". **Postal codes can be set, but return no data.**
- Fields: `location_code` (int), `location_name` (string, e.g. "London,England,United Kingdom"), `location_code_parent` (int, parent location), `country_iso_code` (string), `location_type` (string, Google target type).

### 1.3 Google Ads Languages

https://docs.dataforseo.com/v3/keywords_data/google_ads/languages/

- `GET .../google_ads/languages`. Free.
- Fields: `language_name` (string), `language_code` (string, ISO 639-1).

### 1.4 Google Ads Search Volume

Live: https://docs.dataforseo.com/v3/keywords_data/google_ads/search_volume/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/google_ads/search_volume/task_post/
Tasks Ready: https://docs.dataforseo.com/v3/keywords_data/google_ads/search_volume/tasks_ready/
Task GET: https://docs.dataforseo.com/v3/keywords_data/google_ads/search_volume/task_get/

- `POST .../google_ads/search_volume/live`
- `POST .../google_ads/search_volume/task_post`, `GET .../tasks_ready`, `GET .../task_get/$id`
- Historical data: **4 years**.

Request parameters:

| Param | Type | Req | Rules / default |
|---|---|---|---|
| `keywords` | array of string | **required** | max **1000** keywords; max **80 chars** each; max **10 words** each; lowercased; no emojis / certain UTF symbols |
| `location_name` | string | optional | omit all location fields = **worldwide** |
| `location_code` | integer | optional | e.g. 2840 |
| `location_coordinate` | string | optional | "lat,lng"; data is for the **country** containing the point |
| `language_name` | string | optional | e.g. "English" |
| `language_code` | string | optional | e.g. "en" |
| `search_partners` | boolean | optional | default `false` (Google search only) |
| `date_from` | string yyyy-mm-dd | optional | min = 4 years ago; default = **past 12 months**; cannot exceed `date_to` or yesterday; see Status rule |
| `date_to` | string yyyy-mm-dd | optional | default = yesterday; cannot be later than last month (no current-month data) |
| `include_adult_keywords` | boolean | optional | default `false` |
| `sort_by` | string | optional | `relevance` (default), `search_volume`, `competition_index`, `low_top_of_page_bid`, `high_top_of_page_bid` (descending) |
| `postback_url`, `pingback_url` | string | optional | task_post only |
| `tag` | string | optional | ≤255 chars |

Result: one item per keyword directly in `result[]`:

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `keyword` | string | | keyword (%## decoded, `+` → space) |
| `spell` | string | yes | corrected spelling; if input was misspelled, data is for the corrected spelling |
| `location_code` | integer | yes (null if no data) | from request |
| `language_code` | string | yes (null if no data) | from request |
| `search_partners` | boolean | | whether partner data is included |
| `competition` | string | yes | `HIGH` / `MEDIUM` / `LOW`; paid SERP only |
| `competition_index` | integer | yes | 0–100; paid SERP only |
| `search_volume` | integer | yes | monthly average search volume |
| `low_top_of_page_bid` | float | not stated | ~20th percentile top-of-page bid |
| `high_top_of_page_bid` | float | not stated | ~80th percentile top-of-page bid |
| `cpc` | float | not stated (see migration note) | USD cost per click |
| `monthly_searches` | array | yes | one object per month in the date range |
| `monthly_searches[].year` | integer | | |
| `monthly_searches[].month` | integer | | 1–12 |
| `monthly_searches[].search_volume` | integer | | volume in that month |

Pricing: per request/task, the same for 1 or 1000 keywords. Standard $0.06, Live $0.09.

### 1.5 Google Ads Keywords For Site

Live: https://docs.dataforseo.com/v3/keywords_data/google_ads/keywords_for_site/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/google_ads/keywords_for_site/task_post/
Task GET: https://docs.dataforseo.com/v3/keywords_data/google_ads/keywords_for_site/task_get/

- `POST .../google_ads/keywords_for_site/live`; `task_post` / `tasks_ready` / `task_get/$id`.
- Returns up to **2000** keyword ideas per request. Historical data: 4 years.

Request parameters:

| Param | Type | Req | Rules / default |
|---|---|---|---|
| `target` | string | **required** | domain or page URL |
| `target_type` | string | optional | `site` or `page`; **default `page`** |
| `location_name` / `location_code` / `location_coordinate` | | optional | same as 1.4; omit = worldwide |
| `language_name` / `language_code` | | optional | |
| `search_partners` | boolean | optional | default false |
| `date_from` | string | optional | min 4 years ago; default past 12 months |
| `date_to` | string | optional | default yesterday; cannot exceed yesterday |
| `include_adult_keywords` | boolean | optional | default false |
| `sort_by` | string | optional | same values as 1.4; default relevance |
| `postback_url`, `pingback_url` | | optional | task_post only |
| `tag` | | optional | |

Result items: the same fields as 1.4 **minus `spell`**, **plus**:

| Field | Type | Meaning |
|---|---|---|
| `keyword_annotations` | object | annotations for the keyword |
| `keyword_annotations.concepts[]` | array | concepts |
| `concepts[].name` | string | concept name |
| `concepts[].concept_group.name` | string | concept group name |
| `concepts[].concept_group.type` | string | concept group type |

Nullability: `competition`, `competition_index`, `search_volume`, `monthly_searches`, `location_code`, `language_code` can be null. Others: not stated.

Pricing: per request regardless of keywords returned. Standard $0.06, Live $0.09 (Google Ads price; not broken down per endpoint).

### 1.6 Google Ads Keywords For Keywords

Live: https://docs.dataforseo.com/v3/keywords_data/google_ads/keywords_for_keywords/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/google_ads/keywords_for_keywords/task_post/

- `POST .../google_ads/keywords_for_keywords/live`; `task_post` / `tasks_ready` / `task_get/$id`.
- Up to **20 seed keywords**, up to **20,000** ideas returned per request. Historical data: 4 years.

Request parameters:

| Param | Type | Req | Rules / default |
|---|---|---|---|
| `keywords` | array | **required** | max **20**; max 80 chars each; lowercased |
| `target` | string | optional | **listed on task_post page only** (not on the Live page). Website or URL; even with a URL, keywords are for the whole site |
| location / language fields | | optional | as 1.4; omit location = worldwide |
| `search_partners` | boolean | optional | default false |
| `date_from` / `date_to` | string | optional | as 1.5 |
| `sort_by` | string | optional | as 1.4 |
| `include_adult_keywords` | boolean | optional | default false |
| `postback_url`, `pingback_url` | | optional | task_post only |
| `tag` | | optional | |

Result items: identical to 1.5 (incl. `keyword_annotations`, no `spell`). There is **no field linking a returned idea back to the seed keyword** it came from (not stated in docs).

Pricing: per request. Standard $0.06, Live $0.09.

### 1.7 Google Ads Ad Traffic By Keywords

Live: https://docs.dataforseo.com/v3/keywords_data/google_ads/ad_traffic_by_keywords/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/google_ads/ad_traffic_by_keywords/task_post/
Task GET: https://docs.dataforseo.com/v3/keywords_data/google_ads/ad_traffic_by_keywords/task_get/

- A **forecast** for a future period, not historical volume. Since "June 1" the docs say it returns **bulk data for the entire campaign** (all keywords in the task). Results are account-specific in Google Ads; docs advise a high bid to level other factors.
- Up to 1000 keywords per request.

Request parameters:

| Param | Type | Req | Rules / default |
|---|---|---|---|
| `keywords` | array | **required** | max 1000; 80 chars; 10 words |
| `bid` | integer (Live page) / float (task_post page) | **required** | max custom bid; higher bid → higher metrics |
| `match` | string | **required** | `exact`, `broad`, `phrase` |
| location / language fields | | optional | omit location = worldwide |
| `date_from` | string | required if `date_to` set | min = tomorrow |
| `date_to` | string | required if `date_from` set | min `date_from`+1 day; max = same day next year |
| `date_interval` | string | optional | `next_week`, `next_month` (default), `next_quarter` |
| `sort_by` | string | optional | Live: relevance, impressions, ctr, average_cpc, cost, clicks. task_post: relevance, average_cpc, cost, clicks |
| `postback_url`, `pingback_url` | | optional | task_post only |
| `tag` | | optional | |

Result items:

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `keyword` | string | | |
| `location_code` | integer | yes | |
| `language_code` | string | yes | |
| `date_interval` | string | | from request |
| `search_partners` | boolean | | **deprecated, always false** |
| `bid` | integer | | from request |
| `match` | string | | from request |
| `impressions` | float | **always null (deprecated)** | |
| `ctr` | float | **always null (deprecated)** | |
| `average_cpc` | float | yes | USD |
| `cost` | float | yes | projected spend for the period |
| `clicks` | float | yes | projected clicks for the period |

Pricing: per request, Google Ads rate (Standard $0.06, Live $0.09).
Grain: keyword × location × language × match × bid × forecast window, and per Google Ads account context. Not a stable fact about the keyword; poor fit for a shared keyword table.

---

## 2. Bing Ads

Overview: https://docs.dataforseo.com/v3/keywords_data/bing/overview/

- Source: Bing Ads API (Microsoft Advertising).
- "It can take up to 72 hours before the keyword data for the previous calendar month is available." Status page: "Generally, Bing updates keyword data in the beginning of the month."
- Restricted categories: same whole-batch rule as Google.
- Bing also has **Keyword Suggestions For URL** (`bing/keyword_suggestions_for_url/...`), not covered here.

### 2.1 Bing Status

https://docs.dataforseo.com/v3/keywords_data/bing/status/

- `GET .../keywords_data/bing/status` — free. Fields identical to Google Ads Status: `actual_data`, `date_update`, `last_year_in_monthly_searches`, `last_month_in_monthly_searches`.

### 2.2 Bing Locations / Languages

https://docs.dataforseo.com/v3/keywords_data/bing/locations/ — https://docs.dataforseo.com/v3/keywords_data/bing/languages/

- `GET .../bing/locations` (fields: `location_code`, `location_name`, `location_code_parent`, `country_iso_code`, `location_type`). CSV last updated 2026-09-01.
- `GET .../bing/languages` (fields: `language_name`, `language_code`).
- Keyword Performance and Search Volume History have **their own** location/language lists (below).
- Search Volume, Keywords For Site and Keywords For Keywords only accept languages **English, French, German** (`en`, `fr`, `de`).

### 2.3 Bing Search Volume

Live: https://docs.dataforseo.com/v3/keywords_data/bing/search_volume/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/bing/search_volume/task_post/
Task GET: https://docs.dataforseo.com/v3/keywords_data/bing/search_volume/task_get/

- `POST .../bing/search_volume/live`; `task_post` / `tasks_ready` / `task_get/$id`.
- Historical data: **24 months**.

Request parameters:

| Param | Type | Req | Rules / default |
|---|---|---|---|
| `keywords` | array | **required** | max **1000**; max **100 chars** each; lowercased |
| `location_name` / `location_code` / `location_coordinate` | | **one is required** | coordinate → country |
| `language_name` / `language_code` | | **one is required** | English/French/German only |
| `device` | string | optional | `all` (default), `mobile`, `desktop`, `tablet` |
| `sort_by` | string | optional | `search_volume`, `cpc`, `competition`, `relevance` (default) |
| `date_from` | string | optional | min 24 months ago; default last 12 months; docs advise against custom ranges for past-year dates |
| `date_to` | string | optional | default last 12 months; max "one month from today's date" |
| `search_partners` | boolean | optional | default false (Bing, AOL, Yahoo networks) |
| `postback_url`, `pingback_url` | | optional | task_post only |
| `tag` | | optional | |

Result items:

| Field | Type | Nullable | Meaning |
|---|---|---|---|
| `keyword` | string | | |
| `location_code` | integer | yes | |
| `language_code` | string | yes | |
| `search_partners` | boolean | | |
| `device` | string | yes | from request |
| `competition` | **float** | yes | **0.1 low, 0.5 medium, 0.9 high** (differs from Google's string/int) |
| `cpc` | float | yes | USD, historical average |
| `search_volume` | integer | yes | monthly average; **rounded to the nearest tens** |
| `categories` | array | **always null** | |
| `monthly_searches[]` | array | yes | `year`, `month`, `search_volume` (rounded to tens) |

Pricing: per request regardless of keyword count. Standard $0.06, Live $0.09.

### 2.4 Bing Search Volume History

Live: https://docs.dataforseo.com/v3/keywords_data/bing/search_volume_history/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/bing/search_volume_history/task_post/
Locations & languages: https://docs.dataforseo.com/v3/keywords_data/bing/search_volume_history/locations_and_languages/

- `POST .../bing/search_volume_history/live`; `task_post` / `tasks_ready` / `task_get/$id`.
- `GET .../bing/search_volume_history/locations_and_languages` (free): `language_name`, `language_code`, `available_locations[]` {`location_code`, `location_name`, `country_iso_code`, `location_type`}.
- Only Bing endpoint with **weekly and daily** grain, and **per-device split**.

Request parameters:

| Param | Type | Req | Rules / default |
|---|---|---|---|
| `keywords` | array | **required** | max 1000; max 100 chars |
| location fields | | one required | from the endpoint's own list |
| language fields | | one required | from the endpoint's own list |
| `device` | **array** | optional | `mobile`, `desktop`, `tablet`, `non_smartphones`; default all four |
| `period` | string | optional | `monthly` (default, up to 24 months), `weekly` (up to 15 weeks), `daily` (up to 45 days) |
| `date_from` | string | optional | min 24 months back; default last 24 months (monthly) / 15 weeks / 45 days |
| `date_to` | string | optional | max "one day from today's date" |
| `postback_url`, `pingback_url` | | optional | task_post only |
| `tag` | | optional | |

Result items:

| Field | Type | Meaning |
|---|---|---|
| `keyword` | string | |
| `location_code` | integer, nullable | |
| `language_code` | string, nullable | |
| `device` | string, nullable | from request |
| `period` | string | monthly / weekly / daily |
| `searches` | object | keyed by device |
| `searches.desktop` / `.mobile` / `.tablet` / `.non_smartphones` | object (docs say object; the content is a series) | each entry: `year` (int), `month` (int), `day` (int), `search_volume` (int) |

Pricing: per request regardless of keyword count. Bing rate.

### 2.5 Bing Keywords For Site

Live: https://docs.dataforseo.com/v3/keywords_data/bing/keywords_for_site/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/bing/keywords_for_site/task_post/

- Up to **3000** keywords returned. Historical data 24 months.

Request: `target` (string, **required**, domain or URL), location (one required), language (one required; en/fr/de), `keywords_negative` (array, optional, max **200**, lowercased), `device` (default all), `date_from` / `date_to` (as 2.3), `sort_by` (as 2.3), `search_partners` (default false), `postback_url` / `pingback_url` (task_post only), `tag`.

Result items: `keyword`, `location_code`, `language_code`, `search_partners`, `device` (all/mobile/desktop/tablet), `competition` (float 0.1/0.5/0.9, nullable), `cpc` (nullable), `search_volume` (nullable; "rounded to the closest decimal values"), `categories` (legacy, always null), `monthly_searches[]` {`year`, `month`, `search_volume`}.

Pricing: per request, same for 1 or 3000 keywords returned.

### 2.6 Bing Keywords For Keywords

Live: https://docs.dataforseo.com/v3/keywords_data/bing/keywords_for_keywords/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/bing/keywords_for_keywords/task_post/

- Up to **200 seed keywords** (max 100 chars each); up to **3000** suggestions.
- Request: `keywords` (required), location (one required), language (one required; en/fr/de), `sort_by`, `keywords_negative` (max 200), `device`, `date_from` / `date_to`, `search_partners`, `postback_url` / `pingback_url` (task_post), `tag`.
- Result items: same as 2.5.
- Pricing: per request.

### 2.7 Bing Keyword Performance

Live: https://docs.dataforseo.com/v3/keywords_data/bing/keyword_performance/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/bing/keyword_performance/task_post/
Locations & languages: https://docs.dataforseo.com/v3/keywords_data/bing/keyword_performance/locations_and_languages/

- Ad performance stats (ad position, clicks, impressions, CPC, CTR, cost, bid) **aggregated for the last month**, per device.
- Own location list: `GET .../bing/keyword_performance/locations_and_languages` (location types: Country, Region).
- Keyword limit: the page text says "up to 2500 keywords", but the `keywords` field says **max 1000**, 80 chars, 10 words. The two statements conflict.

Request: `keywords` (required), `device` (`desktop`, `mobile`, `tablet`, `all` default), `match` (`aggregate` default, `broad`, `phrase`, `exact`), location (one required), language (one required), `postback_url` / `pingback_url` (task_post), `tag`.

Result items:

| Field | Type | Meaning |
|---|---|---|
| `keyword`, `location_code`, `language_code` | | nullable location/language |
| `year`, `month` | integer | month the data is for |
| `keyword_kpi` | object, nullable | |
| `keyword_kpi.desktop[]` / `.mobile[]` / `.tablet[]` | array, nullable | one entry per ad position |
| `...ad_position` | string | `FirstPage1`… (ad slot) |
| `...clicks` | integer | last month |
| `...impressions` | integer | last month |
| `...average_cpc` | integer (as documented) | USD |
| `...ctr` | integer (as documented) | percent |
| `...total_cost` | integer (as documented) | USD |
| `...average_bid` | integer (as documented) | |

Pricing: per request; Bing rate. (The Live page says "charged only for setting a task".)

### 2.8 Bing Audience Estimation (brief)

Live: https://docs.dataforseo.com/v3/keywords_data/bing/audience_estimation/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/bing/audience_estimation/task_post/

- Not keyword-level. Estimates audience size for an ad campaign from targeting (location, `age[]`, `gender[]`, `bid` ≤1000 USD, `daily_budget` ≤10000 USD, LinkedIn `industry[]`, `job_function[]`; lookups at `.../audience_estimation/industries` and `.../job_functions`). `location_coordinate` here is "lat,lng,radius_km".
- Result: ranges `est_impressions`, `est_audience_size`, `est_clicks`, `est_spend`, `est_cost_per_event`, `est_ctr` (each {`low`, `high`}), plus `suggested_bid`, `suggested_budget`, `events_lost_to_bid`, `events_lost_to_budget`, `est_reach_audience_size`, `est_reach_impressions`, `currency`.
- Not relevant for keyword storage.

---

## 3. Clickstream Data

Overview: https://docs.dataforseo.com/v3/keywords_data/clickstream_data/overview/

- DataForSEO's own volume, built from "refined clickstream data from reliable providers" with "special multipliers". Help Center (https://dataforseo.com/help-center/what-are-clickstream-based-metrics-and-how-do-we-calculate-them): monthly clickstream × a coefficient; the average is the sum of 12 months ÷ 12; data is collected via plugins, extensions and other apps.
- **Live only.** 2000 calls/min.
- Update cadence: **not stated in docs.** The Help Center update-time page (https://dataforseo.com/help-center/sv-update-time) covers Google Ads and Bing only.
- Not subject to the Google Ads restricted-category rule as far as the docs say (not stated).

### 3.1 Clickstream Locations and Languages

https://docs.dataforseo.com/v3/keywords_data/clickstream_data/locations_and_languages/

- `GET .../clickstream_data/locations_and_languages` — free.
- **Country level only** (`location_type` = Country, `location_code_parent` always null).
- Fields: `location_code`, `location_name`, `location_code_parent`, `country_iso_code`, `location_type`, `available_languages[]` {`language_name`, `language_code`}.

### 3.2 DataForSEO Search Volume

https://docs.dataforseo.com/v3/keywords_data/clickstream_data/dataforseo_search_volume/live/

- `POST .../clickstream_data/dataforseo_search_volume/live`. Live only.
- Volume "normalized with Bing search volume data or clickstream data".
- **12 requests per minute** cap ("limitations beyond our control").

Request:

| Param | Type | Req | Rules / default |
|---|---|---|---|
| `keywords` | array | **required** | max 1000; lowercased; no emojis |
| `location_name` / `location_code` | | one required | from 3.1 |
| `language_name` / `language_code` | | one required | |
| `use_clickstream` | boolean | optional | default `true`. `false` = base on Bing volume — only for locations in Bing Search Volume History / Bing Ads lists; elsewhere clickstream is used anyway |
| `tag` | | optional | |

Result (note the extra `items` level):

| Field | Type | Meaning |
|---|---|---|
| `location_code` | integer, nullable | |
| `language_code` | string, nullable | |
| `items_count` | integer (page says string) | |
| `items[].keyword` | string | |
| `items[].use_clickstream` | boolean | which basis was used |
| `items[].search_volume` | integer | "current search volume rate" |
| `items[].monthly_searches[]` | array | `year`, `month`, `search_volume` |

Nullability of item fields: not stated. History depth: not stated.
Pricing: $0.18 per task (Live).

### 3.3 Global Search Volume

https://docs.dataforseo.com/v3/keywords_data/clickstream_data/global_search_volume/live/

- `POST .../clickstream_data/global_search_volume/live`. Live only. Max 30 simultaneous requests.
- **No location or language parameters.** Returns a global figure and a per-country split.

Request: `keywords` (required, max 1000, **each ≥3 characters**, lowercased), `tag`.

Result:

| Field | Type | Meaning |
|---|---|---|
| `items_count` | integer | |
| `items[].keyword` | string | |
| `items[].search_volume` | integer | clickstream global average monthly volume |
| `items[].country_distribution[]` | array | per country |
| `...country_iso_code` | string | |
| `...search_volume` | integer | volume in that country |
| `...percentage` | float | share of global volume |

No `monthly_searches` here. Pricing: $0.18 per task.

### 3.4 Bulk Clickstream Search Volume

https://docs.dataforseo.com/v3/keywords_data/clickstream_data/bulk_search_volume/live/

- `POST .../clickstream_data/bulk_search_volume/live`. Live only. Max 30 simultaneous requests.
- Monthly history **up to 12 months** ("depending on keywords, location, and language parameters").
- **Only location parameters; no language parameter is documented.**

Request: `keywords` (required, max 1000, each ≥3 chars), `location_name` / `location_code` (one required), `tag`.

Result:

| Field | Type | Meaning |
|---|---|---|
| `location_code` | integer | |
| `items_count` | integer | |
| `items[].keyword` | string | |
| `items[].search_volume` | integer | clickstream average monthly volume |
| `items[].monthly_searches[]` | array | `year`, `month`, `search_volume` |

Pricing: **$0.012 per request + $0.00012 per item returned** (the only per-keyword-priced endpoint in this API). Cheapest volume source per keyword at scale.

---

## 4. Google Trends

Overview: https://docs.dataforseo.com/v3/keywords_data/google_trends/overview/

- Scraped from Google Trends "Explore". Relative popularity (0–100), not absolute volume.
- Max **5 keywords** per task to compare.
- Standard and Live supported; Standard recommended. Live may hit limit errors above 250 tasks/minute; platform-wide cap of 500K Google Trends requests/day across all users.

### 4.1 Google Trends Locations / Languages / Categories

https://docs.dataforseo.com/v3/keywords_data/google_trends/locations/ — https://docs.dataforseo.com/v3/keywords_data/google_trends/categories/

- `GET .../google_trends/locations[/$country]`: `location_code`, `location_name`, `location_code_parent`, `country_iso_code`, `location_type`, **`geo_name`**, **`geo_id`** (Trends identifiers such as `US-NY`).
- `GET .../google_trends/languages`: `language_name`, `language_code` (ISO 639-1).
- `GET .../google_trends/categories`: `category_code` (int), `category_name`, `category_code_parent`.
- All free.

### 4.2 Google Trends Explore

Live: https://docs.dataforseo.com/v3/keywords_data/google_trends/explore/live/
Task POST: https://docs.dataforseo.com/v3/keywords_data/google_trends/explore/task_post/
Task GET: https://docs.dataforseo.com/v3/keywords_data/google_trends/explore/task_get/

- `POST .../google_trends/explore/live`; `task_post` / `tasks_ready` / `task_get/$id`.
- History: `web` from 2004-01-01; other types from 2008-01-01.

Request:

| Param | Type | Req | Rules / default |
|---|---|---|---|
| `keywords` | array | required unless `category_code` set | max **5**; max 100 chars; >1 char; commas removed; cannot be only `| " - + = ~ ! : * ( ) [ ] { }`; topics/queries lists need exactly 1 keyword |
| `location_name` / `location_code` | string/int | optional | omit = global; may be an array (one location per keyword) |
| `language_name` / `language_code` | | optional | default English / `en` |
| `type` | string | optional | `web` (default), `news`, `youtube`, `images`, `froogle` (Shopping) |
| `category_code` | integer | required if no keywords | default 0 (all) |
| `date_from` | string | optional | default = same day last year |
| `date_to` | string | optional | default = today |
| `time_range` | string | optional | ignored if dates given. `past_hour`, `past_4_hours`, `past_day`, `past_7_days`, `past_30_days`, `past_90_days`, `past_12_months`, `past_5_years`; `2004_present` (web), `2008_present` (others) |
| `item_types` | array | optional | `google_trends_graph` (default), `google_trends_map`, `google_trends_topics_list`, `google_trends_queries_list`; docs advise one at a time for speed |
| `postback_url`, `pingback_url` | | optional | task_post only |
| `tag` | | optional | |

Result:

| Field | Type | Meaning |
|---|---|---|
| `keywords` | array | from request |
| `location_code` / `language_code` | nullable | |
| `check_url` | string | link to the Google Trends page |
| `datetime` | string | UTC time the result was fetched |
| `items_count`, `items[]` | | one item per element type |

Item types:

- `google_trends_graph`: `position`, `type`, `title`, `keywords[]`, `data[]` {`date_from`, `date_to`, `timestamp` (unix), `missing_data` (bool), `values` (one value per keyword)}, `averages[]` (per keyword over the whole range). 100 = peak; values are scaled to the highest value across all keywords in the task.
- `google_trends_map`: `data[]` {`geo_id`, `geo_name`, `values`, `max_value_index` (null if one keyword)}.
- `google_trends_topics_list`: `data.top[]` and `data.rising[]` {`topic_id`, `topic_title`, `topic_type`, `value` (string; rising = % increase)}.
- `google_trends_queries_list`: `data.top[]` and `data.rising[]` {`query`, `value` (string)}.

Point granularity (hourly / daily / weekly / monthly) depends on the range Google chooses; not stated in docs.

Pricing: per task, 1–5 keywords. Standard $0.0027, Live $0.011.

---

## 5. DataForSEO Trends

Overview: https://docs.dataforseo.com/v3/dataforseo_trends/overview/

- DataForSEO's own popularity index for Google Search (`web`), Google News (`news`) and Google Shopping (`ecommerce`), based on association with web pages / news / shopping listings combined with anonymous user web-behaviour data. Positioned as "a more reliable alternative to Google Trends API".
- **Live only.** Max 5 keywords per task. Max 30 simultaneous requests. History: web from 2004-01-01, others from 2008-01-01.
- Smallest geography: **country**. `GET .../dataforseo_trends/locations[/$country]` (free) returns the same fields as Google Trends locations incl. `geo_id`, `geo_name`.
- **No language parameter** on any DataForSEO Trends endpoint (responses still carry `language_code`).

Common request parameters for 5.1–5.4:

| Param | Type | Req | Rules / default |
|---|---|---|---|
| `keywords` | array | **required** | max 5; avoid emojis/special chars |
| `location_name` / `location_code` | | optional | omit = global; data is for the country containing the location |
| `type` | string | optional | `web` (default), `news`, `ecommerce` |
| `date_from` / `date_to` | string | optional | default last year → today |
| `time_range` | string | optional | `past_4_hours`, `past_day`, `past_7_days`, `past_30_days`, `past_90_days`, `past_12_months`, `past_5_years`; ignored if dates given |
| `tag` | | optional | |

Common result header: `keywords[]`, `type[]`, `location_code`, `language_code` (nullable), `datetime` (UTC fetch time), `items_count`, `items[]`.

### 5.1 Explore

https://docs.dataforseo.com/v3/keywords_data/dataforseo_trends/explore/live/

- `POST .../dataforseo_trends/explore/live`.
- Item `dataforseo_trends_graph`: `position`, `type`, `keywords[]`, `data[]` {`date_from`, `date_to`, `timestamp`, `values[]` (one per keyword, scaled to the max across all keywords)}, `averages[]`.
- Price: $0.0012 per task.

### 5.2 Subregion Interests

https://docs.dataforseo.com/v3/keywords_data/dataforseo_trends/subregion_interests/live/

- `POST .../dataforseo_trends/subregion_interests/live`.
- Item `subregion_interests`:
  - `interests[]` {`keyword`, `values[]` {`geo_id`, `geo_name`, `value` (int; 100 = that keyword's best region)}}
  - `interests_comparison` (null if 1 keyword): `items[]` {`geo_id`, `geo_name`, `values[]` (per keyword, relative to max within the region)}, `absolute_items[]` {same, relative to max across all regions}.
- Price: $0.0024 per task.

### 5.3 Demography

https://docs.dataforseo.com/v3/keywords_data/dataforseo_trends/demography/live/

- `POST .../dataforseo_trends/demography/live`.
- Item `demography`:
  - `demography.age[]` {`keyword`, `values[]` {`type`: `18-24`|`25-34`|`35-44`|`45-54`|`55-64`, `value` int}}
  - `demography.gender[]` {`keyword`, `values[]` {`type`: `female`|`male`, `value` int}}
  - `demography_comparison` (null if 1 keyword): `age` {"18-24": [per-keyword values], ...}, `gender` {`female`: [...], `male`: [...]}.
- Price: $0.0024 per task.

### 5.4 Merged Data

https://docs.dataforseo.com/v3/keywords_data/dataforseo_trends/merged_data/live/

- `POST .../dataforseo_trends/merged_data/live`.
- Returns all three item types in one response: `dataforseo_trends_graph`, `subregion_interests`, `demography` (same fields as 5.1–5.3).
- Price: $0.006 per task (Explore + Subregion + Demography bought separately = $0.006 too).

---

## 6. Data grain and identity notes

Shared rules for DB design:

- Every keyword record is scoped by **source × keyword × location × language** at minimum. `location_code` and `language_code` can come back **null** ("if there is no data"), so store the **requested** location/language from your own task, not only the echoed one.
- "Worldwide" (no location) is a valid request on Google Ads and both Trends APIs. Use an explicit sentinel (e.g. location_code 0 or NULL with a unique constraint that treats it as a value).
- Keywords are lowercased by the API. Google Ads may return data for a **corrected spelling** (`spell`) or fold similar keywords into the first one. Store the keyword you sent and the keyword returned.
- `search_volume` (the average) is **derived** from the requested date range. Different `date_from` / `date_to` give different averages for the same keyword. Store monthly points as the canonical time series and treat the average as a snapshot attribute with its range.
- Monthly points can be **revised** between pulls (not stated in docs either way); keep a `fetched_at` per point or per snapshot.
- Trends values (Google and DataForSEO) are **relative within the request**. A value only means something next to the other keywords and the date range of the same task. Do not merge points from different tasks into one series.

| Endpoint | Natural unique key of one returned record | Time-varying parts |
|---|---|---|
| Google Ads search_volume | (keyword, location, language, search_partners) | `search_volume` (depends on date range), `competition`, `competition_index`, bids, `cpc` change monthly; `monthly_searches` keyed by (year, month) |
| Google Ads keywords_for_site | (target, target_type, location, language, search_partners) → set of keywords; each keyword row as search_volume | idea list itself changes over time; metrics monthly |
| Google Ads keywords_for_keywords | (seed set, location, language, search_partners) → set of keywords; no seed→idea link | as above |
| Google Ads ad_traffic_by_keywords | (keyword, location, language, match, bid, forecast window) | everything; it is a forecast and account-dependent |
| Bing search_volume | (keyword, location, language, device, search_partners) | as Google; volumes rounded to tens; competition float |
| Bing search_volume_history | (keyword, location, language, device, period) → points keyed by (year, month, day) | each point fixed once published (revision not stated); weekly up to 15 weeks, daily up to 45 days, monthly up to 24 months |
| Bing keywords_for_site / keywords_for_keywords | (target or seed set, location, language, device, search_partners) → set of keywords | idea list and metrics |
| Bing keyword_performance | (keyword, location, language, match, device, year, month, ad_position) | one month of ad stats; "last month" only |
| Bing audience_estimation | (targeting combination) | not keyword data |
| Clickstream dataforseo_search_volume | (keyword, location, language, use_clickstream) | `search_volume`, `monthly_searches` (year, month) |
| Clickstream global_search_volume | (keyword) global; plus (keyword, country_iso_code) in `country_distribution` | volume and shares; no months |
| Clickstream bulk_search_volume | (keyword, location) — **no language** | `search_volume`, up to 12 `monthly_searches` |
| Google Trends explore graph | (task: keywords set, location, language, type, category, date range) → points by timestamp × keyword | whole series is relative to the task; re-fetch changes it |
| Google Trends map / topics / queries | (task, single keyword for lists) → geo_id or topic_id / query | relative, re-fetch changes it |
| DataForSEO Trends explore | (task: keywords set, location, type, date range) → points by timestamp × keyword | relative to the task |
| DataForSEO Trends subregion_interests | (task, keyword, geo_id) | relative to the task |
| DataForSEO Trends demography | (task, keyword, age band or gender) | relative to the task |
| DataForSEO Trends merged_data | union of the three above | relative to the task |

Lookup tables worth caching (free, rarely change): Google Ads locations/languages, Bing locations/languages, Bing Search Volume History locations/languages, Bing Keyword Performance locations/languages, Clickstream locations/languages, Google Trends locations/languages/categories, DataForSEO Trends locations. Each list is source-specific: a `location_code` valid in one source is not guaranteed valid in another (Clickstream and DataForSEO Trends are country-only; Google Ads goes down to postal code, which returns no data).

### Volume source comparison

| | Google Ads search_volume | Clickstream (bulk / dataforseo_search_volume) | Bing search_volume |
|---|---|---|---|
| Underlying data | Google Keyword Planner via Google Ads API | DataForSEO clickstream model (dataforseo_search_volume can use Bing as base) | Microsoft Advertising (Bing, Yahoo, AOL) |
| Keywords per task | 1000 (80 chars, 10 words) | 1000 (bulk/global: ≥3 chars) | 1000 (100 chars) |
| Location grain | any Google target type, or worldwide | country only (global endpoint: worldwide + per-country split) | Bing location list; required |
| Language | optional | required for dataforseo_search_volume; **not a parameter** for bulk | required; en/fr/de only |
| Device split | no | no | yes (`device`); history endpoint splits 4 devices |
| History depth | 4 years, monthly | bulk: up to 12 months; dataforseo_search_volume: not stated | 24 months monthly; history endpoint also 15 weeks / 45 days |
| Extra metrics | competition (LOW/MEDIUM/HIGH + 0–100 index), top-of-page bids, cpc | none (global: country distribution) | competition (0.1/0.5/0.9), cpc |
| Known distortions | similar keywords folded into the first one; spelling correction; restricted categories kill whole batch | not stated | volumes rounded to tens; restricted categories kill whole batch |
| Update cadence | mid-month for previous month; check Status | not stated in docs | start of month, up to 72 h; check Status |
| Methods | Live + Standard | Live only | Live + Standard |
| Rate limits | Live: 12 req/min/account | dataforseo_search_volume: 12 req/min; bulk/global: 30 concurrent | 2000 calls/min general |
| Price | $0.06 std / $0.09 live per task | bulk $0.012/task + $0.00012/item; dataforseo_search_volume $0.18/task | $0.06 std / $0.09 live per task |
