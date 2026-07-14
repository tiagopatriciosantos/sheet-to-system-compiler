"use client";

import { FormEvent, useState } from "react";

type Sheet = {
  name: string;
  visibility: "visible" | "hidden" | "very_hidden";
  max_row: number;
  max_column: number;
  tables: string[];
  formula_cells: { address: string; formula: string; cached_value: unknown }[];
  validations: { range: string; validation_type: string | null }[];
  conditional_formats: { range: string; rule_type: string }[];
  warnings: string[];
};

type WorkbookAnalysis = {
  workbook: {
    filename: string;
    sha256: string;
    sheets: Sheet[];
    unsupported_features: string[];
    formula_dependencies: { source_sheet: string; source_address: string; target_sheet: string; target_address: string }[];
  };
  storage_key: string;
  size_bytes: number;
};

function formatVisibility(visibility: Sheet["visibility"]) {
  if (visibility === "hidden") return "hidden";
  if (visibility === "very_hidden") return "very hidden";
  return "visible";
}

export default function WorkbookAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<WorkbookAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Escolhe primeiro um workbook .xlsx.");
      return;
    }

    setLoading(true);
    setError(null);
    setAnalysis(null);
    const body = new FormData();
    body.append("file", file);

    try {
      const response = await fetch("/api/analyze", { method: "POST", body });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Não foi possível analisar o workbook.");
      setAnalysis(payload as WorkbookAnalysis);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Erro inesperado na análise.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="analyzer" aria-labelledby="analyzer-title">
      <div className="analyzer-header">
        <div>
          <p className="eyebrow">WORKBOOK X-RAY</p>
          <h2 id="analyzer-title">Descobre o que a folha realmente sabe.</h2>
        </div>
        <p className="analyzer-note">A análise é determinística nesta fase. O ficheiro fica no backend local.</p>
      </div>

      <form className="upload-form" onSubmit={handleSubmit}>
        <label className="file-picker">
          <span>{file ? file.name : "Escolher workbook .xlsx"}</span>
          <input
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => setFile(event.target.files?.[0] ?? null)}
          />
        </label>
        <button type="submit" disabled={loading}>
          {loading ? "A analisar…" : "Executar X-Ray"}
        </button>
      </form>

      {error ? <p className="feedback error">{error}</p> : null}

      {analysis ? (
        <div className="analysis-result">
          <div className="analysis-meta">
            <span>{analysis.workbook.filename}</span>
            <span>{analysis.size_bytes.toLocaleString("pt-PT")} bytes</span>
            <code>{analysis.workbook.sha256.slice(0, 16)}…</code>
          </div>

          <div className="analysis-grid">
            <div className="analysis-panel">
              <h3>Sheets encontradas</h3>
              <div className="sheet-list">
                {analysis.workbook.sheets.map((sheet) => (
                  <div className="sheet-row" key={sheet.name}>
                    <div>
                      <strong>{sheet.name}</strong>
                      <span className={`visibility ${sheet.visibility}`}>{formatVisibility(sheet.visibility)}</span>
                    </div>
                    <span>{sheet.formula_cells.length} fórmulas · {sheet.validations.length} validações</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="analysis-panel">
              <h3>Riscos e limites</h3>
              {analysis.workbook.unsupported_features.length > 0 ? (
                <ul className="warning-list">
                  {analysis.workbook.unsupported_features.map((warning) => <li key={warning}>{warning}</li>)}
                </ul>
              ) : (
                <p className="success-copy">Nenhuma funcionalidade fora do MVP foi detetada.</p>
              )}
              <p className="dependency-count">
                {analysis.workbook.formula_dependencies.length} dependências de fórmulas extraídas com evidência.
              </p>
            </div>
          </div>

          <div className="evidence-panel">
            <h3>Fórmulas visíveis para auditoria</h3>
            {analysis.workbook.sheets.filter((sheet) => sheet.formula_cells.length > 0).map((sheet) => (
              <details key={sheet.name} open={sheet.name === "Quotes"}>
                <summary>{sheet.name} · {sheet.formula_cells.length} fórmulas</summary>
                <div className="formula-list">
                  {sheet.formula_cells.slice(0, 8).map((formula) => (
                    <code key={`${sheet.name}-${formula.address}`}><b>{formula.address}</b> {formula.formula}</code>
                  ))}
                </div>
              </details>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}
