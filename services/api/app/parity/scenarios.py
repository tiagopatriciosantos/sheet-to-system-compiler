"""Golden parity inputs for the industrial quote workbook."""

from app.domain.models import ParityScenario


def golden_scenarios() -> list[ParityScenario]:
    return [
        ParityScenario(
            id="scenario-01-standard-quote",
            description="Standard industrial quote with a small discount.",
            inputs={"client_id": "C001", "product_id": "PRD-1001", "quantity": 20, "discount": 0.03},
            source="workbook_row",
        ),
        ParityScenario(
            id="scenario-02-client-discount-limit",
            description="Quote exactly at the client discount limit.",
            inputs={"client_id": "C002", "product_id": "PRD-1002", "quantity": 5, "discount": 0.08},
            source="workbook_row",
        ),
        ParityScenario(
            id="scenario-03-marine-product",
            description="Marine product with a retail client discount.",
            inputs={"client_id": "C003", "product_id": "PRD-1003", "quantity": 3, "discount": 0.05},
            source="workbook_row",
        ),
        ParityScenario(
            id="scenario-04-boundary-strict",
            description="Exactly 15% margin, the approval boundary.",
            inputs={"client_id": "C004", "product_id": "PRD-1004", "quantity": 10, "discount": 0},
            source="generated_boundary",
        ),
        ParityScenario(
            id="scenario-05-below-boundary",
            description="Margin below the configured threshold.",
            inputs={"client_id": "C005", "product_id": "PRD-1005", "quantity": 10, "discount": 0},
            source="workbook_row",
        ),
        ParityScenario(
            id="scenario-06-second-product",
            description="Small quantity of a higher-value product.",
            inputs={"client_id": "C001", "product_id": "PRD-1002", "quantity": 2, "discount": 0.02},
            source="workbook_row",
        ),
        ParityScenario(
            id="scenario-07-zero-discount",
            description="No discount applied.",
            inputs={"client_id": "C001", "product_id": "PRD-1001", "quantity": 1, "discount": 0},
            source="generated_boundary",
        ),
        ParityScenario(
            id="scenario-08-max-client-discount",
            description="Northwind quote at its maximum allowed discount.",
            inputs={"client_id": "C001", "product_id": "PRD-1001", "quantity": 10, "discount": 0.1},
            source="generated_boundary",
        ),
        ParityScenario(
            id="scenario-09-single-unit",
            description="Single-unit quote for rounding behaviour.",
            inputs={"client_id": "C004", "product_id": "PRD-1003", "quantity": 1, "discount": 0.12},
            source="generated_boundary",
        ),
        ParityScenario(
            id="scenario-10-low-margin-discount",
            description="Low-margin product with a small discount.",
            inputs={"client_id": "C005", "product_id": "PRD-1005", "quantity": 2, "discount": 0.02},
            source="generated_boundary",
        ),
        ParityScenario(
            id="scenario-11-high-volume",
            description="High-volume quote with no discount.",
            inputs={"client_id": "C002", "product_id": "PRD-1002", "quantity": 100, "discount": 0},
            source="generated_boundary",
        ),
        ParityScenario(
            id="scenario-12-exact-client-limit",
            description="Construction client at its exact discount limit.",
            inputs={"client_id": "C004", "product_id": "PRD-1004", "quantity": 4, "discount": 0.12},
            source="generated_boundary",
        ),
    ]
