import pytest

from src.providers.errors import ProviderRequestError
from src.providers.json_data_extractor.adapter import boolean, choice, said_yes
from src.providers.json_data_extractor.openrouter_jev import read_answer


def test_jev_answers_are_read_and_clamped():
    yes_no = boolean("Fits?", "fits", "does not fit")
    pick = choice("Which?", {"a": "first", "b": "second"})
    body = {
        "answers": {
            "p0": {"type": "noul", "noul": 1.2},
            "p1": {"type": "choice", "choice": "b", "confidence": 0.7},
        }
    }
    assert read_answer("jev", body, "p0", yes_no) == {"type": "noul", "noul": 1.0}
    assert read_answer("jev", body, "p1", pick) == {
        "type": "choice",
        "choice": "b",
        "confidence": 0.7,
    }
    with pytest.raises(ProviderRequestError):
        read_answer("jev", body, "p2", yes_no)
    with pytest.raises(ProviderRequestError):
        read_answer("jev", {"answers": {"p1": {"choice": "c"}}}, "p1", pick)


def test_said_yes_reads_both_answer_shapes():
    assert said_yes({"type": "noul", "noul": 0.5})
    assert not said_yes({"type": "noul", "noul": 0.49})
    assert said_yes({"type": "choice", "choice": "true"})
    assert not said_yes({"type": "choice", "choice": "false"})
    assert not said_yes(None)
