"""
llm/ollama_provider.py — Ollama local LLM provider for Nexus AI Governance Platform.

Ollama runs models 100% locally on your machine — no API key required.
Supports: Llama 3, Mistral, Gemma, Phi-3, CodeLlama, and any model pulled via `ollama pull`.

Features:
  - Chat completions (single-turn and multi-turn)
  - Streaming responses (for Streamlit live output)
  - Embeddings generation (for RAG / FAISS / ChromaDB)
  - Compliance analysis (fully offline)
  - Model management (list, pull, check available models)
  - Connection test

Setup (run once in terminal):
    # Install Ollama
    curl -fsSL https://ollama.com/install.sh | sh      # Linux/Mac
    # Windows: download from https://ollama.com/download

    # Pull a model
    ollama pull llama3
    ollama pull mistral
    ollama pull nomic-embed-text     # for embeddings

    # Start Ollama server (if not already running)
    ollama serve
"""
from __future__ import annotations

import json
from typing import Any, Dict, Generator, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.llm.ollama_provider")

# ── Defaults ──────────────────────────────────────────────────────────────────

DEFAULT_CHAT_MODEL      = "llama3"
DEFAULT_EMBED_MODEL     = "nomic-embed-text"
DEFAULT_HOST            = "http://localhost:11434"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _host(host: Optional[str] = None) -> str:
    """Return Ollama host URL from argument or settings."""
    return (host or settings.OLLAMA_HOST or DEFAULT_HOST).rstrip("/")


def _default_model(model: Optional[str] = None) -> str:
    """Return model name from argument or settings."""
    return model or settings.OLLAMA_MODEL or DEFAULT_CHAT_MODEL


def is_available(host: Optional[str] = None) -> bool:
    """
    Return True if the Ollama server is reachable.

    Does a lightweight GET /api/tags — no model required.
    """
    try:
        import httpx  # type: ignore
        resp = httpx.get(f"{_host(host)}/api/tags", timeout=3.0)
        return resp.status_code == 200
    except Exception:
        return False


# ── Chat completion ───────────────────────────────────────────────────────────

def chat(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    host: Optional[str] = None,
) -> str:
    """
    Send a chat completion request to Ollama and return the reply.

    Args:
        messages:    List of {"role": "system"|"user"|"assistant", "content": "..."}.
        model:       Ollama model name (e.g. "llama3", "mistral", "gemma").
                     Defaults to OLLAMA_MODEL in .env or "llama3".
        temperature: Sampling temperature (0 = deterministic).
        max_tokens:  Maximum tokens to generate.
        host:        Ollama server URL. Defaults to OLLAMA_HOST in .env.

    Returns:
        Assistant reply as a string.

    Raises:
        RuntimeError: If Ollama is unreachable or the request fails.
    """
    import httpx  # type: ignore

    url        = f"{_host(host)}/api/chat"
    model_name = _default_model(model)

    payload = {
        "model":    model_name,
        "messages": messages,
        "stream":   False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    logger.info("Ollama chat | model=%s | messages=%d", model_name, len(messages))

    try:
        resp = httpx.post(url, json=payload, timeout=120.0)
        resp.raise_for_status()
        data = resp.json()
        reply = data.get("message", {}).get("content", "").strip()
        logger.debug("Ollama reply tokens: %s", data.get("eval_count"))
        return reply

    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot connect to Ollama at {_host(host)}. "
            "Make sure Ollama is running: run 'ollama serve' in your terminal."
        )
    except Exception as exc:
        logger.error("Ollama chat failed: %s", exc)
        raise RuntimeError(f"Ollama chat failed: {exc}") from exc


