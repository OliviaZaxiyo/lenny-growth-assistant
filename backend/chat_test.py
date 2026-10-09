import json
import sys
import uuid

import requests

BASE = "http://127.0.0.1:8000"
question = " ".join(sys.argv[1:]) or "How should I price my product early on?"

s = requests.post(f"{BASE}/sessions", json={"user_id": str(uuid.uuid4())}).json()
print("Session:", s["id"])

with requests.post(f"{BASE}/sessions/{s['id']}/messages", json={"content": question}, stream=True) as r:
    print("HTTP", r.status_code)
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "):
            continue
        ev = json.loads(line[6:])
        if ev["type"] == "sources":
            print("Sources:", [f"{x['n']}. {x['guest']}" for x in ev["sources"]])
        elif ev["type"] == "token":
            print(ev["text"], end="", flush=True)
        else:
            print(f"\n[{ev['type']}]", ev.get("message", ""))

saved = requests.get(f"{BASE}/sessions/{s['id']}").json()["messages"]
print("\nSaved messages:", len(saved))