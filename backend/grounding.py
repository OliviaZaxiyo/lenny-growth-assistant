"""Flag quoted passages that do not appear word for word in the excerpts."""
import re


def _norm(s: str) -> str:
    s = s.lower().replace("\u2019", "'").replace("\u2011", "-")
    s = re.sub(r"\[[^\]]*\]", " ", s)          # drop tags like [inaudible 01:07:08]
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return " ".join(s.split())


def quoted_segments(text: str):
    parts = re.split(r'["\u201c\u201d]', text)
    return [p for i, p in enumerate(parts)
            if i % 2 == 1 and i < len(parts) - 1 and len(p.split()) >= 6]


def unverified_quotes(text: str, results: list):
    haystack = _norm(" ".join(r["content"] for r in results))
    bad = []
    for q in quoted_segments(text):
        pieces = [p for p in re.split(r"\.\.\.|\u2026", q) if len(p.split()) >= 4]
        if pieces and not all(_norm(p) in haystack for p in pieces):
            bad.append(q.strip())
    return bad