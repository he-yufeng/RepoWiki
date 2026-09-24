"""litellm wrapper for repowiki."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from repowiki.llm.providers import (
    normalize_base_url,
    redact_secret,
    resolve_litellm_model,
    suggest_max_tokens,
)

logger = logging.getLogger(__name__)

_litellm = None


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

    def __init__(
        self,
        model: str,
        api_key: str = "",
        api_base: str = "",
        protocol: str | None = None,
    ):
        # fail fast here rather than mid-pipeline if litellm is broken/missing
        self._litellm = _load_litellm()
        self.protocol = protocol or None
        self.model = self._resolve_model(model)
        self.api_key = api_key
        self.api_base = self._resolve_base(api_base) or None
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_cost = 0.0

    def _resolve_model(self, model: str) -> str:
        """Qualify a bare model id with the protocol's litellm prefix."""
        if self.protocol:
            return resolve_litellm_model(self.protocol, model)
        return model

    def _resolve_base(self, api_base: str) -> str:
        """Normalise the base URL to the protocol's /v1 convention."""
        if self.protocol and api_base:
            return normalize_base_url(api_base, self.protocol)
        return api_base

    async def complete(
        self,
        messages: list[dict],
        *,
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict | None = None,
    ) -> str:
        """non-streaming completion, returns the full response text."""
        if max_tokens is None:
            max_tokens = suggest_max_tokens(self.model)
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
            resp = await self._litellm.acompletion(**kwargs)
        except Exception as e:
            # a provider's error text can quote the key back, so scrub it from
            # the log line as well as the string the caller sees
            detail = redact_secret(str(e), self.api_key)
            logger.error("LLM call failed: %s", detail)
            return f"[LLM Error: {detail}]"

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
        max_tokens: int | None = None,
    ) -> AsyncGenerator[str, None]:
        """streaming completion, yields text chunks."""
        if max_tokens is None:
            max_tokens = suggest_max_tokens(self.model)
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
            resp = await self._litellm.acompletion(**kwargs)
            async for chunk in resp:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
        except Exception as e:
            detail = redact_secret(str(e), self.api_key)
            logger.error("LLM stream failed: %s", detail)
            yield f"[LLM Error: {detail}]"
