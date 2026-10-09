"""Pull an <artifact> block out of a model reply (with fallbacks for sloppy output)."""
import re
from uuid import uuid4

TAG = re.compile(r"<artifact\b([^>]*)>(.*?)(?:</artifact>|\Z)", re.S | re.I)
ATTR = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
FENCE = re.compile(r"```(html|markdown|md)\s*\n(.*?)```", re.S | re.I)


def extract_artifact(text: str):
    """Return (chat_text, artifact_dict_or_None)."""
    m = TAG.search(text)
    if m:
        attrs = dict(ATTR.findall(m.group(1)))
        kind = attrs.get("type", "").lower()
        title = attrs.get("title") or "Untitled"
        content = m.group(2).strip()
        chat = (text[: m.start()] + "\n\n" + text[m.end():]).strip()
    else:
        f = FENCE.search(text)
        if not f:
            return text.strip(), None
        kind = "html" if f.group(1).lower() == "html" else "markdown"
        title = "Untitled"
        content = f.group(2).strip()
        chat = (text[: f.start()] + text[f.end():]).strip()

    if kind not in ("html", "markdown"):
        kind = "html" if re.search(r"<\s*(!doctype|html|body|div)", content, re.I) else "markdown"
    content = re.sub(r"^```\w*\s*\n|\n```\s*$", "", content).strip()
    if not content:
        return text.strip(), None
    return chat or "Here is your artifact.", {
        "id": str(uuid4()), "type": kind, "title": title[:120], "content": content,
    }