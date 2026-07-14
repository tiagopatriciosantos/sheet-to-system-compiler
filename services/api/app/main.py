"""API surface for workbook upload and the Fase 1 X-Ray."""

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.domain.models import WorkbookIR
from app.workbook.extractor import extract_workbook
from app.workbook.storage import WorkbookUploadError, store_upload


class HealthResponse(BaseModel):
    status: str
    service: str
    phase: str


app = FastAPI(
    title="Sheet-to-System Compiler API",
    version="0.1.0",
    description="Deterministic workbook ingestion and X-Ray analysis.",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api", phase="workbook-xray")


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
