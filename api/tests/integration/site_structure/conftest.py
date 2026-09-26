import pytest

from tests.integration.site_structure.helpers import fake_screener


@pytest.fixture
def rejecting_screener(monkeypatch):
    return fake_screener(monkeypatch, 0.05)
