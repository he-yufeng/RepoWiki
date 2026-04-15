"""litellm wrapper for repowiki."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

import litellm

litellm.suppress_debug_info = True

logger = logging.getLogger(__name__)


class LLMClient:
    """async LLM client backed by litellm."""

    def __init__(self, model: str, api_key: str = "", api_base: str = ""):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base or None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    async def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        response_format: dict | None = None,
    ) -> str:
        """non-streaming completion, returns the full response text."""
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base
        if response_format:
            kwargs["response_format"] = response_format

        try:
            resp = await litellm.acompletion(**kwargs)
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return f"[LLM Error: {e}]"

        usage = resp.usage
        if usage:
            self.total_input_tokens += usage.prompt_tokens or 0
            self.total_output_tokens += usage.completion_tokens or 0
        # litellm cost tracking
        try:
            cost = litellm.completion_cost(completion_response=resp)
            self.total_cost += cost
        except Exception:
            pass

        return resp.choices[0].message.content or ""

    async def stream(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> AsyncGenerator[str, None]:
        """streaming completion, yields text chunks."""
        kwargs: dict = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        if self.api_key:
            kwargs["api_key"] = self.api_key
        if self.api_base:
            kwargs["api_base"] = self.api_base

        try:
            resp = await litellm.acompletion(**kwargs)
            async for chunk in resp:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            logger.error("LLM stream failed: %s", e)
            yield f"[LLM Error: {e}]"
