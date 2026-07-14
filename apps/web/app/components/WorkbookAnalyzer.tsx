"use client";

import { type DragEvent, type FormEvent, useState } from "react";

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
    workbook_id: string;
    filename: string;
    sha256: string;
    sheets: Sheet[];
    unsupported_features: string[];
    formula_dependencies: { source_sheet: string; source_address: string; target_sheet: string; target_address: string }[];
  };
  storage_key: string;
  size_bytes: number;
};

type EvidenceRef = {
  id: string;
  source_type: string;
  sheet: string | null;
  address: string | null;
  excerpt: string | null;
};

type Interpretation = {
  workbook_id: string;
  source_sha256: string;
  rules: {
    id: string;
    name: string;
    plain_language: string;
    rule_type: string;
    expression: string | null;
    evidence_refs: string[];
    confidence: number;
    assumptions: string[];
    status: string;
  }[];
  questions: {
    id: string;
    question: string;
    options: string[];
    impact: string;
    evidence_refs: string[];
    blocking: boolean;
  }[];
  unsupported_features: string[];
  evidence: EvidenceRef[];
  ai: {
    attempted: boolean;
    succeeded: boolean;
    model: string | null;
    prompt_version: string;
    response_id: string | null;
    input_sha256: string;
    input_bytes: number;
    evidence_count: number;
    redacted: boolean;
    duration_ms: number;
    error: string | null;
  };
};

type AmbiguityAnswer = {
  question_id: string;
  selected_option: string;
  note: string;
  answered_at: string;
};

type AmbiguityState = {
  answers: AmbiguityAnswer[];
  pending_question_ids: string[];
};

type Blueprint = {
  version: string;
  source_workbook_hash: string;
  entities: { name: string; fields: { name: string; data_type: string; required: boolean }[] }[];
  calculations: { id: string; target: string; expression: string; evidence_refs: string[] }[];
  validations: { id: string; target: string; expression: string; message: string; evidence_refs: string[] }[];
  workflows: { name: string; states: string[]; transitions: { from: string; to: string; when: string }[] }[];
  views: { name: string; view_type: string; entity: string }[];
  rules: {
    id: string;
    name: string;
    plain_language: string;
    rule_type: string;
    expression: string | null;
    status: string;
    evidence_refs: string[];
  }[];
  unresolved_items: string[];
  compiled_from_answers: string[];
  answer_fingerprint: string;
};

function formatVisibility(visibility: Sheet["visibility"]) {
  if (visibility === "hidden") return "hidden";
  if (visibility === "very_hidden") return "very hidden";
  return "visible";
}

