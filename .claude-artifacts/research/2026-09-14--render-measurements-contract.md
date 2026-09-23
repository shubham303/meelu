# Render measurement contract (v2)

Spec that the app renderer (`app/src/main/render/page.js`) produces and the API
(`api/src/render_jobs`, `api/src/technical_seo/rules/render.py`) stores and evaluates.
Derived from `.claude-artifacts/research/2026-09-14--rendered-page-technical-checks.md`.
JSON keys are camelCase on the wire; columns are the snake_case form. Every new
column is nullable or has a zero/false/empty default so existing rows stay valid.
Rules never trust a null: a missing measurement never fires a rule.

## Fields the renderer already sends (unchanged)

pageId, device, renderError, userAgentProfile, renderedFromHash, finalUrl, title,
metaDescription, canonical, h1[], robotsDirectives, wordCount, internalLinks,
schemaTypes[], contentHash, consoleErrors, consoleSamples[], failedRequests,
failedSamples[], blockedAssets, blockedSamples[], jsBytes, totalBytes,
requestCount, thirdPartyHosts[], htmlPath; mobile only: hiddenWordCount,
hiddenInternalLinks, viewportOverflowPx, smallTapTargets.

## New fields, both devices

### Document and settle
| key | type | meaning |
|---|---|---|
| status | int | main-document HTTP status from the network log (null if unknown) |
| documentBytes | int | encodedDataLength of the main document response |
| htmlBytes | int | length in bytes of the captured rendered HTML |
| settleReason | text | `idle` or `timeout` |
| pendingRequests | int | requests with no response when captured |
| pendingSamples | json[] | up to 10 `{url, type}` still pending |
| mainFrameNavigations | int | main-frame navigations after the first response (HTTP redirects count, pushState does not) |
| visibleWordCount | int | words in text nodes whose element is visible (no display:none / visibility:hidden ancestor, non-zero rect) |
| exceptionCount | int | uncaught runtime exceptions (subset of consoleErrors; consoleErrors keeps counting both) |
| soft404Signal | bool | title or any h1 matches `/\b(404|not found|page (doesn't|does not|cannot be) (exist|found)|no longer available|oops)\b/i` |
| serviceWorker | bool | `navigator.serviceWorker.getRegistrations()` non-empty |

### Links
| key | type | meaning |
|---|---|---|
| internalLinkUrls | text[] | distinct rendered same-site link URLs, normalised like the crawler (max 500) |
| externalLinkHosts | text[] | distinct hosts of rendered external links (max 100) |
| uncrawlableAnchors | int | per report (a)6: `a` without href but with onclick/role, `href=""`, `#`, `javascript:`, `file:`, `[role=link]` non-anchors, `[onclick]` matching navigation code; exempt mailto/tel and `a[id]` without href |
| uncrawlableNavAnchors | int | subset inside nav/header/footer/[role=navigation] |
| uncrawlableSamples | json[] | up to 10 `{tag, href, text}` |
| hashbangLinks | int | internal hrefs containing `#!` |
| metaFragment | bool | `meta[name=fragment]` present |
| danglingFragmentLinks | int | internal links to this page's own path with a fragment that matches no element id or `[name]` |
| loadMoreControl | bool | visible button/link/[role=button] text matches `/^(load|show|view|see) more/i`, not inside a form |
| paginationLinks | bool | any `a[href]` matching `/[?&]page=\d+|\/page\/\d+/` or `link[rel=next]` |

### Images and embeds
| key | type | meaning |
|---|---|---|
| images | json[] | rendered `img` with non-zero rect: `{src, alt?}` (max 100), alt omitted when the attribute is absent, `alt: ""` kept |
| imagesWithoutSrc | int | visible img with no src, or data: src with naturalWidth <= 1, or data-src/data-lazy/data-original set and currentSrc empty |
| imagesWithoutSrcAboveFold | int | subset with rect top < innerHeight |
| shadowDomWords | int | words inside shadow roots minus slotted light-DOM words |
| pluginContent | int | embed/object/applet with flash/silverlight/java types or .swf/.flv/.class/.xap sources |

