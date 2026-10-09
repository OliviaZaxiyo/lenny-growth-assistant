import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

load_dotenv()
url = os.getenv("DATABASE_URL")
if not url:
    raise SystemExit("DATABASE_URL is missing. Check your backend/.env file.")

sql = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")

with psycopg.connect(url, connect_timeout=10) as conn:
    conn.execute(sql)
    tables = conn.execute(
        "select table_name from information_schema.tables "
        "where table_schema = 'public' order by table_name"
    ).fetchall()

print("Tables in database:", [t[0] for t in tables])