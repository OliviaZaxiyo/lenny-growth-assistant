import json
import urllib.request

with urllib.request.urlopen("https://openrouter.ai/api/v1/models", timeout=20) as r:
    models = json.load(r)["data"]

free = [
    m for m in models
    if str(m.get("pricing", {}).get("prompt")) == "0"
    and str(m.get("pricing", {}).get("completion")) == "0"
]
free.sort(key=lambda m: m.get("context_length") or 0, reverse=True)

for m in free:
    print(f"{m['id']:65} context={m.get('context_length')}")
print(f"\n{len(free)} free models")