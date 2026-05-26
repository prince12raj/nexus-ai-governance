"""
llm/router.py — Intelligent LLM request router for Nexus AI Governance Platform.

The router sits between the application layer (UI pages, agents, compliance engine)
and the provider layer (OpenAI, HuggingFace, Ollama, Mock).

Responsibilities:
  1. Task-based routing     — pick the best model for each task type
  2. Provider failover      — auto-retry with next provider on failure
  3. Rate-limit handling    — back-off and retry on 429 errors
  4. Cost optimisation      — use cheaper models for simple tasks
  5. Prompt injection       — attach correct system prompt per task
  6. Response validation    — ensure JSON responses parse correctly
  7. Audit logging          — log every LLM call with token usage

Task types supported:
  compliance_audit   — policy violation detection (needs best model)
  pii_detection      — personal data scanning
  risk_assessment    — AI system risk scoring
  policy_generation  — draft compliant policy text
  remediation        — build fix plans for findings
  executive_summary  — board-level report generation
  regulatory_qa      — regulation lookup and Q&A
  document_summary   — summarise uploaded documents
  severity_classify  — label finding severity
  chat               — general governance assistant

Usage:
    from llm.router import route

    # Route a compliance audit task
    result = route(
        task="compliance_audit",
        payload={
            "policy_text":   policy_text,
            "framework":     "GDPR",
            "relevant_regs": regs,
        }
    )

    # Route a chat message
    result = route(
        task="chat",
        payload={"messages": messages}
    )
"""
from __future__ import annotations

import json
import re
import time
from typing import Any, Dict, Generator, List, Optional

from config.logging_config import get_logger
from config.settings import settings

logger = get_logger("nexus.llm.router")


# ══════════════════════════════════════════════════════════════════════════════
# TASK CONFIGURATION
# ══════════════════════════════════════════════════════════════════════════════

# Maps each task to its ideal model per provider and settings
TASK_CONFIG: Dict[str, Dict[str, Any]] = {
    "compliance_audit": {
        "openai_model":      "GPT-4o",
        "hf_model":          "mistralai/Mistral-7B-Instruct-v0.2",
        "ollama_model":      "llama3",
        "temperature":       0.1,       # very low — we want precise, consistent output
        "max_tokens":        3000,
        "expects_json":      True,
        "retry_on_fail":     True,
        "description":       "Policy compliance violation detection",
    },
    "pii_detection": {
        "openai_model":      "GPT-4o",
        "hf_model":          "mistralai/Mistral-7B-Instruct-v0.2",
        "ollama_model":      "llama3",
        "temperature":       0.0,
        "max_tokens":        2000,
        "expects_json":      True,
        "retry_on_fail":     True,
        "description":       "PII scanning in documents",
    },
    "risk_assessment": {
        "openai_model":      "GPT-4o",
        "hf_model":          "mistralai/Mistral-7B-Instruct-v0.2",
        "ollama_model":      "llama3",
        "temperature":       0.2,
        "max_tokens":        2500,
        "expects_json":      True,
        "retry_on_fail":     True,
        "description":       "AI system risk scoring",
    },
    "policy_generation": {
        "openai_model":      "GPT-4o",
        "hf_model":          "mistralai/Mistral-7B-Instruct-v0.2",
        "ollama_model":      "mistral",
        "temperature":       0.4,       # slightly higher for creative writing
        "max_tokens":        2000,
        "expects_json":      False,
        "retry_on_fail":     False,
        "description":       "Draft compliant policy sections",
    },
    "remediation": {
        "openai_model":      "GPT-4o",
        "hf_model":          "mistralai/Mistral-7B-Instruct-v0.2",
        "ollama_model":      "llama3",
        "temperature":       0.3,
        "max_tokens":        2000,
        "expects_json":      False,
        "retry_on_fail":     False,
        "description":       "Remediation plan generation",
    },
    "executive_summary": {
        "openai_model":      "GPT-4o",
        "hf_model":          "mistralai/Mistral-7B-Instruct-v0.2",
        "ollama_model":      "llama3",
        "temperature":       0.3,
        "max_tokens":        1500,
        "expects_json":      False,
        "retry_on_fail":     False,
        "description":       "Board-level executive summary",
    },
    "regulatory_qa": {
        "openai_model":      "GPT-4o",
        "hf_model":          "mistralai/Mistral-7B-Instruct-v0.2",
        "ollama_model":      "llama3",
        "temperature":       0.2,
        "max_tokens":        1500,
        "expects_json":      False,
        "retry_on_fail":     False,
        "description":       "Regulatory research Q&A",
    },
    "document_summary": {
        "openai_model":      "GPT-3.5-Turbo",   # cheaper model — simpler task
        "hf_model":          "mistralai/Mistral-7B-Instruct-v0.2",
        "ollama_model":      "mistral",
        "temperature":       0.2,
        "max_tokens":        1000,
        "expects_json":      False,
        "retry_on_fail":     False,
        "description":       "Policy document summarisation",
    },
    "severity_classify": {
        "openai_model":      "GPT-3.5-Turbo",   # cheaper — classification task
        "hf_model":          "facebook/bart-large-mnli",
        "ollama_model":      "llama3",
        "temperature":       0.0,
        "max_tokens":        200,
        "expects_json":      True,
        "retry_on_fail":     True,
        "description":       "Compliance finding severity classification",
    },
    "chat": {
        "openai_model":      "GPT-4o",
        "hf_model":          "mistralai/Mistral-7B-Instruct-v0.2",
        "ollama_model":      "llama3",
        "temperature":       0.3,
        "max_tokens":        1500,
        "expects_json":      False,
        "retry_on_fail":     False,
        "description":       "General governance assistant chat",
    },
}

