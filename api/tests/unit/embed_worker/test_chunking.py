from src.embed_worker.chunking import chunk_body, lead_excerpt, page_chunk, words


def line(tag, n=10):
    return " ".join(f"{tag}w{j}" for j in range(n))


def build_body():
    pre = line("p")
    setup_lines = [line(f"s{i}") for i in range(5)]
    usage_lines = [line(f"u{i}") for i in range(90)]
    details_lines = [line(f"d{i}") for i in range(3)]
    body = "\n".join(
        [
            pre,
            "# Guide",
            "## Setup",
            *setup_lines,
            "## Usage",
            *usage_lines,
            "### Details",
            *details_lines,
        ]
    )
    return body, pre, setup_lines, usage_lines, details_lines


def test_chunk_boundaries_and_word_counts():
    body, pre, setup_lines, usage_lines, details_lines = build_body()
    chunks = chunk_body(body, "Sample Page")

    assert [c["ordinal"] for c in chunks] == [0, 1, 2, 3]
    assert [words(c["text"]) for c in chunks] == [60, 400, 400, 250]
    assert [c["heading_path"] for c in chunks] == [
        "Sample Page",
        "Sample Page › Usage",
        "Sample Page › Usage",
        "Sample Page › Usage",
    ]

    assert chunks[0]["text"] == "\n".join([pre, *setup_lines])
    assert chunks[1]["text"] == "\n".join(usage_lines[:40])
    assert chunks[2]["text"] == "\n".join(usage_lines[34:74])
    assert chunks[3]["text"] == "\n".join([*usage_lines[68:], *details_lines])

    overlap = chunks[1]["text"].split("\n")[-6:]
    assert chunks[2]["text"].split("\n")[:6] == overlap


def test_short_body_single_chunk():
    chunks = chunk_body("just a few words here", None)
    assert len(chunks) == 1
    assert chunks[0] == {"heading_path": None, "text": "just a few words here", "ordinal": 0}


def test_lead_excerpt_skips_and_truncates():
    long_line = " ".join(f"x{i}" for i in range(45))
    body = "\n".join(["# Heading", "| a | b |", "- bullet", long_line])
    excerpt = lead_excerpt(body)
    assert excerpt == " ".join(f"x{i}" for i in range(40)) + "…"
    assert lead_excerpt("# only heading") is None
    assert lead_excerpt(None) is None


def test_page_chunk_assembly():
    page = {
        "title": "Home",
        "h1": ["Welcome"],
        "meta_description": "A store",
        "body_text": "Great gear for everyone",
        "inbound_anchors": [{"anchor": "shop"}, {"anchor": "shop"}, {"anchor": None}, {}],
    }
    chunk = page_chunk(page)
    assert chunk == {
        "heading_path": "Home",
        "text": "Home · Welcome · A store · Great gear for everyone · shop",
    }
    empty = page_chunk(
        {
            "title": None,
            "h1": None,
            "meta_description": None,
            "body_text": None,
            "inbound_anchors": None,
        }
    )
    assert empty is None
