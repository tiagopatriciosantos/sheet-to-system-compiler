"""Version-zero contracts shared by the API and future compiler stages.

The models deliberately describe data and provenance only. They do not execute
workbook formulas or contain OpenAI calls; those responsibilities belong to
later phases in IMPLEMENTATION_PLAN.md.
"""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


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


class WorkbookValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: str
    validation_type: str | None = None
    operator: str | None = None
    formula1: str | None = None
    formula2: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class ConditionalFormatRule(BaseModel):
    model_config = ConfigDict(extra="forbid")

    range: str
    rule_type: str
    operator: str | None = None
    formula: str | None = None
    evidence_refs: list[str] = Field(default_factory=list)


class WorkbookSheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    visibility: SheetVisibility
    max_row: int = Field(ge=0)
    max_column: int = Field(ge=0)
    tables: list[str] = Field(default_factory=list)
    named_ranges: list[str] = Field(default_factory=list)
    merged_ranges: list[str] = Field(default_factory=list)
    formula_cells: list[FormulaCell] = Field(default_factory=list)
    constants_of_interest: list[str] = Field(default_factory=list)
    validations: list[WorkbookValidation] = Field(default_factory=list)
    conditional_formats: list[ConditionalFormatRule] = Field(default_factory=list)
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
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    origin: RuleOrigin
    status: RuleStatus
    confidence: float = Field(ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list)


class ClarificationQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    question: str
    options: list[str] = Field(min_length=2, max_length=5)
    impact: str
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    blocking: bool = False


class InterpretedRule(BaseModel):
    """Strict model output schema; origin and status are assigned by the API."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^rule-[a-z0-9-]+$")
    name: str = Field(min_length=3, max_length=120)
    plain_language: str = Field(min_length=10, max_length=500)
    rule_type: Literal[
        "calculation",
        "approval",
        "validation",
        "workflow",
        "data_dependency",
        "policy",
        "unsupported",
        "other",
    ]
    expression: str | None = Field(default=None, max_length=600)
    inputs: list[str] = Field(default_factory=list, max_length=12)
    outputs: list[str] = Field(default_factory=list, max_length=12)
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    confidence: float = Field(ge=0, le=1)
    assumptions: list[str] = Field(default_factory=list, max_length=6)


class InterpretationOutput(BaseModel):
    """Structured Outputs contract sent to the model."""

    model_config = ConfigDict(extra="forbid")

    rules: list[InterpretedRule] = Field(max_length=12)
    questions: list[ClarificationQuestion] = Field(max_length=5)


class InterpretationTelemetry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempted: bool = False
    succeeded: bool = False
    model: str | None = None
    prompt_version: str
    response_id: str | None = None
    input_sha256: str
    input_bytes: int = Field(ge=0)
    evidence_count: int = Field(ge=0)
    redacted: bool = True
    duration_ms: int = Field(ge=0)
    error: str | None = None


class WorkbookInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workbook_id: str
    source_sha256: str
    rules: list[BusinessRule] = Field(default_factory=list)
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    unsupported_features: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)
    ai: InterpretationTelemetry

    @model_validator(mode="after")
    def validate_evidence_links(self) -> "WorkbookInterpretation":
        evidence_ids = {item.id for item in self.evidence}
        referenced_ids = {
            ref
            for item in [*self.rules, *self.questions]
            for ref in item.evidence_refs
        }
        dangling = referenced_ids - evidence_ids
        if dangling:
            raise ValueError(f"Interpretation evidence does not exist: {sorted(dangling)}")
        return self


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
