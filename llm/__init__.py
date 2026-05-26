"""
llm/__init__.py — Unified LLM interface for Nexus AI Governance Platform.

This file is the single entry point for ALL LLM calls in the project.
Every page, agent, and engine imports from here — not directly from providers.

Provider priority (auto-selected):
    1. OpenAI   — if OPENAI_API_KEY is set in .env
    2. HuggingFace — if HUGGINGFACE_API_KEY is set in .env
    3. Ollama   — if Ollama server is running locally
    4. Mock     — deterministic fallback, always works (no AI, no key needed)

Usage anywhere in the project:
    from llm import chat, ask, embed, call_compliance_llm, get_active_provider

    # Chat
    reply = chat([{"role": "user", "content": "What is GDPR?"}])

    # Simple ask
    reply = ask("Summarise this policy", system="You are a compliance expert.")

    # Embeddings (for RAG)
    vectors = embed(["GDPR Article 5", "data retention policy"])

    # Compliance audit
    findings_json = call_compliance_llm(policy_text, "GDPR", relevant_regs)

    # Check which provider is active
    print(get_active_provider())   # → "openai" | "huggingface" | "ollama" | "mock"
"""
from __future__ import annotations

from typing import Any, Dict, Generator, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.llm")


# ══════════════════════════════════════════════════════════════════════════════
# PROVIDER DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def get_active_provider() -> str:
    """
    Detect and return the best available LLM provider.

    Returns one of: "openai", "huggingface", "ollama", "mock"

    Priority:
        1. OpenAI       — OPENAI_API_KEY set in .env
        2. HuggingFace  — HUGGINGFACE_API_KEY set in .env
        3. Ollama       — local server running at OLLAMA_HOST
        4. Mock         — always available, no AI, deterministic output
    """
    if settings.OPENAI_API_KEY:
        return "openai"

    if settings.HUGGINGFACE_API_KEY:
        return "huggingface"

    try:
        from llm import ollama_provider
        if ollama_provider.is_available():
            return "ollama"
    except Exception:
        pass

    return "mock"


