"""
llm/openai_provider.py — OpenAI LLM provider for Nexus AI Governance Platform.

Supports:
  - Chat completions (GPT-4o, GPT-3.5-turbo)
  - Streaming responses
  - Embedding generation (for RAG / vector store)
  - Compliance analysis via call_compliance_llm()
  - Graceful fallback to mock when no key is present
"""
from __future__ import annotations

import os
from typing import Any, Dict, Generator, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.llm.openai_provider")

# ── Model aliases ─────────────────────────────────────────────────────────────

MODEL_MAP: Dict[str, str] = {
    "GPT-4o":         "gpt-4o",
    "GPT-4o-mini":    "gpt-4o-mini",
    "GPT-4-turbo":    "gpt-4-turbo",
    "GPT-3.5-turbo":  "gpt-3.5-turbo",
}

EMBEDDING_MODEL = "text-embedding-3-small"


# ── Client factory ────────────────────────────────────────────────────────────

def _get_client(api_key: Optional[str] = None):
    """Return an authenticated OpenAI client, or raise if the key is missing."""
    try:
        from openai import OpenAI  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "openai package is not installed. Run: pip install openai"
        ) from exc

    key = api_key or settings.OPENAI_API_KEY
    if not key:
        raise ValueError(
            "OPENAI_API_KEY is not set. Add it to your .env file or pass api_key explicitly."
        )
    return OpenAI(api_key=key)


def is_available(api_key: Optional[str] = None) -> bool:
    """Return True if a non-empty API key is configured."""
    return bool(api_key or settings.OPENAI_API_KEY)


# ── Chat completion ───────────────────────────────────────────────────────────

