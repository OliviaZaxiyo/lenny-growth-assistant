"""Prompt building. Each skill is a markdown file in backend/skills/."""
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parent / "skills"


def load_skill(name: str) -> str:
    return (SKILLS_DIR / f"{name}.md").read_text(encoding="utf-8")


def _trim(text: str, limit: int = 1500) -> str:
    """Cut at a sentence end so the model never quotes a half-finished sentence."""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return cut[: end + 1] if end > limit * 0.5 else cut


def build_excerpts(results: list) -> str:
    blocks = []
    for i, r in enumerate(results, start=1):
        blocks.append(f"[{i}] {r['guest']} - {r['title']}\n{_trim(r['content'])}")
    return "\n\n".join(blocks)


def build_messages(skill, history, question, results, latest_artifact=None):
    system = load_skill(skill)
    if results:
        system += "\n\nEXCERPTS:\n" + build_excerpts(results)
    if skill == "artifact" and latest_artifact:
        system += (
            "\n\nCURRENT ARTIFACT:\n"
            f"type={latest_artifact['type']} title={latest_artifact['title']}\n"
            f"{latest_artifact['content'][:12000]}"
        )
    msgs = [{"role": "system", "content": system}]
    msgs += [{"role": m["role"], "content": m["content"]} for m in history]
    msgs.append({"role": "user", "content": question})
    return msgs


def revision_messages(msgs, draft, words, target):
    direction = "longer" if words < target else "shorter"
    return msgs + [
        {"role": "assistant", "content": draft},
        {
            "role": "user",
            "content": (
                f"This draft is {words} words. Rewrite it to be about {target} words "
                f"(make it {direction}), keeping the same headline, structure, style and citations, "
                "and using only the excerpts. Output only the revised essay."
            ),
        },
    ]