"""One place that talks to the language model.

LLM_PROVIDER=openrouter  -> real model through OpenRouter
LLM_PROVIDER=mock        -> fake streamed text, costs no requests
LLM_MODEL can hold several ids separated by commas; they are tried in order.
"""
import os
import re
import time
from typing import Iterator

from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)

load_dotenv()

OPENROUTER_URL = "https://openrouter.ai/api/v1"


class LLMError(Exception):
    """An error whose message is safe and helpful to show to the user."""


def current_config() -> dict:
    return {
        "provider": os.getenv("LLM_PROVIDER", "openrouter"),
        "model": os.getenv("LLM_MODEL", ""),
    }


def _mock_reply(messages) -> str:
    system = " ".join(m["content"] for m in messages if m["role"] == "system")
    if "artifact_builder" in system:
        return (
            "I built a small demo page (mock mode, no model request used).\n\n"
            '<artifact type="html" title="Mock demo page">\n'
            "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><style>"
            "body{font-family:system-ui,sans-serif;padding:2rem;background:#eef2ff}"
            "h1{color:#4338ca}.card{background:white;border-radius:12px;padding:1rem 1.5rem;"
            "box-shadow:0 1px 4px #0002}</style></head><body><h1>Mock artifact</h1>"
            '<div class="card"><p>This HTML is rendered inside the app viewer.</p></div>'
            "</body></html>\n</artifact>"
        )
    if "ship30for30_essay" in system:
        return ("# 5 Mock Lessons For Testing An Essay Skill\n\nThis is a short mock essay. "
                "It is far below 1,250 words, so the revision step will run.\n\n"
                "## Lesson 1: Test the pipeline\n\n**Mock text keeps your requests safe.** [1]\n")
    return "This is a mock answer, so no OpenRouter request was used. [1] "


def _friendly(error, tried):
    names = ", ".join(tried)
    if isinstance(error, RateLimitError):
        return (f"All models tried are rate-limited right now ({names}). "
                "Free models share limited capacity. Wait a minute, or add another model to LLM_MODEL.")
    if isinstance(error, (APITimeoutError, APIConnectionError)):
        return "Could not reach OpenRouter in time. Check your internet and try again."
    if isinstance(error, APIStatusError):
        return (f"OpenRouter returned error {error.status_code} for the models tried ({names}). "
                "They may be unavailable. Check LLM_MODEL, your OpenRouter privacy settings and credits.")
    return f"The models tried ({names}) returned no answer. Try again or change LLM_MODEL."


def stream_chat(messages: list, model: str | None = None, max_tokens: int | None = None) -> Iterator[str]:
    """Yield the reply piece by piece."""
    provider = os.getenv("LLM_PROVIDER", "openrouter")

    if provider == "mock":
        for piece in re.findall(r"\S+\s*", _mock_reply(messages)):
            time.sleep(0.02)
            yield piece
        return

    if provider != "openrouter":
        raise LLMError(f"Unknown LLM_PROVIDER '{provider}'. Use 'openrouter' or 'mock'.")

    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key or key.startswith("paste-") or key.startswith("your-"):
        raise LLMError("OPENROUTER_API_KEY is not set. Add your key to backend/.env.")
    names = [m.strip() for m in (model or os.getenv("LLM_MODEL", "")).split(",") if m.strip()]
    if not names:
        raise LLMError("LLM_MODEL is not set. Add a model id to backend/.env.")

    client = OpenAI(base_url=OPENROUTER_URL, api_key=key, timeout=90)
    extra = {"max_tokens": max_tokens} if max_tokens else {}
    last_error = None
    for name in names:
        started = False
        try:
            stream = client.chat.completions.create(model=name, messages=messages, stream=True, **extra)
            for part in stream:
                if part.choices and part.choices[0].delta.content:
                    started = True
                    yield part.choices[0].delta.content
            if started:
                return
            last_error = None
        except AuthenticationError:
            raise LLMError("OpenRouter rejected the API key. Check OPENROUTER_API_KEY.")
        except (APIStatusError, APITimeoutError, APIConnectionError) as e:
            if started:
                raise LLMError("The model stopped in the middle of the answer. Please try again.")
            last_error = e
    raise LLMError(_friendly(last_error, names))