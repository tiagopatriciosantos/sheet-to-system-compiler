import WorkbookAnalyzer from "./components/WorkbookAnalyzer";

async function getApiStatus(): Promise<"online" | "offline"> {
  try {
    const response = await fetch(`${process.env.API_BASE_URL ?? "http://localhost:8000"}/health`, {
      cache: "no-store",
    });
    return response.ok ? "online" : "offline";
  } catch {
    return "offline";
  }
}

export default async function Home() {
  const apiStatus = await getApiStatus();

  return (
    <main className="shell">
      <section className="hero" aria-labelledby="page-title">
        <p className="eyebrow">SHEET-TO-SYSTEM COMPILER · FASE 2</p>
        <h1 id="page-title">Folhas críticas. Sistemas verificáveis.</h1>
        <p className="lede">
          Revelamos a estrutura, extraímos evidência e pedimos ao GPT-5.6 apenas uma interpretação
          tipada das regras e ambiguidades que o workbook realmente contém.
        </p>
        <div className="status-row" aria-label="Estado dos serviços">
          <span className={`status-dot ${apiStatus}`} aria-hidden="true" />
          API {apiStatus === "online" ? "online" : "offline"}
        </div>
      </section>

      <WorkbookAnalyzer />

      <section className="cards" aria-label="Próximas capacidades">
        <article className="card">
          <span className="card-index">01</span>
          <h2>Workbook X-Ray</h2>
          <p>Fórmulas, folhas escondidas, dependências e evidência navegável.</p>
        </article>
        <article className="card">
          <span className="card-index">02</span>
          <h2>Human-in-the-loop</h2>
          <p>Confirmação apenas onde a lógica do negócio é ambígua ou arriscada.</p>
        </article>
        <article className="card">
          <span className="card-index">03</span>
          <h2>Parity Lab</h2>
          <p>Comparação entre o workbook original e a aplicação compilada.</p>
        </article>
      </section>
    </main>
  );
}
