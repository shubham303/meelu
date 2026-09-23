from src.site_structure.screening import rejected, yes_confidence


def test_yes_confidence_reads_probabilities_first():
    assert yes_confidence({"choice": "no", "probabilities": {"yes": 0.15, "no": 0.85}}) == 0.15
    assert yes_confidence({"choice": "yes", "confidence": 0.9}) == 0.9
    assert yes_confidence({"choice": "no", "confidence": 0.9}) == 0.09999999999999998
    assert yes_confidence({"choice": "no"}) == 0.5


def test_only_a_confident_no_rejects():
    assert rejected(0.1)
    assert rejected(0.2)
    assert not rejected(0.3)
    assert not rejected(0.9)