def chat(
    messages: List[Dict[str, str]],
    model: str = "GPT-4o",
    temperature: float = 0.2,
    max_tokens: int = 2048,
    api_key: Optional[str] = None,
) -> str:
    """
    Send a chat completion request and return the assistant's reply as a string.

    Args:
        messages:    List of {"role": "system"|"user"|"assistant", "content": "..."} dicts.
        model:       Friendly model alias from MODEL_MAP, or raw OpenAI model string.
        temperature: Sampling temperature (0 = deterministic, 1 = creative).
        max_tokens:  Maximum tokens in the response.
        api_key:     Override the key from settings (optional).

    Returns:
        The assistant's reply text.

    Raises:
        RuntimeError: If the API call fails.
    """
    client = _get_client(api_key)
    oai_model = MODEL_MAP.get(model, model)

    logger.info("OpenAI chat | model=%s | messages=%d", oai_model, len(messages))

    try:
        resp = client.chat.completions.create(
            model=oai_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        reply = resp.choices[0].message.content
        logger.debug("OpenAI response tokens: %s", resp.usage)
        return reply
    except Exception as exc:
        logger.error("OpenAI chat failed: %s", exc)
        raise RuntimeError(f"OpenAI chat failed: {exc}") from exc


def chat_stream(
    messages: List[Dict[str, str]],
    model: str = "GPT-4o",
    temperature: float = 0.2,
    max_tokens: int = 2048,
    api_key: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Streaming version of chat(). Yields text chunks as they arrive.

    Usage (Streamlit):
        with st.chat_message("assistant"):
            st.write_stream(chat_stream(messages))
    """
    client = _get_client(api_key)
    oai_model = MODEL_MAP.get(model, model)

    logger.info("OpenAI stream | model=%s", oai_model)

    try:
        stream = client.chat.completions.create(
            model=oai_model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta and delta.content:
                yield delta.content
    except Exception as exc:
        logger.error("OpenAI stream failed: %s", exc)
        raise RuntimeError(f"OpenAI stream failed: {exc}") from exc


# ── Embeddings ────────────────────────────────────────────────────────────────

def embed(
    texts: List[str],
    model: str = EMBEDDING_MODEL,
    api_key: Optional[str] = None,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts.

    Args:
        texts:   List of strings to embed.
        model:   OpenAI embedding model name.
        api_key: Override the key from settings (optional).

    Returns:
        List of embedding vectors (list of floats), one per input text.
    """
    client = _get_client(api_key)

    logger.info("OpenAI embed | model=%s | texts=%d", model, len(texts))

    try:
        resp = client.embeddings.create(input=texts, model=model)
        return [item.embedding for item in resp.data]
    except Exception as exc:
        logger.error("OpenAI embed failed: %s", exc)
        raise RuntimeError(f"OpenAI embed failed: {exc}") from exc


def embed_single(text: str, api_key: Optional[str] = None) -> List[float]:
    """Convenience wrapper — embed one string and return its vector."""
    return embed([text], api_key=api_key)[0]


# ── Compliance analysis (called by compliance_engine.py) ─────────────────────

def call_compliance_llm(
    policy_text: str,
    framework: str,
    relevant_regs: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    model: str = "GPT-4o",
) -> str:
    """
    Analyse a policy document for compliance violations using OpenAI.

    Returns a raw JSON string (array of Finding objects).
    Falls back to compliance_engine.generate_mock_findings() on any error.

    Args:
        policy_text:   The policy document text to analyse.
        framework:     Compliance framework (e.g. "GDPR", "HIPAA", "ISO 27001").
        relevant_regs: List of regulation dicts from the RAG retrieval step.
        api_key:       Override the key from settings (optional).
        model:         Friendly model alias from MODEL_MAP.

    Returns:
        Raw JSON string — array of Finding objects.
    """
    if not is_available(api_key):
        logger.warning("No OpenAI key — falling back to mock findings.")
        from compliance.compliance_engine import generate_mock_findings
        return generate_mock_findings(policy_text, framework, relevant_regs)

    reg_context = "\n\n".join(
        f"[{r['citation']}] {r['title']}\n{r['text']}" for r in relevant_regs[:4]
    )

    system_prompt = (
        f"You are an expert AI compliance and governance auditor specialising in {framework}.\n"
        "Analyse the provided policy document and identify ALL compliance violations.\n\n"
        f"REGULATORY CONTEXT:\n{reg_context}\n\n"
        "Return ONLY a valid JSON array of findings. Each object must have:\n"
        "  violated_string, legal_reference, severity (Critical/High/Medium/Low),\n"
        "  explanation, corrected_version, confidence_score (0.0–1.0),\n"
        "  department, remediation_steps (array of strings)\n"
        "Return ONLY the JSON array — no markdown, no preamble."
    )
    user_msg = (
        f"Analyse this policy document for {framework} compliance:\n\n{policy_text[:3000]}"
    )

    try:
        result = chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            model=model,
            temperature=0.1,
            max_tokens=3000,
            api_key=api_key,
        )
        logger.info("Compliance LLM call succeeded for framework=%s", framework)
        return result
    except Exception as exc:
        logger.warning("Compliance LLM failed (%s). Falling back to mock.", exc)
        from compliance.compliance_engine import generate_mock_findings
        return generate_mock_findings(policy_text, framework, relevant_regs)


# ── General-purpose prompt helper ─────────────────────────────────────────────

def ask(
    prompt: str,
    system: str = "You are a helpful AI governance assistant.",
    model: str = "GPT-4o",
    temperature: float = 0.3,
    max_tokens: int = 1024,
    api_key: Optional[str] = None,
) -> str:
    """
    Convenience single-turn helper. Send a user prompt and get a reply.

    Args:
        prompt:      User message.
        system:      System instructions.
        model:       Model alias.
        temperature: Sampling temperature.
        max_tokens:  Max response tokens.
        api_key:     Optional key override.

    Returns:
        The assistant's reply as a string.
    """
    return chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        api_key=api_key,
    )


# ── Quick connection test ──────────────────────────────────────────────────────

def test_connection(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Ping the OpenAI API with a minimal request.

    Returns:
        {"status": "ok", "model": ..., "reply": ...}
        {"status": "error", "message": ...}
    """
    try:
        reply = ask(
            prompt="Reply with the single word: connected",
            model="GPT-4o-mini",
            max_tokens=10,
            api_key=api_key,
        )
        return {"status": "ok", "model": "gpt-4o-mini", "reply": reply.strip()}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}