def chat_stream(
    messages: List[Dict[str, str]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    host: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Streaming version of chat(). Yields text chunks as they arrive.

    Usage in Streamlit:
        with st.chat_message("assistant"):
            st.write_stream(ollama_provider.chat_stream(messages))

    Args:
        messages:    OpenAI-style message list.
        model:       Ollama model name.
        temperature: Sampling temperature.
        max_tokens:  Max tokens to generate.
        host:        Ollama server URL.

    Yields:
        Text chunks (strings) as the model generates them.
    """
    import httpx  # type: ignore

    url        = f"{_host(host)}/api/chat"
    model_name = _default_model(model)

    payload = {
        "model":    model_name,
        "messages": messages,
        "stream":   True,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    logger.info("Ollama stream | model=%s", model_name)

    try:
        with httpx.stream("POST", url, json=payload, timeout=120.0) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if not line:
                    continue
                try:
                    chunk = json.loads(line)
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        yield token
                    if chunk.get("done"):
                        break
                except json.JSONDecodeError:
                    continue

    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot connect to Ollama at {_host(host)}. "
            "Run 'ollama serve' in your terminal first."
        )
    except Exception as exc:
        logger.error("Ollama stream failed: %s", exc)
        raise RuntimeError(f"Ollama stream failed: {exc}") from exc


# ── Embeddings ────────────────────────────────────────────────────────────────

def embed(
    texts: List[str],
    model: str = DEFAULT_EMBED_MODEL,
    host: Optional[str] = None,
) -> List[List[float]]:
    """
    Generate embeddings for a list of texts using Ollama.

    Args:
        texts: List of strings to embed.
        model: Embedding model (default: "nomic-embed-text").
               Pull it first: ollama pull nomic-embed-text
        host:  Ollama server URL.

    Returns:
        List of embedding vectors (list of floats), one per input text.
    """
    import httpx  # type: ignore

    url = f"{_host(host)}/api/embeddings"
    logger.info("Ollama embed | model=%s | texts=%d", model, len(texts))

    vectors: List[List[float]] = []

    for text in texts:
        try:
            resp = httpx.post(
                url,
                json={"model": model, "prompt": text},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()
            vectors.append(data["embedding"])

        except httpx.ConnectError:
            raise RuntimeError(
                f"Cannot connect to Ollama at {_host(host)}. "
                "Run 'ollama serve' in your terminal first."
            )
        except Exception as exc:
            logger.error("Ollama embed failed for text: %s", exc)
            raise RuntimeError(f"Ollama embed failed: {exc}") from exc

    return vectors


def embed_single(
    text: str,
    model: str = DEFAULT_EMBED_MODEL,
    host: Optional[str] = None,
) -> List[float]:
    """Convenience wrapper — embed one string and return its vector."""
    return embed([text], model=model, host=host)[0]


# ── Simple generate (no chat format) ─────────────────────────────────────────

def generate(
    prompt: str,
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    host: Optional[str] = None,
) -> str:
    """
    Raw text generation (no chat format). Useful for summarisation or completion tasks.

    Args:
        prompt:      Input text.
        model:       Ollama model name.
        temperature: Sampling temperature.
        max_tokens:  Max tokens to generate.
        host:        Ollama server URL.

    Returns:
        Generated text string.
    """
    import httpx  # type: ignore

    url        = f"{_host(host)}/api/generate"
    model_name = _default_model(model)

    payload = {
        "model":  model_name,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
        },
    }

    logger.info("Ollama generate | model=%s | prompt_len=%d", model_name, len(prompt))

    try:
        resp = httpx.post(url, json=payload, timeout=120.0)
        resp.raise_for_status()
        return resp.json().get("response", "").strip()

    except httpx.ConnectError:
        raise RuntimeError(
            f"Cannot connect to Ollama at {_host(host)}. "
            "Run 'ollama serve' in your terminal first."
        )
    except Exception as exc:
        logger.error("Ollama generate failed: %s", exc)
        raise RuntimeError(f"Ollama generate failed: {exc}") from exc


# ── General-purpose helper ────────────────────────────────────────────────────

def ask(
    prompt: str,
    system: str = "You are a helpful AI governance assistant.",
    model: Optional[str] = None,
    temperature: float = 0.3,
    max_tokens: int = 1024,
    host: Optional[str] = None,
) -> str:
    """
    Convenience single-turn helper. Send a prompt and get a reply.

    Args:
        prompt:      User message.
        system:      System instructions.
        model:       Ollama model name.
        temperature: Sampling temperature.
        max_tokens:  Max tokens.
        host:        Ollama server URL.

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
        host=host,
    )


# ── Compliance analysis ───────────────────────────────────────────────────────

def call_compliance_llm(
    policy_text: str,
    framework: str,
    relevant_regs: List[Dict[str, Any]],
    model: Optional[str] = None,
    host: Optional[str] = None,
) -> str:
    """
    Analyse a policy document for compliance violations using local Ollama.

    Fully offline — no API key needed. Falls back to mock on failure.

    Args:
        policy_text:   Policy document text.
        framework:     Compliance framework (e.g. "GDPR").
        relevant_regs: Regulation dicts from RAG retrieval.
        model:         Ollama model name.
        host:          Ollama server URL.

    Returns:
        Raw JSON string — array of Finding objects.
    """
    if not is_available(host):
        logger.warning("Ollama not reachable — falling back to mock findings.")
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
        f"Analyse this policy document for {framework} compliance:\n\n{policy_text[:2500]}"
    )

    try:
        result = chat(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user",   "content": user_msg},
            ],
            model=model,
            temperature=0.1,
            max_tokens=2500,
            host=host,
        )
        logger.info("Ollama compliance analysis succeeded for framework=%s", framework)
        return result

    except Exception as exc:
        logger.warning("Ollama compliance failed (%s). Falling back to mock.", exc)
        from compliance.compliance_engine import generate_mock_findings
        return generate_mock_findings(policy_text, framework, relevant_regs)


