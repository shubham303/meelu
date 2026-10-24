def test_facebook_identity_uses_post_id():
    from src.providers.social_search.identity import post_key

    for url in (
        "https://www.facebook.com/permalink.php?story_fbid=pfbid02Ka7&id=1",
        "https://www.facebook.com/stella512/posts/pfbid02yDStsc2aAo8",
    ):
        assert post_key("facebook", "10163020137237023", url) == "facebook:10163020137237023"


def test_bluesky_post_builds_the_web_url_from_the_record_uri():
    from src.providers.social_search.meelu_public import bluesky_post

    out = bluesky_post(
        {
            "uri": "at://did:plc:abc/app.bsky.feed.post/3myaaxh3yikro",
            "author": {"handle": "rustybrick.com", "displayName": "Barry Schwartz"},
            "record": {"text": "our traffic dropped", "createdAt": "2026-10-19T13:45:40.930Z"},
            "likeCount": 3,
            "replyCount": 1,
        }
    )
    assert out["url"] == "https://bsky.app/profile/rustybrick.com/post/3myaaxh3yikro"
    assert out["author"] == {"handle": "rustybrick.com", "displayName": "Barry Schwartz"}
    assert out["engagement"]["score"] == 3
    assert out["createdAt"] == "2026-10-19T13:45:40.930000+00:00"


def test_web_found_posts_key_on_the_id_in_their_url():
    from src.providers.social_search.identity import post_key

    assert (
        post_key("reddit", None, "https://www.reddit.com/r/SaaS/comments/1abcde/which_seo_tool/")
        == "reddit:1abcde"
    )
    assert (
        post_key("x", None, "https://x.com/someone/status/1849000000000000000")
        == "x:1849000000000000000"
    )
    assert (
        post_key(
            "linkedin",
            None,
            "https://www.linkedin.com/posts/jane-doe_seo-activity-7254000000000000000-abcd",
        )
        == "linkedin:7254000000000000000"
    )
