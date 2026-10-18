from datetime import UTC, datetime, timedelta

from src.providers.social_search.actors import SearchQuery, facebook, linkedin, reddit, x
from src.providers.social_search.apify import ACTORS, posted_since
from src.providers.social_search.shape import iso_date

QUERY = SearchQuery(keywords=["seo audit"], since=None, per_keyword=20)


def test_every_platform_has_primary_then_fallback():
    order = [(a.platform, a.actor_id) for a in ACTORS]
    for platform, primary, fallback in [
        ("reddit", "harshmaur~reddit-scraper-pro", "fatihtahta~reddit-scraper-search-fast"),
        (
            "x",
            "kaitoeasyapi~twitter-x-data-tweet-scraper-pay-per-result-cheapest",
            "codeperfection~x-twitter-scraper",
        ),
        (
            "linkedin",
            "harvestapi~linkedin-post-search",
            "apimaestro~linkedin-posts-search-scraper-no-cookies",
        ),
    ]:
        ids = [actor for p, actor in order if p == platform]
        assert ids == [primary, fallback]


def test_reddit_harshmaur():
    assert reddit.harshmaur_input(QUERY)["maxPostsCount"] == 20
    out = reddit.harshmaur_post(
        {
            "id": "t3_1x0n36u",
            "parsedId": "1x0n36u",
            "title": "Best SEO audit tool?",
            "body": "Looking for one",
            "postUrl": "https://www.reddit.com/r/SEO/comments/1x0n36u/best/",
            "authorName": "amg",
            "parsedCommunityName": "SEO",
            "upVotes": 4,
            "commentsCount": 2,
            "dataType": "post",
            "createdAt": "2026-10-08T10:08:29.000Z",
        }
    )
    assert out["id"] == "1x0n36u"
    assert out["author"]["handle"] == "amg"
    assert out["context"]["subreddit"] == "SEO"
    assert out["engagement"] == {"score": 4, "comments": 2, "views": None}
    assert reddit.harshmaur_post({"dataType": "comment", "postUrl": "u", "body": "b"}) is None


def test_reddit_fatihtahta():
    out = reddit.fatihtahta_post(
        {
            "kind": "post",
            "id": "1x0n36u",
            "title": "Best SEO audit tool?",
            "body": "",
            "author": "amg",
            "score": 3,
            "num_comments": 1,
            "subreddit": "SEO",
            "created_utc": "2026-10-08T10:08:29.000Z",
            "url": "https://www.reddit.com/r/SEO/comments/1x0n36u/best/",
        }
    )
    assert out["text"] == "Best SEO audit tool?"
    assert out["engagement"]["comments"] == 1


def test_x_kaito_parses_twitter_dates_and_since():
    q = SearchQuery(keywords=["seo audit"], since="2026-10-01T00:00:00Z", per_keyword=20)
    assert x.kaito_input(q)["searchTerms"] == ["seo audit since:2026-10-01"]
    out = x.kaito_post(
        {
            "type": "tweet",
            "id": "2108136095179243850",
            "url": "https://x.com/MadLabs/status/2108136095179243850",
            "text": "SEO audits matter",
            "likeCount": 5,
            "replyCount": 1,
            "viewCount": 40,
            "createdAt": "Thu Oct 08 10:03:07 +0000 2026",
            "author": {"userName": "MadLabs", "name": "SEOptimizers"},
            "entities": {"hashtags": [{"text": "SEO"}]},
        }
    )
    assert out["createdAt"].startswith("2026-10-08T10:03:07")
    assert out["author"] == {"handle": "MadLabs", "displayName": "SEOptimizers"}
    assert out["context"]["tags"] == ["SEO"]


def test_x_codeperfection():
    out = x.codeperfection_post(
        {
            "id": "1",
            "url": "https://x.com/a/status/1",
            "text": "hello",
            "created_at": "2026-10-08T10:03:07+00:00",
            "like_count": 2,
            "reply_count": 0,
            "view_count": 9,
            "hashtags": ["SEO"],
            "author": {"username": "a", "name": "A"},
        }
    )
    assert out["engagement"]["views"] == 9


