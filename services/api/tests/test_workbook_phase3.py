from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.compiler.compiler import BlueprintCompilationError, compile_blueprint
from app.compiler import storage as artifact_storage
from app.domain.models import (
    AmbiguityAnswer,
    BusinessRule,
    ClarificationQuestion,
    EvidenceRef,
    InterpretationTelemetry,
    ResolutionSnapshot,
    RuleOrigin,
    RuleStatus,
    WorkbookInterpretation,
)
from app.main import app
from app.workbook.extractor import extract_workbook
from app.workbook import storage as upload_storage


ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "samples" / "industrial-quotes" / "industrial-quotes.xlsx"


def _interpretation() -> WorkbookInterpretation:
    evidence = [
        EvidenceRef(
            id="evidence-boundary",
            source_type="cell",
            sheet="Config",
            address="B4",
            excerpt="15%",
        )
    ]
    return WorkbookInterpretation(
        workbook_id="00000000-0000-4000-8000-000000000003",
        source_sha256="a" * 64,
        rules=[
            BusinessRule(
                id="rule-margin-approval",
                name="Margin approval boundary",
                plain_language="Quotes below the configured margin need review.",
                rule_type="approval",
                expression="margin < Config!B4",
                outputs=["approval_status"],
                evidence_refs=["evidence-boundary"],
                origin=RuleOrigin.INFERRED,
                status=RuleStatus.INFERRED,
                confidence=0.9,
            )
        ],
        questions=[
            ClarificationQuestion(
                id="question-margin-boundary",
                question="What happens at exactly 15%?",
                options=["AUTO_APPROVED at 15%", "REVIEW at 15%"],
                impact="Changes the approval boundary.",
                evidence_refs=["evidence-boundary"],
                blocking=True,
            )
        ],
        evidence=evidence,
        ai=InterpretationTelemetry(
            attempted=True,
            succeeded=True,
            model="gpt-5.6",
            prompt_version="workbook-interpretation-v1",
            input_sha256="b" * 64,
            input_bytes=100,
            evidence_count=1,
            duration_ms=1,
        ),
    )


def test_compile_requires_blocking_answers() -> None:
    with pytest.raises(BlueprintCompilationError) as error:
        compile_blueprint(_interpretation(), [])

    assert error.value.pending_question_ids == ["question-margin-boundary"]


def test_answer_changes_blueprint_deterministically() -> None:
    interpretation = _interpretation()
    approved = compile_blueprint(
        interpretation,
        [
            AmbiguityAnswer(
                question_id="question-margin-boundary",
                selected_option="AUTO_APPROVED at 15%",
                answered_at="2026-07-14T10:00:00Z",
            )
        ],
    )
    review = compile_blueprint(
        interpretation,
        [
            AmbiguityAnswer(
                question_id="question-margin-boundary",
                selected_option="REVIEW at 15%",
                answered_at="2026-07-14T10:00:00Z",
            )
        ],
    )

    assert approved.version != review.version
    assert approved.answer_fingerprint != review.answer_fingerprint
    assert approved.rules[0].expression == "margin < Config!B4"
    assert review.rules[0].expression == "margin <= Config!B4"
    assert review.rules[0].status is RuleStatus.CONFIRMED
    assert "human:question-margin-boundary" in review.rules[0].evidence_refs


def test_phase3_artifacts_round_trip(tmp_path) -> None:
    interpretation = _interpretation()
    resolution = ResolutionSnapshot(
        workbook_id=interpretation.workbook_id,
        source_sha256=interpretation.source_sha256,
        answers=[
            AmbiguityAnswer(
                question_id="question-margin-boundary",
                selected_option="REVIEW at 15%",
                note="Confirmado pelo responsavel",
                answered_at="2026-07-14T10:00:00Z",
            )
        ],
        updated_at="2026-07-14T10:00:00Z",
    )
    blueprint = compile_blueprint(
        interpretation,
        resolution.answers,
    )
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(artifact_storage, "ARTIFACT_ROOT", tmp_path)
    try:
        artifact_storage.save_interpretation(interpretation)
        artifact_storage.save_resolution(resolution)
        artifact_storage.save_blueprint(interpretation.workbook_id, blueprint)

        assert artifact_storage.load_interpretation(interpretation.workbook_id).source_sha256 == "a" * 64
        loaded_resolution = artifact_storage.load_resolution(interpretation.workbook_id)
        assert loaded_resolution is not None
        assert loaded_resolution.answers[0].selected_option == "REVIEW at 15%"
        assert artifact_storage.load_blueprint(interpretation.workbook_id).version == blueprint.version
    finally:
        monkeypatch.undo()


def test_phase3_api_persists_answers_and_compiles(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(upload_storage, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(artifact_storage, "ARTIFACT_ROOT", tmp_path / "artifacts")

    upload_response = TestClient(app).post(
        "/api/workbooks/analyze",
        files={"file": (SAMPLE.name, SAMPLE.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload_response.status_code == 200
    upload = upload_response.json()

    async def fake_interpret(workbook):
        result = _interpretation()
        return result.model_copy(update={
            "workbook_id": workbook.workbook_id,
            "source_sha256": workbook.sha256,
            "evidence": [item for item in workbook.evidence if item.id == workbook.evidence[0].id],
            "rules": [result.rules[0].model_copy(update={"evidence_refs": [workbook.evidence[0].id]})],
            "questions": [result.questions[0].model_copy(update={"evidence_refs": [workbook.evidence[0].id]})],
        })

    monkeypatch.setattr("app.main.interpret_workbook", fake_interpret)
    interpretation_response = TestClient(app).post(
        "/api/workbooks/interpret",
        json={
            "storage_key": upload["storage_key"],
            "workbook_id": upload["workbook"]["workbook_id"],
            "filename": upload["workbook"]["filename"],
            "sha256": upload["workbook"]["sha256"],
        },
    )
    assert interpretation_response.status_code == 200
    workbook_id = upload["workbook"]["workbook_id"]

    assert TestClient(app).get(f"/api/workbooks/{workbook_id}/ambiguities").json()["pending_question_ids"]
    answer_response = TestClient(app).post(
        f"/api/workbooks/{workbook_id}/answers",
        json={"answers": [{"question_id": "question-margin-boundary", "selected_option": "REVIEW at 15%"}]},
    )
    assert answer_response.status_code == 200
    assert answer_response.json()["pending_question_ids"] == []

    blueprint_response = TestClient(app).post(f"/api/workbooks/{workbook_id}/compile")
    assert blueprint_response.status_code == 200
    assert blueprint_response.json()["rules"][0]["expression"].endswith("<= Config!B4")
    assert TestClient(app).get(f"/api/workbooks/{workbook_id}/blueprint").status_code == 200
