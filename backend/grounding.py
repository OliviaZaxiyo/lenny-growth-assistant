"""Keep quotation marks honest: only text found word for word in the excerpts stays in quotes."""
import re

QUOTE = re.compile(r'["\u201c]([^"\u201c\u201d]{20,}?)["\u201d]')


def _norm(s: str) -> str:
    s = s.lower().replace("\u2019", "'").replace("\u2011", "-")
    s = re.sub(r"\[[^\]]*\]", " ", s)          # drop tags like [inaudible 01:07:08]
    s = re.sub(r"[^a-z0-9' ]+", " ", s)
    return " ".join(s.split())


def _is_verbatim(quote: str, haystack: str) -> bool:
    pieces = [p for p in re.split(r"\.\.\.|\u2026", quote) if len(p.split()) >= 4]
    return (not pieces) or all(_norm(p) in haystack for p in pieces)


def dequote(text: str, results: list):
    """Return (clean_text, removed). Quotes of 6+ words that are not verbatim lose their quote marks."""
    haystack = _norm(" ".join(r["content"] for r in results))
    removed = []

    def fix(m):
        q = m.group(1)
        if len(q.split()) < 6 or _is_verbatim(q, haystack):
            return m.group(0)
        removed.append(q.strip())
        return q

    return QUOTE.sub(fix, text), removed


def unverified_quotes(text: str, results: list):
    return dequote(text, results)[1]