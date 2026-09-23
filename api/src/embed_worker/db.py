import uuid

import psycopg
from psycopg.rows import dict_row

MAX_EMBED_ATTEMPTS = 3

PAGE_COLUMNS = [
    "id",
    "site_id",
    "user_id",
    "url",
    "title",
    "h1",
    "meta_description",
    "inbound_anchors",
    "body_text",
    "content_hash",
]

SEO_KEYWORD_COLUMNS = ("id", "keyword", "embedding", "embed_model", "embed_error", "cluster_id")

CHUNK_COLUMNS = [
    "id",
    "user_id",
    "site_id",
    "page_id",
    "ordinal",
    "heading_path",
    "text",
    "chunk_strategy",
    "from_hash",
    "embedding",
    "embed_model",
    "embedded_from_hash",
    "embed_attempts",
    "embed_error",
    "seq",
]


def normalize_database_url(url):
    prefix = "postgresql+psycopg://"
    if url.startswith(prefix):
        return "postgresql://" + url[len(prefix) :]
    return url


def chunk_id():
    return f"chk_{uuid.uuid4().hex[:10]}"


def vector_literal(vector):
    return "[" + ",".join(repr(v) for v in vector) + "]"


class Db:
    def __init__(self, url):
        self.url = normalize_database_url(url)
        self.conn = None

    def connection(self):
        if self.conn is None or self.conn.closed:
            self.conn = psycopg.connect(self.url, autocommit=True, row_factory=dict_row)
        return self.conn

    def reset(self):
        if self.conn is not None:
            try:
                self.conn.close()
            except Exception:
                pass
        self.conn = None

    def close(self):
        self.reset()

    def query(self, sql, params=None):
        with self.connection().cursor() as cur:
            cur.execute(sql, params)
            if cur.description is None:
                return [], cur.rowcount
            return cur.fetchall(), cur.rowcount

    def missing_columns(self):
        rows, _ = self.query(
            """select table_name, column_name from information_schema.columns
                where table_name in ('site_pages', 'site_chunks', 'seo_keywords')"""
        )
        have = {f"{r['table_name']}.{r['column_name']}" for r in rows}
        wanted = (
            [f"site_pages.{c}" for c in PAGE_COLUMNS]
            + [f"site_chunks.{c}" for c in CHUNK_COLUMNS]
            + [f"seo_keywords.{c}" for c in SEO_KEYWORD_COLUMNS]
        )
        return [c for c in wanted if c not in have]

    def pages_needing_chunks(self, limit):
        rows, _ = self.query(
            f"""select {", ".join(PAGE_COLUMNS)}
                  from site_pages
                 where status = 200
                   and body_text is not null
                   and content_hash is not null
                   and chunked_from_hash is distinct from content_hash
                 order by updated_at asc
                 limit %s""",
            (limit,),
        )
        return rows

    def replace_page_chunks(self, page, chunks):
        conn = self.connection()
        with conn.transaction():
            with conn.cursor() as cur:
                cur.execute("delete from site_chunks where page_id = %s", (page["id"],))
                for c in chunks:
                    cur.execute(
                        """insert into site_chunks
                             (id, user_id, site_id, page_id, ordinal, heading_path, text,
                              chunk_strategy, from_hash, embed_attempts, created_at, updated_at)
                           values (%s, %s, %s, %s, %s, %s, %s, 'headings-v1', %s, 0, now(), now())""",
                        (
                            chunk_id(),
                            page["user_id"],
                            page["site_id"],
                            page["id"],
                            c["ordinal"],
                            c["heading_path"],
                            c["text"],
                            page["content_hash"],
                        ),
                    )
                cur.execute(
                    """update site_pages
                          set chunked_from_hash = %s, embed_state = null, embed_error = null,
                              updated_at = now()
                        where id = %s""",
                    (page["content_hash"] if chunks else None, page["id"]),
                )

    def prune_unserved_chunks(self):
        _, count = self.query(
            """delete from site_chunks c
                 using site_pages p
                where c.page_id = p.id and p.status is distinct from 200"""
        )
        if count > 0:
            self.query(
                """update site_pages
                      set chunked_from_hash = null, updated_at = now()
                    where status is distinct from 200 and chunked_from_hash is not null"""
            )

    def pending_embeddings(self, limit):
        rows, _ = self.query(
            """select c.id, c.page_id, c.text, c.heading_path, c.from_hash, p.title
                 from site_chunks c
                 join site_pages p on p.id = c.page_id
                where c.embedding is null and c.embed_attempts < %s
                order by c.embed_attempts asc, c.seq asc
                limit %s""",
            (MAX_EMBED_ATTEMPTS, limit),
        )
        return rows

    def write_embedding(self, id, hash_at_read, vector, model):
        self.query(
            """update site_chunks
                  set embedding = %(vector)s::vector, embed_model = %(model)s,
                      embedded_from_hash = %(hash)s, embed_error = null, updated_at = now()
                where id = %(id)s and from_hash is not distinct from %(hash)s""",
            {"vector": vector_literal(vector), "model": model, "hash": hash_at_read, "id": id},
        )

    def mark_embed_failed(self, id, message):
        trimmed = message[:500]
        rows, _ = self.query(
            """update site_chunks
                  set embed_attempts = embed_attempts + 1, embed_error = %s, updated_at = now()
                where id = %s
                returning page_id, embed_attempts""",
            (trimmed, id),
        )
        if not rows or rows[0]["embed_attempts"] < MAX_EMBED_ATTEMPTS:
            return
        self.query(
            """update site_pages
                  set embed_state = 'failed', embed_error = %s, updated_at = now()
                where id = %s""",
            (trimmed, rows[0]["page_id"]),
        )

    def pending_query_embeddings(self, limit):
        rows, _ = self.query(
            """select id, text
                 from social_listening_query
                where embedding is null and embed_attempts < %s
                order by embed_attempts asc, seq asc
                limit %s""",
            (MAX_EMBED_ATTEMPTS, limit),
        )
        return rows

    def pending_post_embeddings(self, limit):
        rows, _ = self.query(
            """select id, title, text
                 from social_listening_post
                where embedding is null and embed_attempts < %s
                  and query_id is not null
                  and coalesce(title, text) is not null
                order by embed_attempts asc, seq asc
                limit %s""",
            (MAX_EMBED_ATTEMPTS, limit),
        )
        return rows

    def write_listening_embedding(self, table, id, vector, model):
        self.query(
            f"""update {table}
                  set embedding = %(vector)s::vector, embed_model = %(model)s,
                      embed_error = null, updated_at = now()
                where id = %(id)s and embedding is null""",
            {"vector": vector_literal(vector), "model": model, "id": id},
        )

    def mark_listening_embed_failed(self, table, id, message):
        self.query(
            f"""update {table}
                  set embed_attempts = embed_attempts + 1, embed_error = %s, updated_at = now()
                where id = %s""",
            (message[:500], id),
        )

    def clear_embed_state_if_complete(self, page_id):
        self.query(
            """update site_pages p
                  set embed_state = null, embed_error = null, updated_at = now()
                where p.id = %s
                  and p.embed_state is not null
                  and not exists (select 1 from site_chunks c
                                   where c.page_id = p.id and c.embedding is null)""",
            (page_id,),
        )
