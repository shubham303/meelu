from src.providers.seo_data.shape import ai_overview_answer, llm_answer


def test_llm_answer_joins_text_sections_and_dedupes_citations():
    result = {
        "model_name": "claude-sonnet-4-20250514",
        "items": [
            {"type": "reasoning", "sections": [{"type": "summary_text", "text": "thinking"}]},
            {
                "type": "message",
                "sections": [
                    {
                        "type": "text",
                        "text": "First part.",
                        "annotations": [
                            {"title": "A", "url": "https://a.example.com/x"},
                            {"title": "A again", "url": "https://a.example.com/x"},
                        ],
                    },
                    {"type": "text", "text": "Second part.", "annotations": None},
                ],
            },
        ],
    }
    answer = llm_answer(result)
    assert answer["text"] == "First part.\n\nSecond part."
    assert answer["citations"] == [{"url": "https://a.example.com/x", "title": "A"}]
    assert answer["model"] == "claude-sonnet-4-20250514"


def test_llm_answer_of_nothing_is_empty():
    assert llm_answer(None) == {"text": "", "citations": [], "model": None}


def test_ai_overview_reads_elements_references_and_links():
    result = {
        "items": [
            {"type": "organic", "url": "https://x.example.com"},
            {
                "type": "ai_overview",
                "items": [
                    {
                        "type": "ai_overview_element",
                        "markdown": "**Cannibalization** is two pages competing.",
                        "references": [
                            {
                                "type": "ai_overview_reference",
                                "url": "https://geo.example.com/blog",
                                "title": "Geo blog",
                            }
                        ],
                        "links": [
                            {"type": "link_element", "url": "https://b.example.com", "title": "B"}
                        ],
                    },
                    {"type": "ai_overview_table_element", "markdown": "| a | b |"},
                ],
            },
        ]
    }
    found = ai_overview_answer(result)
    assert found["text"] == "**Cannibalization** is two pages competing.\n\n| a | b |"
    assert [c["url"] for c in found["citations"]] == [
        "https://geo.example.com/blog",
        "https://b.example.com",
    ]


def test_ai_overview_inside_the_knowledge_graph():
    result = {
        "items": [
            {
                "type": "knowledge_graph",
                "items": [
                    {
                        "type": "knowledge_graph_ai_overview_item",
                        "items": [{"type": "ai_overview_element", "text": "Plain text."}],
                    }
                ],
            }
        ]
    }
    assert ai_overview_answer(result)["text"] == "Plain text."


def test_no_ai_overview_on_the_page():
    assert ai_overview_answer({"items": [{"type": "organic"}]}) is None
