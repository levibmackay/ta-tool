from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

_CONFIG_SEARCH = [
    Path("ta_config.toml"),
    Path.home() / ".ta_config.toml",
]

_VALID_FIELDS = {
    "tone", "strictness", "grading_style", "llm_provider",
    "model", "cache_ttl", "cache_dir", "max_tokens",
}


@dataclass
class Config:
    tone: Literal["friendly", "formal", "strict"] = "friendly"
    strictness: Literal["low", "medium", "high"] = "medium"
    grading_style: str = "standard"
    llm_provider: Literal["anthropic", "openai", "stub"] = "anthropic"
    model: str = "claude-sonnet-4-6"
    cache_ttl: int = 3600
    cache_dir: str = "~/.ta_cache"
    max_tokens: int = 4096


def load_config() -> Config:
    for path in _CONFIG_SEARCH:
        if path.exists():
            with open(path, "rb") as fh:
                raw = tomllib.load(fh)
            filtered = {k: v for k, v in raw.items() if k in _VALID_FIELDS}
            return Config(**filtered)
    return Config()
