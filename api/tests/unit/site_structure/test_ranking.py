from src.site_structure.ranking import (
    Candidate,
    PageFacts,
    RankParams,
    SiteDistribution,
    intent,
    link_capacity,
    percentile,
    rank_link_suggestions,
    score_candidates,
)


def page(pid, inlinks=5, outlinks=5, words=900, page_type="informational", existing=0):
    return PageFacts(pid, inlinks, outlinks, words, page_type, existing)


def site_of(*pages):
    return {p.page_id: p for p in pages}, SiteDistribution.from_pages(pages)


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
    cands = [
        Candidate("s1", "src", "orphan_money", 0.9),
        Candidate("s2", "src", "popular_legal", 0.9),
    ]
    scored = {r.candidate.suggestion_id: r for r in score_candidates(cands, pages, site)}
    for r in scored.values():
        assert 0.0 <= r.score <= 1.0
        assert all(0.0 <= v <= 1.0 for v in r.factors.values())
    assert scored["s1"].score > scored["s2"].score


def test_relevance_is_a_multiplier_not_an_addend():
    pages, site = site_of(
        page("src", inlinks=40),
        page("t", inlinks=0, outlinks=9, page_type="money"),
        page("u", inlinks=0, outlinks=9, page_type="money"),
    )
    cands = [Candidate("hi", "src", "t", 0.9), Candidate("zero", "src", "u", 0.0)]
    scored = {r.candidate.suggestion_id: r for r in score_candidates(cands, pages, site)}
    assert scored["zero"].score == 0.0
    assert scored["hi"].score > 0.0
    assert scored["hi"].factors["relevance"] == 0.9


def test_confidence_only_damps():
    pages, site = site_of(page("src"), page("t", inlinks=0, page_type="money"))
    base = score_candidates([Candidate("a", "src", "t", 0.8)], pages, site)[0].score
    damped = score_candidates([Candidate("a", "src", "t", 0.8, confidence=0.2)], pages, site)[
        0
    ].score
    full = score_candidates([Candidate("a", "src", "t", 0.8, confidence=1.0)], pages, site)[0].score
    assert damped < base
    assert full == base


def test_budget_cut_happens_after_scoring_and_drops_the_weakest():
    pages, site = site_of(
        page("src", words=0),
        page("a", inlinks=0, outlinks=5, page_type="money"),
        page("b", inlinks=1, outlinks=5, page_type="money"),
        page("c", inlinks=2, outlinks=5, page_type="money"),
        page("d", inlinks=50, outlinks=0, page_type="legal"),
    )
    cands = [
        Candidate("d", "src", "d", 0.95),
        Candidate("c", "src", "c", 0.90),
        Candidate("b", "src", "b", 0.90),
        Candidate("a", "src", "a", 0.90),
    ]
    out = {r.candidate.suggestion_id: r for r in rank_link_suggestions(cands, pages, site)}
    kept = {k for k, r in out.items() if r.kept}
    assert len(kept) == 3
    assert "d" not in kept


def test_existing_suggestions_reduce_capacity():
    pages, site = site_of(
        page("src", words=0, existing=2),
        page("a", inlinks=0),
        page("b", inlinks=0),
        page("c", inlinks=0),
    )
    cands = [Candidate(t, "src", t, 0.9) for t in ("a", "b", "c")]
    out = rank_link_suggestions(cands, pages, site)
    assert sum(r.kept for r in out) == 1


def test_target_discount_spreads_links_across_targets():
    pages, site = site_of(
        page("s1", words=0, existing=2),
        page("s2", words=0, existing=2),
        page("s3", words=0, existing=2),
        page("star", inlinks=0, outlinks=9, page_type="money"),
        page("other", inlinks=3, outlinks=9, page_type="money"),
    )
    cands = []
    for s in ("s1", "s2", "s3"):
        cands.append(Candidate(f"{s}-star", s, "star", 0.9))
        cands.append(Candidate(f"{s}-other", s, "other", 0.85))
    params = RankParams(target_discount=1.0)
    out = {r.candidate.suggestion_id: r for r in rank_link_suggestions(cands, pages, site, params)}
    to_star = sum(r.kept for k, r in out.items() if k.endswith("star"))
    to_other = sum(r.kept for k, r in out.items() if k.endswith("other"))
    assert to_star == 2
    assert to_other == 1


