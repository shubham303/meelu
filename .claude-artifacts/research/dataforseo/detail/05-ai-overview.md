# DataForSEO: Google AI Overview and AI Mode data

Research date: 2026-10-06. Every statement below comes from a DataForSEO doc page, update post or Help Center article fetched on that date. When the docs do not say something, this file says "not stated in docs".

Out of scope: the AI Optimization API (LLM responses, LLM mentions, LLM scraper, AI keyword search volume).

Main sources:

- Google Organic Live Advanced: https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/
- Google Organic Task POST: https://docs.dataforseo.com/v3/serp/google/organic/task_post/
- Google Organic Task GET Advanced: https://docs.dataforseo.com/v3/serp/google/organic/task_get/advanced/
- Google Organic Live HTML: https://docs.dataforseo.com/v3/serp/google/organic/live/html/
- Google Organic Live Regular: https://docs.dataforseo.com/v3/serp/google/organic/live/regular/
- Google Organic overview (pricing formula): https://docs.dataforseo.com/v3/serp/google/organic/overview/
- Google AI Mode overview: https://docs.dataforseo.com/v3/serp/google/ai_mode/overview/
- Google AI Mode Live Advanced: https://docs.dataforseo.com/v3/serp/google/ai_mode/live/advanced/
- Google AI Mode Task POST: https://docs.dataforseo.com/v3/serp/google/ai_mode/task_post/
- Google AI Mode Task GET Advanced: https://docs.dataforseo.com/v3/serp/google/ai_mode/task_get/advanced/
- Google AI Mode Languages: https://docs.dataforseo.com/v3/serp/google/ai_mode/languages/
- Labs Ranked Keywords: https://docs.dataforseo.com/v3/dataforseo_labs/google/ranked_keywords/live/
- Labs Historical SERPs: https://docs.dataforseo.com/v3/dataforseo_labs/google/historical_serps/live/
- Update post, AI Overview in SERP API: https://dataforseo.com/update/ai-overview-in-google-serp-api
- Update post, AI Overview in Knowledge Graph: https://dataforseo.com/update/ai-overview-in-googles-knowledge-graph
- Update post, AIO references in Ranked Keywords: https://dataforseo.com/update/aio-references-in-ranked-keywords-api
- Update post, upgraded AIO collection for Databases and Labs: https://dataforseo.com/update/upgraded-aio-collection-for-databases-and-labs-api
- Help Center, pull ranked keywords from AI Overviews: https://dataforseo.com/help-center/how-to-pull-ranked-keywords-from-ai-overviews
- Help Center, keywords a website ranks for in AI Overview (updated 03.08.2026): https://dataforseo.com/help-center/how-to-get-keywords-that-a-website-ranks-for-in-google-ai-overview
- Help Center, parse Google AI Overviews and AI Mode (updated 23.06.2026): https://dataforseo.com/help-center/parse-google-ai-overviews-ai-mode
- Pricing, Google Organic SERP API: https://dataforseo.com/pricing/serp/google-organic-serp-api
- Pricing, Google AI Mode SERP API: https://dataforseo.com/pricing/serp/google-ai-mode-serp-api

---

## 1. SERP API: the `ai_overview` item in Google Organic Advanced results

Sources: Organic Live Advanced, Task GET Advanced, Live Regular, AI Overview update post.

### 1.1 Where it appears

- `ai_overview` is one value in the result-level `item_types` array. The update post says: "We now automatically include the `ai_overview` element in the `item_types` list regardless of its type (synchronous/asynchronous), whenever we detect it in the search results."
- The full object is returned only by the **Advanced** endpoints (Live Advanced and Task GET Advanced). Live Regular lists `ai_overview` in `item_types` but says "this endpoint provides data for `featured_snippet`, `organic` and `paid` types only".
- HTML endpoints return raw HTML. See `expand_ai_overview` in section 2.
- AI Overview content also appears nested in two other places (section 1.5): inside `knowledge_graph` (`knowledge_graph_ai_overview_item`) and inside `people_also_ask` (`people_also_ask_ai_overview_expanded_element`).

### 1.2 Top-level `ai_overview` item fields

