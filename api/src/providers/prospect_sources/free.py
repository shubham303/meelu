import re
from html.parser import HTMLParser
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from src.providers.http import vendor_request
from src.providers.prospect_sources.adapter import ProspectSourcesAdapter
from src.providers.prospect_sources.shape import prospect
from src.providers.registry import VendorResponse

MAX_QUERIES = 4


def unwrap_duck_url(href: str | None) -> str | None:
    raw = str(href or "")
    if not raw:
        return None
    absolute = urljoin("https://duckduckgo.com", raw)
    parsed = urlparse(absolute)
    uddg = parse_qs(parsed.query).get("uddg")
    if uddg:
        return unquote(uddg[0])
    return absolute if parsed.scheme.startswith("http") else None


class DuckResultsParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict] = []
        self._current: dict | None = None
        self._field: str | None = None

    def _flush(self) -> None:
        if self._current and self._current["href"]:
            self.results.append(self._current)
        self._current = None
        self._field = None

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = (attrs.get("class") or "").split()
        if "result" in classes:
            self._flush()
            self._current = {"href": None, "title": "", "snippet": ""}
        if self._current is None:
            return
        if "result__a" in classes and self._current["href"] is None:
            self._current["href"] = attrs.get("href")
            self._field = "title"
        elif "result__snippet" in classes:
            self._field = "snippet"

    def handle_endtag(self, tag):
        if tag == "a" and self._field:
            self._field = None

    def handle_data(self, data):
        if self._current is not None and self._field:
            self._current[self._field] += data

    def close(self) -> None:
        super().close()
        self._flush()


class FreeProspectAdapter(ProspectSourcesAdapter):
    id = "meelu-free"
    name = "Meelu free sources"
    capabilities = frozenset({"prospects.web-search", "prospects.hackernews"})
    charges = False

    async def search_prospects(self, source, query):
        if source == "web-search":
            found = await self.web_search(query)
        elif source == "hackernews":
            found = await self.hacker_news(query)
        else:
            raise self.unsupported(f"prospects.{source}")
        return VendorResponse([p for p in found if p])

    @staticmethod
    def queries_of(query: dict) -> list[str]:
        return [q for q in (str(x or "").strip() for x in query.get("queries") or []) if q][
            :MAX_QUERIES
        ]

    async def web_search(self, query):
        queries = self.queries_of(query)
        per_query = max(5, -(-(query.get("limit") or 20) // max(len(queries), 1)))
        out = []
        for q in queries:
            html = await vendor_request(
                self.id,
                "https://html.duckduckgo.com/html/",
                query={"q": q},
                headers={"user-agent": "meelu-api"},
            )
            parser = DuckResultsParser()
            parser.feed(str(html or ""))
            parser.close()
            count = 0
            for result in parser.results:
                if count >= per_query:
                    break
                url = unwrap_duck_url(result["href"])
                title = " ".join(result["title"].split())
                snippet = " ".join(result["snippet"].split())
                if not url or not title:
                    continue
                p = prospect(
                    "web-search",
                    {
                        "name": title,
                        "website": url,
                        "sourceUrl": url,
                        "rawText": f"{title}\n{snippet}",
                    },
                )
                if p:
                    out.append(p)
                    count += 1
        return out

    async def hacker_news(self, query):
        limit = min(query.get("limit") or 20, 30)
        out = []
        for q in self.queries_of(query):
            for tag in ("story", "comment"):
                res = await vendor_request(
                    self.id,
                    "https://hn.algolia.com/api/v1/search",
                    query={"query": q, "tags": tag, "hitsPerPage": limit},
                )
                for hit in (res or {}).get("hits") or []:
                    author = str(hit.get("author") or "").strip()
                    if not author:
                        continue
                    text = re.sub(
                        r"\s+",
                        " ",
                        re.sub(
                            r"<[^>]+>",
                            " ",
                            str(hit.get("comment_text") or hit.get("story_text") or ""),
                        ),
                    ).strip()
                    out.append(
                        prospect(
                            "hackernews",
                            {
                                "name": author,
                                "channelHandles": {"hackernews": author},
                                "sourceUrl": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                                "website": hit.get("url"),
                                "rawText": "\n".join(
                                    s
                                    for s in (
                                        hit.get("title") or hit.get("story_title") or "",
                                        text,
                                    )
                                    if s
                                ),
                            },
                        )
                    )
        return out
