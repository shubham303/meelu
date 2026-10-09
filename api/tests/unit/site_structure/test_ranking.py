import pytest

from src.site_structure.links.ranking import (
    Candidate,
    RankParams,
    intent,
    rank,
    score_additions,
)
from src.site_structure.links.schemas import LinkAction
from src.site_structure.pipeline.ranking import (
    UNLIMITED_CAPACITY,
    PageFacts,
    SiteDistribution,
    is_home,
    link_capacity,
    link_room,
    percentile,
)


def page(pid, inlinks=5, outlinks=5, words=900, page_type="informational", home=False):
    return PageFacts(pid, inlinks, outlinks, words, page_type, is_home=home)


def add(sid, src, dst, score=0.9, confidence=1.0):
    return Candidate(sid, src, dst, LinkAction.CREATE, score, confidence)


def remove(sid, src, dst, score, confidence=1.0):
    return Candidate(sid, src, dst, LinkAction.DELETE, score, confidence)


def site_of(*pages):
    return {p.page_id: p for p in pages}, SiteDistribution.from_pages(pages)


def kept_ids(ranked):
    return {r.candidate.suggestion_id for r in ranked if r.kept}


def test_link_capacity_grows_with_words_and_caps():
    assert link_capacity(page("a", words=0)) == 3
    assert link_capacity(page("a", words=900)) == 6
    assert link_capacity(page("a", words=None)) == 3
    assert link_capacity(page("a", words=100_000)) == 15


def test_percentile_is_midrank_and_bounded():
    assert percentile([1, 2, 3, 4], 1) == 0.125
    assert percentile([1, 2, 3, 4], 4) == 0.875
    assert percentile([3, 3, 3], 3) == 0.5
    assert percentile([], 7) == 0.5


def test_is_home_matches_root_only():
    assert is_home("https://x.example.com")
    assert is_home("https://x.example.com/")
    assert not is_home("https://x.example.com/blog")


def test_intent_prefers_informational_to_money():
    assert intent("informational", "money") == 1.0
    assert intent("hub", "money") == 0.7
    assert intent("money", "legal") == 0.1
    assert intent("informational", None) == 0.3


def test_scores_stay_in_unit_interval_and_favour_needy_money_targets():
    pages, site = site_of(
        page("src", inlinks=40, outlinks=10),
        page("orphan_money", inlinks=0, outlinks=4, page_type="money"),
        page("popular_legal", inlinks=60, outlinks=0, page_type="legal"),
    )
    cands = [add("s1", "src", "orphan_money"), add("s2", "src", "popular_legal")]
    scored = {r.candidate.suggestion_id: r for r in score_additions(cands, pages, site)}
    for r in scored.values():
        assert 0.0 <= r.score <= 1.0
        assert all(0.0 <= v <= 1.0 for v in r.factors.values())
    assert scored["s1"].score > scored["s2"].score


def test_search_score_is_a_multiplier_not_an_addend():
    pages, site = site_of(
        page("src", inlinks=40),
        page("t", inlinks=0, outlinks=9, page_type="money"),
        page("u", inlinks=0, outlinks=9, page_type="money"),
    )
    scored = {
        r.candidate.suggestion_id: r
        for r in score_additions(
            [add("hi", "src", "t", 0.9), add("zero", "src", "u", 0.0)], pages, site
        )
    }
    assert scored["zero"].score == 0.0
    assert scored["hi"].score > 0.0
    assert "relevance" not in scored["hi"].factors


def test_missing_search_score_scores_on_structure_alone():
    pages, site = site_of(page("src"), page("t", inlinks=0, page_type="money"))
    without = score_additions([add("a", "src", "t", None)], pages, site)[0]
    full = score_additions([add("a", "src", "t", 1.0)], pages, site)[0]
    assert without.score > 0.0
    assert without.score == pytest.approx(full.score)


def test_missing_confidence_is_the_worst_case():
    pages, site = site_of(page("src"), page("t", inlinks=0, page_type="money"))

    def score(confidence):
        return score_additions([add("a", "src", "t", 0.8, confidence)], pages, site)[0].score

    assert score(None) == pytest.approx(score(0.0))
    assert score(None) < score(0.2) < score(1.0)
    assert score(None) == pytest.approx(score(1.0) * 0.5)


def test_budget_cut_happens_after_scoring_and_drops_the_weakest():
    pages, site = site_of(
        page("src", outlinks=0, words=0),
        page("a", inlinks=0, outlinks=5, page_type="money"),
        page("b", inlinks=1, outlinks=5, page_type="money"),
        page("c", inlinks=2, outlinks=5, page_type="money"),
        page("d", inlinks=50, outlinks=0, page_type="legal"),
    )
    cands = [
        add("d", "src", "d", 0.95),
        add("c", "src", "c", 0.90),
        add("b", "src", "b", 0.90),
        add("a", "src", "a", 0.90),
    ]
    kept = kept_ids(rank(cands, pages, site))
    assert len(kept) == 3
    assert "d" not in kept