| Field | Type | Doc description |
|---|---|---|
| `type` | string | `"ai_overview"` |
| `rank_group` | integer | position within a group of elements with identical `type` values |
| `rank_absolute` | integer | absolute position among all elements in SERP |
| `page` | integer | SERP page number on which the element is located |
| `position` | string | alignment in SERP: `left` or `right` |
| `xpath` | string | XPath of the element |
| `asynchronous_ai_overview` | boolean | `true` = the element is loaded asynchronously; `false` = loaded from cache. "to obtain the content of ai_overview elements, use the `load_async_ai_overview` parameter in the POST request" |
| `markdown` | string | "the text of the ai_overview formatted in the markdown markup language" |
| `items` | array | items present in the element. Each item is one of the sub-element types in 1.3 |
| `references` | array | "additional references relevant to the item; includes references to webpages that may have been used to generate the ai_overview". Items are `ai_overview_reference` (1.4) |
| `rectangle` | object | `x`, `y`, `width`, `height` (integers, pixels). `null` unless `calculate_rectangles` is `true` in the request |

### 1.3 Sub-element types inside `ai_overview.items[]`

The docs list four types for Google Organic. AI Mode adds two more (section 3.3).

**`ai_overview_element`**

| Field | Type | Doc description |
|---|---|---|
| `type` | string | `"ai_overview_element"` |
| `position` | string | `left` / `right` |
| `title` | string | title of the element |
| `text` | string | text or description of the element in SERP |
| `markdown` | string | content of the element in markdown format |
| `links` | array of `link_element` | website links featured in the element: `type` (`"link_element"`), `title` (anchor text), `description`, `url`, `domain` |
| `images` | array of `images_element` | `null` if none. Fields: `type` (`"images_element"`), `alt`, `url`, `image_url` (original resource or DataForSEO storage) |
| `references` | array of `ai_overview_reference` | "references to webpages that were used to generate the ai_overview_element" |

**`ai_overview_video_element`**

| Field | Type | Doc description |
|---|---|---|
| `type` | string | `"ai_overview_video_element"` |
| `position` | string | `left` / `right` |
| `title` | string | title of the element |
| `snippet` | string | additional information for the video |
| `url` | string | URL of the link to the video |
| `domain` | string | domain of the website hosting the video |
| `image_url` | string | thumbnail URL |
| `source` | string | name of the source of the video |
| `date` | string | date published or indexed, e.g. `Apr 26, 2024` |
| `timestamp` | string | UTC `yyyy-mm-dd hh-mm-ss +00:00` |

No `references` array on this type.

**`ai_overview_table_element`**

| Field | Type | Doc description |
|---|---|---|
| `type` | string | `"ai_overview_table_element"` |
| `position` | string | `left` / `right` |
| `markdown` | string | content of the element in markdown format |
| `table` | object | `table_header` (array, header content), `table_content` (array of rows; "each array represents the table row") |
| `references` | array of `ai_overview_reference` | references used to generate the element |

**`ai_overview_expanded_element`**

| Field | Type | Doc description |
|---|---|---|
| `type` | string | `"ai_overview_expanded_element"` |
| `position` | string | `left` / `right` |
| `title` | string | title of the element in SERP |
| `text` | string | additional text of the element in SERP |
| `components` | array | items of type `ai_overview_expanded_component` |

`ai_overview_expanded_component` fields: `type` (`"ai_overview_expanded_component"`), `title`, `text`, `markdown`, `images` (`images_element`, `null` if none), `links` (`link_element`, described as "sitelinks", `null` if none), `references` (`ai_overview_reference`).

Note: on the Organic Live Advanced page, the component's `references` field appears only in the top-level `ai_overview` block. It does not appear in the copy nested in `knowledge_graph`. The AI Mode page and the Labs Historical SERPs page also list it.

### 1.4 `ai_overview_reference`

Used at three levels: `ai_overview.references[]`, `items[].references[]` (element, table) and `components[].references[]`.

| Field | Type | Doc description |
|---|---|---|
| `type` | string | `"ai_overview_reference"` (in one nested place the docs print the type as "object". This is a doc typo) |
| `source` | string | reference source name or title |
| `domain` | string | domain name of the reference |
| `url` | string | reference page URL |
| `title` | string | reference page title |
| `text` | string | "text snippet from the page that was used to generate the ai_overview_element" |

The SERP API reference has no position or rank field. The order of the array is the only position signal, and the docs do not say what that order means (see section 5).

