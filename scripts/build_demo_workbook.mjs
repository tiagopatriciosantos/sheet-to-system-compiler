import fs from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { SpreadsheetFile, Workbook } from "@oai/artifact-tool";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const outputPath = path.join(root, "samples", "industrial-quotes", "industrial-quotes.xlsx");
const previewDir = path.join(process.env.TEMP ?? path.join(root, ".tmp"), "sheet-system-workbook-previews");

const palette = {
  navy: "#132238",
  teal: "#0F766E",
  mint: "#D8F3E8",
  paleBlue: "#E8F0F8",
  paleAmber: "#FEF3C7",
  paleRed: "#FEE2E2",
  red: "#991B1B",
  green: "#166534",
  ink: "#1F2937",
  muted: "#64748B",
  white: "#FFFFFF",
  line: "#CBD5E1",
};

const titleFormat = {
  fill: palette.navy,
  font: { bold: true, color: palette.white, size: 16 },
  horizontalAlignment: "left",
  verticalAlignment: "center",
};

const subtitleFormat = {
  fill: palette.paleBlue,
  font: { italic: true, color: palette.muted },
  wrapText: true,
  verticalAlignment: "center",
};

const headerFormat = {
  fill: palette.teal,
  font: { bold: true, color: palette.white },
  horizontalAlignment: "center",
  verticalAlignment: "center",
  wrapText: true,
  borders: { preset: "all", style: "thin", color: palette.line },
};

function styleSheet(sheet, titleRange, subtitleRange, headerRange) {
  sheet.showGridLines = false;
  sheet.getRange(titleRange).format = titleFormat;
  sheet.getRange(subtitleRange).format = subtitleFormat;
  sheet.getRange(headerRange).format = headerFormat;
  sheet.getRange(headerRange).format.rowHeight = 30;
}

function styleBody(range) {
  range.format = {
    font: { color: palette.ink },
    verticalAlignment: "center",
    borders: { preset: "inside", style: "thin", color: "#E2E8F0" },
  };
}

const workbook = Workbook.create();
const clients = workbook.worksheets.add("Clients");
const products = workbook.worksheets.add("Products");
const quotes = workbook.worksheets.add("Quotes");
const approvals = workbook.worksheets.add("Approvals");
const config = workbook.worksheets.add("Config");

clients.mergeCells("A1:E1");
clients.getRange("A1").values = [["Clients — customer policy register"]];
clients.getRange("A2:E2").merge();
clients.getRange("A2").values = [["Editable inputs. Maximum discount is a business rule used by the quoting workflow."]];
clients.getRange("A3:E8").values = [
  ["Client ID", "Client name", "Segment", "Max discount", "Payment terms"],
  ["C001", "Northwind Fabrication", "Industrial", 0.1, "30 days"],
  ["C002", "Alpine Components", "Industrial", 0.08, "45 days"],
  ["C003", "Bluebird Retail", "Retail", 0.05, "30 days"],
  ["C004", "Cedar Works", "Construction", 0.12, "60 days"],
  ["C005", "Delta Marine", "Industrial", 0.07, "45 days"],
];
styleSheet(clients, "A1:E1", "A2:E2", "A3:E3");
styleBody(clients.getRange("A4:E8"));
clients.getRange("D4:D8").format.numberFormat = "0.0%";
clients.getRange("A3:E8").format.columnWidth = 18;
clients.getRange("B4:B8").format.columnWidth = 26;
clients.getRange("E4:E8").format.columnWidth = 16;
clients.freezePanes.freezeRows(3);
clients.tables.add("A3:E8", true, "ClientsTable");
clients.getRange("C4:C8").dataValidation = {
  rule: { type: "list", values: ["Industrial", "Retail", "Construction"] },
};

products.mergeCells("A1:F1");
products.getRange("A1").values = [["Products — catalogue and margin inputs"]];
products.getRange("A2:F2").merge();
products.getRange("A2").values = [["Unit cost and base price are the source inputs for quote calculations."]];
products.getRange("A3:F8").values = [
  ["Product ID", "SKU", "Description", "Category", "Unit cost", "Base price"],
  ["PRD-1001", "FAB-01", "Steel mounting frame", "Fabrication", 50, 80],
  ["PRD-1002", "FAB-02", "Precision drive unit", "Fabrication", 120, 180],
  ["PRD-1003", "MAR-01", "Marine-grade enclosure", "Marine", 220, 310],
  ["PRD-1004", "STD-15", "Boundary test component", "Fabrication", 85, 100],
  ["PRD-1005", "STD-10", "Low-margin test component", "Fabrication", 90, 100],
];
styleSheet(products, "A1:F1", "A2:F2", "A3:F3");
styleBody(products.getRange("A4:F8"));
products.getRange("E4:F8").format.numberFormat = '"€"#,##0.00';
products.getRange("A3:F8").format.columnWidth = 16;
products.getRange("C4:C8").format.columnWidth = 28;
products.getRange("A3:F8").format.rowHeight = 22;
products.freezePanes.freezeRows(3);
products.tables.add("A3:F8", true, "ProductsTable");
products.getRange("D4:D8").dataValidation = {
  rule: { type: "list", values: ["Fabrication", "Marine"] },
};

