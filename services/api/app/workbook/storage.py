"""Safe local storage for uploaded `.xlsx` workbooks."""

from __future__ import annotations

import hashlib
import io
import os
import tempfile
import uuid
import zipfile
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile


MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 50 * 1024 * 1024
MAX_ZIP_MEMBERS = 5000
UPLOAD_ROOT = Path(os.getenv("UPLOAD_ROOT", "data/uploads"))


class WorkbookUploadError(ValueError):
    """Raised when an upload is not a safe supported workbook."""


@dataclass(frozen=True)
class StoredWorkbook:
    workbook_id: str
    filename: str
    storage_key: str
    path: Path
    size_bytes: int
    sha256: str


def validate_workbook_bytes(data: bytes, filename: str | None) -> None:
    """Validate extension, package shape and resource limits before storage."""

    safe_name = Path(filename or "").name
    suffix = Path(safe_name).suffix.lower()
    if suffix != ".xlsx":
        raise WorkbookUploadError("Only .xlsx workbooks are supported in this MVP.")
    if not data:
        raise WorkbookUploadError("The workbook upload is empty.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise WorkbookUploadError(f"Workbook exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.")
    if not data.startswith(b"PK"):
        raise WorkbookUploadError("The upload is not a valid XLSX ZIP package.")

    try:
        with zipfile.ZipFile(io.BytesIO(data)) as package:
            members = package.infolist()
            if len(members) > MAX_ZIP_MEMBERS:
                raise WorkbookUploadError("Workbook contains too many ZIP members.")
            total_uncompressed = sum(member.file_size for member in members)
            if total_uncompressed > MAX_UNCOMPRESSED_BYTES:
                raise WorkbookUploadError("Workbook expands beyond the safe resource limit.")
            for member in members:
                member_path = Path(member.filename)
                if member.filename.startswith(("/", "\\")) or ".." in member_path.parts:
                    raise WorkbookUploadError("Workbook contains an unsafe ZIP path.")
                if member.filename.lower().endswith("vbaproject.bin"):
                    raise WorkbookUploadError("Macro-enabled workbooks are not supported.")
            if package.testzip() is not None:
                raise WorkbookUploadError("Workbook contains a corrupt ZIP member.")
    except zipfile.BadZipFile as exc:
        raise WorkbookUploadError("The upload is not a valid XLSX ZIP package.") from exc


async def store_upload(upload: UploadFile) -> StoredWorkbook:
    """Read, validate and atomically persist an upload without using its filename as a path."""

    data = await upload.read(MAX_UPLOAD_BYTES + 1)
    validate_workbook_bytes(data, upload.filename)
    workbook_id = str(uuid.uuid4())
    UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
    target = UPLOAD_ROOT / f"{workbook_id}.xlsx"
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=UPLOAD_ROOT, prefix=f".{workbook_id}.", suffix=".tmp", delete=False
    ) as temporary:
        temporary.write(data)
        temporary_path = Path(temporary.name)
    temporary_path.replace(target)
    return StoredWorkbook(
        workbook_id=workbook_id,
        filename=Path(upload.filename or "workbook.xlsx").name,
        storage_key=target.name,
        path=target,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )


def load_stored_upload(storage_key: str) -> StoredWorkbook:
    """Resolve a previously stored workbook without accepting arbitrary paths."""

    safe_name = Path(storage_key).name
    if safe_name != storage_key or Path(safe_name).suffix.lower() != ".xlsx":
        raise WorkbookUploadError("The storage key is invalid.")
    try:
        workbook_id = str(uuid.UUID(Path(safe_name).stem))
    except ValueError as exc:
        raise WorkbookUploadError("The storage key is invalid.") from exc

    root = UPLOAD_ROOT.resolve()
    target = (root / safe_name).resolve()
    if target.parent != root or not target.is_file():
        raise WorkbookUploadError("The stored workbook was not found.")

    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return StoredWorkbook(
        workbook_id=workbook_id,
        filename=safe_name,
        storage_key=safe_name,
        path=target,
        size_bytes=target.stat().st_size,
        sha256=digest.hexdigest(),
    )
