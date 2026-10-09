# DataForSEO v3 — SERP API (Google focus)

Researched 2026-10-06 from the live DataForSEO docs and help center. All facts below are from the cited pages. When the docs do not say something, this file says "not stated in docs". AI Overview content is only named here; file `05` covers it in full. AI Optimization / LLM APIs are out of scope.

Base URL: `https://api.dataforseo.com/v3/`. Auth: HTTP Basic (login:password from the API dashboard). All POST bodies are JSON (UTF-8). The body is always an **array of task objects**.

---

## 1. Endpoint map and methods

Sources:
- https://docs.dataforseo.com/v3/serp/overview/
- https://docs.dataforseo.com/v3/serp/google/overview/
- https://docs.dataforseo.com/v3/serp/google/organic/overview/

### 1.1 Functions: Regular, Advanced, HTML

| Function | What it returns | Where it is supported |
|---|---|---|
| **Regular** | Only `organic`, `paid` and `featured_snippet` items (simplified fields). `item_types` still lists every type seen on the page. | Organic search types only (Google, Bing, Yahoo, etc.) |
| **Advanced** | Every SERP feature with full fields (the item catalogue in section 5). | All SERP search engine types |
| **HTML** | Raw HTML of each crawled SERP page. | All Google types except Maps and Search by Image |

### 1.2 Methods: Standard (task queue) vs Live

- **Live**: one request, result in the response. One task per call. Highest price.
- **Standard**: `task_post` first, then collect with `task_get` (or receive by postback / pingback). Cheaper. Has two priorities: `priority: 1` (normal, default) and `priority: 2` (high, extra cost).

### 1.3 Google Organic endpoints

| Purpose | Method + URL |
|---|---|
| Live Regular | `POST /v3/serp/google/organic/live/regular` |
| Live Advanced | `POST /v3/serp/google/organic/live/advanced` |
| Live HTML | `POST /v3/serp/google/organic/live/html` |
| Set tasks (Standard) | `POST /v3/serp/google/organic/task_post` |
| List completed tasks | `GET /v3/serp/google/organic/tasks_ready` (also `GET /v3/serp/$se/tasks_ready` and `GET /v3/serp/tasks_ready` for all SERP tasks) |
| Get Regular result | `GET /v3/serp/google/organic/task_get/regular/$id` |
| Get Advanced result | `GET /v3/serp/google/organic/task_get/advanced/$id` |
| Get HTML result | `GET /v3/serp/google/organic/task_get/html/$id` |
| Locations | `GET /v3/serp/google/locations` and `GET /v3/serp/google/locations/$country` |
| Languages | `GET /v3/serp/google/languages` |

One `task_post` is not tied to one function. You collect the same task id with `task_get/regular`, `/advanced` or `/html`. The `tasks_ready` result gives `endpoint_regular`, `endpoint_advanced`, `endpoint_html` for each task (null where the function is not supported).

