"""LLM providers: Anthropic is the primary, Gemini is the fallback."""

import logging

from anthropic import AsyncAnthropic
from google import genai
from google.genai import types as genai_types

from .config import settings

logger = logging.getLogger(__name__)


class ProviderError(Exception):
    pass


async def ask_anthropic(messages: list[dict], system: str) -> str:
    if not settings.anthropic_api_key:
        raise ProviderError("ANTHROPIC_API_KEY is not set")

    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    response = await client.messages.create(
        model=settings.anthropic_model,
        max_tokens=settings.max_tokens,
        system=system,
        messages=messages,
    )
    return "".join(block.text for block in response.content if block.type == "text")


async def ask_gemini(messages: list[dict], system: str) -> str:
    if not settings.gemini_api_key:
        raise ProviderError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=settings.gemini_api_key)
    # Gemini uses "model" instead of "assistant" for the bot's role
    contents = [
        genai_types.Content(
            role="model" if m["role"] == "assistant" else "user",
            parts=[genai_types.Part(text=m["content"])],
        )
        for m in messages
    ]
    response = await client.aio.models.generate_content(
        model=settings.gemini_model,
        contents=contents,
        config=genai_types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=settings.max_tokens,
        ),
    )
    return response.text or ""


async def chat(messages: list[dict], system: str) -> tuple[str, str]:
    """Return (reply, provider_name). Tries Anthropic first, then Gemini."""
    errors = []
    for name, provider in (("anthropic", ask_anthropic), ("gemini", ask_gemini)):
        try:
            return await provider(messages, system), name
        except Exception as exc:
            logger.warning("%s failed: %s", name, exc)
            errors.append(f"{name}: {exc}")
    raise ProviderError("All providers failed -> " + " | ".join(errors))
