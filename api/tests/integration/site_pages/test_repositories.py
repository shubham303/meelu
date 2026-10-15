import uuid

import pytest

from src.core.database import unit_of_work
from src.core.ids import uid
from src.profile.models.user import User
from src.site_pages.llm_extraction.repository import site_page_llm_extractions
from src.site_pages.models.site_page_llm_extraction import SitePageLlmExtraction
from src.site_pages.repositories.chunks import site_chunks
from src.site_pages.repositories.links import site_page_links
from src.site_pages.repositories.pages import site_pages
from src.site_pages.schemas import SitePageCrawlItem
from src.site_pages.schemas.links import NewSitePageLink
from src.sites.models.site import Site


@pytest.fixture
async def seeded():
    user_id = uid("usr")
    site_id = uid("site")
    async with unit_of_work() as db:
        db.add(
            User(
                id=user_id,
                email=f"{uuid.uuid4().hex[:12]}@example.com",
            )
        )
        await db.flush()
        db.add(Site(id=site_id, user_id=user_id, domain="example.com", name="Example"))
        await db.flush()
        refs = await site_pages.upsert_many(
            db,
            user_id,
            site_id,
            [
                SitePageCrawlItem(
                    url="https://example.com/",
                    status=200,
                    content_hash="h0",
                    body_text="home body",
                    title="Home",
                    external_links=[{"url": "https://other.com/x"}],
                ),
                SitePageCrawlItem(
                    url="https://example.com/a",
                    status=200,
                    content_hash="ha",
                    body_text="page a body",
                    title="A",
                ),
                SitePageCrawlItem(url="https://example.com/gone", status=404),
            ],
        )
        ids = {r.url: r.id for r in refs}
        home, a = ids["https://example.com/"], ids["https://example.com/a"]
        await site_page_links.replace_for_pages(
            db,
            user_id,
            site_id,
            {
                home: [
                    NewSitePageLink(
                        dst_page_id=a,
                        dst_url="https://example.com/a",
                        region="body",
                        anchor="to a",
                        count=1,
                        followable=True,
                        dst_canonical=True,
                    )
                ],
                a: [
                    NewSitePageLink(
                        dst_page_id=home,
                        dst_url="https://example.com/",
                        region="nav",
                        anchor="home",
                        count=1,
                        followable=True,
                        dst_canonical=True,
                    )
                ],
            },
        )
    return user_id, site_id, ids


async def test_page_lookups(seeded):
    user_id, site_id, ids = seeded
    home, a, gone = (
        ids["https://example.com/"],
        ids["https://example.com/a"],
        ids["https://example.com/gone"],
    )
    async with unit_of_work() as db:
        assert await site_pages.count(db, site_id) == 3
        assert await site_pages.exists(db, site_id, a)
        assert not await site_pages.exists(db, site_id, "spg_nope")
        assert await site_pages.existing_ids(db, site_id, [a, "spg_nope"]) == {a}
        assert await site_pages.id_by_url(db, site_id, "https://example.com/a") == a
        assert await site_pages.urls_by_ids(db, site_id, [a]) == {a: "https://example.com/a"}
        assert set(await site_pages.ids_by_url_substring(db, site_id, "/a")) == {a}
        assert await site_pages.home_page_id(db, site_id) == home
        assert await site_pages.gone_ids(db, site_id) == {gone}
        assert await site_pages.gone_ids(db, site_id, [home, gone]) == {gone}
        assert await site_pages.gone_ids(db, site_id, [home]) == set()
        assert set(await site_pages.changed_at_by_id(db, site_id, [a])) == {a}
        assert await site_pages.live_ids(db, site_id) == {home, a}
        by_path = await site_pages.list_by_paths(db, site_id, ["/a/", "/"])
        assert {p.id for p in by_path} == {home, a}
        by_url = await site_pages.list_by_urls(db, site_id, ["https://example.com/a/"])
        assert [p.id for p in by_url] == [a]
        briefs = await site_pages.list_by_ids(db, site_id, [a], body_chars=4)
        assert briefs[0].body_text == "page"
        assert [h[0] for h in await site_pages.extractable_hashes(db, site_id)] == [home, a]
        assert (await site_pages.content_hashes_by_ids(db, site_id, [a]))[a] == "ha"
        targets = await site_pages.link_targets(
            db, site_id, ["https://example.com/", "https://example.com/gone", "https://x.com/"]
        )
        assert targets == {
            "https://example.com/": (home, True),
            "https://example.com/gone": (gone, False),
        }
        assert await site_pages.canonical_target_ids(db, site_id) == {home, a}
        eligible = await site_pages.list_render_eligible(db, site_id)
        assert {p.id for p in eligible} == {home, a}


