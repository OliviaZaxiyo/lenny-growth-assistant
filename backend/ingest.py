"""Load Lenny's Podcast transcripts into Postgres: parse, clean, chunk, insert."""
import argparse
import os
import re
from pathlib import Path

import psycopg
import yaml
from dotenv import load_dotenv

load_dotenv()

EPISODES_DIR = (
    Path(__file__).resolve().parent.parent
    / "data" / "lennys-podcast-transcripts" / "episodes"
)
MAX_CHARS = 2400  # roughly 500-600 tokens per chunk
# Exact duplicate files in the dataset (found with check_dupes.py)
SKIP_SLUGS = {
    "hamelshreya", "wes-kao-20", "ethan-evans-20", "yamashata",
    "nicole-forsgren-20", "fei-fei", "andy-raskin_",
}


# "Lenny (00:03:22):" or just "(00:05:54):" on its own line
HEADER = re.compile(r"^(?:(?P<speaker>.+?) )?\((?P<ts>\d{1,2}:\d{2}:\d{2})\):\s*$")
INAUDIBLE = re.compile(r"\[inaudible[^\]]*\]", re.I)
URLISH = re.compile(r"\b[\w-]+\.(?:com|io|co|ai)\b", re.I)
SPONSOR_START = re.compile(r"brought to you by\s+(?:the\s+)?([\w&-]+)", re.I)

def to_seconds(ts: str) -> int:
    h, m, s = (int(x) for x in ts.split(":"))
    return h * 3600 + m * 60 + s


def parse_file(path: Path):
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None, ""
    _, front, body = text.split("---", 2)
    meta = yaml.safe_load(front) or {}
    if "## Transcript" in body:
        body = body.split("## Transcript", 1)[1]
    return meta, body


def parse_turns(body: str):
    """Return a list of (speaker, start_seconds, text)."""
    turns = []
    speaker, ts, buf = None, None, []

    def flush():
        if ts is not None and buf:
            text = " ".join(" ".join(buf).split())
            if text:
                turns.append((speaker or "Unknown", ts, text))

    for line in body.splitlines():
        m = HEADER.match(line.strip())
        if m:
            flush()
            if m.group("speaker"):
                speaker = m.group("speaker").strip()
            ts = to_seconds(m.group("ts"))
            buf = []
        else:
            buf.append(line)
    flush()
    return turns


def is_sponsor(text: str) -> bool:
    return "brought to you by" in text.lower() or len(URLISH.findall(text)) >= 2


def split_long(text: str):
    """Split a very long turn into pieces at sentence boundaries."""
    if len(text) <= MAX_CHARS:
        return [text]
    pieces, cur = [], ""
    for sentence in re.split(r"(?<=[.!?])\s+", text):
        if cur and len(cur) + len(sentence) + 1 > MAX_CHARS:
            pieces.append(cur)
            cur = ""
        cur = f"{cur} {sentence}".strip()
    if cur:
        pieces.append(cur)
    return pieces


def build_chunks(turns):
    chunks, cur, cur_len = [], [], 0
    start, first_speaker = None, None

    def close():
        chunks.append({
            "idx": len(chunks),
            "start": start,
            "speaker": first_speaker,
            "content": "\n".join(cur),
        })

    for speaker, ts, text in turns:
        for piece in split_long(text):
            line = f"{speaker}: {piece}"
            if cur and cur_len + len(line) > MAX_CHARS:
                close()
                cur, cur_len, start = [], 0, None
            if start is None:
                start, first_speaker = ts, speaker
            cur.append(line)
            cur_len += len(line) + 1
    if cur:
        close()
    return chunks


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="only process N episodes")
    args = ap.parse_args()

    url = os.getenv("DATABASE_URL")
    if not url:
        raise SystemExit("DATABASE_URL is missing. Check your backend/.env file.")
    if not EPISODES_DIR.exists():
        raise SystemExit(f"Transcripts not found at {EPISODES_DIR}")

    files = sorted(EPISODES_DIR.glob("*/transcript.md"))
    if args.limit:
        files = files[: args.limit]
        files = [f for f in files if f.parent.name not in SKIP_SLUGS]

    n_episodes = n_chunks = n_dropped = 0
    with psycopg.connect(url, connect_timeout=10) as conn:
        for path in files:
            meta, body = parse_file(path)
            if meta is None:
                print("skipped (no metadata):", path.parent.name)
                continue

            turns = []
            sponsor = None  # name of the sponsor whose ad we are currently inside
            for speaker, ts, text in parse_turns(body):
                text = " ".join(INAUDIBLE.sub("", text).split())
                if not text:
                    continue
                m = SPONSOR_START.search(text)
                if m:
                    sponsor = m.group(1).lower()
                    n_dropped += 1
                    continue
                if sponsor:
                    if sponsor in text.lower():
                        n_dropped += 1
                        continue
                    sponsor = None  # the ad is over
                if is_sponsor(text):
                    n_dropped += 1
                    continue
                turns.append((speaker, ts, text))


            chunks = build_chunks(turns)
            if not chunks:
                print("skipped (no chunks):", path.parent.name)
                continue

            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into episodes (slug, guest, title, youtube_url, publish_date)
                    values (%s, %s, %s, %s, %s)
                    on conflict (slug) do update set
                        guest = excluded.guest, title = excluded.title,
                        youtube_url = excluded.youtube_url,
                        publish_date = excluded.publish_date
                    returning id
                    """,
                    (
                        path.parent.name,
                        meta.get("guest"),
                        meta.get("title"),
                        meta.get("youtube_url"),
                        meta.get("publish_date"),
                    ),
                )
                episode_id = cur.fetchone()[0]
                cur.execute("delete from chunks where episode_id = %s", (episode_id,))
                cur.executemany(
                    "insert into chunks (episode_id, chunk_index, start_seconds, speaker, content) "
                    "values (%s, %s, %s, %s, %s)",
                    [(episode_id, c["idx"], c["start"], c["speaker"], c["content"]) for c in chunks],
                )
            conn.commit()
            n_episodes += 1
            n_chunks += len(chunks)
            print(f"{path.parent.name}: {len(chunks)} chunks")

    print(f"\nDone. Episodes: {n_episodes}, chunks: {n_chunks}, sponsor turns dropped: {n_dropped}")


if __name__ == "__main__":
    main()