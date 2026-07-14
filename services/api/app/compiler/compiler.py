"""Compile confirmed interpretations into a versioned, non-executable blueprint."""

from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict

from app.domain.models import (
    AmbiguityAnswer,
    BusinessRule,
    CalculationSpec,
    ClarificationQuestion,
    EntityField,
    EntitySpec,
    EvidenceRef,
    RuleStatus,
    SystemBlueprint,
    ValidationSpec,
    ViewSpec,
    WorkflowSpec,
    WorkbookInterpretation,
)


class BlueprintCompilationError(ValueError):
    def __init__(self, message: str, pending_question_ids: list[str] | None = None) -> None:
        super().__init__(message)
        self.pending_question_ids = pending_question_ids or []


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")
    return slug or "field"


def _data_type(field_name: str) -> str:
    lowered = field_name.lower()
    if "quantity" in lowered or "quantidade" in lowered:
        return "integer"
    if any(term in lowered for term in ("discount", "desconto", "margin", "margem", "rate", "tax")):
        return "decimal"
    if any(term in lowered for term in ("cost", "custo", "price", "preço", "preco", "pre_o", "revenue", "value", "valor")):
        return "decimal"
    return "string"


def _entity_specs(interpretation: WorkbookInterpretation) -> list[EntitySpec]:
    header_cells: dict[str, list[tuple[str, str]]] = defaultdict(list)
    for item in interpretation.evidence:
        match = re.fullmatch(r"([A-Z]+)3", item.address or "")
        if item.source_type == "cell" and item.sheet and match and item.excerpt:
            header_cells[item.sheet].append((match.group(1), item.excerpt))

    names = {
        "Clients": "Client",
        "Products": "Product",
        "Quotes": "Quote",
        "Approvals": "Approval",
    }
    entities: list[EntitySpec] = []
    for sheet_name, headers in header_cells.items():
        if sheet_name == "Config":
            continue
        fields: list[EntityField] = []
        used_names: set[str] = set()
        for _, header in headers:
            field_name = _slugify(header)
            if field_name in used_names:
                continue
            used_names.add(field_name)
            fields.append(
                EntityField(
                    name=field_name,
                    data_type=_data_type(field_name),
                    required=field_name.endswith("_id") or field_name == "id",
                )
            )
        if fields:
            entities.append(EntitySpec(name=names.get(sheet_name, sheet_name.rstrip("s")), fields=fields))
    return entities


def _calculation_specs(rules: list[BusinessRule]) -> list[CalculationSpec]:
    return [
        CalculationSpec(
            id=f"calc-{rule.id}",
            target=rule.outputs[0] if rule.outputs else rule.name,
            expression=rule.expression or rule.plain_language,
            evidence_refs=rule.evidence_refs,
        )
        for rule in rules
        if rule.rule_type == "calculation"
    ]


def _validation_specs(rules: list[BusinessRule]) -> list[ValidationSpec]:
    return [
        ValidationSpec(
            id=f"validation-{rule.id}",
            target=rule.outputs[0] if rule.outputs else rule.name,
            expression=rule.expression or rule.plain_language,
            message=rule.plain_language,
            evidence_refs=rule.evidence_refs,
        )
        for rule in rules
        if rule.rule_type == "validation"
    ]


def _views(entities: list[EntitySpec]) -> list[ViewSpec]:
    views: list[ViewSpec] = []
    for entity in entities:
        views.extend(
            [
                ViewSpec(name=f"{entity.name} list", view_type="list", entity=entity.name),
                ViewSpec(name=f"{entity.name} detail", view_type="detail", entity=entity.name),
                ViewSpec(name=f"{entity.name} form", view_type="form", entity=entity.name),
            ]
        )
        if entity.name == "Quote":
            views.append(ViewSpec(name="Quote dashboard", view_type="dashboard", entity=entity.name))
    return views


def _workflow(rules: list[BusinessRule]) -> list[WorkflowSpec]:
    if not any(rule.rule_type == "approval" for rule in rules):
        return []
    return [
        WorkflowSpec(
            name="Quote approval",
            states=["DRAFT", "AUTO_APPROVED", "NEEDS_APPROVAL", "APPROVED", "REJECTED"],
            transitions=[
                {"from": "DRAFT", "to": "AUTO_APPROVED", "when": "approval rule passes"},
                {"from": "DRAFT", "to": "NEEDS_APPROVAL", "when": "approval rule requires review"},
                {"from": "NEEDS_APPROVAL", "to": "APPROVED", "when": "authorised human approval"},
                {"from": "NEEDS_APPROVAL", "to": "REJECTED", "when": "authorised human rejection"},
            ],
        )
    ]


