import asyncio
import signal
import sys
import time

import src.core.tables  # noqa: F401
from src.seo.precompute.clusters import run_seo_pass
from src.site_pages.llm_extraction.classify import run_extraction_pass

from .chunking import chunk_body, page_chunk
from .db import Db
from .embedding import Embedder, passage_input, post_input, query_input
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


def run_listening_pass(db, embedder, model, batch=4, max_batches=16):
    done = 0
    for table, fetch, to_input in (
        ("social_listening_query", db.pending_query_embeddings, lambda r: query_input(r["text"])),
        (
            "social_listening_post",
            db.pending_post_embeddings,
            lambda r: post_input(r["title"], r["text"]),
        ),
    ):
        for _ in range(max_batches):
            rows = fetch(batch)
            if not rows:
                break
            try:
                vectors = embedder.embed([to_input(r) for r in rows])
            except Exception as e:
                for r in rows:
                    db.mark_listening_embed_failed(table, r["id"], str(e))
                break
            for row, vector in zip(rows, vectors):
                try:
                    db.write_listening_embedding(table, row["id"], vector, model)
                    done += 1
                except Exception as e:
                    db.mark_listening_embed_failed(table, row["id"], str(e))
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
    loop = asyncio.new_event_loop()

    while not stopping:
        try:
            pages, chunks = run_chunk_pass(db, settings.meelu_chunk_page_batch)
            if pages > 0:
                print(f"embed-worker: re-chunked {pages} page(s) into {chunks} passage(s)")
            embedded = run_embed_pass(db, embedder, settings.meelu_embed_model)
            if embedded > 0:
                print(f"embed-worker: embedded {embedded} chunk(s)")
            extracted = loop.run_until_complete(run_extraction_pass())
            if extracted > 0:
                print(f"embed-worker: extracted {extracted} page(s)")
            listening = run_listening_pass(db, embedder, settings.meelu_embed_model)
            if listening > 0:
                print(f"embed-worker: embedded {listening} listening row(s)")
            seo_sites = run_seo_pass(db, embedder, settings.meelu_embed_model)
            if seo_sites > 0:
                print(f"embed-worker: rebuilt keyword clusters for {seo_sites} site(s)")
            if once:
                break
            if pages == 0 and embedded == 0 and extracted == 0 and listening == 0 and seo_sites == 0:
                time.sleep(interval)
        except Exception as e:
            print(f"embed-worker: pass failed — {e}", file=sys.stderr)
            db.reset()
            if once:
                break
            time.sleep(interval)

    loop.close()
    db.close()
