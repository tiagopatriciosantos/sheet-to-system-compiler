from pathlib import Path

from fastapi.testclient import TestClient

from app.compiler import storage as artifact_storage
from app.compiler.compiler import _decision_kind
from app.domain.models import ParityRun, ParityScenario, ParityStatus
from app.main import app
from app.parity import runner
from app.parity.runner import _compare, run_parity
from app.parity.scenarios import golden_scenarios
from app.parity.storage import load_parity_run, save_parity_run
from tests.test_runtime_phase4 import _blueprint
from app.workbook import storage as upload_storage


ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "samples" / "industrial-quotes" / "industrial-quotes.xlsx"


def test_golden_scenarios_define_twelve_real_cases() -> None:
    scenarios = golden_scenarios()

    assert len(scenarios) == 12
    assert {item.source for item in scenarios} == {"workbook_row", "generated_boundary"}
    boundary = next(item for item in scenarios if item.id == "scenario-04-boundary-strict")
    assert boundary.inputs == {"client_id": "C004", "product_id": "PRD-1004", "quantity": 10, "discount": 0}
    assert boundary.source == "generated_boundary"


def test_compiler_prioritises_explicit_inclusive_approval_boundary() -> None:
    option = "Preservar a logica atual: abaixo de 15% NEEDS_APPROVAL; 15% ou mais AUTO_APPROVED"

    assert _decision_kind(option) == "approve"


def test_compare_applies_field_tolerances_and_reports_exact_diffs() -> None:
    workbook_result = {
        "unit_price": 100.0,
        "revenue": 1000.0,
        "cost": 700.0,
        "gross_margin": 0.3,
        "approval_status": "AUTO_APPROVED",
    }
    runtime_result = {
        "unit_price": 100.005,
        "revenue": 1000.009,
        "cost": 700.02,
        "gross_margin": 0.300002,
        "approval_status": "NEEDS_APPROVAL",
    }

    diffs = _compare(workbook_result, runtime_result)

    assert "unit_price" not in " ".join(diffs)
    assert "revenue" not in " ".join(diffs)
    assert any(diff.startswith("cost:") for diff in diffs)
    assert any(diff.startswith("gross_margin:") for diff in diffs)
    assert any(diff.startswith("approval_status:") for diff in diffs)


def test_missing_libreoffice_blocks_all_scenarios_without_persisting_quotes(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(artifact_storage, "ARTIFACT_ROOT", tmp_path / "artifacts")
    monkeypatch.setattr(runner, "find_soffice", lambda: None)
    workbook_id = "00000000-0000-4000-8000-000000000008"

    report = run_parity(workbook_id, SAMPLE, _blueprint())

    assert report.status == "blocked"
    assert report.total == 12
    assert report.passed == 0
    assert report.failed == 0
    assert report.blocked == 12
    assert all(item.status is ParityStatus.BLOCKED for item in report.scenarios)
    assert all(item.runtime_result for item in report.scenarios)
    assert not (artifact_storage.artifact_directory(workbook_id) / "runtime" / "quotes.json").exists()


def test_parity_run_round_trip_is_atomic_json_artifact(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(artifact_storage, "ARTIFACT_ROOT", tmp_path / "artifacts")
    report = ParityRun(
        run_id="parity-test-round-trip",
        workbook_id="00000000-0000-4000-8000-000000000009",
        blueprint_version="v1-test",
        status="blocked",
        scenarios=[
            ParityScenario(
                id="PARITY-TEST",
                description="Test scenario",
                inputs={"client_id": "C001"},
                source="human",
                status=ParityStatus.BLOCKED,
                diffs=["LibreOffice unavailable"],
            )
        ],
        total=1,
        passed=0,
        failed=0,
        blocked=1,
        started_at="2026-07-14T10:00:00+00:00",
        finished_at="2026-07-14T10:00:01+00:00",
        duration_ms=1000,
    )

    save_parity_run(report)

    assert load_parity_run(report.workbook_id, report.run_id) == report


def test_parity_api_returns_a_blocked_report_when_recalculator_is_unavailable(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(upload_storage, "UPLOAD_ROOT", tmp_path / "uploads")
    monkeypatch.setattr(artifact_storage, "ARTIFACT_ROOT", tmp_path / "artifacts")
    monkeypatch.setattr(runner, "find_soffice", lambda: None)
    upload = TestClient(app).post(
        "/api/workbooks/analyze",
        files={"file": (SAMPLE.name, SAMPLE.read_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert upload.status_code == 200
    workbook_id = upload.json()["workbook"]["workbook_id"]
    artifact_storage.save_blueprint(workbook_id, _blueprint())

    response = TestClient(app).post(f"/api/workbooks/{workbook_id}/parity-runs")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["total"] == 12
    assert payload["blocked"] == 12
    assert payload["scenarios"][0]["status"] == "blocked"
    assert TestClient(app).get(
        f"/api/workbooks/{workbook_id}/parity-runs/{payload['run_id']}"
    ).status_code == 200
