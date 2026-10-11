import pytest

from src.technical_seo.schemas.export import cell


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("=HYPERLINK(\"http://x\")", "\"'=HYPERLINK(\"\"http://x\"\")\""),
        ("+1", "'+1"),
        ("-2+3", "'-2+3"),
        ("@SUM(A1)", "'@SUM(A1)"),
        ("\tcmd", "'\tcmd"),
        ("https://example.com/a", "https://example.com/a"),
        ("a, b", '"a, b"'),
    ],
)
def test_cells_cannot_start_a_formula(value, expected):
    assert cell(value) == expected
