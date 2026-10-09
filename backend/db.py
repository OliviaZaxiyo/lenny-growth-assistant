"""Database connection helper."""
import os

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row

load_dotenv()


def connect():
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is missing. Add it to backend/.env.")
    return psycopg.connect(url, connect_timeout=10, row_factory=dict_row, prepare_threshold=None)