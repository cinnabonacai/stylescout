"""
llm.py

Thin LLM wrapper for StyleScout, with a free option so this project
doesn't require a paid API key to run.

Provider priority, checked at call time via environment variables:

  1. GROQ_API_KEY       -> Groq's free tier (Llama 3.3 70B), via its
                            OpenAI-compatible endpoint. No credit card
                            required to get a key: console.groq.com
  2. ANTHROPIC_API_KEY  -> Claude, if you have a paid key and prefer it
  3. (neither set)      -> deterministic mock response, clearly labeled,
                            so the pipeline is still runnable/testable
                            without any key at all.

See README.md for how to get a free Groq key.
"""

from __future__ import annotations

import os
import re

_GROQ_MODEL = "openai/gpt-oss-120b"
_ANTHROPIC_MODEL = "claude-sonnet-4-5"


def has_real_provider() -> bool:
    """True if a real (non-mock) LLM provider is actually configured."""

    return bool(os.environ.get("GROQ_API_KEY") or os.environ.get("ANTHROPIC_API_KEY"))


_FENCE_RE = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE | re.MULTILINE)


def strip_json_fences(text: str) -> str:
    """
    Models (Groq's especially) often wrap a requested JSON object in a
    markdown code fence like:

        ```json
        {"a": 1}
        ```

    even when told to respond with ONLY the JSON. json.loads() chokes on
    the fence characters, so strip a leading/trailing fence (with an
    optional "json" language tag) before parsing. Safe to call on text
    that has no fence at all -- it's a no-op in that case.
    """

    return _FENCE_RE.sub("", text.strip()).strip()


def _mock_response(system: str, user: str) -> str:
    """
    A clearly-labeled stand-in used only when no API key is configured.
    Keeps the rest of the graph runnable for local development.
    """

    return (
        "[MOCK RESPONSE - set GROQ_API_KEY (free) or ANTHROPIC_API_KEY for real model output]\n"
        f"(system hint: {system[:60]}...)\n"
        f"(user input: {user[:200]})"
    )


def _call_groq(system: str, user: str, max_tokens: int, json_mode: bool = False) -> str:
    """
    Groq exposes an OpenAI-compatible chat completions endpoint, so we
    reuse the `openai` SDK and just point it at Groq's base URL.

    When json_mode=True, we pass response_format={"type": "json_object"}
    -- the OpenAI-compatible way to force the model to emit a bare JSON
    object instead of wrapping it in a markdown code fence (prose like
    "Here's the JSON:\n```json\n{...}\n```" is a common failure mode
    without this, and it breaks a plain json.loads()).
    """

    from openai import OpenAI

    client = OpenAI(
        api_key=os.environ["GROQ_API_KEY"],
        base_url="https://api.groq.com/openai/v1",
    )

    kwargs = {}
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    response = client.chat.completions.create(
        model=_GROQ_MODEL,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        **kwargs,
    )

    return response.choices[0].message.content


def _call_anthropic(system: str, user: str, max_tokens: int) -> str:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

    response = client.messages.create(
        model=_ANTHROPIC_MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    return response.content[0].text


def call_llm(system: str, user: str, max_tokens: int = 1024, json_mode: bool = False) -> str:
    """
    Send a single system+user turn to whichever provider is configured
    and return the text response. See module docstring for the
    provider priority order.

    json_mode=True asks the provider to return a bare JSON object (only
    Groq's OpenAI-compatible endpoint supports forcing this directly --
    see _call_groq). Callers that pass json_mode should still run the
    result through strip_json_fences() before json.loads(), since
    Anthropic and the mock response don't honor this flag and may still
    include a fence.
    """

    if os.environ.get("GROQ_API_KEY"):
        return _call_groq(system, user, max_tokens, json_mode=json_mode)

    if os.environ.get("ANTHROPIC_API_KEY"):
        return _call_anthropic(system, user, max_tokens)

    return _mock_response(system, user)
