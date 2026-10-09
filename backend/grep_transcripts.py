import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent / "data" / "lennys-podcast-transcripts" / "episodes"
word = sys.argv[1].lower()
only = sys.argv[2].lower() if len(sys.argv) > 2 else ""

for f in sorted(root.glob("*/transcript.md")):
    if only and only not in f.parent.name:
        continue
    for i, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
        low = line.lower()
        if word in low:
            k = low.index(word)
            print(f"{f.parent.name} line {i}: ...{line[max(0, k - 150):k + 200]}...\n")