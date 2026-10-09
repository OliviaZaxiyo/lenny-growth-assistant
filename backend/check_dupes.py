import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

SQL = """
with shared as (
    select ca.episode_id as a, cb.episode_id as b, count(*) as n
    from chunks ca
    join chunks cb on ca.content = cb.content and ca.episode_id < cb.episode_id
    group by 1, 2
)
select ea.slug, eb.slug, coalesce(s.n, 0),
       (select count(*) from chunks where episode_id = ea.id),
       (select count(*) from chunks where episode_id = eb.id),
       ea.publish_date, eb.publish_date
from episodes ea
join episodes eb on ea.youtube_url = eb.youtube_url and ea.id < eb.id
left join shared s on s.a = ea.id and s.b = eb.id
order by 3 desc
"""

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    rows = conn.execute(SQL).fetchall()

print("slug_a | slug_b | identical_chunks | chunks_a | chunks_b | date_a | date_b\n")
for r in rows:
    print(" | ".join(str(x) for x in r))
print(f"\n{len(rows)} pairs")