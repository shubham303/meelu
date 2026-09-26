from typing import Any

from src.site_structure.constants import SCREEN_CONFIDENCE, SuggestionState


def yes_confidence(answer: dict[str, Any]) -> float:
    probabilities = answer.get("probabilities")
    if isinstance(probabilities, dict) and isinstance(probabilities.get("yes"), (int, float)):
        return float(probabilities["yes"])
    confidence = answer.get("confidence")
    sure = float(confidence) if isinstance(confidence, (int, float)) else 0.5
    return sure if answer.get("choice") == "yes" else 1.0 - sure


def screened_state(confidence_yes: float) -> SuggestionState:
    if 1.0 - confidence_yes >= SCREEN_CONFIDENCE:
        return SuggestionState.SCREENING_REJECTED
    return SuggestionState.SCREENING_APPROVED
