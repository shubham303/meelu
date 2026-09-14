import math
import re

TARGET = 400
MAX = 800
MIN = 80
OVERLAP = 0.15
LEAD_WORDS = 40

HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def words(s):
    return len([w for w in re.split(r"\s+", s) if w])


def split_long(text):
    if words(text) <= MAX:
        return [text]

    lines = text.split("\n")
    lead = next(
        (ln for ln in lines if ln.strip() and not ln.startswith("|") and not ln.startswith("-")),
        None,
    )
    header = next((ln for ln in lines if ln.startswith("|")), None)

    out = []
    buf = []
    count = 0

    def emit():
        nonlocal buf, count
        if not buf:
            return
        prefix = []
        if out:
            if header and any(ln.startswith("|") for ln in buf):
                prefix.append(header)
            elif lead and any(ln.startswith("-") for ln in buf):
                prefix.append(lead)
        out.append("\n".join(prefix + buf))
        carry = math.ceil(len(buf) * OVERLAP)
        buf = buf[-carry:] if carry > 0 else []
        count = words(" ".join(buf))

    for line in lines:
        n = words(line)
        if count + n > TARGET and count >= MIN:
            emit()
        buf.append(line)
        count += n
    if buf:
        out.append("\n".join(buf))
    return out


def chunk_body(body_text, title):
    lines = body_text.split("\n")
    sections = []
    path = []
    current = []

    def flush():
        nonlocal current
        if any(ln.strip() for ln in current):
            sections.append({"path": list(path), "lines": current})
        current = []

    for line in lines:
        heading = HEADING_RE.match(line)
        if heading:
            flush()
            level = len(heading.group(1))
            path = path[: max(level - 2, 0)]
            path.append(heading.group(2).strip())
            continue
        current.append(line)
    flush()

    out = []
    root = [title] if title else []

    for section in sections:
        heading_path = " › ".join(p for p in root + section["path"] if p) or None
        text = "\n".join(section["lines"]).strip()
        if not text:
            continue

        for piece in split_long(text):
            last = out[-1] if out else None
            if words(piece) < MIN and last and words(last["text"]) + words(piece) <= MAX:
                last["text"] = f"{last['text']}\n{piece}"
                continue
            out.append({"heading_path": heading_path, "text": piece})

    for i, c in enumerate(out):
        c["ordinal"] = i
    return out


def lead_excerpt(body_text):
    if not body_text:
        return None
    line = next(
        (
            ln
            for ln in (raw.strip() for raw in body_text.split("\n"))
            if ln and not ln.startswith("#") and not ln.startswith("|") and not ln.startswith("-")
        ),
        None,
    )
    if not line:
        return None
    parts = [w for w in re.split(r"\s+", line) if w]
    if len(parts) > LEAD_WORDS:
        return " ".join(parts[:LEAD_WORDS]) + "…"
    return line


def page_chunk(page):
    raw_anchors = (
        a.get("anchor") if isinstance(a, dict) else None for a in (page["inbound_anchors"] or [])
    )
    anchors = [a for a in dict.fromkeys(raw_anchors) if a]
    parts = [
        p
        for p in [
            page["title"],
            *(page["h1"] or []),
            page["meta_description"],
            lead_excerpt(page["body_text"]),
            *anchors,
        ]
        if p
    ]
    if not parts:
        return None
    return {"heading_path": page["title"] or None, "text": " · ".join(parts)}
