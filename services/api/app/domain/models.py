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


class AmbiguityAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    selected_option: str = Field(min_length=1, max_length=300)
    note: str = Field(default="", max_length=500)
    answered_at: str


class AnswerSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question_id: str
    selected_option: str = Field(min_length=1, max_length=300)
    note: str = Field(default="", max_length=500)


class AnswerRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answers: list[AnswerSelection] = Field(max_length=5)


class ResolutionSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workbook_id: str
    source_sha256: str
    answers: list[AmbiguityAnswer] = Field(default_factory=list)
    updated_at: str


class AmbiguityResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workbook_id: str
    source_sha256: str
    questions: list[ClarificationQuestion] = Field(default_factory=list)
    answers: list[AmbiguityAnswer] = Field(default_factory=list)
    pending_question_ids: list[str] = Field(default_factory=list)
    evidence: list[EvidenceRef] = Field(default_factory=list)


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
    evidence: list[EvidenceRef] = Field(default_factory=list)
    compiled_from_answers: list[str] = Field(default_factory=list)
    answer_fingerprint: str

    @model_validator(mode="after")
    def validate_rule_evidence(self) -> "SystemBlueprint":
        evidence_ids = {item.id for item in self.evidence}
        dangling = {
            ref
            for rule in self.rules
            for ref in rule.evidence_refs
            if ref not in evidence_ids
        }
        if dangling:
            raise ValueError(f"Blueprint rule evidence does not exist: {sorted(dangling)}")
        return self


QuoteApprovalStatus = Literal["AUTO_APPROVED", "NEEDS_APPROVAL", "APPROVED", "REJECTED"]


class QuoteRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    client_id: str
    product_id: str
    quantity: int = Field(ge=1)
    discount: float = Field(ge=0, le=1)
    unit_price: float = Field(ge=0)
    revenue: float = Field(ge=0)
    cost: float = Field(ge=0)
    gross_margin: float
    approval_status: QuoteApprovalStatus
    evidence_reason: str
    created_at: str
    transition_note: str | None = None


class QuoteCreateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    client_id: str = Field(min_length=1, max_length=80)
    product_id: str = Field(min_length=1, max_length=80)
    quantity: int = Field(ge=1, le=100_000)
    discount: float = Field(ge=0, le=1)


class QuoteTransitionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_status: Literal["APPROVED", "REJECTED"]
    note: str = Field(default="", max_length=300)


class RuntimeClient(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str
    max_discount: float = Field(ge=0, le=1)


class RuntimeProduct(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    sku: str
    description: str
    unit_cost: float = Field(ge=0)
    base_price: float = Field(ge=0)


class RuntimeDashboard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_quotes: int = Field(ge=0)
    needs_approval: int = Field(ge=0)
    approved_quotes: int = Field(ge=0)
    rejected_quotes: int = Field(ge=0)
    total_revenue: float = Field(ge=0)


class GeneratedAppResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workbook_id: str
    blueprint_version: str
    unresolved_items: list[str] = Field(default_factory=list)
    workflow: WorkflowSpec | None = None
    clients: list[RuntimeClient] = Field(default_factory=list)
    products: list[RuntimeProduct] = Field(default_factory=list)
    quotes: list[QuoteRecord] = Field(default_factory=list)
    dashboard: RuntimeDashboard


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
    status: ParityStatus = ParityStatus.BLOCKED
    diffs: list[str] = Field(default_factory=list)


ParityRunStatus = Literal["pass", "fail", "blocked"]


class ParityRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    workbook_id: str
    blueprint_version: str
    status: ParityRunStatus
    scenarios: list[ParityScenario] = Field(default_factory=list)
    total: int = Field(ge=0)
    passed: int = Field(ge=0)
    failed: int = Field(ge=0)
    blocked: int = Field(ge=0)
    started_at: str
    finished_at: str
    duration_ms: int = Field(ge=0)
