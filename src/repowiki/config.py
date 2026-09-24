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

# shortcuts so users don't have to type full provider/model strings
MODEL_ALIASES = {
    "deepseek": "deepseek/deepseek-chat",
    "opus": "anthropic/claude-opus-4-6",
    "claude": "anthropic/claude-sonnet-4-6",
    "gpt": "gpt-5.4",
    "gpt-mini": "gpt-5.4-mini",
    "gemini": "gemini/gemini-3.1-pro-preview",
    "gemini-flash": "gemini/gemini-2.5-flash",
    # Route through each vendor's native litellm provider so the request hits
    # the right endpoint; the old openai/ values silently 404'd on OpenAI.
    "qwen": "dashscope/qwen3.5-plus",
    "kimi": "moonshot/kimi-k2.6",
    "glm": "zai/glm-5",
    # MiniMax has no native litellm provider; it stays OpenAI-compatible and
    # relies on the provider registry supplying its base_url.
    "minimax": "openai/MiniMax-M2.7",
}

# Human labels for those aliases, shown by the settings form's preset picker.
# Same keys as MODEL_ALIASES (served to the UI together) so a new alias only
# needs a label to appear there; a missing label falls back to the alias id.
MODEL_LABELS = {
    "deepseek": "DeepSeek V3.2",
    "opus": "Claude Opus 4.6",
    "claude": "Claude Sonnet 4.6",
    "gpt": "GPT-5.4",
    "gpt-mini": "GPT-5.4 Mini",
    "gemini": "Gemini 3.1 Pro",
    "gemini-flash": "Gemini 2.5 Flash",
    "qwen": "Qwen3.5 Plus",
    "kimi": "Kimi K2.6",
    "glm": "GLM-5",
    "minimax": "MiniMax M2.7",
}


def resolve_model(name: str) -> str:
    return MODEL_ALIASES.get(name, name)


@dataclass
class Config:
    model: str = "deepseek/deepseek-chat"
    api_key: str = ""
    api_base: str = ""
    protocol: str = ""
    language: str = "en"
    max_file_size: int = 200 * 1024  # 200 KB
    max_files: int = 1000
    output_dir: str = "./wiki"
    concurrency: int = 5

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
        if val := os.getenv("REPOWIKI_PROTOCOL"):
            cfg.protocol = val
        if val := os.getenv("REPOWIKI_LANG"):
            cfg.language = val

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
            "protocol": self.protocol,
            "language": self.language,
        }
        # don't persist empty values
        data = {k: v for k, v in data.items() if v}
        _CONFIG_FILE.write_text(json.dumps(data, indent=2) + "\n")

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}
