"""
llm/groq_provider.py — Groq (free tier) provider for Nexus AI Governance Platform.

Groq serves open models through an OpenAI-compatible API with a free tier
(no credit card). Get a key at https://console.groq.com/keys and set:

    GROQ_API_KEY = "gsk_..."
    GROQ_MODEL   = "openai/gpt-oss-120b"      # optional

Groq retires models regularly (e.g. llama-3.3-70b-versatile was shut down for
free/developer tiers on 2026-08-16). If the configured model is rejected, this
provider asks Groq which models the key can use and switches to the best one
automatically, so a retired model no longer breaks audits.

Free-tier limits are per-minute / per-day token budgets, so long prompts are
trimmed to fit (GROQ_MAX_PROMPT_CHARS) rather than failing with HTTP 413/429.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.llm.groq_provider")

DEFAULT_MODEL = "openai/gpt-oss-120b"

# Best first. Used only when the configured model is rejected.
PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-20b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]
# Models on Groq that are not text chat models.
_NOT_CHAT = ("whisper", "tts", "guard", "safeguard", "orpheus", "embed", "compound")

_model_override: Optional[str] = None     # set after automatic model discovery


def _key(api_key: Optional[str] = None) -> str:
    key = api_key or settings.GROQ_API_KEY
    if not key:
        raise RuntimeError("GROQ_API_KEY is not set.")
    return key


def is_available(api_key: Optional[str] = None) -> bool:
    return bool(api_key or settings.GROQ_API_KEY)


def _base() -> str:
    return settings.GROQ_BASE_URL.rstrip("/")


def _fit_messages(messages: List[Dict[str, str]], max_chars: int) -> List[Dict[str, str]]:
    """Trim the longest message so the prompt fits the free-tier token budget (~4 chars/token)."""
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


def _detail(resp) -> str:
    """HTTP status + the error message Groq sent back (raise_for_status hides the body)."""
    try:
        body = resp.json()
        msg = (body.get("error") or {}).get("message") or str(body)
    except Exception:
        msg = (getattr(resp, "text", "") or "")[:300]
    return f"HTTP {resp.status_code}: {msg[:300]}"


def _available_models(key: str) -> List[str]:
    import httpx  # type: ignore
    resp = httpx.get(f"{_base()}/models", headers={"Authorization": f"Bearer {key}"}, timeout=20.0)
    if resp.status_code != 200:
        raise RuntimeError(f"could not list models ({_detail(resp)})")
    return [m["id"] for m in resp.json().get("data", []) if m.get("id")]


def _pick_model(key: str, exclude: Optional[str] = None) -> str:
    ids = [i for i in _available_models(key) if i != exclude]
    for pref in PREFERRED_MODELS:
        if pref in ids:
            return pref
    chat_ids = [i for i in ids if not any(x in i.lower() for x in _NOT_CHAT)]
    if chat_ids:
        return chat_ids[0]
    raise RuntimeError("no usable chat model is available for this Groq key")


def _post(key: str, payload: Dict[str, Any]):
    import httpx  # type: ignore
    return httpx.post(
        f"{_base()}/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json=payload,
        timeout=60.0,
    )


def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 1500,
    api_key: Optional[str] = None,
) -> str:
    global _model_override
    key   = _key(api_key)
    model = model or _model_override or settings.GROQ_MODEL or DEFAULT_MODEL
    msgs  = _fit_messages(messages, settings.GROQ_MAX_PROMPT_CHARS)

    def build(m: str, with_effort: bool = True) -> Dict[str, Any]:
        p: Dict[str, Any] = {
            "model":       m,
            "messages":    [{"role": x.get("role", "user"), "content": x.get("content", "")} for x in msgs],
            "temperature": temperature,
            "max_tokens":  max_tokens,
        }
        if m.startswith("openai/gpt-oss"):
            # Reasoning models spend output tokens on "thinking"; keep it short so the
            # answer (JSON) is not cut off, and leave room for it.
            p["max_tokens"] = max(max_tokens, 2000)
            if with_effort:
                p["reasoning_effort"] = "low"
        return p

    logger.info("Groq chat | model=%s | messages=%d", model, len(msgs))
    try:
        resp = _post(key, build(model))

        if resp.status_code == 400 and "reasoning_effort" in build(model):
            resp = _post(key, build(model, with_effort=False))      # model rejects the option

        if resp.status_code in (400, 404) and not (resp.status_code == 400 and "context" in resp.text.lower()):
            # Model retired / not available to this key → discover a working one and retry once.
            old = model
            model = _pick_model(key, exclude=old)
            _model_override = model
            logger.warning("Groq model '%s' rejected (%s) — switching to '%s'", old, _detail(resp), model)
            resp = _post(key, build(model))

        if resp.status_code >= 400:
            raise RuntimeError(_detail(resp))

        text = (resp.json()["choices"][0]["message"].get("content") or "").strip()
        if not text:
            raise RuntimeError("empty response (model used all tokens on reasoning)")
        return text
    except Exception as exc:
        logger.error("Groq chat failed: %s", exc)
        raise RuntimeError(f"Groq chat failed: {exc}") from exc


def test_connection(api_key: Optional[str] = None) -> Dict[str, Any]:
    try:
        reply = chat([{"role": "user", "content": "Reply with the single word: connected"}],
                     max_tokens=50, api_key=api_key)
        return {"status": "ok", "reply": reply[:60],
                "model": _model_override or settings.GROQ_MODEL or DEFAULT_MODEL}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}