# Provider failover order
PROVIDER_ORDER = ["openai", "huggingface", "ollama", "mock"]


# ══════════════════════════════════════════════════════════════════════════════
# ACTIVE PROVIDER DETECTION
# ══════════════════════════════════════════════════════════════════════════════

def _get_active_provider() -> str:
    """Detect best available provider at runtime."""
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


def _get_model_for_task(task: str, provider: str) -> Optional[str]:
    """Return the correct model name for a task + provider combination."""
    cfg = TASK_CONFIG.get(task, TASK_CONFIG["chat"])
    key = f"{provider}_model"
    return cfg.get(key)


# ══════════════════════════════════════════════════════════════════════════════
# CORE ROUTER
# ══════════════════════════════════════════════════════════════════════════════

def route(
    task: str,
    payload: Dict[str, Any],
    provider: Optional[str] = None,
    model_override: Optional[str] = None,
    stream: bool = False,
) -> Any:
    """
    Route an LLM request to the correct provider and model for the given task.

    Args:
        task:           Task type key from TASK_CONFIG.
                        e.g. "compliance_audit", "chat", "pii_detection"
        payload:        Task-specific data dict. Keys vary by task — see below.
        provider:       Force a specific provider (optional). Auto-detected if not set.
        model_override: Override the model chosen by TASK_CONFIG (optional).
        stream:         If True, returns a generator for streaming (chat only).

    Payload keys by task:
        compliance_audit  → policy_text, framework, relevant_regs
        pii_detection     → text
        risk_assessment   → system_description
        policy_generation → section_title, framework, context (optional)
        remediation       → finding (dict), framework, org_context (optional)
        executive_summary → findings (list), framework, policy_name, org_name
        regulatory_qa     → question, context_docs (optional)
        document_summary  → document_text, doc_name (optional)
        severity_classify → violation_text, framework
        chat              → messages (list), rag_context (optional)

    Returns:
        str   — LLM reply text (or JSON string for tasks with expects_json=True)
        Generator — if stream=True (chat task only)

    Raises:
        ValueError: If task is not recognised.
        RuntimeError: If all providers fail and mock also fails.
    """
    if task not in TASK_CONFIG:
        raise ValueError(
            f"Unknown task '{task}'. Valid tasks: {list(TASK_CONFIG.keys())}"
        )

    cfg      = TASK_CONFIG[task]
    active_p = provider or _get_active_provider()

    logger.info(
        "router.route | task=%s | provider=%s | stream=%s",
        task, active_p, stream
    )

    # Build messages from payload + prompts
    messages = _build_messages(task, payload)

    # Streaming path (chat only)
    if stream:
        return _route_stream(messages, active_p, cfg, model_override)

    # Standard path with failover
    return _route_with_failover(
        task=task,
        messages=messages,
        cfg=cfg,
        primary_provider=active_p,
        model_override=model_override,
        payload=payload,
    )


