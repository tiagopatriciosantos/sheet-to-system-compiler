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

## 2026-07-14 — Fase 2

- A interpretação recebe apenas um payload derivado de `WorkbookIR`; o workbook binário nunca é enviado para a OpenAI.
- `InterpretationOutput` é o schema de Structured Outputs. A API transforma o output em `BusinessRule` inferida e atribui a proveniência (`origin`, `status`) no servidor.
- Toda a regra e pergunta tem de referenciar evidência existente. O adaptador tolera apenas sufixos não alfanuméricos ou texto que siga um ID existente de forma não ambígua; referências desconhecidas continuam a falhar.
- A resposta é `store=False` e inclui hash do payload, tamanho, contagem de evidências, prompt version, modelo, response ID, duração e erro redigido.
- A Fase 2 não gera código executável nem altera o workbook; confirmação humana e `SystemBlueprint` continuam na Fase 3.

## 2026-07-14 — Fase 3

- As respostas humanas são persistidas por `workbook_id` em JSON atómico dentro de `data/artifacts`; esta é uma decisão de MVP para não introduzir jobs ou migrações antes da runtime. A migração para SQLite permanece uma tarefa posterior.
- O compiler é determinístico: `answer_fingerprint` deriva apenas do hash do workbook e das opções selecionadas, ignorando timestamps e notas para que a mesma decisão produza a mesma versão.
- Uma decisão relacionada com uma regra acrescenta evidência `human:<question_id>`, muda o estado da regra para `confirmed` e altera apenas expressões suportadas pelo MVP. O compiler nunca produz ou executa código.

## 2026-07-14 — Fase 4

- A runtime é uma interpretação determinística do `SystemBlueprint`, não código gerado pela OpenAI. No MVP suporta o fluxo industrial de propostas: lookup de clientes/produtos, desconto máximo, receita, custo, margem, fronteira `<`/`<=` e transições de aprovação.
- Os dados tabulares de `Clients`, `Products` e `Config` são lidos como inputs constantes; as fórmulas do workbook nunca são executadas pelo runtime. O operador de comparação é lido da regra confirmada no blueprint.
- As propostas são persistidas em `data/artifacts/<workbook_id>/runtime/quotes.json` com escrita atómica. SQLite e multiutilizador continuam fora desta fase; a paridade real pertence à Fase 5.