def test_linkedin_harvest_and_maestro():
    q = SearchQuery(
        keywords=["seo audit", "crawl"],
        since=(datetime.now(UTC) - timedelta(days=3)).isoformat(),
        per_keyword=20,
    )
    assert linkedin.harvest_input(q)["postedLimit"] == "week"
    assert linkedin.maestro_input(q)["keyword"] == '"seo audit" OR crawl'
    assert linkedin.maestro_input(q)["date_filter"] == "past-week"
    assert linkedin.maestro_input(q)["total_posts"] == 40
    assert linkedin.harvest_input(q)["maxPosts"] == 20

    harvested = linkedin.harvest_post(
        {
            "type": "post",
            "id": "7513897409467486208",
            "linkedinUrl": "https://www.linkedin.com/posts/x-activity-7513897409467486208",
            "content": "SEO audit tips",
            "author": {"publicIdentifier": "safiya1611", "name": "Safiya Banu"},
            "postedAt": {"timestamp": 1791452743880},
            "engagement": {"likes": 3, "comments": 0},
        }
    )
    assert harvested["author"]["handle"] == "safiya1611"
    assert harvested["engagement"]["score"] == 3

    maestro = linkedin.maestro_post(
        {
            "activity_id": "7513897409467486208",
            "post_url": "https://www.linkedin.com/posts/x-activity-7513897409467486208",
            "text": "SEO audit tips",
            "author": {"name": "Safiya Banu"},
            "posted_at": {"timestamp": 1791452743880},
            "stats": {"total_reactions": 3, "comments": 1},
        }
    )
    assert maestro["createdAt"] == harvested["createdAt"]


def test_posted_since_drops_older_posts():
    posts = [
        {"id": "new", "createdAt": iso_date("2026-10-08T00:00:00Z")},
        {"id": "old", "createdAt": iso_date("2026-09-01T00:00:00Z")},
    ]
    assert [p["id"] for p in posted_since(posts, "2026-10-01")] == ["new"]


def test_cost_estimate_floors_lagging_result_events():
    from src.providers.apify import ChargeEvents, _event_estimate_micros

    run = {
        "pricingInfo": {
            "pricingPerEvent": {
                "actorChargeEvents": {
                    "apify-actor-start": {"eventPriceUsd": 0.00005},
                    "post": {"eventPriceUsd": 0.002},
                }
            }
        },
        "chargedEventCounts": {"apify-actor-start": 1, "post": 0},
    }
    charges = ChargeEvents(result="post", start="apify-actor-start")
    assert _event_estimate_micros(run, charges, 5) == 10_050


def test_caps_are_per_keyword():
    q = SearchQuery(keywords=["a b", "c d", "e f"], since=None, per_keyword=25)
    assert q.run_cap() == 75
    assert reddit.harshmaur_input(q)["maxPostsCount"] == 25
    assert reddit.fatihtahta_input(q)["maxPosts"] == 25
    assert x.kaito_input(q)["maxItems"] == 25
    assert x.codeperfection_input(q)["maxTweets"] == 25
    assert x.codeperfection_input(q)["maxTotalTweets"] == 75


def test_facebook_scraper_one():
    q = SearchQuery(keywords=["wordpress slow"], since="2026-10-08T00:00:00Z", per_keyword=25)
    assert facebook.scraper_one_input(q) == {
        "query": "wordpress slow",
        "resultsCount": 25,
        "searchType": "latest",
        "startDate": "2026-10-08",
    }
    out = facebook.scraper_one_post(
        {
            "url": "https://www.facebook.com/groups/784025789158373/permalink/2160015128226092/",
            "postId": "2160015128226092",
            "timestamp": 1792663967000,
            "postText": "A slow WordPress site can have problems",
            "reactionsCount": 1,
            "commentsCount": 1,
            "isReshare": False,
            "author": {"id": "1", "name": "Yasin BusinessDev"},
        }
    )
    assert out["id"] == "2160015128226092"
    assert out["title"] is None
    assert out["author"] == {"handle": "Yasin BusinessDev", "displayName": "Yasin BusinessDev"}
    assert out["engagement"] == {"score": 1, "comments": 1, "views": None}
    assert out["createdAt"] == "2026-10-22T10:12:47+00:00"


def test_facebook_identity_uses_post_id():
    from src.providers.social_search.identity import post_key

    for url in (
        "https://www.facebook.com/permalink.php?story_fbid=pfbid02Ka7&id=1",
        "https://www.facebook.com/stella512/posts/pfbid02yDStsc2aAo8",
    ):
        assert post_key("facebook", "10163020137237023", url) == "facebook:10163020137237023"


def test_bluesky_reads_the_handle_from_the_post_url():
    from src.providers.social_search.actors import bluesky

    parsed = bluesky.lexis_post(
        {
            "url": "https://bsky.app/profile/quadweb.bsky.social/post/3mxtsss27os2s",
            "text": "our traffic dropped",
            "createdAt": "2026-10-17T10:00:00Z",
        }
    )
    assert parsed["author"]["handle"] == "quadweb.bsky.social"
