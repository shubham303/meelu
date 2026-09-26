import pytest

from src.site_structure.pipeline.schemas import review_prompt, workspace_table


def test_workspace_table_names():
    assert workspace_table(" prune_1 ") == "prune_1"
    for bad in ("", "Bad", "1st", "no such", None):
        with pytest.raises(ValueError):
            workspace_table(bad)


def test_review_prompt_is_required_and_trimmed():
    assert review_prompt("  Related  ") == "Related"
    with pytest.raises(ValueError):
        review_prompt(" ")
