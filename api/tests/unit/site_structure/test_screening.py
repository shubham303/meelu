from src.site_structure.constants import SuggestionState
from src.site_structure.pipeline.screening import screened_state, yes_confidence


def test_yes_confidence_reads_probabilities_first():
    assert yes_confidence({"choice": "no", "probabilities": {"yes": 0.15, "no": 0.85}}) == 0.15
    assert yes_confidence({"choice": "yes", "confidence": 0.9}) == 0.9
    assert yes_confidence({"choice": "no", "confidence": 0.9}) == 0.09999999999999998
    assert yes_confidence({"choice": "no"}) == 0.5


def test_only_a_confident_no_rejects():
    assert screened_state(0.1) is SuggestionState.SCREENING_REJECTED
    assert screened_state(0.2) is SuggestionState.SCREENING_REJECTED
    assert screened_state(0.3) is SuggestionState.SCREENING_APPROVED
    assert screened_state(0.9) is SuggestionState.SCREENING_APPROVED