approvals.mergeCells("A1:E1");
approvals.getRange("A1").values = [["Approvals — policy matrix"]];
approvals.getRange("A2:E2").merge();
approvals.getRange("A2").values = [["The margin threshold is intentionally visible here and also stored in hidden Config for auditability."]];
approvals.getRange("A3:E6").values = [
  ["Tier", "Minimum margin", "Required role", "Decision", "Boundary note"],
  ["A", 0.3, "Sales manager", "AUTO_APPROVED", "At or above 30%"],
  ["B", 0.15, "Commercial director", "REVIEW", "Exactly 15% is a deliberate test boundary"],
  ["C", 0, "Finance", "NEEDS_APPROVAL", "Below the configured minimum"],
];
styleSheet(approvals, "A1:E1", "A2:E2", "A3:E3");
styleBody(approvals.getRange("A4:E6"));
approvals.getRange("B4:B6").format.numberFormat = "0.0%";
approvals.getRange("A3:E6").format.columnWidth = 18;
approvals.getRange("C4:C6").format.columnWidth = 24;
approvals.getRange("E4:E6").format.columnWidth = 38;
approvals.freezePanes.freezeRows(3);
approvals.tables.add("A3:E6", true, "ApprovalsTable");

config.mergeCells("A1:D1");
config.getRange("A1").values = [["Config — hidden business parameters"]];
config.getRange("A2:D2").merge();
config.getRange("A2").values = [["Hidden by design: these parameters are evidence, not magic numbers in formulas."]];
config.getRange("A3:D10").values = [
  ["Parameter", "Value", "Business meaning", "Evidence status"],
  ["MarginApprovalThreshold", 0.15, "Quotes below this margin need approval", "Observed in Quotes!J4:J9"],
  ["DefaultMaxDiscount", 0.1, "Fallback when no client policy is found", "Observed in Clients"],
  ["TaxRate", 0.23, "Reference-only tax assumption", "Not used in MVP calculations"],
  ["Currency", "EUR", "Display currency", "Observed in workbook formatting"],
  ["RoundingDecimals", 2, "Currency rounding precision", "Observed in quote output"],
  ["UnsupportedFeature", "PowerQueryRefresh", "External refresh is intentionally outside the MVP", "Warning expected in X-Ray"],
  ["ExternalSource", "Not connected", "No external workbook or network link is executed", "Safety guard"],
];
styleSheet(config, "A1:D1", "A2:D2", "A3:D3");
styleBody(config.getRange("A4:D10"));
config.getRange("B4:B6").format.numberFormat = "0.0%";
config.getRange("A3:D10").format.columnWidth = 22;
config.getRange("C4:C10").format.columnWidth = 42;
config.getRange("D4:D10").format.columnWidth = 30;
config.freezePanes.freezeRows(3);
config.getRange("B9").format = { fill: palette.paleAmber, font: { bold: true, color: "#92400E" } };
config.visibility = "hidden";

