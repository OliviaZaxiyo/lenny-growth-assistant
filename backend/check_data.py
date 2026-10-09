import os

import psycopg
from dotenv import load_dotenv

load_dotenv()
with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    print("Episodes:", conn.execute("select count(*) from episodes").fetchone()[0])
    print("Chunks:  ", conn.execute("select count(*) from chunks").fetchone()[0])
    print("Avg chunk chars:", conn.execute("select round(avg(length(content))) from chunks").fetchone()[0])
    print("\nEpisodes sharing a YouTube URL:")
    rows = conn.execute(
        """
        select youtube_url, array_agg(slug order by slug)
        from episodes
        where youtube_url is not null
        group by youtube_url having count(*) > 1
        """
    ).fetchall()
    for url, slugs in rows:
        print(" ", slugs, url)
    print(f"({len(rows)} groups)")