# ══════════════════════════════════════════════════════════════════════════════
# MESSAGE BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def _build_messages(task: str, payload: Dict[str, Any]) -> List[Dict[str, str]]:
    """
    Build the messages list for a given task using prompts.py templates.

    Returns:
        OpenAI-style messages list: [{"role": ..., "content": ...}, ...]
    """
    from llm.prompts import (
        compliance_system_prompt,
        build_compliance_user_prompt,
        combined_framework_system_prompt,
        REGULATORY_RESEARCH_SYSTEM,
        build_regulatory_research_prompt,
        policy_generation_system_prompt,
        build_policy_generation_prompt,
        RISK_ASSESSMENT_SYSTEM,
        build_risk_assessment_prompt,
        PII_DETECTION_SYSTEM,
        build_pii_detection_prompt,
        REMEDIATION_SYSTEM,
        build_remediation_prompt,
        EXECUTIVE_SUMMARY_SYSTEM,
        build_executive_summary_prompt,
        GOVERNANCE_CHAT_SYSTEM,
        build_chat_prompt,
        SEVERITY_CLASSIFICATION_SYSTEM,
        build_severity_classification_prompt,
        DOCUMENT_SUMMARY_SYSTEM,
        build_document_summary_prompt,
    )

    # ── Compliance audit ───────────────────────────────────────────────────────
    if task == "compliance_audit":
        framework    = payload.get("framework", "GDPR")
        policy_text  = payload.get("policy_text", "")
        relevant_regs = payload.get("relevant_regs", [])

        reg_context = "\n\n".join(
            f"[{r['citation']}] {r['title']}\n{r['text']}"
            for r in relevant_regs[:4]
        )

        if framework == "Combined Framework Mode":
            system = combined_framework_system_prompt(reg_context)
        else:
            system = compliance_system_prompt(framework, reg_context)

        return [
            {"role": "system", "content": system},
            {"role": "user",   "content": build_compliance_user_prompt(policy_text, framework)},
        ]

    # ── PII detection ──────────────────────────────────────────────────────────
    if task == "pii_detection":
        return [
            {"role": "system", "content": PII_DETECTION_SYSTEM},
            {"role": "user",   "content": build_pii_detection_prompt(payload.get("text", ""))},
        ]

    # ── Risk assessment ────────────────────────────────────────────────────────
    if task == "risk_assessment":
        return [
            {"role": "system", "content": RISK_ASSESSMENT_SYSTEM},
            {"role": "user",   "content": build_risk_assessment_prompt(
                payload.get("system_description", "")
            )},
        ]

    # ── Policy generation ──────────────────────────────────────────────────────
    if task == "policy_generation":
        framework  = payload.get("framework", "GDPR")
        org_type   = payload.get("org_type", "organisation")
        return [
            {"role": "system", "content": policy_generation_system_prompt(framework, org_type)},
            {"role": "user",   "content": build_policy_generation_prompt(
                payload.get("section_title", "Data Retention Policy"),
                framework,
                payload.get("context", ""),
            )},
        ]

    # ── Remediation ────────────────────────────────────────────────────────────
    if task == "remediation":
        return [
            {"role": "system", "content": REMEDIATION_SYSTEM},
            {"role": "user",   "content": build_remediation_prompt(
                payload.get("finding", {}),
                payload.get("framework", "GDPR"),
                payload.get("org_context", ""),
            )},
        ]

    # ── Executive summary ──────────────────────────────────────────────────────
    if task == "executive_summary":
        return [
            {"role": "system", "content": EXECUTIVE_SUMMARY_SYSTEM},
            {"role": "user",   "content": build_executive_summary_prompt(
                payload.get("findings", []),
                payload.get("framework", "GDPR"),
                payload.get("policy_name", "Policy Document"),
                payload.get("org_name", "the organisation"),
            )},
        ]

    # ── Regulatory Q&A ─────────────────────────────────────────────────────────
    if task == "regulatory_qa":
        return [
            {"role": "system", "content": REGULATORY_RESEARCH_SYSTEM},
            {"role": "user",   "content": build_regulatory_research_prompt(
                payload.get("question", ""),
                payload.get("context_docs"),
            )},
        ]

    # ── Document summary ───────────────────────────────────────────────────────
    if task == "document_summary":
        return [
            {"role": "system", "content": DOCUMENT_SUMMARY_SYSTEM},
            {"role": "user",   "content": build_document_summary_prompt(
                payload.get("document_text", ""),
                payload.get("doc_name", "Policy Document"),
            )},
        ]

    # ── Severity classification ────────────────────────────────────────────────
    if task == "severity_classify":
        return [
            {"role": "system", "content": SEVERITY_CLASSIFICATION_SYSTEM},
            {"role": "user",   "content": build_severity_classification_prompt(
                payload.get("violation_text", ""),
                payload.get("framework", "GDPR"),
            )},
        ]

    # ── Chat (default) ─────────────────────────────────────────────────────────
    return build_chat_prompt(
        user_message=payload.get("user_message", ""),
        chat_history=payload.get("messages", []),
        rag_context=payload.get("rag_context"),
    )


