import os
import sys

import psycopg
from dotenv import load_dotenv

load_dotenv()
query = " ".join(sys.argv[1:]) or "curiosity loop"

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    rows = conn.execute(
        """
        select e.guest, c.start_seconds, left(c.content, 220)
        from chunks c join episodes e on e.id = c.episode_id
        where c.tsv @@ websearch_to_tsquery('english', %s)
        order by ts_rank(c.tsv, websearch_to_tsquery('english', %s)) desc
        limit 5
        """,
        (query, query),
    ).fetchall()

for guest, start, snippet in rows:
    print(f"\n[{guest} @ {start}s]\n{snippet}...")
print(f"\n{len(rows)} results")