def get_provider_status() -> Dict[str, Any]:
    """
    Return availability status for all providers.

    Returns:
        {
          "active":       "openai",
          "openai":       {"available": True,  "key_set": True},
          "huggingface":  {"available": True,  "key_set": True},
          "ollama":       {"available": False, "host": "http://localhost:11434",
                           "models": []},
          "mock":         {"available": True},
        }
    """
    from llm import ollama_provider

    ollama_up     = ollama_provider.is_available()
    ollama_models = ollama_provider.list_models() if ollama_up else []

    return {
        "active": get_active_provider(),
        "openai": {
            "available": bool(settings.OPENAI_API_KEY),
            "key_set":   bool(settings.OPENAI_API_KEY),
        },
        "huggingface": {
            "available": bool(settings.HUGGINGFACE_API_KEY),
            "key_set":   bool(settings.HUGGINGFACE_API_KEY),
        },
        "ollama": {
            "available": ollama_up,
            "host":      settings.OLLAMA_HOST,
            "models":    ollama_models,
        },
        "mock": {
            "available": True,
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED CHAT
# ══════════════════════════════════════════════════════════════════════════════

def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    provider: Optional[str] = None,
) -> str:
    """
    Send a chat request to the best available LLM provider.

    Args:
        messages:    List of {"role": "system"|"user"|"assistant", "content": "..."}.
        model:       Model name (provider-specific). Uses .env default if not set.
        temperature: Sampling temperature (0 = deterministic).
        max_tokens:  Maximum tokens in the response.
        provider:    Force a specific provider: "openai"|"huggingface"|"ollama"|"mock".
                     Auto-detected if not specified.

    Returns:
        Assistant reply as a string.
    """
    p = provider or get_active_provider()
    logger.info("llm.chat | provider=%s | messages=%d", p, len(messages))

    if p == "openai":
        from llm import openai_provider
        return openai_provider.chat(
            messages=messages,
            model=model or "GPT-4o",
            temperature=temperature,
            max_tokens=max_tokens,
        )

    if p == "huggingface":
        from llm import huggingface_provider
        return huggingface_provider.chat(
            messages=messages,
            model=model or huggingface_provider.DEFAULT_TEXT_MODEL,
            max_new_tokens=max_tokens,
            temperature=temperature,
        )

    if p == "ollama":
        from llm import ollama_provider
        return ollama_provider.chat(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # Mock fallback
    return _mock_chat(messages)


def chat_stream(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    provider: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Streaming version of chat(). Yields text chunks as they arrive.

    Usage in Streamlit:
        with st.chat_message("assistant"):
            st.write_stream(llm.chat_stream(messages))

    Falls back to non-streaming for providers that don't support it.
    """
    p = provider or get_active_provider()
    logger.info("llm.chat_stream | provider=%s", p)

    if p == "openai":
        from llm import openai_provider
        yield from openai_provider.chat_stream(
            messages=messages,
            model=model or "GPT-4o",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return

    if p == "ollama":
        from llm import ollama_provider
        yield from ollama_provider.chat_stream(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return

    # HuggingFace and mock — non-streaming fallback
    reply = chat(messages, model=model, temperature=temperature,
                 max_tokens=max_tokens, provider=p)
    yield reply


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED ASK (single-turn helper)
# ══════════════════════════════════════════════════════════════════════════════

def ask(
    prompt: str,
    system: str = "You are a helpful AI governance assistant.",
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    provider: Optional[str] = None,
) -> str:
    """
    Convenience single-turn helper. Send a prompt and get a reply.

    Args:
        prompt:      User message.
        system:      System instructions.
        model:       Model name (optional).
        temperature: Sampling temperature.
        max_tokens:  Max tokens in response.
        provider:    Force provider (optional).

    Returns:
        Assistant reply as a string.
    """
    return chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        provider=provider,
    )


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED EMBEDDINGS
# ══════════════════════════════════════════════════════════════════════════════

def embed(
    texts: List[str],
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> List[List[float]]:
    """
    Generate embeddings using the best available provider.

    Args:
        texts:    List of strings to embed.
        model:    Embedding model name (provider-specific).
        provider: Force a specific provider (optional).

    Returns:
        List of embedding vectors (list of floats), one per input text.
    """
    p = provider or get_active_provider()
    logger.info("llm.embed | provider=%s | texts=%d", p, len(texts))

    if p == "openai":
        from llm import openai_provider
        return openai_provider.embed(texts, model=model or "text-embedding-3-small")

    if p == "huggingface":
        from llm import huggingface_provider
        return huggingface_provider.embed(
            texts,
            model=model or huggingface_provider.DEFAULT_EMBEDDING_MODEL,
        )

    if p == "ollama":
        from llm import ollama_provider
        return ollama_provider.embed(
            texts,
            model=model or "nomic-embed-text",
        )

    # Mock fallback — returns zero vectors (768-dim)
    logger.warning("No embedding provider available — returning zero vectors.")
    return [[0.0] * 768 for _ in texts]


def embed_single(
    text: str,
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> List[float]:
    """Convenience wrapper — embed one string and return its vector."""
    return embed([text], model=model, provider=provider)[0]


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED COMPLIANCE ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════

def call_compliance_llm(
    policy_text: str,
    framework: str,
    relevant_regs: List[Dict[str, Any]],
    model: Optional[str] = None,
    provider: Optional[str] = None,
) -> str:
    """
    Analyse a policy document for compliance violations.

    Auto-selects the best available provider. Always returns valid JSON.
    Falls back to deterministic mock if all providers fail.

    Args:
        policy_text:   Full text of the policy document.
        framework:     Compliance framework (e.g. "GDPR", "HIPAA", "ISO 27001").
        relevant_regs: Regulation dicts retrieved from the vector store (RAG).
        model:         Model name override (optional).
        provider:      Force provider: "openai"|"huggingface"|"ollama"|"mock".

    Returns:
        Raw JSON string — array of Finding objects.
    """
    p = provider or get_active_provider()
    logger.info("llm.call_compliance_llm | provider=%s | framework=%s", p, framework)

    if p == "openai":
        from llm import openai_provider
        return openai_provider.call_compliance_llm(
            policy_text=policy_text,
            framework=framework,
            relevant_regs=relevant_regs,
            model=model or "GPT-4o",
        )

    if p == "huggingface":
        from llm import huggingface_provider
        return huggingface_provider.call_compliance_llm(
            policy_text=policy_text,
            framework=framework,
            relevant_regs=relevant_regs,
            model=model or huggingface_provider.DEFAULT_TEXT_MODEL,
        )

    if p == "ollama":
        from llm import ollama_provider
        return ollama_provider.call_compliance_llm(
            policy_text=policy_text,
            framework=framework,
            relevant_regs=relevant_regs,
            model=model,
        )

    # Mock fallback
    from compliance.compliance_engine import generate_mock_findings
    return generate_mock_findings(policy_text, framework, relevant_regs)


# ══════════════════════════════════════════════════════════════════════════════
# UNIFIED CONNECTION TEST
# ══════════════════════════════════════════════════════════════════════════════

def test_all_providers() -> Dict[str, Any]:
    """
    Test all providers and return their status.

    Returns:
        {
          "openai":      {"status": "ok",    "reply": "connected"},
          "huggingface": {"status": "error", "message": "..."},
          "ollama":      {"status": "ok",    "models_installed": [...], ...},
          "active":      "openai"
        }
    """
    results: Dict[str, Any] = {}

    # OpenAI
    try:
        from llm import openai_provider
        results["openai"] = openai_provider.test_connection()
    except Exception as exc:
        results["openai"] = {"status": "error", "message": str(exc)}

    # HuggingFace
    try:
        from llm import huggingface_provider
        results["huggingface"] = huggingface_provider.test_connection()
    except Exception as exc:
        results["huggingface"] = {"status": "error", "message": str(exc)}

    # Ollama
    try:
        from llm import ollama_provider
        results["ollama"] = ollama_provider.test_connection()
    except Exception as exc:
        results["ollama"] = {"status": "error", "message": str(exc)}

    results["active"] = get_active_provider()
    return results


# ══════════════════════════════════════════════════════════════════════════════
# MOCK FALLBACK (no provider needed)
# ══════════════════════════════════════════════════════════════════════════════

def _mock_chat(messages: List[Dict[str, str]]) -> str:
    """
    Deterministic mock reply when no LLM provider is available.
    Used for testing and offline development.
    """
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"),
        ""
    )
    return (
        f"[Mock Response] No LLM provider is configured. "
        f"Your message was: '{last_user[:80]}'. "
        "Please set OPENAI_API_KEY or HUGGINGFACE_API_KEY in your .env file, "
        "or start Ollama locally with 'ollama serve'."
    )


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API — what gets imported when you do `from llm import ...`
# ══════════════════════════════════════════════════════════════════════════════

__all__ = [
    # Core functions
    "chat",
    "chat_stream",
    "ask",
    "embed",
    "embed_single",
    "call_compliance_llm",

    # Provider management
    "get_active_provider",
    "get_provider_status",
    "test_all_providers",
]