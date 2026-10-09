"""One place that talks to the language model.

LLM_PROVIDER=openrouter  -> real model through OpenRouter
LLM_PROVIDER=mock        -> fake streamed text, costs no requests (for building the UI)
LLM_MODEL can hold several ids separated by commas; they are tried in order.
"""
import os
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


def stream_chat(messages: list, model: str | None = None) -> Iterator[str]:
    """Yield the reply piece by piece."""
    provider = os.getenv("LLM_PROVIDER", "openrouter")

    if provider == "mock":
        reply = "This is a mock reply, so no OpenRouter request was used. " * 3
        for word in reply.split():
            time.sleep(0.03)
            yield word + " "
        return

    if provider != "openrouter":
        raise LLMError(f"Unknown LLM_PROVIDER '{provider}'. Use 'openrouter' or 'mock'.")

    key = os.getenv("OPENROUTER_API_KEY", "")
    if not key or key.startswith("paste-") or key.startswith("your-"):
        raise LLMError("OPENROUTER_API_KEY is not set. Add your key to backend/.env.")
    names = [m.strip() for m in (model or os.getenv("LLM_MODEL", "")).split(",") if m.strip()]
    if not names:
        raise LLMError("LLM_MODEL is not set. Add a model id to backend/.env.")

    client = OpenAI(base_url=OPENROUTER_URL, api_key=key, timeout=60)
    last_error = None
    for name in names:
        started = False
        try:
            stream = client.chat.completions.create(model=name, messages=messages, stream=True)
            for part in stream:
                if part.choices and part.choices[0].delta.content:
                    started = True
                    yield part.choices[0].delta.content
            if started:
                return
            last_error = None  # empty answer: try the next model
        except AuthenticationError:
            raise LLMError("OpenRouter rejected the API key. Check OPENROUTER_API_KEY.")
        except (APIStatusError, APITimeoutError, APIConnectionError) as e:
            if started:
                raise LLMError("The model stopped in the middle of the answer. Please try again.")
            last_error = e  # try the next model
    raise LLMError(_friendly(last_error, names))