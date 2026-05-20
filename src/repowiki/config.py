"""configuration management for repowiki."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_CONFIG_DIR = Path.home() / ".repowiki"
_CONFIG_FILE = _CONFIG_DIR / "config.json"

# shortcuts so users don't have to type full provider/model strings.
# values intentionally point at well-known stable model IDs that litellm recognises.
# update freely -- aliases are advisory, full model strings always work.
MODEL_ALIASES = {
    "deepseek": "deepseek/deepseek-chat",
    "deepseek-coder": "deepseek/deepseek-coder",
    "opus": "anthropic/claude-opus-4-5",
    "claude": "anthropic/claude-sonnet-4-5",
    "haiku": "anthropic/claude-haiku-4-5",
    "gpt": "openai/gpt-4o",
    "gpt-mini": "openai/gpt-4o-mini",
    "gemini": "gemini/gemini-1.5-pro",
    "gemini-flash": "gemini/gemini-1.5-flash",
    "qwen": "openrouter/qwen/qwen-2.5-72b-instruct",
    "kimi": "moonshot/moonshot-v1-128k",
    "glm": "openai/glm-4-plus",
}


def resolve_model(name: str) -> str:
    return MODEL_ALIASES.get(name, name)


@dataclass
class Config:
    model: str = "deepseek/deepseek-chat"
    api_key: str = ""
    api_base: str = ""
    language: str = "en"
    max_file_size: int = 200 * 1024  # 200 KB
    max_files: int = 1000
    output_dir: str = "./wiki"
    concurrency: int = 5
    # token budget for the slice of project context we ship to the LLM
    # (overview / architecture / reading-guide passes). 0 = unlimited.
    max_context_tokens: int = 32_000
    # --- RAG / chat retrieval tuning --------------------------------------
    # All of these are runtime-tunable so the user can adjust to repo shape
    # without touching code. Defaults reproduce the original behaviour.
    rag_chunk_max_lines: int = 60
    rag_chunk_soft_lines: int = 30
    rag_chunk_overlap_lines: int = 5
    rag_top_k: int = 5
    rag_min_score: float = 0.0
    rag_bm25_k1: float = 1.5
    rag_bm25_b: float = 0.75
    # When true, also feed the generated wiki markdown into the chat index
    # so questions about the architecture page hit the page directly.
    rag_index_wiki: bool = True

    @classmethod
    def load(cls) -> Config:
        """Load config from file, then override with env vars."""
        data: dict = {}
        if _CONFIG_FILE.exists():
            try:
                data = json.loads(_CONFIG_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                pass

        cfg = cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

        # env overrides
        if val := os.getenv("REPOWIKI_MODEL"):
            cfg.model = val
        if val := os.getenv("REPOWIKI_API_KEY"):
            cfg.api_key = val
        if val := os.getenv("REPOWIKI_API_BASE"):
            cfg.api_base = val
        if val := os.getenv("REPOWIKI_LANG"):
            cfg.language = val
        if val := os.getenv("REPOWIKI_CONCURRENCY"):
            try:
                cfg.concurrency = max(1, int(val))
            except ValueError:
                pass
        if val := os.getenv("REPOWIKI_MAX_CONTEXT_TOKENS"):
            try:
                cfg.max_context_tokens = max(0, int(val))
            except ValueError:
                pass

        # RAG tuning -- one env var per knob, parsed permissively so a typo
        # just falls back to the hardcoded default.
        def _int_env(name: str, default: int) -> int:
            val = os.getenv(name)
            if not val:
                return default
            try:
                return int(val)
            except ValueError:
                return default

        def _float_env(name: str, default: float) -> float:
            val = os.getenv(name)
            if not val:
                return default
            try:
                return float(val)
            except ValueError:
                return default

        cfg.rag_chunk_max_lines = _int_env("REPOWIKI_RAG_CHUNK_MAX_LINES", cfg.rag_chunk_max_lines)
        cfg.rag_chunk_soft_lines = _int_env("REPOWIKI_RAG_CHUNK_SOFT_LINES", cfg.rag_chunk_soft_lines)
        cfg.rag_chunk_overlap_lines = _int_env("REPOWIKI_RAG_CHUNK_OVERLAP", cfg.rag_chunk_overlap_lines)
        cfg.rag_top_k = _int_env("REPOWIKI_RAG_TOP_K", cfg.rag_top_k)
        cfg.rag_min_score = _float_env("REPOWIKI_RAG_MIN_SCORE", cfg.rag_min_score)
        cfg.rag_bm25_k1 = _float_env("REPOWIKI_RAG_BM25_K1", cfg.rag_bm25_k1)
        cfg.rag_bm25_b = _float_env("REPOWIKI_RAG_BM25_B", cfg.rag_bm25_b)
        if (val := os.getenv("REPOWIKI_RAG_INDEX_WIKI")) is not None:
            cfg.rag_index_wiki = val.strip().lower() not in ("0", "false", "no", "")

        # fall back to common provider keys
        if not cfg.api_key:
            for env_key in ("DEEPSEEK_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
                if val := os.getenv(env_key):
                    cfg.api_key = val
                    break

        cfg.model = resolve_model(cfg.model)
        return cfg

    def save(self) -> None:
        _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        data = {
            "model": self.model,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "language": self.language,
        }
        # don't persist empty values
        data = {k: v for k, v in data.items() if v}
        _CONFIG_FILE.write_text(json.dumps(data, indent=2) + "\n")

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}