### Metadata after render
| key | type | meaning |
|---|---|---|
| titleCount | int | `title` elements in head (svg titles excluded) |
| descriptionCount | int | `meta[name=description]` count |
| canonicalCount | int | `link[rel=canonical]` count |
| canonicalHrefs | text[] | resolved canonical hrefs in document order (max 10) |
| robotsMetaContents | text[] | content of every `meta[name=robots]` and `meta[name=googlebot]` in order (max 10) |
| schemaBlocks | int | `script[type="application/ld+json"]` count |
| schemaInvalidBlocks | int | blocks where JSON.parse throws |
| schemaHashes | text[] | per parsed node (after `@graph` flatten): `sha256(type + ":" + JSON with sorted keys)` first 16 hex chars (max 60) |
| hreflang | json | `{lang: href}` from rendered `link[rel=alternate][hreflang]` |
| hreflangInvalid | int | rendered hreflang entries whose href is not http(s) or whose language subtag is not 2-3 letters and not x-default |
| socialMetaCount | int | `meta[property^="og:"]` + `meta[name^="twitter:"]` |
| nosnippetCount | int | `[data-nosnippet]` count |
| templateTokensHead | int | matches of `/\{\{[^}]+\}\}|\[\[[^\]]+\]\]/` in title + description + h1 texts |
| templateTokensBody | int | same regex over visible body text |
| viewportMeta | text | content of rendered `meta[name=viewport]` or null |

### Network log derived
| key | type | meaning |
|---|---|---|
| failedDataRequests | int | XHR/Fetch, same registrable domain (or preconnected host), status >= 400 or errorText, excluding paths matching `/collect|beacon|track|log|analytics|pixel/` |
| failedDataSamples | json[] | up to 10 `{url, status?, error?}` |
| failedScripts | int | Script type, same site, status >= 400 or errorText |
| failedScriptSamples | json[] | up to 10 |
| corsErrors | int | console messages matching `/blocked by CORS policy|No 'Access-Control-Allow-Origin'/i` |
| websocketUsed | bool | any WebSocket request in the log |
| mixedContentActive | int | http:// requests of type Script/Stylesheet/XHR/Fetch/Document on an https page |
| mixedContentPassive | int | http:// requests of type Image/Media/Font on an https page |
| largestResourceBytes | int | max encodedDataLength over Script/Stylesheet |
| largestResourceUrl | text | its URL |

## New fields, mobile only (null on desktop rows)
| key | type | meaning |
|---|---|---|
| overlayCoverage | real | 0..1 share of the viewport covered by the largest fixed/sticky/absolute element that `elementFromPoint(center)` resolves into, per report (c)4; 0 when none |
| overlaySample | text | tag#id.class and first 100 chars of its text |
| smallTextRatio | real | characters in visible text under 12px computed font size divided by all visible characters |
| textChars | int | all visible characters counted for the ratio |

## Rules to add (all in `rules/render.py`, issue_type = the device the row belongs to; cross-device rules are issue_type mobile)

Desktop rules read alias `r`, mobile rules alias `m`; a rule that should run on both devices is written twice with a kind prefix `mobile-` for the `m` version. Raw comparisons use `site_pages` columns: title, meta_description, h1, canonical, robots_directives, word_count, out_links (json `{url}`), external_links, images (json `{src, alt}`), hreflang (json), schema_types, has_viewport.

(a) JavaScript dependency and indexability
- soft-404-after-render p0: status 200, soft404Signal, (visibleWordCount < 150 or internalLinks = 0), rendered robots not noindex, raw title/h1 do NOT match the regex.
- rendered-body-empty p0: status 200, visibleWordCount < 30, h1 empty.
- render-exception-with-thin-content p0: exceptionCount >= 1 and (wordCount < raw word_count or wordCount < 100).
- content-lost-after-render p1: wordCount < 0.7 * raw and raw - wordCount >= 100.
- links-lost-after-render p1: lost = raw out_links urls not in internalLinkUrls; lost >= 5 or lost >= 0.2 * raw count.
- uncrawlable-anchors-after-render p1: uncrawlableAnchors >= 3 or uncrawlableNavAnchors >= 1.
- old-ajax-crawling-scheme p1: hashbangLinks >= 1 or metaFragment.
- dangling-fragment-links p2: danglingFragmentLinks >= 5.
- url-changed-by-history-api p1: finalUrl <> site_pages.url and mainFrameNavigations = 0 (client-side-redirect keeps the navigation case: add `and mainFrameNavigations > 0` to it).
- interaction-gated-content p2: loadMoreControl and not paginationLinks.
- images-without-src-after-render p1: imagesWithoutSrcAboveFold >= 1 or (image count > 0 and imagesWithoutSrc >= 0.25 * count).
- shadow-dom-content-unslotted p2: shadowDomWords >= 200.
- service-worker-registered p3: serviceWorker.

