import signal
import sys
import time

from .chunking import chunk_body, page_chunk
from .db import Db
from .embedding import Embedder, passage_input
from .settings import WorkerSettings

stopping = False


def request_stop(signum, frame):
    global stopping
    stopping = True


def rechunk_page(db, page):
    built = chunk_body(page["body_text"], page["title"])
    synthetic = page_chunk(page)
    chunks = ([synthetic] if synthetic else []) + built
    for i, c in enumerate(chunks):
        c["ordinal"] = i
    db.replace_page_chunks(page, chunks)
    return len(chunks)


def run_chunk_pass(db, page_batch):
    db.prune_unserved_chunks()
    pages = db.pages_needing_chunks(page_batch)
    chunks = 0
    for page in pages:
        try:
            chunks += rechunk_page(db, page)
        except Exception as e:
            print(f"embed-worker: could not chunk {page['url']} — {e}", file=sys.stderr)
    return len(pages), chunks


def run_embed_pass(db, embedder, model, batch=32, max_batches=4):
    done = 0
    for _ in range(max_batches):
        rows = db.pending_embeddings(batch)
        if not rows:
            break

        inputs = [passage_input(r["title"], r["heading_path"], r["text"]) for r in rows]
        try:
            vectors = embedder.embed(inputs)
        except Exception as e:
            for r in rows:
                db.mark_embed_failed(r["id"], str(e))
            break

        touched = set()
        for row, vector in zip(rows, vectors):
            try:
                db.write_embedding(row["id"], row["from_hash"], vector, model)
                touched.add(row["page_id"])
                done += 1
            except Exception as e:
                db.mark_embed_failed(row["id"], str(e))
        for page_id in touched:
            try:
                db.clear_embed_state_if_complete(page_id)
            except Exception:
                pass
    return done


def main():
    settings = WorkerSettings()

    if not settings.database_url:
        print("embed-worker: DATABASE_URL is not set", file=sys.stderr)
        sys.exit(1)

    if settings.meelu_embed_disabled == "1":
        print("embed-worker: disabled (MEELU_EMBED_DISABLED=1) — exiting rather than idle forever")
        sys.exit(0)

    db = Db(settings.database_url)

    missing = db.missing_columns()
    if missing:
        print(
            f"embed-worker: the schema is missing {', '.join(missing)} — refusing to start",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"embed-worker: loading {settings.meelu_embed_model}…")
    embedder = Embedder(settings.meelu_embed_model)
    interval = settings.meelu_embed_interval_ms / 1000
    print(
        f"embed-worker: ready — chunking and embedding every {settings.meelu_embed_interval_ms}ms"
    )

    signal.signal(signal.SIGINT, request_stop)
    signal.signal(signal.SIGTERM, request_stop)

    once = settings.meelu_embed_once == "1"

    while not stopping:
        try:
            pages, chunks = run_chunk_pass(db, settings.meelu_chunk_page_batch)
            if pages > 0:
                print(f"embed-worker: re-chunked {pages} page(s) into {chunks} passage(s)")
            embedded = run_embed_pass(db, embedder, settings.meelu_embed_model)
            if embedded > 0:
                print(f"embed-worker: embedded {embedded} chunk(s)")
            if once:
                break
            if pages == 0 and embedded == 0:
                time.sleep(interval)
        except Exception as e:
            print(f"embed-worker: pass failed — {e}", file=sys.stderr)
            db.reset()
            if once:
                break
            time.sleep(interval)

    db.close()
