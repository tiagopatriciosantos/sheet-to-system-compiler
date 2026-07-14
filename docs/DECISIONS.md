# Decisões de arquitetura

## 2026-07-14 — Fase 0

- O MVP será um monorepo com frontend Next.js e API FastAPI.
- A runtime futura será orientada por `SystemBlueprint`; o modelo não produzirá código executável.
- `.env.local` é o destino local da chave OpenAI e está excluído do Git.
- O repositório remoto será `tiagopatriciosantos/sheet-to-system-compiler`.
- O arranque real por Docker foi validado com portas temporárias (`18000`/`13000`), porque a porta 8000 já estava ocupada pelo stack SOFICO local. O Compose suporta agora `API_HOST_PORT` e `WEB_HOST_PORT` sem alterar os defaults documentados.

## 2026-07-14 — Fase 1

- O workbook de demonstração é criado com `@oai/artifact-tool`, mantendo a autoria da folha dentro do runtime disponibilizado para o workspace.
- O extractor usa `openpyxl` apenas para leitura/análise e produz um `WorkbookIR` determinístico com referências de evidência.
- Uploads aceites nesta fase são apenas `.xlsx`, com limites de tamanho, validação ZIP, rejeição de traversal e rejeição de macros `vbaProject.bin`.
- O X-Ray não interpreta ainda a intenção de negócio nem chama a OpenAI; apresenta factos extraídos e warnings explicitamente marcados.
- Como o facade do `artifact-tool` não expõe a visibilidade da worksheet, o builder aplica uma alteração XML mínima e determinística para marcar `Config` como hidden depois da exportação. O conteúdo e a autoria da workbook continuam a ser produzidos pelo `artifact-tool`.