# ── Model management ──────────────────────────────────────────────────────────

def list_models(host: Optional[str] = None) -> List[str]:
    """
    Return a list of model names currently installed in Ollama.

    Returns:
        List of model name strings (e.g. ["llama3:latest", "mistral:latest"]).
        Returns empty list if Ollama is not reachable.
    """
    try:
        import httpx  # type: ignore
        resp = httpx.get(f"{_host(host)}/api/tags", timeout=5.0)
        resp.raise_for_status()
        models = resp.json().get("models", [])
        return [m["name"] for m in models]
    except Exception as exc:
        logger.warning("Could not list Ollama models: %s", exc)
        return []


def pull_model(model_name: str, host: Optional[str] = None) -> bool:
    """
    Pull (download) a model from the Ollama library.

    Args:
        model_name: Model to pull (e.g. "llama3", "mistral", "gemma").
        host:       Ollama server URL.

    Returns:
        True if pulled successfully, False otherwise.

    Note:
        This can take several minutes for large models.
        Run in a background thread for Streamlit apps.
    """
    try:
        import httpx  # type: ignore
        logger.info("Pulling Ollama model: %s", model_name)
        resp = httpx.post(
            f"{_host(host)}/api/pull",
            json={"name": model_name, "stream": False},
            timeout=600.0,  # 10 min for large models
        )
        resp.raise_for_status()
        logger.info("Model %s pulled successfully.", model_name)
        return True
    except Exception as exc:
        logger.error("Failed to pull model %s: %s", model_name, exc)
        return False


def model_is_installed(model_name: str, host: Optional[str] = None) -> bool:
    """
    Check if a specific model is already installed.

    Args:
        model_name: Model name to check (e.g. "llama3").
        host:       Ollama server URL.

    Returns:
        True if installed, False otherwise.
    """
    installed = list_models(host)
    return any(model_name in m for m in installed)


# ── Connection test ───────────────────────────────────────────────────────────

def test_connection(host: Optional[str] = None) -> Dict[str, Any]:
    """
    Test the Ollama connection and return status info.

    Returns:
        {
          "status":         "ok" | "error",
          "host":           "http://localhost:11434",
          "models_installed": ["llama3:latest", ...],
          "active_model":   "llama3",
          "reply":          "connected"          # only on success
          "message":        "error details"      # only on error
        }
    """
    h = _host(host)

    if not is_available(host):
        return {
            "status":  "error",
            "host":    h,
            "message": (
                f"Cannot connect to Ollama at {h}. "
                "Make sure Ollama is installed and running: 'ollama serve'"
            ),
        }

    installed = list_models(host)
    active    = _default_model()

    if not installed:
        return {
            "status":           "error",
            "host":             h,
            "models_installed": [],
            "message":          (
                "Ollama is running but no models are installed. "
                f"Run: ollama pull {active}"
            ),
        }

    try:
        reply = ask(
            prompt="Reply with the single word: connected",
            model=active,
            max_tokens=10,
            host=host,
        )
        return {
            "status":           "ok",
            "host":             h,
            "models_installed": installed,
            "active_model":     active,
            "reply":            reply.strip(),
        }
    except Exception as exc:
        return {
            "status":           "error",
            "host":             h,
            "models_installed": installed,
            "message":          str(exc),
        }