import argparse
import random
import time

from .embedding import Embedder, post_input
from .settings import WorkerSettings

WORDS = (
    "site slow wordpress plugin hosting cache image page speed theme server checkout cart "
    "customer support ranking google search traffic audit backlink keyword content blog "
    "agency client invoice pricing plan migration database query timeout error deploy"
).split()


def sample_post(rng: random.Random, chars: int) -> str:
    words, size = [], 0
    while size < chars:
        word = rng.choice(WORDS)
        words.append(word)
        size += len(word) + 1
    return post_input("A question", " ".join(words))


def measure(embedder: Embedder, texts: list[str], batch: int) -> float:
    started = time.perf_counter()
    for i in range(0, len(texts), batch):
        embedder.embed(texts[i : i + batch])
    return len(texts) / (time.perf_counter() - started)


def main() -> None:
    parser = argparse.ArgumentParser(description="Embedding throughput in rows per second.")
    parser.add_argument("--rows", type=int, default=512)
    parser.add_argument("--chars", type=int, default=600)
    parser.add_argument("--batches", default="8,16,32,64,128")
    parser.add_argument("--threads", default="1,2,4")
    args = parser.parse_args()

    model = WorkerSettings().meelu_embed_model
    rng = random.Random(7)
    texts = [sample_post(rng, args.chars) for _ in range(args.rows)]
    print(f"model={model} rows={args.rows} chars={args.chars}")
    print("threads  batch  rows/s")
    for threads in (int(t) for t in args.threads.split(",")):
        embedder = Embedder(model, threads)
        embedder.embed(texts[:8])
        for batch in (int(b) for b in args.batches.split(",")):
            print(f"{threads:>7}  {batch:>5}  {measure(embedder, texts, batch):>6.1f}")


if __name__ == "__main__":
    main()
