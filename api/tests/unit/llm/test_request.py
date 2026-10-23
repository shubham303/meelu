from src.llm.request import forwarded, max_output_tokens


def test_forwarded_keeps_known_fields_and_pins_the_model():
    body = {"model": "y/other", "max_tokens": 5, "messages": [], "models": ["z"], "plugins": []}
    assert forwarded(body, "x/model", 5) == {"max_tokens": 5, "messages": [], "model": "x/model"}


def test_forwarded_keeps_the_server_tool_budget():
    body = {"max_tokens": 5, "messages": [], "tools": [{"type": "x"}], "max_tool_calls": 3}
    assert forwarded(body, "x/model", 5)["max_tool_calls"] == 3


def test_forwarded_caps_max_tokens_and_a_thinking_budget_above_it():
    body = {
        "max_tokens": 100_000,
        "messages": [],
        "thinking": {"type": "enabled", "budget_tokens": 64_000},
    }
    sent = forwarded(body, "x/model", 32_000)
    assert sent["max_tokens"] == 32_000
    assert sent["thinking"] == {"type": "enabled", "budget_tokens": 16_000}


def test_max_tokens_must_be_a_positive_int():
    assert max_output_tokens({"max_tokens": 64}) == 64
    for bad in (0, -1, 1.5, "64", True, None):
        assert max_output_tokens({"max_tokens": bad}) is None
