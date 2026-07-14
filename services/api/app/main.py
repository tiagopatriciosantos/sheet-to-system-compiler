"""API surface for workbook upload, X-Ray and Fase 2 interpretation."""

from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.domain.models import WorkbookIR, WorkbookInterpretation
from app.workbook.extractor import extract_workbook
from app.workbook.interpreter import interpret_workbook
from app.workbook.storage import WorkbookUploadError, load_stored_upload, store_upload


class HealthResponse(BaseModel):
    status: str
    service: str
    phase: str


app = FastAPI(
    title="Sheet-to-System Compiler API",
    version="0.1.0",
    description="Deterministic workbook ingestion, X-Ray analysis and evidence-grounded interpretation.",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api", phase="workbook-interpretation")


class WorkbookAnalysisResponse(BaseModel):
    workbook: WorkbookIR
    storage_key: str
    size_bytes: int


@app.post("/api/workbooks/analyze", response_model=WorkbookAnalysisResponse, tags=["workbooks"])
async def analyze_workbook_upload(file: UploadFile = File(...)) -> WorkbookAnalysisResponse:
    try:
        stored = await store_upload(file)
    except WorkbookUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    workbook = extract_workbook(
        path=stored.path,
        workbook_id=stored.workbook_id,
        filename=stored.filename,
        sha256=stored.sha256,
    )
    return WorkbookAnalysisResponse(
        workbook=workbook,
        storage_key=stored.storage_key,
        size_bytes=stored.size_bytes,
    )


class WorkbookInterpretationRequest(BaseModel):
    storage_key: str
    workbook_id: str
    filename: str
    sha256: str


@app.post(
    "/api/workbooks/interpret",
    response_model=WorkbookInterpretation,
    tags=["workbooks"],
)
async def interpret_stored_workbook(request: WorkbookInterpretationRequest) -> WorkbookInterpretation:
    try:
        stored = load_stored_upload(request.storage_key)
    except WorkbookUploadError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if stored.workbook_id != request.workbook_id:
        raise HTTPException(status_code=409, detail="The workbook identity does not match the stored upload.")
    if stored.sha256 != request.sha256:
        raise HTTPException(status_code=409, detail="The workbook hash does not match the stored upload.")

    filename = Path(request.filename).name or stored.filename
    workbook = extract_workbook(
        path=stored.path,
        workbook_id=stored.workbook_id,
        filename=filename,
        sha256=stored.sha256,
    )
    return await interpret_workbook(workbook)