The docs use different wording for the two levels:
- per-element `references` = webpages "that **were used** to generate the ai_overview_element"
- top-level `references` = "**additional** references … that **may have been used** to generate the ai_overview"

The Help Center (parse article) describes the top-level array as listing "every source Google cited", and says per-section references "sit inside each ai_overview_element, so you can attribute citations down to the chunk that triggered them". The docs do not say whether the top-level array is a superset of, or separate from, the per-element arrays.

### 1.5 AI Overview nested in other SERP features

**`knowledge_graph_ai_overview_item`** (an item inside `knowledge_graph.items[]`)
- Fields: `type`, `rank_group`, `rank_absolute`, `page`, `position`, `xpath`, `asynchronous_ai_overview`, `items` (the same element types as 1.3), `references`, `rectangle`.
- For knowledge-graph sub-items, `rank_group` and `rank_absolute` are documented as "always equals 0 for desktop".
- Update post: "currently observed in mobile results".
- Docs: "knowledge_graph items in mobile results may be separated by other elements; in such cases, the API response returns several knowledge_graph elements".

**`people_also_ask_ai_overview_expanded_element`** (inside `people_also_ask.items[].expanded_element[]`)
- Fields: `type`, `items` (`ai_overview_element`, `ai_overview_video_element`, `ai_overview_table_element`, … with the same fields), `references` (`ai_overview_reference`), `asynchronous_ai_overview` ("if true, the people_also_ask_ai_overview_expanded_element element is loaded asynchronously; if false … loaded from cache").
- Extra PAA expansions are a paid option: `people_also_ask_click_depth` 1–4, $0.00015 per click, refunded if fewer clicks happen.

### 1.6 Result-level fields needed for identity

These come from the Advanced result object: `keyword`, `type`, `se_domain`, `location_code`, `language_code`, `check_url`, `datetime` (UTC, "date and time when the result was received"), `spell`, `refinement_chips`, `item_types`, `se_results_count`, `pages_count`, `items_count`, `items`. The task envelope adds `id` (UUID), `cost`, and `data` (an echo of the request, including `device`, `os` and `tag`).

---

## 2. Request parameters that control AI Overview

Sources: Organic Live Advanced, Task POST, Live HTML, Organic overview, AI Overview update post, Knowledge Graph update post, pricing page.

### 2.1 `load_async_ai_overview` (boolean, default `false`)

Doc text: "set to `true` to obtain `ai_overview` items is SERPs even if they are loaded asynchronously; if set to `false`, you will only obtain `ai_overview` items from cache".

