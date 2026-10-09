import json
import sys
import uuid

import requests

BASE = "http://127.0.0.1:8000"
args = sys.argv[1:]
mode = args.pop(0) if args and args[0] in ("auto", "qa", "essay", "artifact") else "auto"
question = " ".join(args) or "How should I price my product early on?"

s = requests.post(f"{BASE}/sessions", json={"user_id": str(uuid.uuid4())}).json()
print("Session:", s["id"], "| mode:", mode)

with requests.post(f"{BASE}/sessions/{s['id']}/messages",
                   json={"content": question, "mode": mode}, stream=True) as r:
    print("HTTP", r.status_code)
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        ev = json.loads(line[6:])
        t = ev["type"]
        if t == "skill":
            print(f"[skill] {ev['skill']} ({ev['reason']})")
        elif t == "sources":
            print("[sources]", [f"{x['n']}. {x['guest']}" for x in ev["sources"]])
        elif t == "token":
            print(ev["text"], end="", flush=True)
        elif t == "artifact":
            a = ev["artifact"]
            print(f"\n[artifact] {a['type']} '{a['title']}' ({len(a['content'])} chars)")
        else:
            print(f"\n[{t}]", ev.get("message") or ev.get("words") or "")

data = requests.get(f"{BASE}/sessions/{s['id']}").json()
print("\nSaved messages:", len(data["messages"]), "| saved artifacts:", len(data["artifacts"]))