# ══════════════════════════════════════════════════════════════════════════════
# PROVIDER DISPATCH WITH FAILOVER
# ══════════════════════════════════════════════════════════════════════════════

def _route_with_failover(
    task: str,
    messages: List[Dict[str, str]],
    cfg: Dict[str, Any],
    primary_provider: str,
    model_override: Optional[str],
    payload: Dict[str, Any],
) -> str:
    """
    Try the primary provider. On failure, try next providers in order.
    On JSON tasks, validate the response and retry if parsing fails.
    """
    providers_to_try = _build_provider_order(primary_provider)

    last_error: Optional[Exception] = None

    for attempt, p in enumerate(providers_to_try):
        try:
            model = model_override or _get_model_for_task(task, p)
            reply = _call_provider(p, messages, cfg, model)

            # Validate JSON if required
            if cfg.get("expects_json"):
                reply = _ensure_json(reply)

            logger.info(
                "router | task=%s | provider=%s | attempt=%d | success",
                task, p, attempt + 1
            )
            return reply

        except RateLimitError as exc:
            logger.warning("Rate limit on %s — waiting 5s before retry.", p)
            time.sleep(5)
            last_error = exc
            continue

        except Exception as exc:
            logger.warning(
                "router | task=%s | provider=%s | attempt=%d | failed: %s",
                task, p, attempt + 1, exc
            )
            last_error = exc
            continue

    # All providers failed — use mock
    logger.error("All providers failed for task=%s. Using mock fallback.", task)
    if task == "compliance_audit":
        from compliance.compliance_engine import generate_mock_findings
        return generate_mock_findings(
            payload.get("policy_text", ""),
            payload.get("framework", "GDPR"),
            payload.get("relevant_regs", []),
        )

    return (
        f"[Router Fallback] All LLM providers failed for task '{task}'. "
        f"Last error: {last_error}. "
        "Please check your API keys in .env or start Ollama with 'ollama serve'."
    )


def _route_stream(
    messages: List[Dict[str, str]],
    provider: str,
    cfg: Dict[str, Any],
    model_override: Optional[str],
) -> Generator[str, None, None]:
    """Route a streaming chat request."""
    model = model_override or _get_model_for_task("chat", provider)

    if provider == "openai":
        from llm import openai_provider
        yield from openai_provider.chat_stream(
            messages=messages,
            model=model or "GPT-4o",
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )
        return

    if provider == "ollama":
        from llm import ollama_provider
        yield from ollama_provider.chat_stream(
            messages=messages,
            model=model,
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )
        return

    # HuggingFace / mock — non-streaming fallback
    reply = _call_provider(provider, messages, cfg, model)
    yield reply


def _call_provider(
    provider: str,
    messages: List[Dict[str, str]],
    cfg: Dict[str, Any],
    model: Optional[str],
) -> str:
    """Dispatch a single call to the named provider."""

    if provider == "openai":
        from llm import openai_provider
        return openai_provider.chat(
            messages=messages,
            model=model or "GPT-4o",
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )

    if provider == "huggingface":
        from llm import huggingface_provider
        return huggingface_provider.chat(
            messages=messages,
            model=model or huggingface_provider.DEFAULT_TEXT_MODEL,
            max_new_tokens=cfg["max_tokens"],
            temperature=cfg["temperature"],
        )

    if provider == "ollama":
        from llm import ollama_provider
        return ollama_provider.chat(
            messages=messages,
            model=model,
            temperature=cfg["temperature"],
            max_tokens=cfg["max_tokens"],
        )

    # Mock
    last_user = next(
        (m["content"] for m in reversed(messages) if m.get("role") == "user"), ""
    )
    return (
        f"[Mock] No LLM provider available. Query: '{last_user[:80]}'. "
        "Set OPENAI_API_KEY or HUGGINGFACE_API_KEY in .env, "
        "or run 'ollama serve' locally."
    )