| Where documented | Stated extra charge |
|---|---|
| Live Advanced | "charged extra $0.002 for using this parameter" |
| Task POST (Standard) | "charged extra $0.0006 for using this parameter" |
| Organic overview formula | `cost = B * C * K * (D/default)`; `C=2 if "calculate_rectangles": true, or "load_async_ai_overview": true` |
| Pricing page | `"load_async_overview"` (the pricing page's spelling): "Add one base price" |

These all mean the same thing: the base price is charged a second time. Base prices are Standard $0.0006, Priority $0.0012, Live $0.002 per SERP of 10 results. The Task POST page quotes only $0.0006 and does not say what happens with high priority. The docs do not say how the surcharge combines with `depth` above 10.

Refund rule (both pages): "if the element is absent or contains `"asynchronous_ai_overview": false`, all extra charges will be returned to your account balance."

The update post gives these cases:
- `true`, and a cached AI Overview is present: the AIO is returned and the extra charge is refunded.
- `true`, and an asynchronous AIO is retrieved: the data is returned and the extra charge applies.
- `false`, and a cached AIO is present: returned at no extra charge.
- `false`, and an asynchronous AIO is detected: the API returns `ai_overview: null`.

Mechanism (update post): "when set to `true`, the API will make an additional request to retrieve data if an asynchronous AI Overview is detected."

Definitions (update post):
- Synchronous (cached by Google): "immediately available when the search results load … embedded directly within the HTML".
- Asynchronous: "not immediately available in the HTML content when the search results are first loaded … needs more time to generate or retrieve the necessary information".

Help Center (parse article): "without it, you'll see `ai_overview: null` on queries where Google didn't have a cached version ready." The same article recommends `load_async_ai_overview: true` for scheduled presence tracking.

Applies to: Google Organic Live Advanced and Standard Task POST (whose results are read through Task GET Advanced). It is **not** a parameter on the AI Mode endpoints.

### 2.2 `expand_ai_overview` (boolean, default `false`)

- Task POST: "set to true to expand the ai_overview item … Note: this parameter applies only to HTML task results".
- Live HTML documents it with no restriction note.
- It is **not** a parameter on Live Advanced.
- Update post: expands the element "for Standard HTML and Live HTML endpoints at no additional charge … In the responses of Advanced SERP API endpoints, you will always get complete expanded JSON data from this feature."
- The Knowledge Graph update post says the same for `knowledge_graph_ai_overview_item`.

### 2.3 Other parameters that touch AI Overview

- `device`: `desktop` (default) or `mobile`. `os`: `windows`/`macos` for desktop, `android`/`ios` for mobile. The docs give no per-device restriction on `ai_overview` or `load_async_ai_overview`. The only device-specific note is that the knowledge-graph AI Overview is "currently observed in mobile results".
- `calculate_rectangles`: fills `rectangle`. Costs one extra base price (the same ×2 multiplier).
- `people_also_ask_click_depth`: see 1.5.
- Search operators in `keyword` (`site:` and others) multiply the cost by 5. The docs say nothing about how operators affect AIO.

### 2.4 Live vs Standard

Both methods document the same `ai_overview` response fields. Only the price differs:
- Standard normal: about 5 minutes.
- Standard high priority: about 1 minute.
- Live: up to about 6 seconds.

The docs say nothing about the AIO presence rate being different between Live and Standard. Desktop vs mobile presence: not stated in docs beyond the knowledge-graph note.

---

## 3. Google AI Mode SERP endpoint

Sources: AI Mode overview, Live Advanced, Task POST, Task GET Advanced, Languages, AI Mode pricing page, Help Center parse article.

### 3.1 Endpoints

- `POST /v3/serp/google/ai_mode/live/advanced`: one task per call.
- `POST /v3/serp/google/ai_mode/live/html`
- `POST /v3/serp/google/ai_mode/task_post`: up to 100 tasks per call. Then `tasks_ready`, `task_get/advanced/{id}` and `task_get/html/{id}`.
- `GET /v3/serp/google/ai_mode/languages`: free. Returns `language_name` and `language_code` (ISO 639-1).
- Locations: the shared `/v3/serp/google/locations` list. Doc note: "check Google Search Help for the list of countries where AI Mode is currently available."
- Rate limit: 2000 POST+GET calls per minute.

### 3.2 Request parameters

| Param | Notes |
|---|---|
| `keyword` | required, up to 700 chars |
| `location_code` / `location_name` / `location_coordinate` | one is required. Coordinate format is `"lat,lng,zoom"`, zoom 4z–18z, default 9z |
| `language_code` / `language_name` | one is **required** (unlike Organic, where it is optional when the name is given). Uses the AI Mode languages list |
| `device` | `desktop` (default) / `mobile` |
| `os` | `windows`/`macos`, or `android`/`ios` |
| `priority` | Task POST only: 1 normal, 2 high (charged extra) |
| `tag` | up to 255 chars |
| `pingback_url`, `postback_url`, `postback_data` (`advanced`/`html`) | Task POST only |
| `calculate_rectangles` | "the charge per task will be multiplied by 2". Plus `browser_screen_width`, `browser_screen_height`, `browser_screen_resolution_ratio` |

AI Mode has **no** `load_async_ai_overview`, `expand_ai_overview`, `depth` or `people_also_ask_click_depth` parameter. The AI Mode overview page still says "setting depth above the default value will increase the cost … billed for every 20 results for desktop and for every 10 results for mobile", but no `depth` field is documented on the AI Mode Task POST or Live Advanced pages.

### 3.3 Response

Result level: `keyword`, `type`, `se_domain`, `location_code`, `language_code`, `check_url`, `datetime`, `spell`, `refinement_chips`, `item_types` ("possible item types: `ai_overview`"), `se_results_count`, `items_count`, `items`.

`items[]` holds one `ai_overview` object. Its fields are the same as Organic, except that there is **no `asynchronous_ai_overview`**:
`type`, `rank_group`, `rank_absolute`, `page`, `position`, `xpath`, `markdown`, `items`, `references`, `rectangle`.

`items[]` types: `ai_overview_element`, `ai_overview_video_element`, `ai_overview_table_element`, `ai_overview_expanded_element` (the same fields as 1.3), plus two types found only in AI Mode:

**`ai_overview_shopping`**
- Fields: `type`, `position`, `title`, `markdown`, `items[]`.
- `items[]` are `ai_overview_shopping_element`: `product_id`, `data_docid`, `gid`, `title`, `url`, `domain`, `rating` {`rating_type` (Max5/Percents/CustomMax), `value`, `votes_count`, `rating_max`}, `price` {`current`, `regular`, `max_value`, `currency`, `is_price_range`, `displayed_price`}, `seller`, `snippet`, `marketplace`, `marketplace_url`, `image_url`.

**`ai_overview_paid`**
- Fields: `type`, `position`, `text` (intro text before the ads), `markdown`, `items[]`.
- `items[]` are `ai_overview_paid_element`: `title`, `url`, `domain`, `ad_aclk`, `website_name`, `breadcrumb`, `snippet`, `images[]` (`images_element`: `alt`, `url`, `image_url`).

There is a conflict between the Help Center and the docs. The Help Center example shows `ai_overview_shopping_element` directly in `items` with a `products` array. The doc pages show `ai_overview_shopping` with `items[]` of `ai_overview_shopping_element`. Treat the doc pages as the contract, and check this against a real response.

References use the same `ai_overview_reference` shape as Organic.

The Help Center says: "The Google AI Mode Live Advanced endpoint returns content in the same format [as the Organic ai_overview], so anything in the list below applies to both surfaces."

### 3.4 Pricing (AI Mode pricing page)

| Method | Price per SERP page | Turnaround |
|---|---|---|
| Standard (normal) | $0.0012 | 5 minutes ("target turnaround time is 45 minutes. Extended processing may occur") |
| Priority (high) | $0.0024 | up to 1 minute on average |
| Live | $0.004 | up to 6 seconds on average |

Help Center example responses: Organic Live with `load_async_ai_overview` cost $0.0024. An AI Mode Live call cost $0.004.

### 3.5 How AI Mode differs from AI Overview (Help Center parse article)

- AI Mode "lives on a separate surface and cites a different set of sources for the same queries".
- AI Mode "fans the query out into related subqueries, researches each, and synthesizes an answer … The two paths often land on different source sets, so a domain cited in one isn't automatically cited in the other."
- The article recommends pulling both endpoints for each keyword on the same day and diffing the two `references` arrays by domain.

---

## 4. DataForSEO Labs: AI Overview citations

Sources: Labs Ranked Keywords, Historical SERPs, Keyword Overview, Keyword Ideas, Domain/Page Intersection, Competitors Domain, SERP Competitors, Domain Rank Overview, Relevant Pages, Subdomains doc pages (all `/v3/dataforseo_labs/google/<name>/live/`), plus the AIO-references update post, the upgraded-collection update post and both Help Center articles.

### 4.1 Which Labs endpoints accept `ai_overview_reference`

From each endpoint's `item_types` "possible values":

| Endpoint | `item_types` possible values | AIO reference data? |
|---|---|---|
| **Ranked Keywords** | `organic`, `paid`, `featured_snippet`, `local_pack`, **`ai_overview_reference`** (default `["organic","paid"]`) | **Yes** |
| Competitors Domain | `organic`, `paid`, `featured_snippet`, `local_pack` | No |
| SERP Competitors | `organic`, `paid`, `featured_snippet`, `local_pack` | No |
| Domain Intersection | `organic`, `paid`, `featured_snippet`, `local_pack` | No |
| Page Intersection | `organic`, `paid`, `featured_snippet`, `local_pack` | No |
| Relevant Pages | `organic`, `paid`, `featured_snippet`, `local_pack` | No |
| Subdomains | `organic`, `paid`, `featured_snippet`, `local_pack` | No |
| Domain Rank Overview / Historical Rank Overview | no `item_types`. `metrics` has only `organic` and `paid` | No |

So, per the docs as of this date, the only Labs endpoint that returns AIO **citations** is Ranked Keywords. There is no `ai_overview_reference` counter in `serp_competitors`, `competitors_domain` or domain rank metrics.

Rule for using it (Ranked Keywords doc and Help Center): "if the item_types array contains item types that are different from organic, the results will be ordered by the first item type in the array; you will not be able to sort and filter results by the types of search results not included in the response." If you leave `ai_overview_reference` out, you get zero AIO data. The Help Center article from 03.08.2026 uses `"item_types": ["ai_overview_reference"]`. The older update post says `["ai_overview"]`. Follow the doc page: `ai_overview_reference` is the value listed there.

Target format (Help Center): give a domain without `https://` or `www.`, and a page with `https://`. A page given without the protocol is treated as the whole domain.

### 4.2 Ranked Keywords: `metrics.ai_overview_reference`

The result has `metrics` with `organic`, `paid`, `featured_snippet`, `local_pack` and `ai_overview_reference`. Each is `null` unless that type was requested.

| Field | Type | Doc description |
|---|---|---|
| `pos_1`, `pos_2_3`, `pos_4_10`, `pos_11_20`, `pos_21_30`, … `pos_91_100` | integer | "number of ai_overivew references where the target ranks #N" (doc spelling) |
| `etv` | float | estimated traffic volume. The doc copy says "estimated paid monthly traffic", which looks copied from another block |
| `count` | integer | doc copy says "total count of featured snippet items that contain the target" (copied wording). In the Help Center example, `count` equals `total_count` |
| `estimated_paid_traffic_cost` | float | estimated cost of the traffic in USD |
| `is_new`, `is_up`, `is_down`, `is_lost` | integer | counts of ranked elements that are new, went up, went down or were lost |
| `clickstream_etv`, `clickstream_gender_distribution`, `clickstream_age_distribution` | | only with `include_clickstream_data` |

`load_rank_absolute: true` adds `metrics_absolute`, which bins by `rank_absolute` instead of `rank_group`.

### 4.3 Ranked Keywords: `ranked_serp_element.serp_item` of type `ai_overview_reference`

| Field | Type | Doc description |
|---|---|---|
| `se_type` | string | `google` |
| `type` | string | `"ai_overview_reference"` |
| `rank_group` | integer | "position within a group of elements with identical type values" |
| `rank_absolute` | integer | "absolute position among all the elements in SERP" |
| `position` | string | `left` / `right` |
| `source` | string | reference source name or title |
| `domain` | string | domain of the reference |
| `title` | string | reference page title |
| `url` | string | reference page URL |
| `text` | string | snippet used to generate the AIO element |
| `main_domain` | string | primary domain |
| `relative_url` | string | URL without protocol and domain |
| `etv` | float | estimated monthly traffic for this keyword (CTR × search volume) |
| `estimated_paid_traffic_cost` | float | etv × cpc |
| `clickstream_etv` | | only with clickstream |
| `rank_changes` | object | `previous_rank_absolute` (null if new), `is_new`, `is_up`, `is_down`, compared to `previous_updated_time` |
| `backlinks_info` | object | `referring_domains`, `referring_main_domains`, `referring_pages`, `dofollow`, `backlinks`, `time_update` |
| `rank_info` | object | `page_rank`, `main_domain_rank` |

Next to `serp_item`, the `ranked_serp_element` also has `check_url`, `serp_item_types`, `se_results_count`, `keyword_difficulty`, `is_lost`, `last_updated_time` and `previous_updated_time`. Each item also has `keyword_data`: `keyword`, `location_code`, `language_code`, `keyword_info` (search volume, cpc …), `keyword_properties`, `serp_info` and `search_intent_info`.

The docs do not explain what `rank_group` and `rank_absolute` mean for a reference. One Help Center example shows `rank_group: 1, rank_absolute: 3`, and the update post shows `1/1`. The Help Center says each citation comes with "its position within the overview". Whether that is the index in the top-level `references` array or a SERP-wide count is not stated in docs.

The docs do not say how a page cited in several places (top-level and per-element) is counted. They also do not say whether one keyword can return several `ai_overview_reference` rows for the same target.

`historical_serp_mode` (`live` default / `lost` / `all`) applies to all item types, so lost AIO citations can be pulled with `lost`.

### 4.4 `serp_info.serp_item_types` containing `ai_overview`

These endpoints list `ai_overview` among the possible values of `serp_info.serp_item_types`: Keyword Overview, Keyword Ideas, Domain Intersection, Page Intersection and Ranked Keywords (`keyword_data.serp_info`). They add the note "the actual results will be returned only for organic, paid, featured_snippet, and local_pack elements" (Ranked Keywords adds "and ai_overview_reference").

This is a presence flag only: it shows that an AIO was on the stored SERP snapshot, dated by `serp_info.last_updated_time`. The Ranked Keywords `ranked_serp_element.serp_item_types` list on the doc page does not name `ai_overview`, but the Help Center example response contains it.

### 4.5 Labs Historical SERPs

`/v3/dataforseo_labs/google/historical_serps/live` returns past SERP snapshots. They contain the full `ai_overview` object, including `asynchronous_ai_overview`, `markdown`, `items` (element, video, table and expanded element/component) and `references`, with the same fields as section 1.

### 4.6 Async AIO in Labs data

The upgraded-collection update post says Labs and Databases now "retrieve asynchronous AIOs". Earlier data "captured data only for those AIOs that were already cached". The upgrade applies automatically ("no action is required").

Labs endpoints covered: Keyword Overview, Page Intersection, Domain Intersection, Ranked Keywords, Top Searches, Keywords for Categories, Keyword Ideas, Keyword Suggestions, Related Keywords, Keywords for Site and Historical SERPs.

The post date is not shown in the fetched text. So Labs AIO data from before the upgrade under-counts async AIOs.

---

## 5. Practical caveats documented by DataForSEO

- **Appearance rate.** Help Center (03.08.2026): "AI Overviews appear on most Google SERPs." No numeric rate is given. The 2024 update post said Google rolled AIO out to US users in May 2024 and planned to expand globally by the end of that year.
- **Volatility.** Help Center parse article: "Triggers are noisy. The same query can produce a full overview on Monday, nothing on Tuesday, and a different overview with a different source set on Wednesday. A daily pull is the only way to keep up." It also says the two signals move independently: "A page can get cited in an AI Overview for a query where its organic rank is mediocre, and it can hold a strong organic rank without ever getting cited."
- **What to store per run** (Help Center recommendation): whether the overview triggered, the `asynchronous_ai_overview` value, the full `references` array, and a boolean for whether the target domain is in it.
- **Location and language support.**
  - AI Overview: not stated in docs. There is no AIO-specific location or language list, and Organic uses the general Google locations and languages.
  - AI Mode: separate languages list (`/serp/google/ai_mode/languages`). For countries, the docs point to Google Search Help.
- **Async vs cached.** Without `load_async_ai_overview`, an asynchronous AIO comes back as `ai_overview: null`. In that case, whether `item_types` still lists `ai_overview` is not stated precisely. The update post says it is included "regardless of its type" whenever detected.
- **Device.** Desktop vs mobile AIO differences: not stated in docs, apart from the knowledge-graph AIO being "currently observed in mobile results".
- **Ordering of references.** Not stated in docs. The SERP API reference objects have no position field. Labs gives `rank_group`/`rank_absolute` for a reference but does not define them for this type.
- **Personalisation.** AI Mode overview: "user preferences, search history, and other personalized search factors are ignored". `check_url` can be opened in Incognito to verify the result.
- **How to tell if your site is cited.**
  - SERP API: compare `domain` and `url` in `ai_overview.references[]` (and in the nested `references[]` arrays) against your domain and pages. The Help Center describes "a boolean for whether the target domain appears in it".
  - Labs: call Ranked Keywords with `target` = domain or page and `item_types: ["ai_overview_reference"]`. Each returned item is a keyword where the target is cited, and `relative_url` gives the cited page.
  - The docs do not describe how URLs are normalised (fragments, query strings, `#:~:text=` anchors).
- **Labs data age.** Labs SERP data is a snapshot dated by `last_updated_time`, with `previous_updated_time` for the change flags. It is not live.

---

## Data grain and identity notes

These notes help with Postgres design for Meelu. Each fact is from the sources above. Where the docs are silent, the note says so.

**Snapshot identity.**
- One AI Overview snapshot is one `ai_overview` item inside one SERP result.
- The docs give no ID for the AIO itself. A snapshot is identified only by the SERP task: `tasks[].id` (UUID) plus result `keyword`, `location_code`, `language_code`, `se_domain`, `datetime` (UTC fetch time), and the request's `device`/`os` (echoed in `tasks[].data`). The surface is `organic` vs `ai_mode`, from `result.type` or `path`.
- A natural key is (surface, keyword, location_code, language_code, device, os, fetched_at).
- One SERP can hold more than one AIO-like block:
  - the main `ai_overview` (identified by `rank_absolute` / `xpath`)
  - a `knowledge_graph_ai_overview_item`
  - one or more `people_also_ask_ai_overview_expanded_element` (one per expanded PAA question)
  - Store the block kind and its `rank_absolute`/`xpath` if all of them are kept.
- Store "absent" as a row as well: `item_types` without `ai_overview`, or `ai_overview: null`. Presence over time is the main metric. Keep `asynchronous_ai_overview` and whether `load_async_ai_overview` was sent. Without the flag, a null AIO may mean "async, not fetched", not "no AIO".

**References and how they relate to the snapshot.**
- References live at three levels:
  - `ai_overview.references[]`: "additional … may have been used"
  - `items[i].references[]` on `ai_overview_element` and `ai_overview_table_element`: "were used to generate" that element
  - `items[i].components[j].references[]` on expanded components
- The video, shopping and paid elements have no references.
- Order: the SERP API has no position field and the docs do not define the order. If you keep the array index, label it "index in array", not a documented rank. Labs gives a `rank_group`/`rank_absolute` for a cited target, but does not define it for references.
- Dedup by URL: the docs do not say whether one URL can appear at several levels or more than once in one array. The Help Center implies overlap ("per-section references also sit inside each element"). A safe design is:
  - one row per (snapshot, level, element index, reference index)
  - plus a derived unique set per snapshot on a normalised `url`
  - Normalisation rules are not stated in docs.
- Reference fields are all short text: `source`, `domain`, `url`, `title`, `text` (a snippet). There is no date, rank or ID.

**Text-heavy vs structured fields.**
- Text-heavy:
  - `ai_overview.markdown` (the whole answer)
  - per-element `text` and `markdown`
  - expanded-component `text` and `markdown`
  - table `markdown`
  - reference `text` (a quoted snippet)
  - video `snippet`
  - AI Mode shopping and paid `markdown`, `snippet` and `text`
- Structured:
  - `type`, `rank_group`, `rank_absolute`, `page`, `position`, `xpath`, `asynchronous_ai_overview`, `rectangle{x,y,width,height}`
  - `links[]` (`url`, `domain`, `title`, `description`) and `images[]` (`url`, `image_url`, `alt`)
  - reference `url`/`domain`/`title`/`source`
  - `table.table_header`/`table_content` (arrays)
  - video `url`/`domain`/`date`/`timestamp`
  - shopping `product_id`/`gid`/`price{…}`/`rating{…}`
- Note that `links[]` inside an element are separate from `references[]`. They are links shown in the answer text, not citations.

**Tying a citation to keyword × location × language × date.**
- From the SERP API: keyword = result `keyword` (decoded; `spell` shows whether Google autocorrected it), location = `location_code`, language = `language_code`, date = result `datetime` (the fetch time), and device/os from the request echo.
- From Labs Ranked Keywords: keyword, location and language come from `keyword_data` or the result. The date is `ranked_serp_element.last_updated_time` (when the Labs SERP was collected), not the call time. `previous_updated_time` and `rank_changes` describe the change since the previous Labs snapshot. Labs also gives per-citation `etv` and the keyword's `search_volume`, which the SERP API does not.
- Labs AIO rows collected before the async-AIO upgrade may miss async overviews (section 4.6).

**Tying a citation to the user's own pages.**
- SERP API: match the reference `url` (normalised) to the site's page URLs, and the reference `domain` to the site's domain or subdomains. `domain` is the full host (for example `www.semrush.com`), so subdomain handling is your choice.
- Labs: `relative_url` and `main_domain` are given directly for the cited target, which makes the join to a page table by path simple.
- The docs do not say whether reference URLs can include text-fragment anchors or tracking parameters. Organic has a `remove_from_url` request parameter (up to 10 query parameters stripped from result URLs). The docs do not say whether it also applies to `ai_overview_reference.url`.
