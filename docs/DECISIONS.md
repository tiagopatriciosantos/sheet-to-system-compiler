# Decisões de arquitetura

## 2026-07-14 — Fase 0

- O MVP será um monorepo com frontend Next.js e API FastAPI.
- A runtime futura será orientada por `SystemBlueprint`; o modelo não produzirá código executável.
- `.env.local` é o destino local da chave OpenAI e está excluído do Git.
- O repositório remoto será `tiagopatriciosantos/sheet-to-system-compiler`.
- O arranque real por Docker foi validado com portas temporárias (`18000`/`13000`), porque a porta 8000 já estava ocupada pelo stack SOFICO local. O Compose suporta agora `API_HOST_PORT` e `WEB_HOST_PORT` sem alterar os defaults documentados.
