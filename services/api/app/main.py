"""API surface for workbook upload, X-Ray, interpretation and blueprint compilation."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from app.compiler.compiler import BlueprintCompilationError, compile_blueprint
from app.compiler.storage import (
    ArtifactNotFoundError,
    load_blueprint,
    load_interpretation,
    load_resolution,
    save_blueprint,
    save_interpretation,
    save_resolution,
)
from app.domain.models import (
    AmbiguityAnswer,
    AmbiguityResponse,
    AnswerRequest,
    GeneratedAppResponse,
    QuoteCreateRequest,
    QuoteTransitionRequest,
    ResolutionSnapshot,
    SystemBlueprint,
    WorkbookIR,
    WorkbookInterpretation,
)
from app.runtime.service import QuoteRuntime, RuntimeConfigurationError, RuntimeValidationError
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
    return HealthResponse(status="ok", service="api", phase="generated-app")


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
    interpretation = await interpret_workbook(workbook)
    save_interpretation(interpretation)
    return interpretation


def _load_interpretation(workbook_id: str) -> WorkbookInterpretation:
    try:
        interpretation = load_interpretation(workbook_id)
    except (ArtifactNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not interpretation.ai.succeeded:
        raise HTTPException(status_code=409, detail="A successful interpretation is required first.")
    return interpretation


def _ambiguity_response(
    interpretation: WorkbookInterpretation,
    resolution: ResolutionSnapshot | None,
) -> AmbiguityResponse:
    answers = resolution.answers if resolution else []
    answered_ids = {answer.question_id for answer in answers}
    return AmbiguityResponse(
        workbook_id=interpretation.workbook_id,
        source_sha256=interpretation.source_sha256,
        questions=interpretation.questions,
        answers=answers,
        pending_question_ids=[
            question.id for question in interpretation.questions if question.id not in answered_ids
        ],
        evidence=interpretation.evidence,
    )


@app.get(
    "/api/workbooks/{workbook_id}/ambiguities",
    response_model=AmbiguityResponse,
    tags=["workbooks"],
)
def get_workbook_ambiguities(workbook_id: str) -> AmbiguityResponse:
    interpretation = _load_interpretation(workbook_id)
    try:
        resolution = load_resolution(workbook_id)
    except (ArtifactNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _ambiguity_response(interpretation, resolution)


@app.post(
    "/api/workbooks/{workbook_id}/answers",
    response_model=AmbiguityResponse,
    tags=["workbooks"],
)
def save_workbook_answers(workbook_id: str, request: AnswerRequest) -> AmbiguityResponse:
    interpretation = _load_interpretation(workbook_id)
    questions = {question.id: question for question in interpretation.questions}
    try:
        resolution = load_resolution(workbook_id)
    except (ArtifactNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    existing = {answer.question_id: answer for answer in (resolution.answers if resolution else [])}
    for selection in request.answers:
        question = questions.get(selection.question_id)
        if question is None:
            raise HTTPException(status_code=400, detail=f"Unknown clarification question: {selection.question_id}.")
        if selection.selected_option not in question.options:
            raise HTTPException(status_code=400, detail=f"Selected option is not valid for {selection.question_id}.")
        existing[selection.question_id] = AmbiguityAnswer(
            question_id=selection.question_id,
            selected_option=selection.selected_option,
            note=selection.note,
            answered_at=datetime.now(timezone.utc).isoformat(),
        )

    snapshot = ResolutionSnapshot(
        workbook_id=workbook_id,
        source_sha256=interpretation.source_sha256,
        answers=sorted(existing.values(), key=lambda answer: answer.question_id),
        updated_at=datetime.now(timezone.utc).isoformat(),
    )
    save_resolution(snapshot)
    return _ambiguity_response(interpretation, snapshot)


@app.post(
    "/api/workbooks/{workbook_id}/compile",
    response_model=SystemBlueprint,
    tags=["workbooks"],
)
def compile_workbook_blueprint(workbook_id: str) -> SystemBlueprint:
    interpretation = _load_interpretation(workbook_id)
    try:
        resolution = load_resolution(workbook_id)
        blueprint = compile_blueprint(interpretation, resolution.answers if resolution else [])
        save_blueprint(workbook_id, blueprint)
    except BlueprintCompilationError as exc:
        raise HTTPException(
            status_code=409,
            detail={"message": str(exc), "pending_question_ids": exc.pending_question_ids},
        ) from exc
    except (ArtifactNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return blueprint


@app.get(
    "/api/workbooks/{workbook_id}/blueprint",
    response_model=SystemBlueprint,
    tags=["workbooks"],
)
def get_workbook_blueprint(workbook_id: str) -> SystemBlueprint:
    try:
        blueprint = load_blueprint(workbook_id)
    except (ArtifactNotFoundError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if blueprint is None:
        raise HTTPException(status_code=404, detail="The workbook blueprint was not compiled yet.")
    return blueprint


def _load_quote_runtime(workbook_id: str) -> QuoteRuntime:
    try:
        blueprint = load_blueprint(workbook_id)
        if blueprint is None:
            raise HTTPException(status_code=404, detail="Compile the workbook blueprint before opening the app.")
        stored = load_stored_upload(f"{workbook_id}.xlsx")
    except HTTPException:
        raise
    except (ArtifactNotFoundError, WorkbookUploadError, ValueError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if stored.sha256 != blueprint.source_workbook_hash:
        raise HTTPException(status_code=409, detail="The uploaded workbook does not match the compiled blueprint.")
    try:
        return QuoteRuntime(workbook_id, stored.path, blueprint)
    except RuntimeConfigurationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.get(
    "/api/workbooks/{workbook_id}/app",
    response_model=GeneratedAppResponse,
    tags=["generated-app"],
)
def get_generated_app(workbook_id: str) -> GeneratedAppResponse:
    return _load_quote_runtime(workbook_id).snapshot()


@app.post(
    "/api/workbooks/{workbook_id}/app/quotes",
    response_model=GeneratedAppResponse,
    tags=["generated-app"],
)
def create_generated_quote(workbook_id: str, request: QuoteCreateRequest) -> GeneratedAppResponse:
    runtime = _load_quote_runtime(workbook_id)
    try:
        return runtime.create_quote(request)
    except RuntimeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post(
    "/api/workbooks/{workbook_id}/app/quotes/{quote_id}/transitions",
    response_model=GeneratedAppResponse,
    tags=["generated-app"],
)
def transition_generated_quote(
    workbook_id: str,
    quote_id: str,
    request: QuoteTransitionRequest,
) -> GeneratedAppResponse:
    runtime = _load_quote_runtime(workbook_id)
    try:
        return runtime.transition_quote(quote_id, request)
    except RuntimeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