quotes.mergeCells("A1:K1");
quotes.getRange("A1").values = [["Quotes — industrial quoting workbook"]];
quotes.getRange("A2:K2").merge();
quotes.getRange("A2").values = [["Formula-driven quote register. Approval status is calculated from Gross Margin and the hidden Config threshold."]];
quotes.getRange("A3:K9").values = [
  ["Quote ID", "Client ID", "Product ID", "Quantity", "Discount", "Unit price", "Revenue", "Cost", "Gross margin", "Approval status", "Evidence / reason"],
  ["Q-1001", "C001", "PRD-1001", 20, 0.03, null, null, null, null, null, null],
  ["Q-1002", "C002", "PRD-1002", 5, 0.1, null, null, null, null, null, null],
  ["Q-1003", "C003", "PRD-1003", 3, 0.05, null, null, null, null, null, null],
  ["Q-1004", "C004", "PRD-1004", 10, 0, null, null, null, null, null, null],
  ["Q-1005", "C005", "PRD-1005", 10, 0, null, null, null, null, null],
  ["Q-1006", "C001", "PRD-1002", 2, 0.02, null, null, null, null, null, null],
];
quotes.getRange("F4:K4").formulas = [[
  "=IFERROR(VLOOKUP(C4,'Products'!$A$4:$F$8,6,FALSE),0)",
  "=D4*F4*(1-E4)",
  "=D4*IFERROR(VLOOKUP(C4,'Products'!$A$4:$F$8,5,FALSE),0)",
  "=IF(G4=0,0,(G4-H4)/G4)",
  "=IF(I4<'Config'!$B$4,\"NEEDS_APPROVAL\",\"AUTO_APPROVED\")",
  "=IF(I4<'Config'!$B$4,\"Margin below configured threshold\",\"Margin meets policy\")",
]];
quotes.getRange("F4:K9").fillDown();
styleSheet(quotes, "A1:K1", "A2:K2", "A3:K3");
styleBody(quotes.getRange("A4:K9"));
quotes.getRange("E4:E9").format.numberFormat = "0.0%";
quotes.getRange("F4:H9").format.numberFormat = '"€"#,##0.00';
quotes.getRange("I4:I9").format.numberFormat = "0.0%";
quotes.getRange("A3:K9").format.rowHeight = 23;
quotes.getRange("A3:K9").format.columnWidth = 14;
quotes.getRange("J3:J9").format.columnWidth = 20;
quotes.getRange("K4:K9").format.columnWidth = 34;
quotes.getRange("A3:K9").format.wrapText = true;
quotes.freezePanes.freezeRows(3);
quotes.tables.add("A3:K9", true, "QuotesTable");
quotes.getRange("B4:B9").dataValidation = {
  rule: { type: "list", formula1: "='Clients'!$A$4:$A$8" },
};
quotes.getRange("C4:C9").dataValidation = {
  rule: { type: "list", formula1: "='Products'!$A$4:$A$8" },
};
quotes.getRange("E4:E9").dataValidation = {
  rule: { type: "decimal", operator: "between", formula1: 0, formula2: 0.2 },
};
quotes.getRange("I4:I9").conditionalFormats.add("cellIs", {
  operator: "lessThan",
  formula: "='Config'!$B$4",
  format: { fill: palette.paleRed, font: { bold: true, color: palette.red } },
});
quotes.getRange("I4:I9").conditionalFormats.add("cellIs", {
  operator: "greaterThanOrEqual",
  formula: "='Config'!$B$4",
  format: { fill: palette.mint, font: { bold: true, color: palette.green } },
});
quotes.getRange("M3:N6").values = [
  ["Summary", "Value"],
  ["Total revenue", null],
  ["Average margin", null],
  ["Quotes needing approval", null],
];
quotes.getRange("N4:N6").formulas = [["=SUM(G4:G9)"], ["=SUM(I4:I9)/6"], ["=COUNTIF(J4:J9,\"NEEDS_APPROVAL\")"]];
quotes.getRange("M3:N3").format = headerFormat;
quotes.getRange("M4:N6").format = { fill: palette.paleBlue, borders: { preset: "all", style: "thin", color: palette.line } };
quotes.getRange("N4").format.numberFormat = '"€"#,##0.00';
quotes.getRange("N5").format.numberFormat = "0.0%";
quotes.getRange("M3:N6").format.columnWidth = 22;

await fs.mkdir(path.dirname(outputPath), { recursive: true });
await fs.mkdir(previewDir, { recursive: true });

const summary = await workbook.inspect({
  kind: "workbook,sheet,table",
  maxChars: 7000,
  tableMaxRows: 4,
  tableMaxCols: 8,
  tableMaxCellChars: 80,
});
console.log("WORKBOOK_SUMMARY");
console.log(summary.ndjson);

const formulas = await workbook.inspect({
  kind: "formula",
  sheetId: "Quotes",
  range: "F4:N9",
  maxChars: 5000,
  options: { maxResults: 100 },
});
console.log("FORMULA_SUMMARY");
console.log(formulas.ndjson);

const errors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A",
  options: { useRegex: true, maxResults: 100 },
  summary: "demo workbook formula error scan",
});
console.log("FORMULA_ERRORS");
console.log(errors.ndjson);

for (const sheetName of ["Clients", "Products", "Quotes", "Approvals", "Config"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: 1, format: "png" });
  const bytes = new Uint8Array(await preview.arrayBuffer());
  await fs.writeFile(path.join(previewDir, `${sheetName}.png`), bytes);
}

const output = await SpreadsheetFile.exportXlsx(workbook);
await output.save(outputPath);
execFileSync("python", [path.join(root, "scripts", "mark_sheet_hidden.py"), outputPath], { stdio: "inherit" });
await fs.rm(`${outputPath}.inspect.ndjson`, { force: true });
console.log(JSON.stringify({ outputPath, previewDir }, null, 2));
process.exit(0);
