"""Thin, optional wrapper around the Anthropic API.

The project works fully offline. If ANTHROPIC_API_KEY is set (or a key is passed
in), the agents use Claude for extraction and explanations, and automatically
fall back to the offline tools if anything goes wrong.
"""
from __future__ import annotations

import os
from typing import Optional

DEFAULT_MODEL = os.environ.get("LM_MODEL", "claude-sonnet-5-5")


class LLMClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        import anthropic  # imported lazily so the package is optional

        self._client = anthropic.Anthropic(api_key=api_key, timeout=60.0, max_retries=1)
        self.model = model

    def complete(self, system: str, user_content, max_tokens: int = 1000) -> str:
        message = self._client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_content}],
        )
        return "".join(
            block.text for block in message.content if getattr(block, "type", "") == "text"
        )


def get_llm(api_key: Optional[str] = None) -> Optional[LLMClient]:
    """Return an LLMClient, or None if no key / library is available."""
    key = (api_key or os.environ.get("ANTHROPIC_API_KEY") or "").strip()
    if not key:
        return None
    try:
        return LLMClient(key)
    except Exception:
        return None
