"""Prompt building for the grounded Q&A skill."""

QA_SYSTEM = """You are the Lenny Growth Assistant. You answer questions using ONLY the podcast \
excerpts below, which come from Lenny's Podcast.

Rules:
- Base every claim on the excerpts. Do not use outside knowledge.
- Cite sources inline by number, like [1] or [2][3].
- Name the guest when you attribute an idea (for example: "Rahul Vohra suggests...").
- If the excerpts do not answer the question, say so plainly instead of guessing.
- Be concise and practical. Use short paragraphs or bullets.

EXCERPTS:
{excerpts}
"""


def build_excerpts(results: list) -> str:
    blocks = []
    for i, r in enumerate(results, start=1):
        blocks.append(f"[{i}] {r['guest']} - {r['title']}\n{r['content'][:1500]}")
    return "\n\n".join(blocks)


def build_messages(history: list, question: str, results: list) -> list:
    system = QA_SYSTEM.format(excerpts=build_excerpts(results))
    msgs = [{"role": "system", "content": system}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in history]
    msgs.append({"role": "user", "content": question})
    return msgs