def test_no_discount_lets_the_top_target_take_every_slot():
    pages, site = site_of(
        page("s1", words=0, existing=2),
        page("s2", words=0, existing=2),
        page("star", inlinks=0, outlinks=9, page_type="money"),
        page("other", inlinks=3, outlinks=9, page_type="money"),
    )
    cands = [
        Candidate("s1-star", "s1", "star", 0.9),
        Candidate("s1-other", "s1", "other", 0.85),
        Candidate("s2-star", "s2", "star", 0.9),
        Candidate("s2-other", "s2", "other", 0.85),
    ]
    out = {
        r.candidate.suggestion_id: r
        for r in rank_link_suggestions(cands, pages, site, RankParams(target_discount=0.0))
    }
    assert out["s1-star"].kept and out["s2-star"].kept
    assert not out["s1-other"].kept and not out["s2-other"].kept


def test_max_per_target_is_a_hard_cap():
    pages, site = site_of(
        page("s1", words=0),
        page("s2", words=0),
        page("s3", words=0),
        page("star", inlinks=0, outlinks=9, page_type="money"),
    )
    cands = [Candidate(s, s, "star", 0.9) for s in ("s1", "s2", "s3")]
    out = rank_link_suggestions(cands, pages, site, RankParams(max_per_target=2))
    assert sum(r.kept for r in out) == 2


def test_home_and_hub_pages_link_out_without_limit():
    from src.site_structure.ranking import UNLIMITED_CAPACITY

    assert link_capacity(page("h", words=0, page_type="hub")) == UNLIMITED_CAPACITY
    assert (
        link_capacity(PageFacts("home", 0, 0, 50, "money", 0, is_home=True)) == UNLIMITED_CAPACITY
    )
    assert link_capacity(page("u", words=0, page_type="utility")) == 3


def test_hub_source_is_never_cut():
    pages, site = site_of(
        page("hub", words=0, page_type="hub"),
        *[page(f"t{i}", inlinks=i) for i in range(20)],
    )
    cands = [Candidate(f"t{i}", "hub", f"t{i}", 0.9) for i in range(20)]
    out = rank_link_suggestions(cands, pages, site)
    assert all(r.kept for r in out)


def test_removals_prefer_unrelated_links_and_respect_floors():
    from src.site_structure.ranking import rank_link_removals

    src = page("src", outlinks=10, words=300, page_type="money")
    weak = page("weak", inlinks=2, page_type="legal")
    strong = page("strong", inlinks=9, page_type="money")
    pages, _ = site_of(src, weak, strong)
    ranked = rank_link_removals(
        [
            Candidate("unrelated", "src", "strong", search_score=0.1, action="delete"),
            Candidate("related", "src", "strong", search_score=0.9, action="delete"),
            Candidate("last-ish", "src", "weak", search_score=0.0, action="delete"),
        ],
        pages,
    )
    by_id = {r.candidate.suggestion_id: r for r in ranked}
    assert by_id["unrelated"].score > by_id["related"].score
    assert by_id["last-ish"].kept is False
    assert sum(1 for r in ranked if r.kept) <= 3
    assert by_id["unrelated"].kept is True


def test_removal_budget_is_a_third_of_outlinks():
    from src.site_structure.ranking import rank_link_removals

    src = page("src", outlinks=10, words=0)
    targets = [page(f"t{i}", inlinks=5) for i in range(5)]
    pages, _ = site_of(src, *targets)
    ranked = rank_link_removals(
        [
            Candidate(f"c{i}", "src", f"t{i}", search_score=0.1 * i, action="delete")
            for i in range(5)
        ],
        pages,
    )
    assert sum(1 for r in ranked if r.kept) == 3