(b) Rendering health
- failed-data-request p1: failedDataRequests >= 1.
- failed-first-party-script p1: failedScripts >= 1.
- cors-blocked-request p1: corsErrors >= 1.
- network-never-idle p2: settleReason = timeout and pendingRequests >= 3.
- websocket-transport-used p2: websocketUsed.
- mixed-content-active p1: mixedContentActive >= 1. mixed-content-passive p3: mixedContentPassive >= 1.
- document-over-2mb p0: documentBytes > 2097152. resource-over-2mb p1: largestResourceBytes > 2097152. rendered-html-over-2mb p1: htmlBytes > 2097152.

(c) Mobile usability and parity (mobile / cross-device)
- mobile-status-differs-from-desktop p0: both rendered, r.status is distinct from m.status.
- mobile-final-url-differs-from-desktop p1: r.final_url is distinct from m.final_url.
- viewport-meta-missing p1: m.viewportMeta null or lacks `width=`. viewport-meta-restrictive p2: contains `user-scalable=no|0`, `maximum-scale` < 1, or `initial-scale` < 1.
- mobile-intrusive-overlay p1: m.overlayCoverage >= 0.5. desktop version intrusive-overlay p2 on r if you also collect it on desktop (collect on both; overlay fields become both-device fields).
- mobile-illegible-text p2: smallTextRatio >= 0.4 and textChars >= 200.
- mobile-word-count-drop p1: both rendered, m.visibleWordCount < 0.8 * r.visibleWordCount and difference >= 100.
- mobile-description-differs-from-desktop p1, mobile-h1-differs-from-desktop p2, mobile-schema-differs-from-desktop p1 (schema_types sorted differ or any r.schemaHashes missing from m.schemaHashes).
- mobile-image-alt-differs p3: an image src present in both with different alt, or with alt on desktop and none on mobile.

(e) Structured data and metadata
- schema-changed-by-js p1: any raw schema_types entry missing from rendered schemaTypes; schema-duplicated-after-render p2: a schemaHashes value appears twice.
- schema-invalid-after-render p1: schemaInvalidBlocks >= 1.
- canonical-duplicated-after-render p0 when canonicalHrefs has >= 2 distinct values, p2 when canonicalCount >= 2 and all identical (two kinds: canonical-conflict-after-render p0, canonical-repeated-after-render p2).
- canonical-invalid-after-render p1: rendered canonical not http(s), or resolves to the origin root while the page path is not `/`, and the raw canonical did not have the same defect.
- robots-directives-conflict-after-render p1: robotsMetaContents length >= 2, or one content string contains both a positive (index, follow, all) and a negative (noindex, nofollow, none) directive.
- nofollow-changed-by-js p1: rendered robots contains nofollow/none is distinct from raw.
- title-modified-by-js p1, meta-description-modified-by-js p2, h1-modified-by-js p2: present in both raw and rendered and differ after trim/whitespace collapse (h1 compares the ordered array).
- meta-description-only-after-js p2: raw null, rendered not null.
- title-duplicated-after-render p2: titleCount >= 2. description-duplicated-after-render p2: descriptionCount >= 2.
- hreflang-changed-by-js p2: rendered hreflang json is distinct from raw. hreflang-invalid-after-render p2: hreflangInvalid >= 1.
- unrendered-template-tokens p1: templateTokensHead >= 1; unrendered-template-tokens-body p2: templateTokensBody >= 3.

(f) Links
- js-injected-images-missing-alt p2: a rendered image src not in raw images whose alt attribute is absent.
- external-links-injected-by-js p3: count of externalLinkHosts not present among raw external_links hosts >= 5.
- plugin-content-after-render p3: pluginContent >= 1.

Skipped because the raw crawl does not store the counterpart: viewport-meta-changed-by-js, data-nosnippet-changed-by-js, og-tags-only-after-js. Recorded as backlog.
