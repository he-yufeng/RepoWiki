"""LLM client retries: transient failures get backoff, fatal ones don't."""

from __future__ import annotations

import asyncio

from repowiki.llm import client as client_module
from repowiki.llm.client import LLMClient


class RateLimitError(Exception):
    pass


class AuthenticationError(Exception):
    pass


def _usage():
    class U:
        prompt_tokens = 1
        completion_tokens = 1

    return U()


def _response(text: str):
    class R:
        usage = _usage()
        choices = [type("C", (), {"message": type("M", (), {"content": text})()})()]

    return R()


class FlakyLitellm:
    """acompletion fails with the scripted errors, then returns text."""

    def __init__(self, errors: list[Exception], text: str = "ok"):
        self._errors = list(errors)
        self.calls = 0

    async def acompletion(self, **kwargs):
        self.calls += 1
        if self._errors:
            raise self._errors.pop(0)
        return _response("ok")

    def completion_cost(self, completion_response=None):
        return 0.0


def _client(monkeypatch, fake: FlakyLitellm, **kw) -> LLMClient:
    monkeypatch.setattr(client_module, "_litellm", fake)
    return LLMClient(model="m", retry_delay=0, **kw)


def test_transient_error_retries_until_success(monkeypatch):
    fake = FlakyLitellm([RateLimitError("slow down")])
    c = _client(monkeypatch, fake)

    assert asyncio.run(c.complete([{"role": "user", "content": "hi"}])) == "ok"
    assert fake.calls == 2
    assert c.total_input_tokens == 1


def test_exhausted_retries_return_the_error_string(monkeypatch):
    fake = FlakyLitellm([RateLimitError("x"), RateLimitError("y"), RateLimitError("z")])
    c = _client(monkeypatch, fake, max_retries=3)

    out = asyncio.run(c.complete([{"role": "user", "content": "hi"}]))
    assert out.startswith("[LLM Error:")
    assert fake.calls == 3


def test_non_transient_error_is_not_retried(monkeypatch):
    fake = FlakyLitellm([AuthenticationError("bad key")])
    c = _client(monkeypatch, fake)

    out = asyncio.run(c.complete([{"role": "user", "content": "hi"}]))
    assert out.startswith("[LLM Error:")
    assert fake.calls == 1  # no point retrying a 401


def test_stream_retries_the_connect_but_not_mid_stream(monkeypatch):
    class Chunky:
        def __init__(self):
            self.n = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            self.n += 1
            if self.n == 1:
                delta = type("D", (), {"content": "he"})()
                return type("C", (), {"choices": [type("X", (), {"delta": delta})()]})()
            raise RateLimitError("socket dropped")

    class StreamFake(FlakyLitellm):
        async def acompletion(self, **kwargs):
            self.calls += 1
            if self.calls == 1:
                raise RateLimitError("connect failed")
            return Chunky()

    fake = StreamFake([])
    monkeypatch.setattr(client_module, "_litellm", fake)
    c = LLMClient(model="m", retry_delay=0)

    async def collect():
        return [t async for t in c.stream([{"role": "user", "content": "hi"}])]

    out = asyncio.run(collect())
    assert fake.calls == 2  # one retry on connect
    assert out[0] == "he"
    assert out[1].startswith("[LLM Error:")  # mid-stream stays fatal
