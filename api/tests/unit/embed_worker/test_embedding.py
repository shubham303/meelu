import math

import pytest

from src.embed_worker.embedding import Embedder, passage_input


def test_passage_input():
    assert passage_input("T", "T › H", "body") == "passage: T › T › H\nbody"
    assert passage_input(None, "H", "body") == "passage: H\nbody"
    assert passage_input(None, None, "body") == "passage: body"


@pytest.fixture(scope="module")
def embedder():
    try:
        return Embedder("Xenova/multilingual-e5-small", 2)
    except Exception as e:
        pytest.skip(f"model unavailable: {e}")


def test_embed_shape_and_unit_norm(embedder):
    (vector,) = embedder.embed(["passage: hello world"])
    assert len(vector) == 384
    norm = math.sqrt(sum(v * v for v in vector))
    assert abs(norm - 1.0) < 1e-3


def test_embed_batch(embedder):
    vectors = embedder.embed(["passage: hello world", "passage: a much longer piece of text here"])
    assert len(vectors) == 2
    assert all(len(v) == 384 for v in vectors)
