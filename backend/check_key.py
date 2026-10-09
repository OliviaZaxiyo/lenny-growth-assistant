import os
import urllib.error
import urllib.request

from dotenv import dotenv_values, load_dotenv

file_key = dotenv_values(".env").get("OPENROUTER_API_KEY") or ""
load_dotenv()
used_key = os.getenv("OPENROUTER_API_KEY") or ""


def mask(k):
    return f"{k[:9]}...{k[-3:]} (length {len(k)})" if k else "(empty)"


print("Key in the .env file:", mask(file_key))
print("Key Python is using :", mask(used_key))

if file_key != used_key:
    print("PROBLEM: Python is using a different key from the .env file (an old one set in Windows).")
if used_key != used_key.strip() or used_key[:1] in "\"'":
    print("PROBLEM: the key has a space or quote mark around it.")
if used_key and not used_key.startswith("sk-or-"):
    print("PROBLEM: the key does not start with sk-or-")

for path in ("key", "auth/key"):
    req = urllib.request.Request(
        f"https://openrouter.ai/api/v1/{path}",
        headers={"Authorization": f"Bearer {used_key.strip()}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            print(f"OpenRouter check ({path}): HTTP {r.status} -> the key is VALID")
            break
    except urllib.error.HTTPError as e:
        print(f"OpenRouter check ({path}): HTTP {e.code}")
    except Exception as e:
        print("Could not reach OpenRouter:", e)
        break