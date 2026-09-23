from src.providers import apify
from src.providers.errors import ProviderRequestError
from src.providers.prospect_sources.adapter import ProspectSourcesAdapter
from src.providers.prospect_sources.shape import handle_from_url, prospect
from src.providers.prospect_sources.sources import source_entry
from src.providers.registry import VendorResponse

MAX_QUERIES = 3

INPUTS = {
    "linkedin": lambda q: {"searchQuery": " ".join(q["queries"]), "maxItems": min(q["limit"], 25)},
    "reddit": lambda q: {
        "searches": q["queries"],
        "searchPosts": True,
        "searchComments": False,
        "sort": "new",
        "time": "month",
        "maxPostCount": q["limit"],
        "maxItems": q["limit"],
        "skipComments": True,
    },
    "x": lambda q: {
        "searchTerms": q["queries"],
        "queryType": "Latest",
        "lang": "en",
        "maxItems": q["limit"],
    },
    "youtube": lambda q: {
        "searchQueries": q["queries"],
        "maxResults": min(q["limit"], 25),
        "maxResultsShorts": 0,
        "maxResultStreams": 0,
    },
    "instagram": lambda q: {
        "search": " ".join(q["queries"]),
        "searchType": "user",
        "resultsLimit": min(q["limit"], 25),
    },
}


def _join(*parts):
    return "\n".join(str(p) for p in parts if p)


NORMALIZERS = {
    "linkedin": lambda i: prospect(
        "apify:linkedin",
        {
            "name": i.get("fullName")
            or i.get("name")
            or " ".join(x for x in (i.get("firstName"), i.get("lastName")) if x),
            "role": i.get("headline") or i.get("position") or i.get("jobTitle"),
            "company": i.get("companyName")
            or (i.get("currentCompany") or {}).get("name")
            or i.get("company"),
            "website": i.get("website"),
            "sourceUrl": i.get("profileUrl") or i.get("url") or i.get("linkedinUrl"),
            "channelHandles": {
                "linkedin": i.get("publicIdentifier")
                or i.get("username")
                or handle_from_url(i.get("profileUrl") or i.get("url"))
            },
            "rawText": _join(
                i.get("headline"), i.get("summary") or i.get("about"), i.get("location")
            ),
        },
    ),
    "reddit": lambda i: prospect(
        "apify:reddit",
        {
            "name": i.get("username") or i.get("author"),
            "channelHandles": {"reddit": i.get("username") or i.get("author")},
            "sourceUrl": i.get("url") or i.get("link"),
            "rawText": _join(i.get("title"), i.get("body")),
        },
    ),
    "x": lambda i: prospect(
        "apify:x",
        {
            "name": (i.get("author") or {}).get("name")
            or (i.get("author") or {}).get("userName")
            or (i.get("author") or {}).get("username"),
            "role": (i.get("author") or {}).get("description"),
            "website": (i.get("author") or {}).get("url") or (i.get("author") or {}).get("website"),
            "channelHandles": {
                "x": (i.get("author") or {}).get("userName")
                or (i.get("author") or {}).get("username")
            },
            "sourceUrl": i.get("url") or i.get("twitterUrl"),
            "rawText": _join(
                (i.get("author") or {}).get("description"), i.get("text") or i.get("fullText")
            ),
        },
    ),
    "youtube": lambda i: prospect(
        "apify:youtube",
        {
            "name": i.get("channelName"),
            "website": i.get("channelUrl"),
            "channelHandles": {
                "youtube": i.get("channelUsername")
                or handle_from_url(i.get("channelUrl"))
                or i.get("channelName")
            },
            "sourceUrl": i.get("url") or i.get("channelUrl"),
            "rawText": _join(i.get("title"), i.get("text") or i.get("description")),
        },
    ),
    "instagram": lambda i: prospect(
        "apify:instagram",
        {
            "name": i.get("fullName") or i.get("username"),
            "website": i.get("externalUrl") or i.get("website"),
            "channelHandles": {"instagram": i.get("username") or i.get("ownerUsername")},
            "sourceUrl": i.get("url")
            or (f"https://www.instagram.com/{i['username']}/" if i.get("username") else None),
            "rawText": _join(i.get("biography") or i.get("bio"), i.get("caption")),
        },
    ),
}


class ApifyProspectAdapter(ProspectSourcesAdapter):
    id = "apify"
    name = "Apify"
    capabilities = frozenset(f"prospects.apify:{p}" for p in INPUTS)

    def configured(self) -> bool:
        return apify.configured()

    async def search_prospects(self, source, query):
        entry = source_entry(source)
        platform = (entry or {}).get("platform")
        build = INPUTS.get(platform)
        normalize = NORMALIZERS.get(platform)
        if not entry or not entry.get("actor") or not build or not normalize:
            raise self.unsupported(f"prospects.{source}")
        queries = [q for q in query.get("queries") or [] if q][:MAX_QUERIES]
        actor_input = build({"queries": queries, "limit": query.get("limit") or 20})
        try:
            run = await apify.run_actor(self.id, entry["actor"], actor_input)
        except ProviderRequestError:
            if not entry.get("backup_actor"):
                raise
            run = await apify.run_actor(self.id, entry["backup_actor"], actor_input)
        found = [normalize(i) for i in run.data if isinstance(i, dict)]
        return VendorResponse([p for p in found if p], run.cost_micros)
