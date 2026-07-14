import json
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.models import (
    ClarificationQuestion,
    InterpretedRule,
    InterpretationOutput,
    InterpretationTelemetry,
    RuleOrigin,
    RuleStatus,
    WorkbookInterpretation,
)
from app.main import app
from app.workbook.evals import evaluate_interpretation
from app.workbook.extractor import extract_workbook
from app.workbook.interpreter import (
    _business_rules,
    _normalize_model_output,
    _validate_model_output,
    build_interpretation_payload,
)
from app.workbook import storage


ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "samples" / "industrial-quotes" / "industrial-quotes.xlsx"
EVAL_FIXTURE = Path(__file__).parent / "fixtures" / "industrial_quotes_interpretation_eval.json"


def _sample_workbook():
    data = SAMPLE.read_bytes()
    return extract_workbook(SAMPLE, "phase2-demo", SAMPLE.name, sha256(data).hexdigest())


def test_interpretation_payload_is_bounded_and_redacted() -> None:
    workbook = _sample_workbook()
    next(item for item in workbook.evidence if item.source_type == "formula").excerpt = (
        "Contact sales@example.com or +351 912 345 678"
    )

    prepared = build_interpretation_payload(workbook)

    assert prepared.payload["limits"]["workbook_binary_included"] is False
    assert "[REDACTED_EMAIL]" in prepared.serialized
    assert "[REDACTED_PHONE]" in prepared.serialized
    assert "PK" not in prepared.serialized
    assert prepared.evidence_count <= 160


def test_structured_output_requires_existing_evidence() -> None:
    output = InterpretationOutput(
        rules=[
            InterpretedRule(
                id="rule-margin",
                name="Margin threshold",
                plain_language="A quote below the threshold needs approval.",
                rule_type="approval",
                expression="margin < threshold",
                evidence_refs=["Quotes!J7"],
                confidence=0.9,
            )
        ],
        questions=[],
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        _validate_model_output(output, {"Quotes!I7"})


def test_sdk_dict_output_is_normalized_by_pydantic_contract() -> None:
    parsed = InterpretationOutput.model_validate(
        {
            "rules": [
                {
                    "id": "rule-margin",
                    "name": "Margin threshold",
                    "plain_language": "A quote below the threshold needs approval.",
                    "rule_type": "approval",
                    "expression": "margin < threshold",
                    "inputs": ["margin"],
                    "outputs": ["approval_status"],
                    "evidence_refs": ["Quotes!J7"],
                    "confidence": 0.9,
                    "assumptions": [],
                }
            ],
            "questions": [],
        }
    )

    assert parsed.rules[0].id == "rule-margin"


def test_only_unambiguous_evidence_prefixes_are_repaired() -> None:
    output = InterpretationOutput(
        rules=[
            InterpretedRule(
                id="rule-margin",
                name="Margin threshold",
                plain_language="A quote below the threshold needs approval.",
                rule_type="approval",
                expression="margin < threshold",
                evidence_refs=["Approvals!B5!A1"],
                confidence=0.9,
            )
        ],
        questions=[],
    )

    normalized = _normalize_model_output(output, {"Approvals!B5", "Quotes!J7"})

    assert normalized.rules[0].evidence_refs == ["Approvals!B5"]

    output.rules[0].evidence_refs = ["Approvals!B5 current"]
    normalized = _normalize_model_output(output, {"Approvals!B5", "Quotes!J7"})

    assert normalized.rules[0].evidence_refs == ["Approvals!B5"]


def test_phase2_eval_contract_covers_rules_evidence_and_ambiguity() -> None:
    workbook = _sample_workbook()
    output = InterpretationOutput(
        rules=[
            InterpretedRule(
                id="rule-margin-calculation",
                name="Gross margin is calculated from revenue and cost",
                plain_language="Gross margin is revenue minus cost divided by revenue.",
                rule_type="calculation",
                expression="(revenue - cost) / revenue",
                evidence_refs=["Quotes!I7"],
                confidence=0.96,
            ),
            InterpretedRule(
                id="rule-approval-threshold",
                name="Low margin requires approval",
                plain_language="Quotes below the configured margin threshold need approval.",
                rule_type="approval",
                expression="margin < Config!B4",
                evidence_refs=["Quotes!J7", "Config!B4"],
                confidence=0.93,
            ),
        ],
        questions=[
            ClarificationQuestion(
                id="question-margin-boundary",
                question="Should exactly 15% be approved or sent for review?",
                options=["Approve at exactly 15%", "Require review at exactly 15%"],
                impact="This changes the approval boundary.",
                evidence_refs=["Quotes!J7", "Config!B4"],
                blocking=True,
            )
        ],
    )
    for item in output.rules:
        assert item.evidence_refs
    result = WorkbookInterpretation(
        workbook_id=workbook.workbook_id,
        source_sha256=workbook.sha256,
        rules=_business_rules(output),
        questions=output.questions,
        unsupported_features=workbook.unsupported_features,
        evidence=workbook.evidence,
        ai=InterpretationTelemetry(
            attempted=True,
            succeeded=True,
            model="gpt-5.6",
            prompt_version="workbook-interpretation-v1",
            input_sha256="0" * 64,
            input_bytes=100,
            evidence_count=len(workbook.evidence),
            duration_ms=1,
        ),
    )

    failures = evaluate_interpretation(result, json.loads(EVAL_FIXTURE.read_text(encoding="utf-8")))

    assert failures == []
    assert result.rules[0].origin is RuleOrigin.INFERRED
    assert result.rules[0].status is RuleStatus.INFERRED


def test_interpret_endpoint_reuses_persisted_upload_without_network(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "UPLOAD_ROOT", tmp_path)
    upload_response = TestClient(app).post(
        "/api/workbooks/analyze",
        files={"file": (SAMPLE.name, SAMPLE.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_response.status_code == 200
    upload = upload_response.json()

    async def fake_interpret(workbook):
        return WorkbookInterpretation(
            workbook_id=workbook.workbook_id,
            source_sha256=workbook.sha256,
            rules=[],
            questions=[],
            unsupported_features=workbook.unsupported_features,
            evidence=workbook.evidence,
            ai=InterpretationTelemetry(
                attempted=False,
                succeeded=False,
                model="gpt-5.6",
                prompt_version="workbook-interpretation-v1",
                input_sha256="1" * 64,
                input_bytes=100,
                evidence_count=len(workbook.evidence),
                duration_ms=0,
                error="test double",
            ),
        )

    monkeypatch.setattr("app.main.interpret_workbook", fake_interpret)
    response = TestClient(app).post(
        "/api/workbooks/interpret",
        json={
            "storage_key": upload["storage_key"],
            "workbook_id": upload["workbook"]["workbook_id"],
            "filename": upload["workbook"]["filename"],
            "sha256": upload["workbook"]["sha256"],
        },
    )

    assert response.status_code == 200
    assert response.json()["ai"]["error"] == "test double"
    assert response.json()["unsupported_features"] == ["Declared unsupported feature: PowerQueryRefresh"]
