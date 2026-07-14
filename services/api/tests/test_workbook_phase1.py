import json
from hashlib import sha256
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.domain.models import SheetVisibility
from app.main import app
from app.workbook.extractor import extract_workbook
from app.workbook import storage
from app.workbook.storage import WorkbookUploadError, validate_workbook_bytes


ROOT = Path(__file__).resolve().parents[3]
SAMPLE = ROOT / "samples" / "industrial-quotes" / "industrial-quotes.xlsx"
SNAPSHOT = Path(__file__).parent / "fixtures" / "industrial_quotes_ir.json"


def test_demo_workbook_matches_phase1_snapshot() -> None:
    workbook_bytes = SAMPLE.read_bytes()
    workbook = extract_workbook(
        SAMPLE,
        workbook_id="snapshot-demo",
        filename=SAMPLE.name,
        sha256=sha256(workbook_bytes).hexdigest(),
    )
    expected = json.loads(SNAPSHOT.read_text(encoding="utf-8"))

    assert [sheet.name for sheet in workbook.sheets] == expected["sheet_names"]
    assert [sheet.name for sheet in workbook.sheets if sheet.visibility != SheetVisibility.VISIBLE] == expected[
        "hidden_sheets"
    ]
    assert {sheet.name: len(sheet.formula_cells) for sheet in workbook.sheets if sheet.formula_cells} == expected[
        "formula_counts"
    ]
    quotes = next(sheet for sheet in workbook.sheets if sheet.name == "Quotes")
    assert {cell.address for cell in quotes.formula_cells}.issuperset(expected["required_formula_addresses"])
    assert {sheet.name: len(sheet.validations) for sheet in workbook.sheets if sheet.validations} == expected[
        "validation_counts"
    ]
    assert {sheet.name: len(sheet.conditional_formats) for sheet in workbook.sheets if sheet.conditional_formats} == expected[
        "conditional_format_counts"
    ]
    assert workbook.unsupported_features == expected["unsupported_features"]
    assert any(item["target_sheet"] == "Config" for item in workbook.formula_dependencies)
    assert any(item.id == "Quotes!J7" and item.source_type == "formula" for item in workbook.evidence)


def test_upload_validation_rejects_unsupported_or_invalid_files() -> None:
    with pytest.raises(WorkbookUploadError, match="Only .xlsx"):
        validate_workbook_bytes(b"PK", "quotes.xlsm")
    with pytest.raises(WorkbookUploadError, match="valid XLSX"):
        validate_workbook_bytes(b"PK-not-a-zip", "quotes.xlsx")


def test_upload_endpoint_persists_and_returns_xray(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(storage, "UPLOAD_ROOT", tmp_path)
    response = TestClient(app).post(
        "/api/workbooks/analyze",
        files={
            "file": (
                SAMPLE.name,
                SAMPLE.read_bytes(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["workbook"]["filename"] == SAMPLE.name
    assert len(payload["workbook"]["sheets"]) == 5
    assert payload["workbook"]["unsupported_features"] == ["Declared unsupported feature: PowerQueryRefresh"]
    assert (tmp_path / payload["storage_key"]).exists()
