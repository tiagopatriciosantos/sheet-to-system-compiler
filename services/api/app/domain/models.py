"""Version-zero contracts shared by the API and future compiler stages.

The models deliberately describe data and provenance only. They do not execute
workbook formulas or contain OpenAI calls; those responsibilities belong to
later phases in IMPLEMENTATION_PLAN.md.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvidenceRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source_type: Literal["cell", "range", "formula", "style", "screenshot", "human"]
    sheet: str | None = None
    address: str | None = None
    excerpt: str | None = None


class SheetVisibility(str, Enum):
    VISIBLE = "visible"
    HIDDEN = "hidden"
    VERY_HIDDEN = "very_hidden"


class FormulaCell(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str
    formula: str
    cached_value: Any | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class WorkbookSheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    visibility: SheetVisibility
    max_row: int = Field(ge=0)
    max_column: int = Field(ge=0)
    formula_cells: list[FormulaCell] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class WorkbookIR(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workbook_id: str
    sha256: str
    filename: str
    sheets: list[WorkbookSheet] = Field(default_factory=list)
    formula_dependencies: list[dict[str, str]] = Field(default_factory=list)
    external_links: list[str] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


class RuleOrigin(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    HUMAN = "human"


class RuleStatus(str, Enum):
    OBSERVED = "observed"
    INFERRED = "inferred"
    CONFIRMED = "confirmed"
    REJECTED = "rejected"
    UNSUPPORTED = "unsupported"


class BusinessRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    plain_language: str
    rule_type: str
    expression: str | None = None
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    origin: RuleOrigin
    status: RuleStatus
    confidence: float = Field(ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list)


class ClarificationQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    options: list[str] = Field(min_length=2)
    impact: str
    evidence_refs: list[str] = Field(default_factory=list)
    blocking: bool = False


class EntityField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    data_type: str
    required: bool = False
    default: Any | None = None


class EntitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    fields: list[EntityField] = Field(default_factory=list)


class CalculationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    target: str
    expression: str
    evidence_refs: list[str] = Field(default_factory=list)


class ValidationSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    target: str
    expression: str
    message: str
    evidence_refs: list[str] = Field(default_factory=list)


class WorkflowSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    states: list[str] = Field(min_length=1)
    transitions: list[dict[str, str]] = Field(default_factory=list)


class ViewSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    view_type: Literal["list", "detail", "form", "dashboard"]
    entity: str


class SystemBlueprint(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    source_workbook_hash: str
    entities: list[EntitySpec] = Field(default_factory=list)
    calculations: list[CalculationSpec] = Field(default_factory=list)
    validations: list[ValidationSpec] = Field(default_factory=list)
    workflows: list[WorkflowSpec] = Field(default_factory=list)
    views: list[ViewSpec] = Field(default_factory=list)
    rules: list[BusinessRule] = Field(default_factory=list)
    unresolved_items: list[str] = Field(default_factory=list)


class ParityStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    BLOCKED = "blocked"


class ParityScenario(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    description: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outputs: dict[str, Any] = Field(default_factory=dict)
    tolerances: dict[str, float] = Field(default_factory=dict)
    source: Literal["workbook_row", "generated_boundary", "human"]
    workbook_result: dict[str, Any] = Field(default_factory=dict)
    runtime_result: dict[str, Any] = Field(default_factory=dict)
    status: ParityStatus
    diffs: list[str] = Field(default_factory=list)
