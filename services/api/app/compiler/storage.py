"""File-backed persistence for Fase 3 artifacts in the local MVP."""

from __future__ import annotations

import os
import json
import tempfile
import uuid
from pathlib import Path

from app.domain.models import ResolutionSnapshot, SystemBlueprint, WorkbookInterpretation


ARTIFACT_ROOT = Path(os.getenv("ARTIFACT_ROOT", "data/artifacts"))


class ArtifactNotFoundError(FileNotFoundError):
    pass


def _workbook_dir(workbook_id: str) -> Path:
    try:
        safe_id = str(uuid.UUID(workbook_id))
    except ValueError as exc:
        raise ArtifactNotFoundError("The workbook identity is invalid.") from exc
    root = ARTIFACT_ROOT.resolve()
    target = (root / safe_id).resolve()
    if target.parent != root:
        raise ArtifactNotFoundError("The workbook artifact path is invalid.")
    return target


def artifact_directory(workbook_id: str) -> Path:
    """Return the validated artifact directory for a workbook identity."""

    return _workbook_dir(workbook_id)


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as temporary:
        temporary.write(json.dumps(value, ensure_ascii=False, indent=2))
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)


def save_interpretation(interpretation: WorkbookInterpretation) -> None:
    _write_json(_workbook_dir(interpretation.workbook_id) / "interpretation.json", interpretation.model_dump(mode="json"))


def load_interpretation(workbook_id: str) -> WorkbookInterpretation:
    path = _workbook_dir(workbook_id) / "interpretation.json"
    if not path.is_file():
        raise ArtifactNotFoundError("The workbook interpretation was not found. Run interpretation first.")
    return WorkbookInterpretation.model_validate_json(path.read_text(encoding="utf-8"))


def save_resolution(snapshot: ResolutionSnapshot) -> None:
    _write_json(_workbook_dir(snapshot.workbook_id) / "resolution.json", snapshot.model_dump(mode="json"))


def load_resolution(workbook_id: str) -> ResolutionSnapshot | None:
    path = _workbook_dir(workbook_id) / "resolution.json"
    if not path.is_file():
        return None
    return ResolutionSnapshot.model_validate_json(path.read_text(encoding="utf-8"))


def save_blueprint(workbook_id: str, blueprint: SystemBlueprint) -> None:
    directory = _workbook_dir(workbook_id)
    _write_json(directory / "blueprints" / f"{blueprint.version}.json", blueprint.model_dump(mode="json"))
    _write_json(directory / "blueprints" / "current.json", blueprint.model_dump(mode="json"))


def load_blueprint(workbook_id: str) -> SystemBlueprint | None:
    path = _workbook_dir(workbook_id) / "blueprints" / "current.json"
    if not path.is_file():
        return None
    return SystemBlueprint.model_validate_json(path.read_text(encoding="utf-8"))