def test_rank_time_capacity_ignores_approved_suggestions():
    pages, site = site_of(
        page("src", outlinks=0, words=0),
        page("a", inlinks=0),
        page("b", inlinks=0),
        page("c", inlinks=0),
    )
    out = rank([add(t, "src", t) for t in ("a", "b", "c")], pages, site)
    assert sum(r.kept for r in out) == 3


def _star_setup():
    fillers = [
        page(f"f{s}{i}", inlinks=0, outlinks=9, page_type="money")
        for s in range(3)
        for i in range(2)
    ]
    pages, site = site_of(
        *[page(f"s{s}", outlinks=0, words=0) for s in range(3)],
        page("star", inlinks=0, outlinks=9, page_type="money"),
        page("other", inlinks=3, outlinks=9, page_type="money"),
        *fillers,
    )
    cands = []
    for s in range(3):
        cands += [add(f"s{s}-f{i}", f"s{s}", f"f{s}{i}", 1.0) for i in range(2)]
        cands.append(add(f"s{s}-star", f"s{s}", "star", 0.9))
        cands.append(add(f"s{s}-other", f"s{s}", "other", 0.85))
    return pages, site, cands


def test_target_discount_spreads_links_across_targets():
    pages, site, cands = _star_setup()

    def to_star(discount):
        kept = kept_ids(rank(cands, pages, site, RankParams(target_discount=discount)))
        return sum(1 for k in kept if k.endswith("star"))

    assert to_star(0.0) == 3
    assert to_star(1.0) < 3


def test_max_per_target_is_a_hard_cap():
    pages, site = site_of(
        page("s1", outlinks=0, words=0),
        page("s2", outlinks=0, words=0),
        page("s3", outlinks=0, words=0),
        page("star", inlinks=0, outlinks=9, page_type="money"),
    )
    out = rank(
        [add(s, s, "star") for s in ("s1", "s2", "s3")], pages, site, RankParams(max_per_target=2)
    )
    assert sum(r.kept for r in out) == 2


def test_home_and_hub_pages_link_out_without_limit():
    assert link_capacity(page("h", words=0, page_type="hub")) == UNLIMITED_CAPACITY
    assert link_capacity(page("home", words=50, page_type="money", home=True)) == UNLIMITED_CAPACITY
    assert link_capacity(page("u", words=0, page_type="utility")) == 3


def test_hub_source_is_never_cut():
    pages, site = site_of(
        page("hub", words=0, page_type="hub"),
        *[page(f"t{i}", inlinks=i) for i in range(20)],
    )
    out = rank([add(f"t{i}", "hub", f"t{i}") for i in range(20)], pages, site)
    assert all(r.kept for r in out)


def test_candidates_on_unknown_pages_are_skipped():
    pages, site = site_of(page("src"), page("t", inlinks=0))
    out = rank([add("ok", "src", "t"), add("gone", "src", "missing")], pages, site)
    assert [r.candidate.suggestion_id for r in out] == ["ok"]


def test_removals_prefer_unrelated_links_and_respect_floors():
    src = page("src", outlinks=10, words=300, page_type="money")
    weak = page("weak", inlinks=2, page_type="legal")
    strong = page("strong", inlinks=9, page_type="money")
    pages, site = site_of(src, weak, strong)
    ranked = rank(
        [
            remove("unrelated", "src", "strong", 0.9),
            remove("related", "src", "strong", 0.1),
            remove("last-ish", "src", "weak", 1.0),
        ],
        pages,
        site,
    )
    by_id = {r.candidate.suggestion_id: r for r in ranked}
    assert by_id["unrelated"].score > by_id["related"].score
    assert by_id["last-ish"].kept is False
    assert by_id["unrelated"].kept is True


def test_removal_budget_is_a_third_of_outlinks():
    src = page("src", outlinks=10, words=0)
    targets = [page(f"t{i}", inlinks=5) for i in range(5)]
    pages, site = site_of(src, *targets)
    ranked = rank([remove(f"c{i}", "src", f"t{i}", 0.1 * i) for i in range(5)], pages, site)
    assert sum(1 for r in ranked if r.kept) == 3
    assert kept_ids(ranked) == {"c2", "c3", "c4"}


def test_link_room_counts_the_body_links_a_page_already_has():
    assert link_room(page("a", outlinks=0, words=900)) == 6
    assert link_room(page("a", outlinks=4, words=900)) == 2
    assert link_room(page("a", outlinks=20, words=900)) == 0
    assert link_room(page("h", outlinks=50, page_type="hub")) == link_capacity(
        page("h", page_type="hub")
    )
    pages, site = site_of(
        page("full", outlinks=3, words=0),
        page("a", inlinks=0),
        page("b", inlinks=0),
    )
    assert kept_ids(rank([add(t, "full", t) for t in ("a", "b")], pages, site)) == set()