def _decision_kind(option: str) -> str:
    lowered = option.lower()
    if any(term in lowered for term in ("review", "revis", "needs_approval", "needs approval", "requer aprovação")):
        return "review"
    if any(term in lowered for term in ("auto_approved", "auto approved", "automaticamente", "auto-aprov")):
        return "approve"
    return "other"


def _apply_answer_to_expression(expression: str | None, option: str) -> str | None:
    if not expression:
        return expression
    kind = _decision_kind(option)
    if kind == "review" and "<=" not in expression and "<" in expression:
        return expression.replace("<", "<=", 1)
    if kind == "approve" and "<=" in expression:
        return expression.replace("<=", "<", 1)
    return expression


def _answer_evidence(answer: AmbiguityAnswer) -> EvidenceRef:
    return EvidenceRef(
        id=f"human:{answer.question_id}",
        source_type="human",
        excerpt=f"Resposta humana: {answer.selected_option}",
    )


def _rules_with_answers(
    interpretation: WorkbookInterpretation,
    questions: dict[str, ClarificationQuestion],
    answers: dict[str, AmbiguityAnswer],
) -> tuple[list[BusinessRule], list[EvidenceRef]]:
    human_evidence: list[EvidenceRef] = []
    for answer in answers.values():
        human_evidence.append(_answer_evidence(answer))

    compiled_rules: list[BusinessRule] = []
    for rule in interpretation.rules:
        compiled = rule.model_copy(deep=True)
        related = [
            (questions[question_id], answer)
            for question_id, answer in answers.items()
            if question_id in questions
            and set(rule.evidence_refs).intersection(questions[question_id].evidence_refs)
        ]
        for question, answer in related:
            compiled.status = RuleStatus.CONFIRMED
            compiled.expression = _apply_answer_to_expression(compiled.expression, answer.selected_option)
            compiled.assumptions = [
                *compiled.assumptions,
                f"Human decision {question.id}: {answer.selected_option}",
            ][:6]
            human_ref = f"human:{question.id}"
            if human_ref not in compiled.evidence_refs:
                compiled.evidence_refs = [*compiled.evidence_refs, human_ref][:8]
        compiled_rules.append(compiled)
    return compiled_rules, human_evidence


def compile_blueprint(
    interpretation: WorkbookInterpretation,
    answers: list[AmbiguityAnswer],
) -> SystemBlueprint:
    questions = {question.id: question for question in interpretation.questions}
    answer_map: dict[str, AmbiguityAnswer] = {}
    for answer in answers:
        if answer.question_id in answer_map:
            raise BlueprintCompilationError(f"Duplicate answer for question {answer.question_id}.")
        question = questions.get(answer.question_id)
        if question is None:
            raise BlueprintCompilationError(f"Unknown clarification question: {answer.question_id}.")
        if answer.selected_option not in question.options:
            raise BlueprintCompilationError(f"Selected option is not valid for {answer.question_id}.")
        answer_map[answer.question_id] = answer

    pending = [
        question.id
        for question in interpretation.questions
        if question.blocking and question.id not in answer_map
    ]
    if pending:
        raise BlueprintCompilationError(
            "Resolve all blocking ambiguities before compiling the blueprint.", pending_question_ids=pending
        )

    compiled_rules, human_evidence = _rules_with_answers(interpretation, questions, answer_map)
    fingerprint_payload = [
        {"question_id": answer.question_id, "selected_option": answer.selected_option}
        for answer in sorted(answer_map.values(), key=lambda item: item.question_id)
    ]
    fingerprint = hashlib.sha256(
        json.dumps(
            {"source_sha256": interpretation.source_sha256, "answers": fingerprint_payload},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    unresolved = [
        question.id
        for question in interpretation.questions
        if question.id not in answer_map
    ]
    unresolved.extend(f"unsupported:{feature}" for feature in interpretation.unsupported_features)
    evidence = [*interpretation.evidence, *human_evidence]
    return SystemBlueprint(
        version=f"v1-{fingerprint[:12]}",
        source_workbook_hash=interpretation.source_sha256,
        entities=_entity_specs(interpretation),
        calculations=_calculation_specs(compiled_rules),
        validations=_validation_specs(compiled_rules),
        workflows=_workflow(compiled_rules),
        views=_views(_entity_specs(interpretation)),
        rules=compiled_rules,
        unresolved_items=unresolved,
        evidence=evidence,
        compiled_from_answers=sorted(answer_map),
        answer_fingerprint=fingerprint,
    )
