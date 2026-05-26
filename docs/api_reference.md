# API Reference

## compliance.pii_detector

### `detect_pii(text: str) -> Dict[str, List[str]]`
Returns a mapping of PII type → matched values.

### `redact_pii(text: str, replacement="[REDACTED]") -> str`
Returns text with all PII replaced.

---

## compliance.injection_detector

### `detect_prompt_injection(text: str) -> List[str]`
Returns list of matched adversarial patterns.

### `injection_risk_score(text: str) -> float`
Returns 0–1 risk score.

---

## compliance.compliance_engine

### `call_compliance_llm(policy_text, framework, relevant_regs, api_key, model_name) -> str`
Returns raw JSON string of findings from LLM or mock.

### `parse_findings(raw_json: str) -> List[Finding]`
Parses and validates LLM output into Finding objects.

---

## compliance.scoring

### `calculate_compliance_score(findings: List[Finding]) -> float`
Returns 0–100 score based on finding severities.

### `grade_score(score: float) -> str`
Returns A–F letter grade.

---

## database.memory_store

### `MockVectorStore.similarity_search(query, k, framework_filter) -> List[Dict]`
Keyword-scored semantic retrieval.

### `MockVectorStore.add_document(doc: Dict) -> None`
Adds a regulation document to the store.
