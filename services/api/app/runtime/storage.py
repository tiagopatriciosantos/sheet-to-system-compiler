"""Atomic runtime state storage for generated application records."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

from app.compiler import storage as artifact_storage
from app.domain.models import QuoteRecord


def _quotes_path(workbook_id: str) -> Path:
    return artifact_storage.artifact_directory(workbook_id) / "runtime" / "quotes.json"


def load_quotes(workbook_id: str) -> list[QuoteRecord]:
    path = _quotes_path(workbook_id)
    if not path.is_file():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [QuoteRecord.model_validate(item) for item in payload.get("quotes", [])]


def save_quotes(workbook_id: str, quotes: list[QuoteRecord]) -> None:
    path = _quotes_path(workbook_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".quotes-",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        json.dump({"quotes": [quote.model_dump(mode="json") for quote in quotes]}, temporary, ensure_ascii=False, indent=2)
        temporary_path = Path(temporary.name)
    temporary_path.replace(path)
