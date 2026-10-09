import os

import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")

if not url:
    raise SystemExit("DATABASE_URL is missing. Check your backend/.env file.")

with psycopg.connect(url, connect_timeout=10) as conn:
    version = conn.execute("select version()").fetchone()[0]
    print("Connected!", version)
    vec = conn.execute(
        "select extname from pg_extension where extname = 'vector'"
    ).fetchone()
    print("pgvector enabled:", vec is not None)