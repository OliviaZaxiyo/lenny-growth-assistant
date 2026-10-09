import os

import psycopg
from dotenv import load_dotenv

load_dotenv()

DELETE = [
    "hamelshreya",
    "wes-kao-20",
    "ethan-evans-20",
    "yamashata",
    "nicole-forsgren-20",
    "fei-fei",
    "andy-raskin_",
]

with psycopg.connect(os.environ["DATABASE_URL"]) as conn:
    rows = conn.execute(
        "delete from episodes where slug = any(%s) returning slug", (DELETE,)
    ).fetchall()
    print("Deleted:", sorted(r[0] for r in rows))
    print("Episodes left:", conn.execute("select count(*) from episodes").fetchone()[0])
    print("Chunks left:  ", conn.execute("select count(*) from chunks").fetchone()[0])