from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Optional

import diskcache

from .config import Config, load_config

_cache: Optional[diskcache.Cache] = None


def _get_cache(cfg: Config) -> diskcache.Cache:
    global _cache
    if _cache is None:
        cache_dir = Path(cfg.cache_dir).expanduser()
        cache_dir.mkdir(parents=True, exist_ok=True)
        _cache = diskcache.Cache(str(cache_dir))
    return _cache


def _cache_key(prompt: str, mode: str, provider: str, model: str) -> str:
    payload = json.dumps(
        {"prompt": prompt, "mode": mode, "provider": provider, "model": model},
        sort_keys=True,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def call_llm(
    prompt: str,
    mode: str = "default",
    system_prompt: Optional[str] = None,
    cfg: Optional[Config] = None,
    use_cache: bool = True,
    verbose: bool = False,
) -> str:
    """Single entry point for all LLM calls. Handles caching and provider dispatch."""
    if cfg is None:
        cfg = load_config()

    cache = _get_cache(cfg)
    key = _cache_key(prompt, mode, cfg.llm_provider, cfg.model)

    if use_cache and cfg.cache_ttl > 0 and key in cache:
        if verbose:
            print("[cache] hit — returning cached response")
        return cache[key]

    if verbose:
        print(f"[llm] provider={cfg.llm_provider} model={cfg.model} mode={mode}")

    result = _dispatch(prompt, system_prompt, cfg)

    if use_cache and cfg.cache_ttl > 0:
        cache.set(key, result, expire=cfg.cache_ttl)

    return result


def _dispatch(prompt: str, system_prompt: Optional[str], cfg: Config) -> str:
    if cfg.llm_provider == "anthropic":
        return _call_anthropic(prompt, system_prompt, cfg)
    if cfg.llm_provider == "openai":
        return _call_openai(prompt, system_prompt, cfg)
    if cfg.llm_provider == "stub":
        return json.dumps({"stub": True, "prompt_preview": prompt[:120]})
    raise ValueError(f"Unknown LLM provider: {cfg.llm_provider!r}")


def _call_anthropic(prompt: str, system_prompt: Optional[str], cfg: Config) -> str:
    try:
        import anthropic
    except ImportError:
        raise ImportError("Run: pip install anthropic") from None

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY is not set. Export it or add it to your shell profile."
        )

    client = anthropic.Anthropic(api_key=api_key)
    kwargs: dict = {
        "model": cfg.model,
        "max_tokens": cfg.max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    response = client.messages.create(**kwargs)
    return response.content[0].text


def _call_openai(prompt: str, system_prompt: Optional[str], cfg: Config) -> str:
    try:
        import openai
    except ImportError:
        raise ImportError("Run: pip install openai") from None

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise EnvironmentError("OPENAI_API_KEY is not set.")

    client = openai.OpenAI(api_key=api_key)
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = client.chat.completions.create(
        model=cfg.model,
        messages=messages,
        max_tokens=cfg.max_tokens,
    )
    return response.choices[0].message.content
