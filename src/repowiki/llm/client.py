"""litellm wrapper for repowiki."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)

_litellm = None

# transient failures worth retrying, matched by class name: importing
# litellm.exceptions here would defeat the lazy load that `repowiki map`
# relies on (see tests/test_lazy_litellm.py)
_TRANSIENT_ERRORS = {
    "RateLimitError",
    "APIConnectionError",
    "Timeout",
    "ServiceUnavailableError",
    "InternalServerError",
}


def _load_litellm():
    # litellm's import takes seconds (and can hang on 3.14), so zero-LLM paths
    # like `repowiki map` must not pay it; import only on first LLM use
    global _litellm
    if _litellm is None:
        import litellm

        litellm.suppress_debug_info = True
        _litellm = litellm
    return _litellm


class LLMClient:
    """async LLM client backed by litellm."""

    def __init__(self, model: str, api_key: str = "", api_base: str = "",
                 max_retries: int = 3, retry_delay: float = 1.0):
        # fail fast here rather than mid-pipeline if litellm is broken/missing
        self._litellm = _load_litellm()
        self.model = model
        self.api_key = api_key
        self.api_base = api_base or None
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    async def _complete_with_retry(self, kwargs: dict):
        """acompletion with backoff on transient failures. Returns the exception
        instead of raising after the last attempt, so callers keep their
        error-string contract."""
        for attempt in range(self.max_retries):
            try:
                return await self._litellm.acompletion(**kwargs)
            except Exception as e:
                if type(e).__name__ not in _TRANSIENT_ERRORS or attempt == self.max_retries - 1:
                    return e
                delay = self.retry_delay * 2 ** attempt
                logger.warning(
                    "LLM call failed (%s), retry %d/%d in %.1fs",
                    type(e).__name__, attempt + 2, self.max_retries, delay,
                )
                await asyncio.sleep(delay)

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

        resp = await self._complete_with_retry(kwargs)
        if isinstance(resp, Exception):
            logger.error("LLM call failed: %s", resp)
            return f"[LLM Error: {resp}]"

        usage = resp.usage
        if usage:
            self.total_input_tokens += usage.prompt_tokens or 0
            self.total_output_tokens += usage.completion_tokens or 0
        # litellm cost tracking
        try:
            cost = self._litellm.completion_cost(completion_response=resp)
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

        resp = await self._complete_with_retry(kwargs)
        if isinstance(resp, Exception):
            logger.error("LLM stream failed: %s", resp)
            yield f"[LLM Error: {resp}]"
            return
        try:
            # retrying past this point would duplicate already-yielded text,
            # so a mid-stream failure stays fatal
            async for chunk in resp:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            logger.error("LLM stream failed: %s", e)
            yield f"[LLM Error: {e}]"
