"""
llm/huggingface_provider.py — HuggingFace provider for Nexus AI Governance Platform.

Supports two modes:
  1. Inference API (cloud)  — uses your HF API key to call hosted models via REST.
  2. Local Transformers     — loads a model directly on your machine (no API key needed).

Common use-cases in this project:
  - Text generation  : policy summaries, Q&A, governance chat
  - Embeddings       : RAG vector store (FAISS / ChromaDB)
  - Zero-shot classify: quick severity / category tagging
  - Compliance chat  : fallback when OpenAI key is not set
"""
from __future__ import annotations

import os
from typing import Any, Dict, Generator, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.llm.huggingface_provider")


# ── Default models ────────────────────────────────────────────────────────────

# Inference API — hosted on HuggingFace Hub
DEFAULT_TEXT_MODEL      = "mistralai/Mistral-7B-Instruct-v0.2"
DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
DEFAULT_CLASSIFY_MODEL  = "facebook/bart-large-mnli"

# Inference API base URL
HF_API_BASE = "https://api-inference.huggingface.co/models"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_api_key(api_key: Optional[str] = None) -> str:
    key = api_key or settings.HUGGINGFACE_API_KEY
    if not key:
        raise ValueError(
            "HUGGINGFACE_API_KEY is not set. Add it to your .env file or pass api_key explicitly."
        )
    return key


def is_available(api_key: Optional[str] = None) -> bool:
    """Return True if a HuggingFace API key is configured."""
    return bool(api_key or settings.HUGGINGFACE_API_KEY)


