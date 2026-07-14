from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.compiler import storage as artifact_storage
from app.domain.models import (
    BusinessRule,
    EntitySpec,
    EvidenceRef,
    RuleOrigin,
    RuleStatus,
    SystemBlueprint,
    WorkflowSpec,
    QuoteCreateRequest,
    QuoteTransitionRequest,
)
from app.main import app
from app.runtime.service import QuoteRuntime, RuntimeValidationError
from app.workbook import storage as upload_storage


ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "samples" / "industrial-quotes" / "industrial-quotes.xlsx"
EVIDENCE = EvidenceRef(
    id="Quotes!J7",
    source_type="formula",
    sheet="Quotes",
    address="J7",
    excerpt="=IF(I7<'Config'!$B$4,\"NEEDS_APPROVAL\",\"AUTO_APPROVED\")",
)


def _blueprint(operator: str = "<") -> SystemBlueprint:
    digest = sha256(SAMPLE.read_bytes()).hexdigest()
    rule = BusinessRule(
        id="rule-runtime-approval",
        name="Quote margin approval",
        plain_language="Quotes at or below the configured margin threshold need approval.",
        rule_type="approval",
        expression=f"margin {operator} Config!B4",
        outputs=["approval_status"],
        evidence_refs=[EVIDENCE.id],
        origin=RuleOrigin.HUMAN,
        status=RuleStatus.CONFIRMED,
        confidence=1,
    )
    return SystemBlueprint(
        version=f"v1-runtime-{operator.replace('<', 'lt')}",
        source_workbook_hash=digest,
        entities=[EntitySpec(name="Quote")],
        workflows=[
            WorkflowSpec(
                name="Quote approval",
                states=["DRAFT", "AUTO_APPROVED", "NEEDS_APPROVAL", "APPROVED", "REJECTED"],
                transitions=[
                    {"from": "NEEDS_APPROVAL", "to": "APPROVED", "when": "authorised approval"},
                    {"from": "NEEDS_APPROVAL", "to": "REJECTED", "when": "authorised rejection"},
                ],
            )
        ],
        rules=[rule],
        evidence=[EVIDENCE],
        answer_fingerprint="f" * 64,
    )


def test_runtime_calculates_and_auto_approves(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(artifact_storage, "ARTIFACT_ROOT", tmp_path)
    runtime = QuoteRuntime("00000000-0000-4000-8000-000000000004", SAMPLE, _blueprint())

    response = runtime.create_quote(
        QuoteCreateRequest(client_id="C001", product_id="PRD-1001", quantity=20, discount=0.03)
    )
    quote = response.quotes[0]

    assert quote.revenue == 1552
    assert quote.cost == 1000
    assert quote.gross_margin == pytest.approx(0.3556701031)
    assert quote.approval_status == "AUTO_APPROVED"
    assert response.dashboard.total_quotes == 1


def test_runtime_uses_blueprint_boundary_operator(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(artifact_storage, "ARTIFACT_ROOT", tmp_path)
    request = QuoteCreateRequest(client_id="C004", product_id="PRD-1004", quantity=10, discount=0)

    strict = QuoteRuntime("00000000-0000-4000-8000-000000000005", SAMPLE, _blueprint("<"))
    inclusive = QuoteRuntime("00000000-0000-4000-8000-000000000006", SAMPLE, _blueprint("<="))

    assert strict.create_quote(request).quotes[0].approval_status == "AUTO_APPROVED"
    assert inclusive.create_quote(request).quotes[0].approval_status == "NEEDS_APPROVAL"


def test_runtime_enforces_discount_and_allows_approval_transition(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(artifact_storage, "ARTIFACT_ROOT", tmp_path)
    runtime = QuoteRuntime("00000000-0000-4000-8000-000000000007", SAMPLE, _blueprint("<="))

    with pytest.raises(RuntimeValidationError, match="client policy"):
        runtime.create_quote(QuoteCreateRequest(client_id="C002", product_id="PRD-1002", quantity=1, discount=0.1))

    created = runtime.create_quote(
        QuoteCreateRequest(client_id="C005", product_id="PRD-1005", quantity=10, discount=0)
    )
    quote_id = created.quotes[0].id
    transitioned = runtime.transition_quote(
        quote_id,
        QuoteTransitionRequest(target_status="APPROVED", note="Commercial director"),
    )

    assert transitioned.quotes[0].approval_status == "APPROVED"
    assert transitioned.quotes[0].transition_note == "Commercial director"


def test_runtime_api_creates_quote_and_exposes_workflow(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(upload_storage, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(artifact_storage, "ARTIFACT_ROOT", tmp_path / "artifacts")
    upload = TestClient(app).post(
        "/api/workbooks/analyze",
        files={"file": (SAMPLE.name, SAMPLE.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 200
    workbook_id = upload.json()["workbook"]["workbook_id"]
    artifact_storage.save_blueprint(workbook_id, _blueprint())

    client = TestClient(app)
    app_response = client.get(f"/api/workbooks/{workbook_id}/app")
    assert app_response.status_code == 200
    assert app_response.json()["workflow"]["name"] == "Quote approval"
    assert len(app_response.json()["products"]) == 5

    quote_response = client.post(
        f"/api/workbooks/{workbook_id}/app/quotes",
        json={"client_id": "C005", "product_id": "PRD-1005", "quantity": 10, "discount": 0},
    )
    assert quote_response.status_code == 200
    quote = quote_response.json()["quotes"][0]
    assert quote["approval_status"] == "NEEDS_APPROVAL"

    transition_response = client.post(
        f"/api/workbooks/{workbook_id}/app/quotes/{quote['id']}/transitions",
        json={"target_status": "REJECTED"},
    )
    assert transition_response.status_code == 200
    assert transition_response.json()["quotes"][0]["approval_status"] == "REJECTED"