Sandbox: `https://sandbox.dataforseo.com/v3/serp/google/organic/task_get/advanced/00000000-0000-0000-0000-000000000000` returns every Advanced item type with dummy data, free (https://docs.dataforseo.com/v3/serp/google/organic/task_get/advanced/). This is the fastest way to get a full fixture for schema design.

### 1.4 Personalisation and device

From the overview pages: "user preferences, search history, and other personalized search factors are ignored". You can check a result by opening `check_url` in incognito. Devices: desktop (OS `windows`, `macos`) and mobile (OS `android`, `ios`). Google News, Images, Search by Image and Jobs are desktop only.

---

## 2. Request parameters — Google Organic

Sources:
- https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/
- https://docs.dataforseo.com/v3/serp/google/organic/task_post/
- https://docs.dataforseo.com/v3/serp/google/organic/live/regular/
- https://docs.dataforseo.com/v3/serp/google/organic/live/html/

Column key: **LA** = Live Advanced, **LR** = Live Regular, **LH** = Live HTML, **TP** = Task POST. "Y" means the doc page lists the parameter.

### 2.1 Location, language, query

| Param | Type | Rules / limits / default | LA | LR | LH | TP |
|---|---|---|---|---|---|---|
| `keyword` | string | **Required.** Up to 700 characters. `%##` is decoded; `+` becomes space (send `%25` for `%`, `%2B` for `+`). If it contains search operators (`allinanchor:`, `allintext:`, `allintitle:`, `allinurl:`, `cache:`, `define:`, `definition:`, `filetype:`, `id:`, `inanchor:`, `info:`, `intext:`, `intitle:`, `inurl:`, `link:`, `site:`) the charge is multiplied by 5. The cost help article says `cache:` now returns a validation error. Returned in results with `%##` decoded. | Y | Y | Y | Y |
| `location_code` | integer | Required unless `location_name` or `location_coordinate` is given. Example `2840` (United States). From the locations endpoint. | Y | Y | Y | Y |
| `location_name` | string | Required unless `location_code` / `location_coordinate`. Example `London,England,United Kingdom`. | Y | Y | Y | Y |
| `location_coordinate` | string | `"latitude,longitude,radius"`. Max 7 decimal digits for lat/long. Radius min 199, max 199999 (unit shown as "mm" in docs). Example `53.476225,-2.243572,200`. | Y | Y | Y | Y |
| `language_code` | string | ISO 639-1 such as `en`. Live Advanced page marks it "optional if you specify language_name"; Task POST page marks it "required if you don't specify language_name". | Y | Y | Y | Y |
| `language_name` | string | Example `English`. | Y | Y | Y | Y |
| `se_domain` | string | Optional. Chosen automatically from location + language. Override example `google.co.uk`, `google.de`. | Y | Y | Y | Y |
| `url` | string | Direct Google search URL; the API parses it into fields. Docs say it is the hardest method to process and do not recommend it. `lr`, `cr`, `as_qdr`, `as_sitesearch`, `as_occt`, `as_filetype` are unset if present. | Y | Y | Y | Y |
| `search_param` | string | Extra Google URL query parameters. Same six parameters (`lr`, `cr`, `as_qdr`, `as_sitesearch`, `as_occt`, `as_filetype`) are not supported and are unset. | Y | Y | Y | Y |

### 2.2 Device and browser

| Param | Type | Rules / default | LA | LR | LH | TP |
|---|---|---|---|---|---|---|
| `device` | string | `desktop` or `mobile`. Default `desktop`. | Y | Y | Y | Y |
| `os` | string | Desktop: `windows` (default) or `macos`. Mobile: `android` (default) or `ios`. | Y | Y | Y | Y |
| `calculate_rectangles` | boolean | Default `false`. Fills `rectangle` (pixel position) on Advanced items. **Paid** (see section 7). | Y | – | – | Y |
| `browser_screen_width` | integer | 240–9999. Default 1920 desktop, 360 android, 375 iOS. Needs `calculate_rectangles: true`. | Y | – | – | Y |
| `browser_screen_height` | integer | 240–9999. Default 1080 desktop, 640 android, 812 iOS. Needs `calculate_rectangles: true`. | Y | – | – | Y |
| `browser_screen_resolution_ratio` | integer (docs say integer; range is 0.5–3) | Default 1 desktop, 3 android, 3 iOS. Needs `calculate_rectangles: true`. | Y | – | – | Y |

### 2.3 Depth and crawl control

| Param | Type | Rules / default | LA | LR | LH | TP |
|---|---|---|---|---|---|---|
| `depth` | integer | Number of results. Default **10**. Max **200** on Live pages, **700** on Task POST. Billed per SERP page of up to 10 results; depth is rounded up to the next 10. If depth is higher than what Google returns, the difference is refunded (help center + pricing update). | Y | Y | Y | Y |
| `max_crawl_pages` | integer | Number of SERP pages to crawl. Max 100. Charged per page crawled (10 organic results per page). "max_crawl_pages and depth complement each other" (exact interaction: see help center, not detailed on the endpoint page). | Y | Y | Y | Y |
| `stop_crawl_on_match` | array of objects | Up to 10 target objects `{match_type, match_value}`. The response contains results up to and including the first match. Billed for every SERP page crawled until the condition is met. | Y | Y | Y | Y |
| ↳ `match_type` | string | Required inside the object. `domain` (exact domain or subdomain), `with_subdomains` (domain + subdomains), `wildcard`. | | | | |
| ↳ `match_value` | string | Required. Domain without protocol, or wildcard such as `/blog/post-*`. | | | | |
| `target_search_mode` | string | Needs `stop_crawl_on_match`. `any` (default; stop when any target is found) or `all` (stop only when all are found). | Y | Y | Y | Y |
| `find_targets_in` | array | Needs `stop_crawl_on_match`. Which item types to check. Default: all first-level items that have `url` and `domain`. Values: `organic`, `paid`, `local_pack`, `featured_snippet`, `events`, `google_flights`, `images`, `jobs`, `knowledge_graph`, `local_service`, `map`, `scholarly_articles`, `third_party_reviews`, `twitter`. Must not overlap with `ignore_targets_in`. | Y | Y | Y | Y |
| `ignore_targets_in` | array | Needs `stop_crawl_on_match`. Same value list. Item types to skip. | Y | Y | Y | Y |
| `target` | string | Live pages only (not listed on Task POST). Domain, subdomain or page, without `https://` and `www.`. Results only include elements that have a `url`. Wildcards: `example.com` = home page; `example.com*` = whole domain; `*example.com*` = domain + subdomains; `*example.com` = home page on any subdomain; `example.com/page` = exact URL; `example.com/page*` = URL prefix. | Y | Y | Y | – |

### 2.4 Result shaping

| Param | Type | Rules / default | LA | LR | LH | TP |
|---|---|---|---|---|---|---|
| `group_organic_results` | boolean | Default `true`: a `related_result` (another result from the same domain) is nested inside its parent organic item. `false`: each related result is returned as its own `organic` item. **This changes organic `rank_group` / `rank_absolute` counts.** | Y | Y | – | Y |
| `remove_from_url` | array | Up to 10 URL query parameters to strip from result URLs, for example `["srsltid"]`. If `target` is set, they are removed before matching. | Y | – | – | Y |
| `people_also_ask_click_depth` | integer | 1–4. Clicks on the People Also Ask box to load more `people_also_ask_element` items. **$0.00015 per click** (any priority). Refunded if PAA is absent or fewer clicks were made. Supported in Google Organic Advanced Task POST and Live (per https://dataforseo.com/update/click-depth-for-paa-in-serp-api). | Y | – | – | Y |
| `load_async_ai_overview` | boolean | Default `false`. `true` waits for an AI Overview that Google loads asynchronously; `false` returns AI Overviews only from cache. **Paid**: endpoint pages state extra $0.002 (Live) / $0.0006 (Task POST, normal priority); refunded if the AI Overview is absent or `asynchronous_ai_overview` is false. See file 05. | Y | – | Y | Y |
| `expand_ai_overview` | boolean | Default `false`. Expands the AI Overview. "Applies only to HTML task results." Cost not stated in docs. See file 05. | – | – | Y | Y |

### 2.5 Task POST only (Standard method)

| Param | Type | Rules |
|---|---|---|
| `priority` | integer | `1` normal (default), `2` high (extra cost). |
| `tag` | string | Up to 255 characters. Your own id. Echoed in `tasks[].data.tag`. Also available on Live endpoints. |
| `pingback_url` | string | When the task completes, DataForSEO sends a **GET** to this URL. `$id` and `$tag` placeholders are replaced (tag is URL-encoded). Special characters are URL-encoded (`#` → `%23`). |
| `postback_url` | string | When the task completes, DataForSEO sends a **POST** with the results, **gzip-compressed**. Same `$id` / `$tag` placeholders. |
| `postback_data` | string | Required with `postback_url`. `regular`, `advanced` or `html`: which function's result to send. |

Postback / pingback rules (Task POST page, Tasks Ready page):
- If your server does not respond within **10 seconds**, the connection is dropped and the task moves to the Tasks Ready list.
- A task with `postback_url` appears in Tasks Ready **only if** the delivery failed (your server returned an HTTP code below 200 or above 300).
- Retry schedule for failed postbacks: not stated in docs. (A "Webhook Resend" appendix endpoint exists in the docs menu; not researched here.)

### 2.6 Limits on requests

- Up to **2000 API calls per minute** in total (POST and GET). Contact support to raise it.
- Task POST: up to **100 tasks per call**; tasks beyond 100 return error `40006`.
- Live: **one task per call** (`40000` if more).
- Tasks Ready: **20 calls per minute**, up to **1000 tasks** per call, tasks completed within the **previous 3 days**. Collected tasks and tasks older than 3 days are not listed. Docs recommend postbacks/pingbacks if you collect over 1000 tasks per minute because the ready queue updates with a small delay.
- Simultaneous requests: max **30** per user (error `40209`, https://docs.dataforseo.com/v3/appendix/errors/).
- Live task processing timeout: **120 seconds** (error `50401`).

---

## 3. Response envelope

Sources:
- https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/
- https://docs.dataforseo.com/v3/serp/google/organic/task_get/advanced/
- https://docs.dataforseo.com/v3/serp/google/organic/task_post/

HTTP status is always **200** except 401, 402, 404, 500. Real status lives in `status_code` at the top level and per task.

```
{
  version         string   API version, e.g. "0.1.20200129"
  status_code     integer  general status (20000 = ok)
  status_message  string
  time            string   execution time, e.g. "0.3059 sec."
  cost            float    total cost of all tasks in this call, USD
  tasks_count     integer
  tasks_error     integer  number of tasks that returned an error
  tasks: [
    {
      id              string   UUID of the task (key for task_get, postbacks)
      status_code     integer  10000–60000 (20000 ok, 20100 task created, 40xxx/50xxx errors)
      status_message  string
      time            string
      cost            float    cost of this task, USD
      result_count    integer  number of elements in result[]
      path            array    URL path, e.g. ["v3","serp","google","organic","advanced","live"]
      data            object   echo of the request params, plus "api","function","se","se_type"
                               (example: {"api":"serp","function":"live","se":"google","se_type":"organic",
                                "language_name":"English","location_name":"United States","keyword":"...",
                                "tag":"tag2","device":"desktop","os":"windows"})
      result: [ ... ]          null for task_post responses
    }
  ]
}
```

### 3.1 `result[]` for Advanced (Live Advanced / task_get Advanced)

| Field | Type | Meaning |
|---|---|---|
| `keyword` | string | Keyword as received, `%##` decoded. |
| `type` | string | Search engine type from the POST (e.g. `organic`). |
| `se_domain` | string | Google domain used, e.g. `google.com`. |
| `location_code` | integer | Location used. |
| `language_code` | string | Language used. |
| `check_url` | string | Direct Google URL to verify the result. |
| `datetime` | string | When the result was received, UTC, format `"yyyy-mm-dd hh-mm-ss +00:00"`, e.g. `2019-11-15 12:57:46 +00:00`. |
| `spell` | object or null | Google autocorrection: `keyword` (corrected keyword; results are for this keyword) and `type` (`did_you_mean`, `showing_results_for`, `no_results_found_for`, `including_results_for`). |
| `refinement_chips` | object or null | `type: "refinement_chips"`, `xpath`, `items[]` of `refinement_chips_element` {`type`, `title`, `url`, `domain`, `options[]`}. Each option is `refinement_chips_option` {`type`, `title`, `url`, `domain`}. |
| `item_types` | array of string | Every item type found on the SERP (see list below). |
| `se_results_count` | integer | Google's "about N results" total. |
| `pages_count` | integer | Number of SERP pages retrieved. |
| `items_count` | integer | Number of items in `items[]`. |
| `items` | array | The SERP items (section 5). |

`item_types` possible values (Google Organic Advanced, as listed): `answer_box`, `app`, `carousel`, `multi_carousel`, `featured_snippet`, `google_flights`, `google_reviews`, `third_party_reviews`, `images`, `jobs`, `knowledge_graph`, `local_pack`, `hotels_pack`, `map`, `organic`, `paid`, `people_also_ask`, `related_searches`, `people_also_search`, `shopping`, `top_stories`, `twitter`, `video`, `events`, `recipes`, `top_sights`, `scholarly_articles`, `popular_products`, `questions_and_answers`, `find_results_on`, `stocks_box`, `commercial_units`, `local_services`, `google_hotels`, `math_solver`, `currency_box`, `product_considerations`, `short_videos`, `refine_products`, `perspectives`, `discussions_and_forums`, `compare_sites`, `ai_overview`.

### 3.2 `result[]` for Regular

Same header fields (`keyword` … `items_count`, including `refinement_chips` and `item_types`). `items[]` only contains three types, each with: `type`, `rank_group`, `rank_absolute`, `page`, `domain`, `title`, `description`, `url`, `breadcrumb`.
- `featured_snippet`: `breadcrumb` always null.
- `organic`, `paid`: as above.
- Note from docs: in Regular, `rank_absolute` values are "returned in ascending order, with values corresponding to advanced SERP features omitted". So gaps in `rank_absolute` are where Advanced-only features sit.

Source: https://docs.dataforseo.com/v3/serp/google/organic/live/regular/

### 3.3 `result[]` for HTML

`keyword`, `type`, `se_domain`, `location_code`, `language_code`, `datetime`, `items_count`, `items[]` where each item is one page: `page` (integer, serial number of the HTML page), `date` (when the page was scanned, UTC), `html` (string, full HTML).

Sources: https://docs.dataforseo.com/v3/serp/google/organic/live/html/, https://docs.dataforseo.com/v3/serp/google/organic/task_get/html/

### 3.4 Tasks Ready `result[]`

`id`, `se`, `se_type`, `date_posted` (UTC), `tag`, `endpoint_regular`, `endpoint_advanced`, `endpoint_html`. Free.

Source: https://docs.dataforseo.com/v3/serp/google/organic/tasks_ready/

---

## 4. Ranking fields — how to read them

Sources:
- https://docs.dataforseo.com/v3/serp/google/overview/
- https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/

Fields shared by almost every first-level Advanced item:

| Field | Type | Meaning |
|---|---|---|
| `type` | string | Item type. |
| `rank_group` | integer | Position among items with the **same `type`** (organic #1, #2 …). Items of other types are not counted. |
| `rank_absolute` | integer | Position among **all** items on the SERP. |
| `page` | integer | Which SERP page (1-based) the item is on. |
| `position` | string | Alignment: `left` (main column) or `right` (side panel, e.g. desktop knowledge graph). |
| `xpath` | string | XPath of the element in the page HTML. |
| `rectangle` | object or null | `{x, y, width, height}` in pixels, origin is the top-left corner of the screen. Null unless `calculate_rectangles: true`. |

Nested elements (inside `items[]` of a feature) generally have **no** `rank_group` / `rank_absolute`. Their order is the array order. Exceptions: the knowledge graph sub-items carry `rank_group` / `rank_absolute`, which "always equals 0 for desktop".

Pixel ranking ("distance between the result snippet and top of the SERP page") is available only via `calculate_rectangles` on Google Organic Advanced (plus News and Search by Image).

---

## 5. Advanced SERP item catalogue (Google Organic)

Source for this whole section: https://docs.dataforseo.com/v3/serp/google/organic/live/advanced/ (the task_get Advanced page lists the same types: https://docs.dataforseo.com/v3/serp/google/organic/task_get/advanced/).

Shorthand used below:
- **[R]** = the common ranking block: `type`, `rank_group`, `rank_absolute`, `page`, `position`, `xpath`, `rectangle`.
- **rating** = `{rating_type ("Max5" | "Percents" | "CustomMax"), value (float), votes_count (int), rating_max (int)}`, null if none.
- **price** = `{current (float), regular (float), max_value (float), currency (ISO), is_price_range (bool), displayed_price (string, raw)}`, null if none.
- **images_element** = `{type: "images_element", alt, url, image_url}`. `image_url` may point to DataForSEO storage when the original is not available.
- **link_element** = `{type: "link_element", title, description, url, domain}` (some contexts also have `ad_aclk`, `snippet`, `xpath`).
- **table** = `{table_header: [..], table_content: [[..], ..]}`.
- **checks** = array of true properties. Values: `is_image`, `is_video`, `is_featured_snippet`, `amp_version`, `is_malicious`, `is_web_story`, `is_highly_cited`. Null if none.
- `timestamp` fields are UTC `"yyyy-mm-dd hh-mm-ss +00:00"`.

### 5.1 Core web results

**`organic`** — [R] plus:
- `domain`, `title`, `url`, `description`, `breadcrumb`, `website_name`
- `cache_url`, `related_search_url`
- `pre_snippet` (text before the description), `extended_snippet` (text after it), `highlighted` (array of bold words)
- `is_image`, `is_video`, `is_featured_snippet`, `is_malicious`, `is_web_story` (each documented with "this check no longer appears in SERP")
- `amp_version` (bool)
- `images` (array of images_element or null)
- `rating`, `price`
- `links` (sitelinks: array of link_element or null)
- `faq` (deprecated, always null), `about_this_result` (deprecated, always null)
- `extended_people_also_search` (array of related queries shown after the user clicks the result and returns)
- `timestamp` (publication date of the result)
- `related_result` (array; only when `group_organic_results: true`): each `{type: "related_result", xpath, domain, title, url, cache_url, related_search_url, breadcrumb, is_image, is_video, checks, description, pre_snippet, extended_snippet, images, amp_version, rating, price, highlighted, about_this_result, timestamp, rectangle}`. No own rank fields.

**`paid`** (ads) — [R] plus: `title`, `domain`, `website_name`, `description`, `url`, `breadcrumb`, `is_image`, `is_video`, `checks`, `images`, `highlighted`, `extra` {`ad_aclk` (ad id)}, `description_rows` (array or null), `links` (link_element with `ad_aclk`), `price`, `rating`.

**`featured_snippet`** — [R] plus: `domain`, `title`, `featured_title` (title of the source page), `description`, `timestamp`, `url`, `images` (images_element[]), `table` (or null).

**`answer_box`** — [R] plus: `text` (array of strings or null), `links` (link_element[] or null).

### 5.2 Questions and related queries

**`people_also_ask`** — [R] plus `items[]` of:
- **`people_also_ask_element`**: `type`, `title` (the question), `seed_question` ("question that triggered additional expanded elements"; null in the example for first-level questions), `xpath`, `expanded_element[]`.
  - `expanded_element[]` holds one of:
    - **`people_also_ask_expanded_element`**: `featured_title`, `url`, `domain`, `title`, `description`, `images` (images_element[]), `timestamp`, `table`.
    - **`people_also_ask_ai_overview_expanded_element`**: an AI-generated answer with `items[]` (ai_overview_element, ai_overview_video_element, ai_overview_table_element, ai_overview_expanded_element), `references[]` (ai_overview_reference {source, domain, url, title, text}), `asynchronous_ai_overview`. Full structure: file 05.
- PAA expansion: with `people_also_ask_click_depth` 1–4, more `people_also_ask_element` items are added to the same `items[]`. The docs describe added questions only as "additional people_also_ask_element items"; how many each click adds is not stated in docs. The `seed_question` field is the only documented link between a loaded question and the one that triggered it.

**`related_searches`** — [R] plus `items` (array of **plain strings**, e.g. `["iphone xr","iphone 11", ...]`).

**`people_also_search`** — [R] plus `title`, `items` (array of plain strings).

**`questions_and_answers`** — [R] plus `items[]` of `questions_and_answers_element` {`url`, `question_text`, `answer_text`, `source`, `domain`, `votes`}.

**`discussions_and_forums`** — [R] plus `title`, `items[]` of `discussions_and_forums_element` {`title`, `url`, `domain`, `source`, `description`, `timestamp`, `posts_count`}.

**`perspectives`** — [R] plus `title`, `items[]` of `perspectives_element` {`title`, `description`, `url`, `domain`, `date` (e.g. "13 hours ago"), `source`, `timestamp`}.

**`find_results_on`** — [R] plus `items[]` of `find_results_on_element` {`title`, `domain`, `url`, `source`}.

**`compare_sites`** — [R] plus `title`, `items[]` of `compare_sites_element` {`title`, `url`, `domain`, `image_url`, `source`}.

### 5.3 Knowledge graph

**`knowledge_graph`** — [R] plus: `title`, `subtitle`, `description`, `card_id`, `url`, `image_url`, `logo_url`, `cid` (Google client id of a local business), `items[]`.

Docs note: on **mobile**, knowledge graph parts may be separated by other elements; then the response contains **several `knowledge_graph` items**, each with distinct sub-items, each placed where it appears.

Sub-items in `items[]` (each has `type`, `rank_group`, `rank_absolute` — both "always 0 for desktop" — `page`, `position`, `xpath`, `rectangle`):

| Sub-item type | Extra fields |
|---|---|
| `knowledge_graph_images_item` | `link` (link_element + `snippet`, `xpath`), `items[]` of `knowledge_graph_images_element` {`url`, `domain`, `alt`, `image_url`, `xpath`} |
| `knowledge_graph_list_item` | `title`, `data_attrid` (Google attribute id, e.g. `action:listen_artist`), `link`, `items[]` of `knowledge_graph_list_element` {`title`, `subtitle`, `url`, `domain`, `image_url`, `xpath`} |
| `knowledge_graph_ai_overview_item` | `asynchronous_ai_overview`, `items[]` (AI overview elements, `references[]`). See file 05. |
| `knowledge_graph_description_item` | `text`, `links[]` (link_element + `snippet`, `xpath`) |
| `knowledge_graph_row_item` | `title`, `data_attrid` (e.g. `ss:/webfacts:net_worth`), `text`, `links[]` |
| `knowledge_graph_carousel_item` | `title`, `data_attrid`, `link`, `items[]` of `knowledge_graph_carousel_element` {`title`, `subtitle`, `url`, `domain`, `image_url`, `xpath`} |
| `knowledge_graph_part_item` | `title`, `data_attrid`, `text`, `links[]` |
| `knowledge_graph_expanded_item` | `title`, `data_attrid`, `expanded_element[]` of `knowledge_graph_expanded_element` {`featured_title`, `url`, `domain`, `title`, `snippet`, `timestamp`, `images`, `table` (with `table_element`)} |
| `knowledge_graph_shopping_item` | `title`, `data_attrid`, `items[]` of `knowledge_graph_shopping_element` {`title`, `url`, `domain`, `price`, `source`, `snippet`, `marketplace`, `marketplace_url`} |
| `knowledge_graph_hotels_booking_item` | `title`, `date_from`, `date_to`, `data_attrid`, `items[]` of `knowledge_graph_hotels_booking_element` {`source`, `description`, `url`, `domain`, `price`, `is_paid`} |

### 5.4 News, media and social

**`top_stories`** — [R] plus `title`, `items[]` of `top_stories_element` {`source`, `domain`, `title`, `date` (published), `amp_version`, `timestamp`, `url`, `image_url`, `badges` (array)}.

**`images`** — [R] plus `title`, `url`, `items[]` of `images_element` {`alt`, `url` (original image URL), `image_url` (compressed copy on DataForSEO storage)}, `related_image_searches` (deprecated, always null).

**`video`** — [R] plus `items[]` of `video_element` {`source`, `title`, `timestamp`, `url`}.

**`short_videos`** — [R] plus `title`, `items[]` of `short_videos_element` {`title`, `url`, `domain`, `source`}.

**`twitter`** — [R] plus `title`, `url`, `items[]` of `twitter_element` {`tweet`, `date`, `timestamp`, `url`}.

**`carousel`** — [R] plus `title`, `items[]` of `carousel_element` {`title`, `subtitle`, `image_url`}. No URLs.

**`multi_carousel`** — [R] plus `items[]` of `multi_carousel_element` {`title`, `multi_carousel_snippets[]` of `multi_carousel_snippet` {`title`, `subtitle`, `image_url`}}. No URLs.

**`scholarly_articles`** — [R] plus `title`, `url`, `items[]` of `scholarly_articles_element` {`title`, `url`, `author`, `description`}.

### 5.5 Local and travel

**`local_pack`** — [R] plus `title`, `description`, `domain`, `phone`, `booking_url`, `url`, `is_paid`, `rating`, `cid`. Each business in the pack is **its own first-level `local_pack` item** (no nested items).

**`map`** — [R] plus `title`, `url`.

**`local_services`** — [R] plus `title`, `url`, `domain`, `items[]` of `local_services_element` {`title`, `url`, `domain`, `description`, `rating`, `profile_image_url`}.

**`google_reviews`** — [R] plus `reviews_count`, `rating`, `place_id`, `feature`, `cid`.

**`third_party_reviews`** — [R] plus `reviews_count`, `title` (review source name), `url`, `rating`.

**`hotels_pack`** — [R] plus `title`, `date_from`, `date_to`, `items[]` of `hotels_pack_element` {`price`, `title`, `desription` (sic), `hotel_identifier`, `domain`, `url`, `is_paid`, `rating`}.

**`google_hotels`** — [R] plus `hotel_identifier`, `url`, `cid`.

**`google_flights`** — [R] plus `title`, `url`, `items[]` of `google_flights_element` {`description`, `url`}.

**`top_sights`** — [R] plus `title`, `items[]` of `top_sights_element` {`title`, `url`, `description`, `rating`}.

**`events`** — [R] plus `title`, `url`, `items[]` of `events_element` {`title`, `snippet`, `url`}.

**`jobs`** — [R] plus `title`, `url`, `items[]` of `jobs_element` {`title`, `description`, `location`, `author`, `job_posted_time`, `timestamp`, `contract_type`, `salary`, `url`}.

**`recipes`** — [R] plus `items[]` of `recipes_element` {`title`, `url`, `domain`, `source`, `description`, `time`, `rating`}.

### 5.6 Shopping and commerce

**`shopping`** — [R] plus `title`, `items[]` of `shopping_element` {`title`, `price`, `source`, `description`, `marketplace`, `marketplace_url`, `url`, `rating`}.

**`popular_products`** — [R] plus `title`, `items[]` of `popular_products_element` {`title`, `url`, `domain`, `description`, `more_sellers`, `seller`, `image_url`, `price`, `rating`, `product_identifiers` {`product_id`, `data_docid`, `gid`}}.

**`commercial_units`** — [R] plus `title`, `items[]` of `commercial_units_element` {`title`, `url`, `domain`, `price`, `source`, `rating`}.

**`refine_products`** — [R] plus `title`, `items[]` of `refine_products_element` {`title`, `image_url`, `keyword`, `refine_type`, `xpath`}.

**`product_considerations`** — [R] (`position` documented as `left` only) plus `title`, `items[]` of `product_considerations_element` {`title`, `consideration_category`, `expanded_element[]`}. Expanded elements are either `product_considerations_expanded_element` {`title`, `featured_title`, `breadcrumb`, `snippet`, `domain`, `url`, `timestamp`, `related_searches`, `about_this_result` (deprecated)} or `product_considerations_ai_overview_expanded_element` (AI overview shape, file 05).

**`app`** — [R] plus `items[]` of `app_element` {`description`, `title`, `url`, `price`}.

### 5.7 Utility boxes

**`stocks_box`** — [R] plus `title`, `source`, `snippet`, `price`, `url`, `domain`, `table`, `graph` {`items[]` and `previous_items[]` of `graph_element` {`date` (ISO 8601), `value`}}.

**`currency_box`** — [R] plus `value`, `converted_value`, `currency`, `converted_currency`, `timestamp`, `table`, `graph` (same shape as stocks_box).

**`math_solver`** — [R] plus `title`, `result`, `items[]` of `math_solver_element` {`title`, `expanded_element[]` of `math_solver_expanded_element` {`title`, `solution` (array)}}, `links` (link_element[]).

### 5.8 AI Overview

**`ai_overview`** — [R] plus `asynchronous_ai_overview` (bool), `markdown`, `items[]` (`ai_overview_element`, `ai_overview_video_element`, `ai_overview_table_element`, `ai_overview_expanded_element`) and `references[]` (`ai_overview_reference` {source, domain, url, title, text}). **Full detail in `05-ai-overview.md`.** Note that AI overview content also appears nested inside `people_also_ask`, `knowledge_graph` and `product_considerations`.

---

## 6. Other Google SERP types and Bing / YouTube (brief)

### 6.1 Google Autocomplete

Sources: https://docs.dataforseo.com/v3/serp/google/autocomplete/live/advanced/, https://docs.dataforseo.com/v3/serp/google/autocomplete/task_post/

- Endpoints: `POST /v3/serp/google/autocomplete/live/advanced`, `task_post`, `tasks_ready`, `task_get` (Advanced only; `postback_data` can only be `advanced`).
- Params: `keyword` (≤700), `location_code`/`location_name`, `language_code`/`language_name`, `cursor_pointer` (integer ≥ 0; cursor position inside the keyword; default = end of keyword; changes suggestions), `client` (`chrome`, `chrome-omni`, `gws-wiz`, `gws-wiz-serp`, `safari`, `firefox`, `psy-ab`, `toolbar`, `youtube`, `gws-wiz-local`, `img`, `products-cc`), `tag`. Task POST adds `priority`, `pingback_url`, `postback_url`, `postback_data`. No `depth`, no `device`.
- `item_types`: `autocomplete` only. Each item: `type: "autocomplete"`, `rank_group`, `rank_absolute`, `relevance` (500–2000, only `chrome`/`chrome-omni`), `suggestion`, `suggestion_type` (only `chrome`/`chrome-omni`), `search_query_url`, `thumbnail_url` (only `gws-wiz`, `gws-wiz-serp`), `highlighted` (only `gws-wiz`, `psy-ab`, `gws-wiz-local`).

### 6.2 Google Maps

Source: https://docs.dataforseo.com/v3/serp/google/maps/live/advanced/

- Live Advanced + Standard (task_post / task_get advanced). No HTML function.
- `depth` default **100**, max **700**; billed per SERP of up to 100 results. Mobile returns only 20 results per SERP.
- `location_coordinate` format is `"latitude,longitude,zoom"` (zoom 3z–21z, default 17z). Extra params: `search_this_area` (default true), `search_places` (default true), `max_crawl_pages`, `url`, `se_domain`, `os`, `tag`.
- `item_types`: `maps_search`, `maps_paid_item`. A `maps_search` item has `rank_group`, `rank_absolute`, `domain`, `title`, `original_title`, `url`, `contact_url`, `contributor_url`, `book_online_url`, `rating`, `rating_distribution`, `snippet`, `address`, `address_info` {borough, address, city, zip, region, country_code}, `place_id`, `phone`, `main_image`, `total_photos`, `category`, `additional_categories`, `category_ids`, `work_hours`, `feature_id`, `cid`, `latitude`, `longitude`, `is_claimed`, `local_justifications`, `is_directory_item`, `price_level`, `hotel_rating`.

### 6.3 Google Local Finder

Source: https://docs.dataforseo.com/v3/serp/google/local_finder/live/advanced/

- `depth` default 10, max 100 on the Live page (help center says Local Finder is billed per 20 results on desktop and per 10 on mobile). Unused depth is refunded.
- `location_coordinate` is `"latitude,longitude,zoom"` (zoom 4z–18z, default 9z). Extra filters: `min_rating` (desktop 3.5/4/4.5; mobile 2–4.5), `time_filter` (`open_now`, `24_hours`, `monday`, `tuesday;18`, …).
- `item_types`: `local_pack` only, same fields as the organic `local_pack` (`title`, `description`, `domain`, `phone`, `booking_url`, `url`, `is_paid`, `rating`, `cid`). `rectangle` is always null here.

### 6.4 Google News

Source: https://docs.dataforseo.com/v3/serp/google/news/live/advanced/

Desktop only (`os` windows/macos). `depth` default 10, max 200 on the Live page; the help center says News is billed per 100 results. Supports `max_crawl_pages`, `search_param`, `calculate_rectangles` (doubles the price for News: "two base prices") and the browser screen params. `item_types`: `top_stories`, `news_search`. A `news_search` item has `rank_group`, `rank_absolute`, `xpath`, `domain`, `title`, `url`, `image_url`, `snippet`, `time_published`, `timestamp`, `rectangle`. `top_stories` has nested `top_stories_element` {source, domain, title, date, amp_version, timestamp, url, image_url}.

### 6.5 Google Images

Source: https://docs.dataforseo.com/v3/serp/google/images/live/advanced/

Desktop only. `depth` default 100, max 200, billed per 100 results. Supports `max_crawl_pages`, `search_param`, `url`, `location_coordinate`. `item_types`: `carousel`, `images_search`, `related_searches`. An `images_search` item has `rank_group`, `rank_absolute`, `xpath`, `title`, `subtitle`, `alt`, `url` (page hosting the image), `source_url` (the image file), `encoded_url` (Google cached copy). `calculate_rectangles` is not available, so `rectangle` is always null.

### 6.6 Bing Organic

Source: https://docs.dataforseo.com/v3/serp/bing/organic/live/advanced/

Same endpoint pattern as Google (`/v3/serp/bing/organic/...`: live regular/advanced/html, task_post, tasks_ready, task_get). Own locations and languages lists (`/v3/serp/bing/locations`, `/v3/serp/bing/languages`). `depth` default 10, max 200 (Live). Supports `device`, `os`, `target`, `tag` and others. `item_types`: `answer_box`, `carousel`, `events`, `featured_snippet`, `hotels_pack`, `images`, `jobs`, `local_pack`, `map`, `organic`, `paid`, `people_also_ask`, `people_also_search`, `questions_and_answers`, `recipes`, `related_searches`, `shopping`, `top_stories`, `video`, `ai_overview`. The Bing `organic` item has the same field set as Google `organic` (rank fields, `domain`, `title`, `url`, `breadcrumb`, `website_name`, `description`, `links`, etc.). Billed per 10 results.

### 6.7 YouTube Organic

Source: https://docs.dataforseo.com/v3/serp/youtube/organic/live/advanced/

`POST /v3/serp/youtube/organic/live/advanced` (+ Standard). Uses `block_depth` (default 20, max 200; billed per 20 results) instead of `depth`. Params: `keyword`, location, language, `device`, `os`, `tag`, `search_param`. `item_types`: `youtube_channel`, `youtube_video`, `youtube_video_paid`, `youtube_playlist`. Items carry `rank_group`, `rank_absolute`, plus `block_rank` (position among blocks) and `block_name` (e.g. "People also watched"). `youtube_video` fields include `title`, `url`, `video_id`, `thumbnail_url`, `channel_id`, `channel_name`, `channel_url`, `description`, `badges`, `is_live`, `is_shorts`, `is_movie`, `views_count`, `publication_date`, `timestamp`, `duration_time`.

---

## 7. Pricing

Sources:
- https://dataforseo.com/help-center/serp-api-cost-explained (updated 02.07.2026)
- https://dataforseo.com/pricing/serp/google-organic-serp-api
- https://dataforseo.com/update/organic-serp-api-pricing-changes-now-in-effect
- https://dataforseo.com/update/google-organic-serp-api-critical-updates-depth
- https://docs.dataforseo.com/v3/serp/google/organic/overview/

### 7.1 Base price per SERP page (Google Organic, 1 page = 10 results)

| Method / priority | Turnaround | Base price | Per 1M SERP pages |
|---|---|---|---|
| Standard, normal priority (`priority: 1`) | ~5 min on average (guaranteed: 45 min) | **$0.0006** | $600 |
| Standard, high priority (`priority: 2`) | up to 1 min on average | **$0.0012** | $1,200 |
| Live | up to 6 s on average | **$0.002** | $2,000 |

Only `task_post` and Live calls cost money. `tasks_ready`, `task_get`, locations, languages and errors endpoints are free.

### 7.2 Billing unit per search type ("default depth")

| Billed per | Search types |
|---|---|
| 10 results | Organic (Google, Bing, Yahoo, Baidu, Seznam), Google Jobs, Events |
| 100 results | Google News, Images, Search by Image, Maps |
| 20 desktop / 10 mobile | Google Local Finder |
| 20 results | YouTube organic and comments, Google Dataset Search |
| 15 results | Naver |
| 40 results | Ads Search |

`depth` is rounded up to the next unit. If you ask for more than Google returns, the difference is refunded.

### 7.3 Depth above default — two statements that do not agree

- Help center + Google Organic pricing page + 2025-09-13 depth update: cost is linear, **base × (depth / 10)**. Example: depth 100 at Standard normal = $0.006; Live ~ $0.02.
- Pricing update effective **2025-09-19 10:00 UTC** (organic results of Google, Bing, Yahoo, Baidu, Seznam, Naver): "Base price (1st page) + 0.75 × Base price × Number of additional pages". On that formula depth 100 at Standard normal = 0.0006 + 0.75 × 0.0006 × 9 = $0.00465.

Which one is billed today is not resolved by the docs. Use `tasks[].cost` from each response as the source of truth.

Background (2025-09-13 update): Google dropped `&num=100`; it now returns 10 results per page, so 100 results means 10 page fetches. Default `depth` became 10.

### 7.4 Paid parameters

| Parameter | Cost |
|---|---|
| Search operator in `keyword` (`site:`, `intitle:`, …) | Base × 5. Standard $0.003, High $0.006, Live $0.01. Supported in Google Organic, Maps, News, Images. |
| `calculate_rectangles: true` | Google Organic: **+1 base price** (Standard $0.0012 total, High $0.0024, Live $0.004). News and Search by Image: +2 base prices. The Organic overview page still shows an older multiplier formula (C = 2); the help center and the 2025-09-19 update say "adds one base price". |
| `load_async_ai_overview: true` | +1 base price (pricing page: "Add one base price"; endpoint pages: +$0.002 Live, +$0.0006 Task POST). Refunded if no async AI overview. |
| `people_also_ask_click_depth` | +$0.00015 per click, any priority. Refunded for clicks not made. |
| `expand_ai_overview` | Cost not stated in docs. |
| `stop_crawl_on_match` / `max_crawl_pages` | No surcharge; you pay for each page crawled. |

Combined formula (help center): `cost = B × K × (D / default) + C`, where B = base price, K = 5 if operators, D = depth rounded up (or pages from `max_crawl_pages`), C = +B if `calculate_rectangles`. Example from help center: Standard high priority, `calculate_rectangles: true`, `depth: 15` → 0.0012 × (20/10) + 0.0012 = **$0.0036**.

---

## 8. Result retention

| What | How long | Source |
|---|---|---|
| `task_get/regular/$id`, `task_get/advanced/$id` | **30 days**, free | task_get regular / advanced pages |
| `task_get/html/$id` | **7 days**, free | https://docs.dataforseo.com/v3/serp/google/organic/task_get/html/ |
| Tasks Ready list | tasks completed in the **last 3 days** that were not yet collected | tasks_ready page |
| After expiry | error `40403` "results expired" (task created more than a month ago) | errors page |
| Live results | Not stored for later retrieval per the docs (no task_get for Live is described). Store them yourself. | Live pages |

Image URLs on `api.dataforseo.com/cdn/i/...` appear in results; how long DataForSEO keeps those images is not stated in docs.

---

## 9. Status codes worth handling

Source: https://docs.dataforseo.com/v3/appendix/errors/

HTTP: 401 (bad credentials), 402 (billing problem), 404 (endpoint not found), 500 (server error). Everything else is HTTP 200 with a `status_code`.

| Code | Meaning | Suggested handling |
|---|---|---|
| 20000 | OK | Process result. |
| 20100 | Task created | Task POST accepted; store `id`. |
| 40000 | Only one task allowed (Live) | Bug in caller. |
| 40006 | More than 100 tasks in one POST | Split batches. |
| 40101 | Search engine returned an error | Retry later. |
| 40102 | No search results | Store as an empty snapshot, do not retry blindly. |
| 40103 | Task execution failed | Resubmit. |
| 40105 | Task deleted | Give up on that id. |
| 40106 | Partial results (some pages failed after retries; not charged for missing pages) | Keep what came back; mark snapshot partial. |
| 40200 / 40210 | Payment required / insufficient funds | Stop and alert. |
| 40201 | Account paused for unusual activity | Stop and alert. |
| 40202 | Rate limit (2000/min) exceeded | Back off. |
| 40203 | Cost limit exceeded (dashboard setting) | Stop and alert. |
| 40205 / 40206 | Duplicate task limit per hour / per day | Dedupe on your side. |
| 40207 | IP not whitelisted | Config. |
| 40209 | More than 30 simultaneous requests | Lower concurrency. |
| 40401 | Task not found | Check id / path. |
| 40403 | Results expired | Re-post if still needed. |
| 40501 / 40503 / 40506 | Invalid field / invalid POST structure / unknown fields | Bug in caller. |
| 40505 | Outdated location parameters | Refresh locations list. |
| 40601 / 40602 | Task handed / task in queue | Not ready yet; poll again. |
| 50000 / 50001 | Internal error / balance check error | Retry, then contact support. |
| 50301 | Third-party source unavailable | Retry later. |
| 50303 | Update in progress | Retry in a few minutes. |
| 50401 | Live task timed out (120 s) | Retry. |

---

## 10. Locations and languages

Sources: https://docs.dataforseo.com/v3/serp/google/locations/, https://docs.dataforseo.com/v3/serp/google/languages/

- `GET /v3/serp/google/locations` (optionally `/$country` with ISO code, e.g. `us`). Free. Result rows: `location_code` (int), `location_name` (e.g. `"Lower Austria,Austria"`), `location_code_parent` (int; parent location), `country_iso_code`, `location_type` (e.g. `Country`, `State`). CSV downloads exist for Google, Bing, Yahoo, YouTube (Google list last updated 2026-09-01).
- `GET /v3/serp/google/languages`. Free. Rows: `language_name`, `language_code` (ISO 639-1).
- All locations in Russia and Belarus are no longer supported.
- Bing and YouTube have their own `/locations` and `/languages` endpoints.

---

## 11. Data grain and identity notes

These notes restate what the docs say in a form useful for a Postgres design. They do not add facts beyond the cited pages.

### 11.1 What identifies a SERP snapshot

A snapshot is one task result (`tasks[i].result[0]`). Its identity is:

- `keyword` (as returned, `%##` decoded) — note `spell.keyword` may differ; results are for the corrected keyword when `spell` is set.
- search engine + type: `data.se` (`google`) and `data.se_type` / `result.type` (`organic`).
- `se_domain` (e.g. `google.com`, can be overridden).
- location: `location_code` (or `location_coordinate` if you used coordinates; the result echoes `location_code`).
- `language_code`.
- `device` and `os` (only in `tasks[].data`, not in `result`).
- `datetime` (UTC time the SERP was fetched).
- Request knobs that change content and should be stored with the snapshot: `depth` / `max_crawl_pages` / `stop_crawl_on_match`, `group_organic_results`, `calculate_rectangles` and browser size, `people_also_ask_click_depth`, `load_async_ai_overview`, `search_param`, `target` (filters items), `remove_from_url` (alters URLs).
- DataForSEO's own handle: `tasks[].id` (UUID). Useful for idempotency and refetch within 30 days; not a natural key.
- `tag` is yours and is echoed in `data.tag`.
- Snapshot-level metrics: `se_results_count`, `pages_count`, `items_count`, `item_types`, `check_url`, `refinement_chips`, `spell`, and `tasks[].cost`.

### 11.2 How items relate to a snapshot

- `items[]` is a flat list of first-level features. Order them by `rank_absolute` (1 = top of the page across all features). `rank_group` is the position within the same `type` (e.g. organic #3). `page` says which SERP page the item came from.
- `position` (`left`/`right`) separates the main column from the side panel; desktop knowledge graph sits on the right.
- Nested arrays hang off a first-level item and have **no own rank** except knowledge graph sub-items (rank fields always 0 on desktop). Array order is the only order. Key nested arrays: `organic.links` (sitelinks), `organic.related_result`, `organic.images`, `people_also_ask.items[].expanded_element[]`, `knowledge_graph.items[]`, `top_stories.items`, `video.items`, `short_videos.items`, `discussions_and_forums.items`, `perspectives.items`, `local_services.items`, `shopping.items`, `popular_products.items`, `ai_overview.items[]` and `references[]`.
- `local_pack` businesses are separate first-level items, each with its own `rank_group`.
- On mobile, one knowledge graph can be split into **several** `knowledge_graph` items.
- `group_organic_results: false` turns `related_result` entries into extra `organic` items, which shifts organic `rank_group`. Pick one setting and keep it fixed across snapshots, or record it.
- Regular results omit Advanced features, so their `rank_absolute` has gaps; do not mix Regular and Advanced snapshots in one rank series without noting the function.
- `xpath` locates the element in the HTML of that fetch only.
- `rectangle` exists only when `calculate_rectangles` was true and depends on the browser size params.

### 11.3 Item types that carry URLs that could match the user's own pages

First-level `url` + `domain`: `organic`, `paid`, `featured_snippet`, `local_pack` (business website), `third_party_reviews` (review source URL), `map`, `twitter`, `google_flights`, `jobs`, `events`, `scholarly_articles`, `images` (`url`), `google_hotels`, `local_services`, `knowledge_graph` (`url`), `stocks_box`.

Nested `url` + `domain` worth matching:
- `organic.links[]` (sitelinks) and `organic.related_result[]` — often the user's own deeper pages.
- `people_also_ask_element.expanded_element[].url` — the page that answers a PAA question.
- `top_stories_element`, `video_element`, `short_videos_element`, `discussions_and_forums_element`, `perspectives_element`, `find_results_on_element`, `compare_sites_element`, `questions_and_answers_element`, `recipes_element`, `top_sights_element`, `scholarly_articles_element`, `popular_products_element`, `commercial_units_element`, `shopping_element`, `local_services_element`, `knowledge_graph_*_element`, `product_considerations_expanded_element`.
- `answer_box.links[]`, `math_solver.links[]`.
- AI overview `references[]` and `links[]` (file 05).

The docs' own list for target matching (`find_targets_in`) is: `organic`, `paid`, `local_pack`, `featured_snippet`, `events`, `google_flights`, `images`, `jobs`, `knowledge_graph`, `local_service`, `map`, `scholarly_articles`, `third_party_reviews`, `twitter`. By default, matching checks "all first-level elements with url and domain fields".

Items with **no** URL (cannot map to a page): `carousel`, `multi_carousel`, `related_searches` (strings), `people_also_search` (strings), `refine_products` (has a `keyword`, no URL), `currency_box`, `math_solver` (result only; links optional).

URL caveats: Google adds tracking parameters such as `srsltid`; `remove_from_url` strips up to 10 named parameters. Normalisation beyond that is not done by the API.

### 11.4 Volatile fields (change between fetches without a ranking change)

- `datetime`, `tasks[].id`, `time`, `cost`, `version`.
- `xpath` (depends on Google's DOM), `rectangle` (depends on layout and browser size).
- `check_url`, `refinement_chips[].url` (contain session parameters such as `sca_esv`, `ved`, `uds`).
- `image_url` on DataForSEO storage (`api.dataforseo.com/cdn/i/<task-id>:<n>`) — tied to the task.
- `cache_url`, `related_search_url`, `ad_aclk` (ad click id).
- `se_results_count` (Google's estimate).
- Relative dates such as `date: "13 hours ago"` in `perspectives` / `top_stories`; prefer `timestamp`.
- `description`, `pre_snippet`, `extended_snippet`, `highlighted` (Google rewrites snippets).
- `asynchronous_ai_overview` and all AI overview content.
- Fields marked deprecated always return null: `faq`, `about_this_result`, `related_image_searches`; the `is_*` booleans are documented as "no longer appears in SERP" — use `checks` where present.

### 11.5 Stable-ish identifiers in items

- Local businesses: `cid`, `place_id`, `feature_id` (Maps).
- Hotels: `hotel_identifier`.
- Knowledge graph: `card_id`, `data_attrid` on sub-items.
- Products: `product_identifiers.product_id`, `gid`, `data_docid`.
- YouTube: `video_id`, `channel_id`.
- Organic/paid: no item id from DataForSEO; identity is the `url` (normalised) within a snapshot.