def _headers(api_key: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {api_key}"}


# ── Inference API: Text Generation ───────────────────────────────────────────

def generate(
    prompt: str,
    model: str = DEFAULT_TEXT_MODEL,
    max_new_tokens: int = 512,
    temperature: float = 0.3,
    repetition_penalty: float = 1.1,
    api_key: Optional[str] = None,
) -> str:
    """
    Generate text using the HuggingFace Inference API.

    Args:
        prompt:             Input text / instruction.
        model:              HuggingFace model repo id (e.g. "mistralai/Mistral-7B-Instruct-v0.2").
        max_new_tokens:     Maximum tokens to generate.
        temperature:        Sampling temperature (0 = deterministic).
        repetition_penalty: Penalise repeated tokens (>1.0 reduces repetition).
        api_key:            Override key from settings (optional).

    Returns:
        Generated text string.
    """
    import httpx  # type: ignore

    key = _get_api_key(api_key)
    url = f"{HF_API_BASE}/{model}"

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens":     max_new_tokens,
            "temperature":        temperature,
            "repetition_penalty": repetition_penalty,
            "return_full_text":   False,
        },
    }

    logger.info("HF generate | model=%s | prompt_len=%d", model, len(prompt))

    try:
        resp = httpx.post(url, headers=_headers(key), json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()

        # API returns a list of dicts: [{"generated_text": "..."}]
        if isinstance(data, list) and data:
            return data[0].get("generated_text", "").strip()
        if isinstance(data, dict):
            return data.get("generated_text", str(data)).strip()
        return str(data)

    except Exception as exc:
        logger.error("HF generate failed: %s", exc)
        raise RuntimeError(f"HuggingFace generate failed: {exc}") from exc


# ── Inference API: Chat (instruction-tuned models) ────────────────────────────

def chat(
    messages: List[Dict[str, str]],
    model: str = DEFAULT_TEXT_MODEL,
    max_new_tokens: int = 1024,
    temperature: float = 0.3,
    api_key: Optional[str] = None,
) -> str:
    """
    Chat with an instruction-tuned model via the Inference API.

    Converts OpenAI-style messages to a single prompt string using
    [INST] / [/INST] formatting (Mistral / Llama2 style).

    Args:
        messages:       List of {"role": "system"|"user"|"assistant", "content": "..."}.
        model:          HuggingFace model repo id.
        max_new_tokens: Max tokens to generate.
        temperature:    Sampling temperature.
        api_key:        Override key (optional).

    Returns:
        Assistant reply as a string.
    """
    prompt = _messages_to_prompt(messages)
    return generate(
        prompt=prompt,
        model=model,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        api_key=api_key,
    )


def _messages_to_prompt(messages: List[Dict[str, str]]) -> str:
    """
    Convert OpenAI-style message list to Mistral/Llama2 instruct format.

    System message is prepended inside the first [INST] block.
    """
    parts: List[str] = []
    system_text = ""

    for msg in messages:
        role    = msg.get("role", "user")
        content = msg.get("content", "").strip()

        if role == "system":
            system_text = content
        elif role == "user":
            if system_text:
                parts.append(f"[INST] {system_text}\n\n{content} [/INST]")
                system_text = ""
            else:
                parts.append(f"[INST] {content} [/INST]")
        elif role == "assistant":
            parts.append(content)

    return "\n".join(parts)


# ── Inference API: Embeddings ─────────────────────────────────────────────────

def embed(
    texts: List[str],
    model: str = DEFAULT_EMBEDDING_MODEL,
    api_key: Optional[str] = None,
) -> List[List[float]]:
    """
    Generate sentence embeddings via the HuggingFace Inference API.

    Args:
        texts:   List of strings to embed.
        model:   Sentence-transformer model id.
        api_key: Override key (optional).

    Returns:
        List of embedding vectors (list of floats), one per input text.
    """
    import httpx  # type: ignore

    key = _get_api_key(api_key)
    url = f"{HF_API_BASE}/{model}"

    logger.info("HF embed | model=%s | texts=%d", model, len(texts))

    try:
        resp = httpx.post(
            url,
            headers=_headers(key),
            json={"inputs": texts, "options": {"wait_for_model": True}},
            timeout=60.0,
        )
        resp.raise_for_status()
        data = resp.json()

        # Returns list of vectors directly
        if isinstance(data, list) and data and isinstance(data[0], list):
            return data

        # Some models wrap in a dict
        if isinstance(data, dict) and "embeddings" in data:
            return data["embeddings"]

        raise ValueError(f"Unexpected embed response shape: {type(data)}")

    except Exception as exc:
        logger.error("HF embed failed: %s", exc)
        raise RuntimeError(f"HuggingFace embed failed: {exc}") from exc


def embed_single(text: str, api_key: Optional[str] = None) -> List[float]:
    """Convenience wrapper — embed one string and return its vector."""
    return embed([text], api_key=api_key)[0]


# ── Inference API: Zero-shot Classification ───────────────────────────────────

def classify(
    text: str,
    candidate_labels: List[str],
    model: str = DEFAULT_CLASSIFY_MODEL,
    multi_label: bool = False,
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Zero-shot text classification using BART-large-MNLI (or similar).

    Useful for tagging policy documents with compliance categories,
    severity levels, or department assignments without fine-tuning.

    Args:
        text:             Text to classify.
        candidate_labels: List of label strings (e.g. ["Critical", "High", "Medium", "Low"]).
        model:            Zero-shot classification model repo id.
        multi_label:      If True, labels are independent (not mutually exclusive).
        api_key:          Override key (optional).

    Returns:
        Dict with keys: "labels" (sorted by score), "scores", "top_label", "top_score".

    Example:
        result = classify(
            "User data is retained indefinitely.",
            ["GDPR violation", "HIPAA violation", "no issue"],
        )
        print(result["top_label"])  # → "GDPR violation"
    """
    import httpx  # type: ignore

    key = _get_api_key(api_key)
    url = f"{HF_API_BASE}/{model}"

    payload = {
        "inputs": text,
        "parameters": {
            "candidate_labels": candidate_labels,
            "multi_label":      multi_label,
        },
    }

    logger.info("HF classify | model=%s | labels=%s", model, candidate_labels)

    try:
        resp = httpx.post(url, headers=_headers(key), json=payload, timeout=60.0)
        resp.raise_for_status()
        data = resp.json()

        labels = data.get("labels", [])
        scores = data.get("scores", [])

        return {
            "labels":    labels,
            "scores":    scores,
            "top_label": labels[0] if labels else "",
            "top_score": scores[0] if scores else 0.0,
        }

    except Exception as exc:
        logger.error("HF classify failed: %s", exc)
        raise RuntimeError(f"HuggingFace classify failed: {exc}") from exc


# ── Local Transformers (offline / Anaconda) ───────────────────────────────────

def generate_local(
    prompt: str,
    model_name: str = "mistralai/Mistral-7B-Instruct-v0.2",
    max_new_tokens: int = 512,
    temperature: float = 0.3,
    device: str = "auto",
) -> str:
    """
    Generate text using a locally loaded HuggingFace Transformers model.

    No API key required — model is downloaded to ~/.cache/huggingface on first run.

    Args:
        prompt:         Input text.
        model_name:     HuggingFace model repo id or local path.
        max_new_tokens: Max tokens to generate.
        temperature:    Sampling temperature.
        device:         "auto" (GPU if available), "cpu", or "cuda".

    Returns:
        Generated text string.

    Note:
        Requires: pip install transformers accelerate torch
        First run downloads the model weights (~4–14 GB depending on model).
    """
    try:
        from transformers import pipeline  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "transformers not installed. Run: pip install transformers accelerate torch"
        ) from exc

    logger.info("HF local generate | model=%s", model_name)

    pipe = pipeline(
        "text-generation",
        model=model_name,
        device_map=device,
        trust_remote_code=True,
    )
    result = pipe(
        prompt,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        do_sample=temperature > 0,
        return_full_text=False,
    )
    return result[0]["generated_text"].strip()


def embed_local(
    texts: List[str],
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
) -> List[List[float]]:
    """
    Generate embeddings locally using sentence-transformers.

    No API key required. Fast and accurate for RAG.

    Args:
        texts:      List of strings to embed.
        model_name: Sentence-transformer model repo id.

    Returns:
        List of embedding vectors.

    Note:
        Requires: pip install sentence-transformers
    """
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "sentence-transformers not installed. Run: pip install sentence-transformers"
        ) from exc

    logger.info("HF local embed | model=%s | texts=%d", model_name, len(texts))

    model = SentenceTransformer(model_name)
    vectors = model.encode(texts, convert_to_numpy=True)
    return vectors.tolist()


# ── Compliance analysis (fallback from OpenAI) ────────────────────────────────

def call_compliance_llm(
    policy_text: str,
    framework: str,
    relevant_regs: List[Dict[str, Any]],
    api_key: Optional[str] = None,
    model: str = DEFAULT_TEXT_MODEL,
) -> str:
    """
    Analyse a policy document for compliance violations using HuggingFace.

    Returns a raw JSON string (array of Finding objects).
    Falls back to compliance_engine.generate_mock_findings() on any error.

    Args:
        policy_text:   Policy document text.
        framework:     Compliance framework name (e.g. "GDPR").
        relevant_regs: Regulation dicts from RAG retrieval.
        api_key:       Override HF key (optional).
        model:         HF model repo id.

    Returns:
        Raw JSON string — array of Finding objects.
    """
    if not is_available(api_key):
        logger.warning("No HuggingFace key — falling back to mock findings.")
        from compliance.compliance_engine import generate_mock_findings
        return generate_mock_findings(policy_text, framework, relevant_regs)

    reg_context = "\n\n".join(
        f"[{r['citation']}] {r['title']}\n{r['text']}" for r in relevant_regs[:3]
    )

    system_prompt = (
        f"You are an expert AI compliance auditor specialising in {framework}. "
        "Analyse the policy document and identify ALL compliance violations. "
        f"REGULATORY CONTEXT:\n{reg_context}\n\n"
        "Return ONLY a valid JSON array of findings. Each object must have: "
        "violated_string, legal_reference, severity (Critical/High/Medium/Low), "
        "explanation, corrected_version, confidence_score (0.0-1.0), "
        "department, remediation_steps (array of strings). "
        "Return ONLY the JSON array — no markdown, no preamble."
    )
    user_msg = (
        f"Analyse this policy document for {framework} compliance:\n\n{policy_text[:2000]}"
    )

    try:
        result = chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            model=model,
            max_new_tokens=2048,
            temperature=0.1,
            api_key=api_key,
        )
        logger.info("HF compliance LLM call succeeded for framework=%s", framework)
        return result
    except Exception as exc:
        logger.warning("HF compliance LLM failed (%s). Falling back to mock.", exc)
        from compliance.compliance_engine import generate_mock_findings
        return generate_mock_findings(policy_text, framework, relevant_regs)


# ── General-purpose helper ────────────────────────────────────────────────────

def ask(
    prompt: str,
    system: str = "You are a helpful AI governance assistant.",
    model: str = DEFAULT_TEXT_MODEL,
    max_new_tokens: int = 512,
    temperature: float = 0.3,
    api_key: Optional[str] = None,
) -> str:
    """
    Convenience single-turn helper. Send a prompt and get a reply.

    Args:
        prompt:         User message.
        system:         System instructions.
        model:          HF model repo id.
        max_new_tokens: Max tokens to generate.
        temperature:    Sampling temperature.
        api_key:        Override key (optional).

    Returns:
        Assistant reply as a string.
    """
    return chat(
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": prompt},
        ],
        model=model,
        max_new_tokens=max_new_tokens,
        temperature=temperature,
        api_key=api_key,
    )


# ── Connection test ───────────────────────────────────────────────────────────

def test_connection(api_key: Optional[str] = None) -> Dict[str, Any]:
    """
    Ping the HuggingFace Inference API with a minimal request.

    Returns:
        {"status": "ok",    "model": ..., "reply": ...}
        {"status": "error", "message": ...}
    """
    try:
        reply = generate(
            prompt="Reply with one word: connected",
            model="mistralai/Mistral-7B-Instruct-v0.2",
            max_new_tokens=10,
            api_key=api_key,
        )
        return {"status": "ok", "model": DEFAULT_TEXT_MODEL, "reply": reply.strip()}
    except Exception as exc:
        return {"status": "error", "message": str(exc)}