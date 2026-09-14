import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


@pytest.fixture(scope="session", autouse=True)
def test_database():
    yield


@pytest.fixture(scope="session", autouse=True)
def schema():
    yield
