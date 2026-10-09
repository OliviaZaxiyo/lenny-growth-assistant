"""Find the transcript chunks most relevant to a question (full-text search)."""
import os
import re
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()

STOPWORDS = set(
    """a an and are as at be but by can could did do does for from had has have how i if in
    into is it its me my of on or our should so than that the their them then there these they
    this to up us was we were what when where which who why will with would you your about tell
    give explain say says said think thing things get got make made lenny podcast guest guests
    episode episodes""".split()
)

# Words found in more than this share of all chunks are too common to help
MAX_SHARE = 0.10


def extract_terms(question: str):
    words = re.findall(r"[a-z0-9]+", question.lower())
    terms = []
    for w in words:
        if len(w) > 2 and w not in STOPWORDS and w not in terms:
            terms.append(w)
    return terms


def informative_terms(conn, terms):
    """Keep only words that are reasonably rare across the whole knowledge base."""
    if not terms:
        return []
    total = conn.execute("select count(*) from chunks").fetchone()[0]
    rows = conn.execute(
        """
        select t, (select count(*) from chunks where tsv @@ to_tsquery('english', t))
        from unnest(%s::text[]) as t
        """,
        (terms,),
    ).fetchall()
    keep = [t for t, n in rows if 0 < n <= total * MAX_SHARE]
    return keep or terms


def timestamp_url(youtube_url, seconds):
    if not youtube_url:
        return None
    sep = "&" if "?" in youtube_url else "?"
    return f"{youtube_url}{sep}t={seconds or 0}s"


def search(question: str, k: int = 6, per_episode: int = 2):
    terms = extract_terms(question)
    if not terms:
        return [], []
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is missing")

    with psycopg.connect(url, connect_timeout=10) as conn:
        used = informative_terms(conn, terms)
        tsq = " | ".join(used)
        rows = conn.execute(
            """
            select e.slug, e.guest, e.title, e.youtube_url, c.start_seconds, c.content,
                   ts_rank_cd(c.tsv, to_tsquery('english', %s)) as score
            from chunks c join episodes e on e.id = c.episode_id
            where c.tsv @@ to_tsquery('english', %s)
            order by score desc
            limit 60
            """,
            (tsq, tsq),
        ).fetchall()

    results, per_ep, seen = [], {}, set()
    for slug, guest, title, yt, start, content, score in rows:
        fingerprint = content[:200]
        if fingerprint in seen or per_ep.get(slug, 0) >= per_episode:
            continue
        seen.add(fingerprint)
        per_ep[slug] = per_ep.get(slug, 0) + 1
        results.append({
            "guest": guest,
            "title": title,
            "url": timestamp_url(yt, start),
            "start_seconds": start,
            "content": content,
            "score": float(score),
        })
        if len(results) >= k:
            break
    return results, used


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "how should I price my product"
    results, used = search(q)
    print("Search words used:", used)
    for r in results:
        print(f"\n[{r['guest']}] score={r['score']:.2f}\n{r['url']}\n{r['content'][:250]}...")