async def test_link_queries_and_graph_writes(seeded):
    user_id, site_id, ids = seeded
    home, a = ids["https://example.com/"], ids["https://example.com/a"]
    async with unit_of_work() as db:
        assert set(await site_page_links.existing_pairs(db, site_id, [(home, a), (a, a)])) == {
            (home, a)
        }
        assert await site_page_links.pairs_among(db, site_id, [home, a]) == {(home, a), (a, home)}
        assert await site_page_links.pairs_into(db, site_id, [a]) == {(home, a)}
        assert await site_page_links.pairs_into(db, site_id, []) == set()
        assert await site_page_links.src_ids_linking_to(db, site_id, a) == {home}
        assert await site_page_links.inlink_counts(db, site_id, [a]) == {a: 1}
        assert (await site_page_links.outlink_counts(db, site_id, "body"))[home] == 1
        assert await site_page_links.out_link_counts_by_src_ids(db, site_id, [home]) == {home: 1}
        assert await site_page_links.inbound_anchors_by_page_ids(db, [a, home]) == {
            a: ["to a"],
            home: ["home"],
        }
        edges = await site_page_links.resolved_edges(db, site_id)
        assert {(e[0], e[1]) for e in edges} == {(home, a), (a, home)}
        assert {(e.src, e.dst) for e in await site_page_links.followable_edges(db, site_id)} == {
            (home, a),
            (a, home),
        }
        between = await site_page_links.list_between(db, site_id, [home], [a], region="body")
        assert [link.anchor for link in between] == ["to a"]
        assert len(await site_page_links.list_inbound(db, site_id, a)) == 1
        assert len(await site_page_links.list_outbound(db, site_id, home)) == 1
        await site_page_links.set_dst_canonical(db, site_id, {home})
        between = await site_page_links.list_between(db, site_id, [home, a], [home, a])
        assert {link.dst_page_id: link.dst_canonical for link in between} == {
            a: False,
            home: True,
        }
        await site_pages.write_graph_stamps(db, site_id, {a: (1, 1), home: (1, 0)})
        page = await site_pages.get(db, site_id, a)
        assert (page.inlinks, page.depth) == (1, 1)
        gone = await site_pages.get(db, site_id, ids["https://example.com/gone"])
        assert (gone.inlinks, gone.depth) == (0, None)


async def test_chunk_and_extraction_queries(seeded):
    user_id, site_id, ids = seeded
    home, a = ids["https://example.com/"], ids["https://example.com/a"]
    async with unit_of_work() as db:
        written = await site_chunks.replace_for_page(
            db,
            user_id,
            site_id,
            a,
            "ha",
            [
                {"ordinal": 0, "heading_path": "A", "text": "alpha beta"},
                {"ordinal": 1, "heading_path": "A > B", "text": "gamma delta"},
            ],
        )
        assert written == 2
        await site_pages.mark_chunked(db, a, "ha")
        chunks = await site_chunks.list_for_page(db, site_id, a)
        assert [c.ordinal for c in chunks] == [0, 1]
        first = chunks[0].id
        assert await site_chunks.page_id_of(db, site_id, first) == a
        assert await site_chunks.first_ids_containing(
            db, site_id, [(a, "gamma"), (a, "alpha"), (a, "zzz"), (home, "gamma"), (a, "")]
        ) == {(a, "gamma"): chunks[1].id, (a, "alpha"): first}
        hits = await site_chunks.phrase_hits(
            db, site_id, [("t1", "ALPHA"), ("t1", "beta"), ("t2", "alpha"), ("t2", "a%")], [], 5
        )
        assert [(h.key, h.page_id, h.chunk_id, h.phrase) for h in hits] == [
            ("t1", a, first, "ALPHA"),
            ("t2", a, first, "alpha"),
        ]
        assert await site_chunks.phrase_hits(db, site_id, [("t1", "alpha")], [("t1", a)], 5) == []
        assert await site_chunks.page_ids_with_unembedded(db, [a, home]) == {a}
        pending = await site_chunks.claim_pending_embeddings(db, 3, 10_000)
        assert {c.id for c in pending} >= {c.id for c in chunks}
        await site_chunks.write_embedding(db, first, "ha", [0.1] * 384, "m")
        await site_chunks.write_embedding(db, chunks[1].id, "ha", [0.2] * 384, "m")
        counts = await site_chunks.counts(db, site_id)
        assert (counts.total, counts.embedded, counts.failed) == (2, 2, 0)
        hits = await site_chunks.keyword_hits(db, site_id, "gamma", False, 10)
        assert [h.page_id for h in hits] == [a]
        sem = await site_chunks.semantic_hits(db, site_id, [0.1] * 384, "m", 0.0, 10)
        assert [h.page_id for h in sem] == [a]
        best = await site_chunks.best_similarity_by_page(db, site_id, [0.1] * 384)
        assert best[a] == pytest.approx(1.0)
        assert len(await site_chunks.page_vectors(db, site_id)) == 1
        assert await site_chunks.mean_embedding(db, site_id, [a]) is not None
        sims = await site_chunks.chunk_page_similarities(db, site_id, [(first, a)])
        assert sims[(first, a)] == pytest.approx(1.0)
        assert await site_chunks.page_similarities(db, site_id, [(a, a)]) == {
            (a, a): pytest.approx(1.0)
        }
        failed = await site_chunks.mark_embed_failed(db, first, "boom")
        assert failed == (a, 1)
        assert await site_pages.clear_embed_state(db, [a]) == 0
        await site_pages.mark_embed_failed(db, a, "boom")
        assert await site_pages.clear_embed_state(db, [a]) == 1
        assert gone_id(ids) in await site_pages.unserved_page_ids(db)
        sources = await site_pages.claim_needing_chunks(db, 50)
        assert home in {s.id for s in sources}
        assert a not in {s.id for s in sources}

        db.add(
            SitePageLlmExtraction(
                id=uid("spx"),
                user_id=user_id,
                site_id=site_id,
                page_id=a,
                page_type="hub",
                extracted_from_hash="ha",
                extract_attempts=0,
            )
        )
        await db.flush()
        states = await site_page_llm_extractions.states_by_page_ids(db, site_id, [a, home])
        assert set(states) == {a}
        assert states[a].extracted_from_hash == "ha"
        assert await site_page_llm_extractions.page_types_by_page_ids(db, site_id) == {a: "hub"}
        assert await site_page_llm_extractions.page_ids_with_types(db, site_id, ["hub"]) == [a]
        assert await site_chunks.delete_by_page_ids(db, [a]) == 2


def gone_id(ids):
    return ids["https://example.com/gone"]
