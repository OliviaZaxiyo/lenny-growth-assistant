"""Decide which skill handles a message: the UI mode first, then keyword rules."""
import re

MODE_TO_SKILL = {"qa": "qa", "essay": "ship30for30", "artifact": "artifact"}

BUILD = re.compile(r"\b(create|build|make|generate|draft|design|turn|convert|put|produce|give me)\b", re.I)
STRONG_ARTIFACT = re.compile(
    r"\b(html|css|landing page|web ?page|website|dashboard|artifact|mock-?up|infographic|widget|component)\b", re.I)
SOFT_ARTIFACT = re.compile(
    r"\b(markdown|document|one[- ]pager|cheat ?sheet|checklist|template|playbook|report)\b", re.I)
ESSAY = re.compile(
    r"\b(essay|ship ?-?30( ?for ?30)?|atomic essay|write (me )?(an? )?(article|post|blog))\b", re.I)


def choose_skill(text: str, mode: str = "auto"):
    """Return (skill, reason). Skills: qa, ship30for30, artifact."""
    if mode in MODE_TO_SKILL:
        return MODE_TO_SKILL[mode], f"you chose {mode} mode"
    build = BUILD.search(text)
    strong = STRONG_ARTIFACT.search(text)
    if build and strong:
        return "artifact", f"build request mentioning '{strong.group(0)}'"
    essay = ESSAY.search(text)
    if essay:
        return "ship30for30", f"matched '{essay.group(0)}'"
    soft = SOFT_ARTIFACT.search(text)
    if build and soft:
        return "artifact", f"build request mentioning '{soft.group(0)}'"
    return "qa", "no essay or artifact request detected"