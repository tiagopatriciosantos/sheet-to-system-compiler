"""Minimal API surface for Fase 0."""

from fastapi import FastAPI
from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    phase: str


app = FastAPI(
    title="Sheet-to-System Compiler API",
    version="0.1.0",
    description="Foundation API; workbook analysis starts in the next phase.",
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="api", phase="foundation")