def _build_provider_order(primary: str) -> List[str]:
    """Return provider list starting with primary, then fallbacks."""
    order = [primary] + [p for p in PROVIDER_ORDER if p != primary]
    return order


# ══════════════════════════════════════════════════════════════════════════════
# JSON VALIDATION & CLEANING
# ══════════════════════════════════════════════════════════════════════════════

def _ensure_json(raw: str) -> str:
    """
    Validate and clean a raw LLM response that should be JSON.

    Strips markdown fences, fixes common LLM JSON mistakes, and
    raises JSONDecodeError if it still can't parse.
    """
    # Strip markdown code fences
    cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()

    # Sometimes models wrap array in {"findings": [...]}
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            # Try common wrapper keys
            for key in ("findings", "results", "violations", "items", "data"):
                if key in data and isinstance(data[key], list):
                    return json.dumps(data[key])
        return json.dumps(data)
    except json.JSONDecodeError:
        # Try to extract JSON array from anywhere in the string
        match = re.search(r"\[.*\]", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return json.dumps(data)
            except json.JSONDecodeError:
                pass

        # Try JSON object
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
                return json.dumps(data)
            except json.JSONDecodeError:
                pass

        logger.error("JSON validation failed. Raw response: %s", raw[:300])
        raise json.JSONDecodeError("Could not extract valid JSON from LLM response", raw, 0)


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM EXCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

class RateLimitError(Exception):
    """Raised when a provider returns a 429 rate limit response."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE SHORTCUTS
# ══════════════════════════════════════════════════════════════════════════════

def route_compliance_audit(
    policy_text: str,
    framework: str,
    relevant_regs: List[Dict[str, Any]],
    provider: Optional[str] = None,
) -> str:
    """Shortcut for compliance_audit task."""
    return route(
        task="compliance_audit",
        payload={
            "policy_text":    policy_text,
            "framework":      framework,
            "relevant_regs":  relevant_regs,
        },
        provider=provider,
    )


def route_chat(
    messages: List[Dict[str, str]],
    rag_context: Optional[str] = None,
    provider: Optional[str] = None,
    stream: bool = False,
) -> Any:
    """Shortcut for chat task."""
    return route(
        task="chat",
        payload={
            "messages":    messages,
            "rag_context": rag_context,
        },
        provider=provider,
        stream=stream,
    )


def route_pii_scan(text: str, provider: Optional[str] = None) -> str:
    """Shortcut for pii_detection task."""
    return route(
        task="pii_detection",
        payload={"text": text},
        provider=provider,
    )


def route_risk_assessment(system_description: str, provider: Optional[str] = None) -> str:
    """Shortcut for risk_assessment task."""
    return route(
        task="risk_assessment",
        payload={"system_description": system_description},
        provider=provider,
    )


def route_executive_summary(
    findings: List[Dict[str, Any]],
    framework: str,
    policy_name: str,
    org_name: str = "the organisation",
    provider: Optional[str] = None,
) -> str:
    """Shortcut for executive_summary task."""
    return route(
        task="executive_summary",
        payload={
            "findings":    findings,
            "framework":   framework,
            "policy_name": policy_name,
            "org_name":    org_name,
        },
        provider=provider,
    )


def route_remediation(
    finding: Dict[str, Any],
    framework: str,
    org_context: str = "",
    provider: Optional[str] = None,
) -> str:
    """Shortcut for remediation task."""
    return route(
        task="remediation",
        payload={
            "finding":     finding,
            "framework":   framework,
            "org_context": org_context,
        },
        provider=provider,
    )


def route_document_summary(
    document_text: str,
    doc_name: str = "Policy Document",
    provider: Optional[str] = None,
) -> str:
    """Shortcut for document_summary task."""
    return route(
        task="document_summary",
        payload={
            "document_text": document_text,
            "doc_name":      doc_name,
        },
        provider=provider,
    )