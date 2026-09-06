"""
Multi-provider AI helper with automatic failover.

Reads provider priority + API keys from config.py (config.config), tries
each provider in order, and automatically falls through to the next one if
a provider fails or is rate-limited. A provider that fails is put on a short
cooldown so we don't keep hammering a dead/exhausted key on every message.

Usage:
    from Nobara.helper.ai_provider import get_ai_response

    text, provider_used = await get_ai_response("Hello!", system_prompt="Be nice.")
    if text:
        ...
"""

import time
import logging
import httpx
from config import config

log = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 30
COOLDOWN_SECONDS = 300  # 5 minutes - how long a failed provider is skipped for

# name -> config. "type" selects which request format to use.
PROVIDERS = {
    "groq": {
        "type": "openai",
        "base_url": "https://api.groq.com/openai/v1",
        "key_attr": "GROQ_API_KEY",
        "model_attr": "GROQ_MODEL",
        "default_model": "llama-3.3-70b-versatile",
    },
    "openrouter": {
        "type": "openai",
        "base_url": "https://openrouter.ai/api/v1",
        "key_attr": "OPENROUTER_API_KEY",
        "model_attr": "OPENROUTER_MODEL",
        # "openrouter/free" auto-picks whatever model is currently free on
        # OpenRouter, avoiding 404s when a specific ":free" model gets pulled.
        "default_model": "openrouter/free",
        "extra_headers": {
            "HTTP-Referer": "https://github.com/",
            "X-Title": "Nobara",
        },
    },
    "cerebras": {
        "type": "openai",
        "base_url": "https://api.cerebras.ai/v1",
        "key_attr": "CEREBRAS_API_KEY",
        "model_attr": "CEREBRAS_MODEL",
        "default_model": "llama-3.3-70b",
    },
    "gemini": {
        "type": "gemini",
        "key_attr": "GEMINI_API_KEY",
        "model_attr": "GEMINI_MODEL",
        "default_model": "gemini-2.0-flash",
    },
    "together": {
        "type": "openai",
        "base_url": "https://api.together.xyz/v1",
        "key_attr": "TOGETHER_API_KEY",
        "model_attr": "TOGETHER_MODEL",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    },
    "huggingface": {
        "type": "openai",
        "base_url": "https://router.huggingface.co/v1",
        "key_attr": "HUGGINGFACE_API_KEY",
        "model_attr": "HUGGINGFACE_MODEL",
        "default_model": "meta-llama/Llama-3.3-70B-Instruct",
    },
    "deepseek": {
        "type": "openai",
        "base_url": "https://api.deepseek.com/v1",
        "key_attr": "DEEPSEEK_API_KEY",
        "model_attr": "DEEPSEEK_MODEL",
        "default_model": "deepseek-chat",
    },
    "openai": {
        "type": "openai",
        "base_url": "https://api.openai.com/v1",
        "key_attr": "OPENAI_API_KEY",
        "model_attr": "OPENAI_MODEL",
        "default_model": "gpt-4o-mini",
    },
}

DEFAULT_PRIORITY = "groq,openrouter,cerebras,gemini,together,huggingface,deepseek"

# In-memory cooldown tracker: provider name -> unix timestamp until which it's skipped
_cooldowns: dict[str, float] = {}


def _on_cooldown(name: str) -> bool:
    return _cooldowns.get(name, 0) > time.time()


def _set_cooldown(name: str, seconds: int = COOLDOWN_SECONDS) -> None:
    _cooldowns[name] = time.time() + seconds


def _get_priority_list() -> list[str]:
    raw = getattr(config, "AI_PROVIDER_PRIORITY", DEFAULT_PRIORITY)
    return [p.strip().lower() for p in raw.split(",") if p.strip()]


async def _chat_openai_compatible(cfg: dict, api_key: str, model: str, messages: list) -> str:
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    headers.update(cfg.get("extra_headers", {}))
    payload = {"model": model, "messages": messages, "max_tokens": 1024, "temperature": 0.8}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        resp = await client.post(f"{cfg['base_url']}/chat/completions", headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


async def _chat_gemini(api_key: str, model: str, messages: list) -> str:
    contents = []
    system_instruction = None
    for m in messages:
        if m["role"] == "system":
            system_instruction = m["content"]
            continue
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {"contents": contents}
    if system_instruction:
        payload["systemInstruction"] = {"parts": [{"text": system_instruction}]}

    async with httpx.AsyncClient(timeout=DEFAULT_TIMEOUT) as client:
        resp = await client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()


async def get_ai_response(prompt: str, system_prompt: str = "You are a helpful assistant.") -> tuple[str | None, str | None]:
    """
    Try each configured AI provider in priority order until one succeeds.

    Returns (response_text, provider_name_used) or (None, None) if every
    provider is unavailable/failed.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": prompt},
    ]

    for name in _get_priority_list():
        cfg = PROVIDERS.get(name)
        if not cfg:
            log.warning(f"Unknown AI provider in AI_PROVIDER_PRIORITY: {name}")
            continue

        if _on_cooldown(name):
            continue

        api_key = getattr(config, cfg["key_attr"], "").strip()
        if not api_key:
            continue  # provider not configured, skip silently

        model = getattr(config, cfg["model_attr"], cfg["default_model"]) or cfg["default_model"]

        try:
            if cfg["type"] == "gemini":
                text = await _chat_gemini(api_key, model, messages)
            else:
                text = await _chat_openai_compatible(cfg, api_key, model, messages)

            if text:
                return text, name

        except httpx.HTTPStatusError as e:
            status = e.response.status_code
            log.warning(f"[AI] {name} failed with HTTP {status}: {e}")
            # 401/403 = bad key, 404 = bad model, 429 = rate limited, 5xx = provider down
            _set_cooldown(name)
            continue
        except Exception as e:
            log.warning(f"[AI] {name} failed: {e}")
            _set_cooldown(name)
            continue

    return None, None
