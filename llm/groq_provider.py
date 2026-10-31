"""
llm/groq_provider.py — Groq (free tier) provider for Nexus AI Governance Platform.

Groq serves open models (Llama 3.x, GPT-OSS …) through an OpenAI-compatible API
with a free tier (no credit card). Get a key at https://console.groq.com/keys and set:

    GROQ_API_KEY = "gsk_..."
    GROQ_MODEL   = "llama-3.3-70b-versatile"     # optional

Free-tier limits are per-minute / per-day token budgets, so long prompts are
trimmed to fit (see GROQ_MAX_PROMPT_CHARS) rather than failing with HTTP 413/429.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.llm.groq_provider")

DEFAULT_MODEL = "llama-3.3-70b-versatile"


def _key(api_key: Optional[str] = None) -> str:
    key = api_key or settings.GROQ_API_KEY
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set.")
    return key


def is_available(api_key: Optional[str] = None) -> bool:
    return bool(api_key or settings.GROQ_API_KEY)


def _fit_messages(messages: List[Dict[str, str]], max_chars: int) -> List[Dict[str, str]]:
    """
    Trim the longest message so the whole prompt fits the free-tier token budget
    (~4 characters per token). Keeps the start of the text, which holds the
    instructions and the first part of the document.
    """
    msgs = [dict(m) for m in messages]
    total = sum(len(m.get("content", "")) for m in msgs)
    if total <= max_chars:
        return msgs
    excess = total - max_chars
    longest = max(msgs, key=lambda m: len(m.get("content", "")))
    content = longest.get("content", "")
    keep = max(500, len(content) - excess - 80)
    longest["content"] = content[:keep] + "\n\n[... text truncated to fit the free API limit ...]"
    logger.info("Groq prompt trimmed from %d to ~%d chars", total, max_chars)
    return msgs


def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 1500,
    api_key: Optional[str] = None,
) -> str:
    import httpx  # type: ignore

    key = _key(api_key)
    model = model if (model and "/" not in model and not model.lower().startswith("gpt")) \
        else (settings.GROQ_MODEL or DEFAULT_MODEL)
    msgs = _fit_messages(messages, settings.GROQ_MAX_PROMPT_CHARS)

    payload = {
        "model":       model,
        "messages":    [{"role": m.get("role", "user"), "content": m.get("content", "")} for m in msgs],
        "temperature": temperature,
        "max_tokens":  max_tokens,
    }
    logger.info("Groq chat | model=%s | messages=%d", model, len(msgs))

    try:
        resp = httpx.post(
            f"{settings.GROQ_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json=payload,
            timeout=60.0,
        )
        resp.raise_for_status()
        return (resp.json()["choices"][0]["message"]["content"] or "").strip()
    except Exception as exc:
        logger.error("Groq chat failed: %s", exc)
        raise RuntimeError(f"Groq chat failed: {exc}") from exc


def test_connection(api_key: Optional[str] = None) -> Dict[str, Any]:
    try:
        reply = chat([{"role": "user", "content": "Reply with the single word: connected"}],
                     max_tokens=10, api_key=api_key)
        return {"status": "ok", "reply": reply[:60], "model": settings.GROQ_MODEL or DEFAULT_MODEL}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
