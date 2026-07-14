"""Atomic persistence for parity run reports."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.compiler import storage as artifact_storage
from app.domain.models import ParityRun


def _run_path(workbook_id: str, run_id: str) -> Path:
    return artifact_storage.artifact_directory(workbook_id) / "parity-runs" / f"{run_id}.json"


def save_parity_run(run: ParityRun) -> None:
    path = _run_path(run.workbook_id, run.run_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{run.run_id}.", suffix=".tmp", delete=False
    ) as temporary:
        json.dump(run.model_dump(mode="json"), temporary, ensure_ascii=False, indent=2)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def load_parity_run(workbook_id: str, run_id: str) -> ParityRun:
    path = _run_path(workbook_id, run_id)
    if not path.is_file():
        raise FileNotFoundError("The parity run was not found.")
    return ParityRun.model_validate_json(path.read_text(encoding="utf-8"))