export default function WorkbookAnalyzer() {
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<WorkbookAnalysis | null>(null);
  const [interpretation, setInterpretation] = useState<Interpretation | null>(null);
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [blueprint, setBlueprint] = useState<Blueprint | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [interpreting, setInterpreting] = useState(false);
  const [compiling, setCompiling] = useState(false);
  const [isDragging, setIsDragging] = useState(false);

  function acceptFile(candidate: File | undefined) {
    if (!candidate) return;
    if (!candidate.name.toLowerCase().endsWith(".xlsx")) {
      setFile(null);
      setError("Escolhe um workbook .xlsx. Ficheiros .xls e .xlsm não são suportados.");
      return;
    }
    setFile(candidate);
    setError(null);
    setInterpretation(null);
    setAnswers({});
    setBlueprint(null);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragging(false);
    acceptFile(event.dataTransfer.files?.[0]);
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>) {
    const relatedTarget = event.relatedTarget;
    if (!(relatedTarget instanceof Node) || !event.currentTarget.contains(relatedTarget)) {
      setIsDragging(false);
    }
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Escolhe primeiro um workbook .xlsx.");
      return;
    }

    setLoading(true);
    setError(null);
    setAnalysis(null);
    setInterpretation(null);
    setAnswers({});
    setBlueprint(null);
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

  async function handleInterpretation() {
    if (!analysis) return;
    setInterpreting(true);
    setError(null);
    try {
      const response = await fetch("/api/interpret", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          storage_key: analysis.storage_key,
          workbook_id: analysis.workbook.workbook_id,
          filename: analysis.workbook.filename,
          sha256: analysis.workbook.sha256,
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "Não foi possível interpretar o workbook.");
      const interpreted = payload as Interpretation;
      setInterpretation(interpreted);
      setBlueprint(null);
      const stateResponse = await fetch(`/api/workbooks/${interpreted.workbook_id}/ambiguities`, { cache: "no-store" });
      if (stateResponse.ok) {
        const state = (await stateResponse.json()) as AmbiguityState;
        setAnswers(Object.fromEntries(state.answers.map((answer) => [answer.question_id, answer.selected_option])));
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Erro inesperado na interpretação.");
    } finally {
      setInterpreting(false);
    }
  }

  function handleAnswerChange(questionId: string, selectedOption: string) {
    setAnswers((current) => ({ ...current, [questionId]: selectedOption }));
    setBlueprint(null);
  }

  async function handleCompile() {
    if (!interpretation) return;
    setCompiling(true);
    setError(null);
    try {
      const selections = interpretation.questions
        .filter((question) => answers[question.id])
        .map((question) => ({
          question_id: question.id,
          selected_option: answers[question.id],
          note: "",
        }));
      const saveResponse = await fetch(`/api/workbooks/${interpretation.workbook_id}/answers`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ answers: selections }),
      });
      const savedPayload = await saveResponse.json();
      if (!saveResponse.ok) {
        const detail = typeof savedPayload.detail === "string" ? savedPayload.detail : "NÃ£o foi possÃ­vel guardar as decisÃµes.";
        throw new Error(detail);
      }

      const compileResponse = await fetch(`/api/workbooks/${interpretation.workbook_id}/compile`, {
        method: "POST",
        cache: "no-store",
      });
      const compiledPayload = await compileResponse.json();
      if (!compileResponse.ok) {
        const detail = compiledPayload.detail;
        if (detail && typeof detail === "object" && "message" in detail) {
          throw new Error(String(detail.message));
        }
        throw new Error(typeof detail === "string" ? detail : "NÃ£o foi possÃ­vel compilar o blueprint.");
      }
      setBlueprint(compiledPayload as Blueprint);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Erro inesperado na compilaÃ§Ã£o.");
    } finally {
      setCompiling(false);
    }
  }

  const evidenceById = new Map((interpretation?.evidence ?? []).map((item) => [item.id, item]));
  const answeredCount = interpretation?.questions.filter((question) => answers[question.id]).length ?? 0;

  return (
    <section className="analyzer" aria-labelledby="analyzer-title">
      <div className="analyzer-header">
        <div>
          <p className="eyebrow">WORKBOOK X-RAY</p>
          <h2 id="analyzer-title">Descobre o que a folha realmente sabe.</h2>
        </div>
        <p className="analyzer-note">O X-Ray é determinístico. A interpretação envia apenas um payload minimizado para a API.</p>
      </div>

      <form className="upload-form" onSubmit={handleSubmit}>
        <label
          className={`file-picker ${isDragging ? "dragging" : ""}`}
          onDragEnter={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragOver={(event) => {
            event.preventDefault();
            setIsDragging(true);
          }}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
        >
          <span>{file ? file.name : "Arrasta um workbook .xlsx ou clica para escolher"}</span>
          <small>{isDragging ? "Larga o ficheiro aqui" : "Apenas .xlsx · máximo 10 MB"}</small>
          <input
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(event) => acceptFile(event.target.files?.[0])}
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

          <div className="interpretation-action">
            <div>
              <strong>Próximo passo: interpretar regras</strong>
              <span>O workbook já foi minimizado; agora o GPT-5.6 identifica regras e ambiguidades com evidência.</span>
            </div>
            <button type="button" onClick={handleInterpretation} disabled={interpreting}>
              {interpreting ? "A interpretar…" : "Interpretar com GPT-5.6"}
            </button>
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

          {interpretation ? (
            <div className="interpretation-panel">
              <div className="interpretation-heading">
                <div>
                  <p className="eyebrow">INTERPRETAÇÃO TIPADA</p>
                  <h3>{interpretation.ai.succeeded ? "Regras que o workbook está a aplicar" : "Interpretação não concluída"}</h3>
                </div>
                <span className={`ai-badge ${interpretation.ai.succeeded ? "success" : "error"}`}>
                  {interpretation.ai.succeeded ? `${interpretation.rules.length} regras · ${interpretation.questions.length} perguntas` : "ver estado abaixo"}
                </span>
              </div>

              {interpretation.ai.error ? <p className="feedback error">{interpretation.ai.error}</p> : null}

              {interpretation.rules.length > 0 ? (
                <div className="rule-list">
                  {interpretation.rules.map((rule) => (
                    <article className="rule-card" key={rule.id}>
                      <div className="rule-card-heading">
                        <div><span className="rule-type">{rule.rule_type}</span><h4>{rule.name}</h4></div>
                        <strong>{Math.round(rule.confidence * 100)}% confiança</strong>
                      </div>
                      <p>{rule.plain_language}</p>
                      {rule.expression ? <code className="rule-expression">{rule.expression}</code> : null}
                      {rule.assumptions.length > 0 ? <small>Assunções: {rule.assumptions.join(" · ")}</small> : null}
                      <div className="rule-evidence">
                        {rule.evidence_refs.map((ref) => {
                          const item = evidenceById.get(ref);
                          return <span key={ref} title={item?.excerpt ?? ref}>{item?.sheet ? `${item.sheet}!${item.address ?? ""}` : ref}</span>;
                        })}
                      </div>
                    </article>
                  ))}
                </div>
              ) : null}

              {interpretation.questions.length > 0 ? (
                <div className="question-list">
                  <div className="section-heading compact"><div><p className="eyebrow">RESOLVER AMBIGUIDADES</p><h4>Perguntas que mudam o sistema</h4></div></div>
                  {interpretation.questions.map((question) => (
                    <article className="question-card" key={question.id}>
                      <div><strong>{question.question}</strong><span>{question.blocking ? "Bloqueante" : "Decisão recomendada"}</span></div>
                      <p>{question.impact}</p>
                      <label className="answer-picker">
                        <span>DecisÃ£o</span>
                        <select
                          value={answers[question.id] ?? ""}
                          onChange={(event) => handleAnswerChange(question.id, event.target.value)}
                        >
                          <option value="">Escolher uma opÃ§Ã£o</option>
                          {question.options.map((option) => <option key={option} value={option}>{option}</option>)}
                        </select>
                      </label>
                    </article>
                  ))}
                  <div className="answer-actions">
                    <span>{answeredCount}/{interpretation.questions.length} decisÃµes respondidas. As perguntas bloqueantes tÃªm de ser resolvidas.</span>
                    <button type="button" onClick={handleCompile} disabled={compiling}>
                      {compiling ? "A compilar..." : "Guardar decisÃµes e gerar blueprint"}
                    </button>
                  </div>
                </div>
              ) : null}

              {interpretation.questions.length === 0 ? (
                <div className="answer-actions">
                  <span>NÃ£o foram detetadas ambiguidades; o blueprint pode ser gerado diretamente.</span>
                  <button type="button" onClick={handleCompile} disabled={compiling}>
                    {compiling ? "A compilar..." : "Gerar blueprint"}
                  </button>
                </div>
              ) : null}

              {blueprint ? (
                <div className="blueprint-panel">
                  <div className="interpretation-heading">
                    <div>
                      <p className="eyebrow">SYSTEM BLUEPRINT</p>
                      <h3>Contrato compilado e auditÃ¡vel</h3>
                    </div>
                    <code>{blueprint.version}</code>
                  </div>
                  <div className="blueprint-stats">
                    <span><strong>{blueprint.entities.length}</strong> entidades</span>
                    <span><strong>{blueprint.calculations.length}</strong> cÃ¡lculos</span>
                    <span><strong>{blueprint.validations.length}</strong> validaÃ§Ãµes</span>
                    <span><strong>{blueprint.workflows.length}</strong> workflows</span>
                    <span><strong>{blueprint.views.length}</strong> vistas</span>
                  </div>
                  <div className="blueprint-columns">
                    <div>
                      <h4>Regras confirmadas</h4>
                      <div className="blueprint-list">
                        {blueprint.rules.map((rule) => (
                          <article className="blueprint-rule" key={rule.id}>
                            <div><strong>{rule.name}</strong><span>{rule.status}</span></div>
                            {rule.expression ? <code>{rule.expression}</code> : null}
                          </article>
                        ))}
                      </div>
                    </div>
                    <div>
                      <h4>Entidades e limites</h4>
                      <ul className="blueprint-list plain-list">
                        {blueprint.entities.map((entity) => <li key={entity.name}><strong>{entity.name}</strong> · {entity.fields.length} campos</li>)}
                        {blueprint.unresolved_items.map((item) => <li className="unresolved" key={item}>Pendente: {item}</li>)}
                      </ul>
                    </div>
                  </div>
                  <details className="provenance-details">
                    <summary>Fingerprint da decisÃ£o humana</summary>
                    <code>{blueprint.answer_fingerprint}</code>
                  </details>
                </div>
              ) : null}

              <details className="provenance-details">
                <summary>Proveniência e limites da chamada</summary>
                <p>{interpretation.ai.model ?? "modelo não executado"} · prompt {interpretation.ai.prompt_version} · {interpretation.ai.evidence_count} evidências enviadas · {interpretation.ai.input_bytes.toLocaleString("pt-PT")} bytes · payload redigido: {interpretation.ai.redacted ? "sim" : "não"}</p>
                <code>input_sha256 {interpretation.ai.input_sha256}</code>
              </details>
            </div>
          ) : null}
        </div>
      ) : null}
    </section>
  );
}
