# Decisões de arquitetura

## 2026-07-14 — Fase 0

- O MVP será um monorepo com frontend Next.js e API FastAPI.
- A runtime futura será orientada por `SystemBlueprint`; o modelo não produzirá código executável.
- `.env.local` é o destino local da chave OpenAI e está excluído do Git.
- O repositório remoto será `tiagopatriciosantos/sheet-to-system-compiler`.
- A validação local passou; o arranque real por Docker ficou pendente porque o daemon Docker Desktop não estava disponível. Não tratar essa limitação de ambiente como falha do código.
