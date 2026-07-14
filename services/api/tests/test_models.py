from app.domain.models import (
    BusinessRule,
    EvidenceRef,
    RuleOrigin,
    RuleStatus,
    SheetVisibility,
    SystemBlueprint,
    WorkbookIR,
    WorkbookSheet,
)


def test_workbook_ir_preserves_provenance_and_visibility() -> None:
    evidence = EvidenceRef(
        id="evidence-config-a1",
        source_type="cell",
        sheet="Config",
        address="A1",
        excerpt="Approval threshold",
    )
    workbook = WorkbookIR(
        workbook_id="demo-1",
        sha256="a" * 64,
        filename="industrial-quotes.xlsx",
        sheets=[
            WorkbookSheet(
                name="Config",
                visibility=SheetVisibility.HIDDEN,
                max_row=4,
                max_column=3,
            )
        ],
        evidence=[evidence],
    )

    payload = workbook.model_dump(mode="json")

    assert payload["sheets"][0]["visibility"] == "hidden"
    assert payload["evidence"][0]["address"] == "A1"


def test_blueprint_accepts_rules_with_explicit_evidence() -> None:
    evidence = EvidenceRef(
        id="evidence-config-a1",
        source_type="cell",
        sheet="Config",
        address="A1",
        excerpt="Approval threshold",
    )
    rule = BusinessRule(
        id="rule-margin-approval",
        name="Margem mínima para aprovação",
        plain_language="Propostas abaixo da margem mínima precisam de aprovação.",
        rule_type="approval",
        expression="margin < threshold",
        evidence_refs=["evidence-config-a1"],
        origin=RuleOrigin.INFERRED,
        status=RuleStatus.INFERRED,
        confidence=0.8,
    )
    blueprint = SystemBlueprint(
        version="0.1.0",
        source_workbook_hash="b" * 64,
        rules=[rule],
        evidence=[evidence],
        answer_fingerprint="c" * 64,
    )

    assert blueprint.rules[0].evidence_refs == ["evidence-config-a1"]
    assert blueprint.model_dump(mode="json")["rules"][0]["status"] == "inferred"
