"""Small deterministic acceptance checks for semantic interpretation outputs."""

from __future__ import annotations

from typing import Any

from app.domain.models import WorkbookInterpretation


def evaluate_interpretation(result: WorkbookInterpretation, expected: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if not result.ai.succeeded:
        failures.append("AI interpretation did not succeed.")

    required_types = set(expected.get("required_rule_types", []))
    actual_types = {rule.rule_type for rule in result.rules}
    missing_types = required_types - actual_types
    if missing_types:
        failures.append(f"Missing required rule types: {sorted(missing_types)}")

    required_evidence = set(expected.get("required_evidence_any", []))
    actual_evidence = {ref for rule in result.rules for ref in rule.evidence_refs}
    if required_evidence and not actual_evidence.intersection(required_evidence):
        failures.append("No required demo evidence was referenced by a rule.")

    question_terms = [str(term).lower() for term in expected.get("ambiguity_terms", [])]
    question_text = " ".join(
        f"{question.question} {question.impact} {' '.join(question.options)}"
        for question in result.questions
    ).lower()
    if question_terms and not any(term in question_text for term in question_terms):
        failures.append("The planned ambiguity was not surfaced in a clarification question.")

    return failures
