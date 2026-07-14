# Sheet-to-System Compiler — plano de implementação

Estado: Fase 4 concluída; Fase 5 por iniciar
Data de referência: 14 de julho de 2026
Track: Work & Productivity
Prazo do hackathon: 21 de julho de 2026, 17:00 PDT

## 1. Tese do produto

As empresas mantêm processos críticos em folhas de cálculo que funcionam como software informal: fórmulas, validações, cores, folhas escondidas, tabelas de referência e conhecimento oral. Migrá-las para uma aplicação costuma exigir entrevistas longas e arrisca perder regras que ninguém documentou.

O Sheet-to-System Compiler recebe um workbook, constrói um “raio-X” verificável das suas regras, pergunta ao utilizador apenas o que é ambíguo, compila uma aplicação web e prova o comportamento através de testes de paridade com a folha original.

### Frase de apresentação

> Transformamos folhas de cálculo críticas em sistemas verificáveis — sem perder as regras invisíveis que mantêm o negócio a funcionar.

### Utilizador inicial

Pequenas e médias empresas, consultores de operações e equipas financeiras que dependem de ficheiros Excel de orçamentação, aprovação comercial ou cálculo de margem.

### Caso de demonstração

Um workbook de orçamentação industrial com clientes, produtos, margens, descontos e aprovação de propostas. Uma regra de margem contém uma fronteira ambígua (`< 15%` versus `<= 15%`). A primeira execução obtém 11/12 cenários; o utilizador corrige a regra com evidência visível e a segunda execução obtém 12/12.

## 2. O que torna a ideia competitiva

O projeto deve demonstrar quatro capacidades em conjunto:

- análise determinística do workbook, não apenas um prompt sobre Excel;
- interpretação semântica com GPT-5.6 e respostas tipadas;
- confirmação humana orientada por evidência;
- verificação comportamental automática.

Um simples “Excel → formulário/CRUD” não é suficiente: esse espaço já é coberto por produtos como AppSheet, Power Apps e Glide. O argumento vencedor é confiança na migração de lógica de negócio.

## 3. Princípios arquiteturais

### 3.1 Compilar um contrato, não código arbitrário

O GPT-5.6 gera objetos que cumprem schemas Pydantic estritos. A aplicação gerada é renderizada por uma runtime determinística a partir de `SystemBlueprint`; o modelo não produz nem executa Python, JavaScript ou SQL.

### 3.2 Separar observação, inferência e confirmação

Cada regra tem uma origem e um estado:

- `observed`: extraída diretamente de fórmula, validação ou estrutura;
- `inferred`: interpretação proposta pelo modelo;
- `confirmed`: validada pelo utilizador;
- `rejected`: rejeitada pelo utilizador;
- `unsupported`: detetada, mas fora das capacidades do MVP.

### 3.3 Toda a afirmação tem proveniência

Uma `EvidenceRef` aponta para sheet, célula/range, fórmula, estilo, screenshot ou resposta humana. A UI deve permitir saltar de uma regra para a respetiva evidência.

### 3.4 O workbook original é o oráculo de regressão

Nos testes de paridade, a mesma entrada é executada no workbook e na runtime compilada. Comparam-se saídas normalizadas e tolerâncias explícitas.

## 4. Arquitetura proposta

```text
Browser / Next.js
        |
        v
FastAPI REST API ---- SQLite (projetos, jobs, respostas, blueprints)
        |
        +---- Upload storage (workbooks e artefactos)
        |
        +---- Worker Python
                |---- openpyxl extractor
                |---- OpenAI Responses API / GPT-5.6
                |---- Blueprint compiler
                `---- LibreOffice headless parity runner
```

### 4.1 Estrutura do repositório

```text
/
  AGENTS.md
  IMPLEMENTATION_PLAN.md
  README.md
  .env.example
  docker-compose.yml
  apps/
    web/                      # Next.js 16 + TypeScript
  services/
    api/
      app/
        api/                  # endpoints HTTP
        ai/                   # prompts, schemas e cliente OpenAI
        domain/               # modelos e regras puras
        workbook/             # extração e normalização
        compiler/             # WorkbookIR -> SystemBlueprint
        parity/               # cenários e comparação
        runtime/              # operações sobre apps compiladas
        worker/               # jobs persistidos
      tests/
        fixtures/
        unit/
        integration/
  samples/
    industrial-quotes/
  docs/
    DECISIONS.md
    AI_USAGE.md
    EVALS.md
    DEMO_SCRIPT.md
```

### 4.2 Stack

| Área | Escolha | Razão |
|---|---|---|
| UI | Next.js 16, App Router, TypeScript | experiência coerente e frontend rápido de iterar |
| Componentes | Tailwind CSS + shadcn/ui | acabamento visual consistente sem construir design system |
| API | Python 3.12 + FastAPI + Pydantic v2 | excelente adequação a análise de Excel e contratos tipados |
| Excel | openpyxl 3.1.x | fórmulas, estilos, validações, nomes e folhas escondidas |
| IA | OpenAI Responses API, `gpt-5.6`, Structured Outputs | interpretação semântica estruturada e exigência do hackathon |
| Persistência | SQLite + SQLAlchemy 2 + Alembic | suficiente para demonstração, sem infraestrutura adicional |
| Jobs | tabela persistida + processo worker | simples, reiniciável e mais seguro do que trabalho pesado no request |
| Paridade | LibreOffice headless isolado | recalcular o workbook sem depender do Excel instalado |
| E2E | Playwright | validar o percurso real no browser |
| Packaging | Docker Compose | execução reproduzível pelo júri e pela equipa |

Não introduzir Redis, Celery, Kubernetes, autenticação multi-tenant ou cloud storage no MVP.

## 5. Contratos centrais

### 5.1 `WorkbookIR`

Representação factual e serializável do workbook:

```text
WorkbookIR
  workbook_id, sha256, filename
  sheets[]
    name, visibility, dimensions
    tables[], named_ranges[], validations[], conditional_formats[]
    formula_cells[], constants_of_interest[], merged_ranges[]
  formula_dependencies[]
  external_links[]
  unsupported_features[]
  evidence[]
```

Para cada fórmula guardar o texto original, tokens, referências, valor cached quando disponível e `EvidenceRef`. O `openpyxl` não calcula fórmulas; nunca interpretar um cached value como recalculado.

### 5.2 `BusinessRule`

```text
id
name
plain_language
rule_type
expression
inputs[] / outputs[]
evidence_refs[]
origin: observed | inferred | human
status: observed | inferred | confirmed | rejected | unsupported
confidence: 0..1
assumptions[]
```

### 5.3 `ClarificationQuestion`

Pergunta concreta, com opções mutuamente exclusivas, impacto previsto e evidência que originou a dúvida. Uma resposta deve produzir uma alteração rastreável no blueprint.

### 5.4 `SystemBlueprint`

```text
version
entities[]              # Client, Product, Quote, QuoteLine
fields[]                # tipos, obrigatoriedade, defaults
calculations[]          # expressões determinísticas suportadas
validations[]
workflows[]             # estados e transições
views[]                 # list/detail/form/dashboard
permissions[]           # apenas papéis simples no MVP
rules[]
unresolved_items[]
source_workbook_hash
```

O schema é versionado. O compiler recusa blueprints inválidos ou com referências pendentes.

### 5.5 `ParityScenario`

```text
id, description
inputs{}
expected_outputs{}
tolerances{}
source: workbook_row | generated_boundary | human
workbook_result{}
runtime_result{}
status: pass | fail | blocked
diffs[]
```

## 6. Pipeline funcional

### Passo A — ingestão segura

1. validar extensão, MIME, tamanho e assinatura ZIP;
2. copiar para storage com UUID e calcular SHA-256;
3. rejeitar ficheiros encriptados, macros e limites anormais de descompressão;
4. criar job persistido;
5. devolver imediatamente o ID do job.

Limites iniciais: `.xlsx`, máximo 10 MB, 50 sheets, 200 mil células não vazias e 60 segundos por subprocesso.

### Passo B — extração determinística

Abrir duas vezes quando necessário:

- `data_only=False` para fórmulas;
- `data_only=True` para valores cached.

Extrair estrutura, fórmulas, dependências, nomes, tabelas, validações, estilos relevantes, formatação condicional, sheets escondidas e ligações externas. Produzir warnings explícitos para funcionalidades não suportadas.

### Passo C — interpretação com GPT-5.6

Enviar uma versão minimizada do `WorkbookIR`, exemplos de linhas redigidos e, apenas quando acrescentem semântica, imagens de regiões relevantes. Usar Structured Outputs com Pydantic para gerar:

1. conceitos de negócio;
2. regras candidatas;
3. ambiguidades;
4. proposta inicial de entidades e workflows.

Invariantes do prompt:

- não inventar fórmulas ou campos;
- cada regra exige evidência;
- ausência de evidência resulta em `unknown`;
- separar observação de inferência;
- assinalar conflito entre fontes;
- nunca devolver código executável.

Usar `gpt-5.6` com esforço de raciocínio médio por defeito. Registar `response_id`, modelo, versão do prompt, duração e schema version. Não registar dados sensíveis.

### Passo D — entrevista de ambiguidades

A UI agrupa questões por impacto. O utilizador vê a pergunta, as células relacionadas, a interpretação atual e o efeito de cada resposta. Não pedir confirmação de tudo: apenas de conflitos, baixa confiança ou regras com impacto elevado.

### Passo E — compilação

Combinar `WorkbookIR`, regras confirmadas e respostas humanas. Validar o `SystemBlueprint` e criar uma versão imutável. A runtime genérica passa a renderizar formulários, listas, cálculos e workflow a partir desta versão.

### Passo F — paridade

Para cada cenário:

1. criar uma cópia temporária do workbook;
2. escrever inputs apenas em células/named ranges permitidos;
3. recalcular com LibreOffice headless, sem rede e com timeout;
4. ler outputs;
5. executar a mesma entrada na runtime;
6. normalizar moedas, percentagens, datas e arredondamentos;
7. apresentar diferenças com ligação à regra e evidência.

Se o LibreOffice não reproduzir uma funcionalidade, marcar `blocked`; nunca converter em `pass`.

## 7. API mínima

```text
POST   /api/projects
POST   /api/projects/{project_id}/workbooks
GET    /api/jobs/{job_id}
GET    /api/projects/{project_id}/analysis
POST   /api/projects/{project_id}/answers
POST   /api/projects/{project_id}/compile
GET    /api/projects/{project_id}/blueprints/{version}
POST   /api/projects/{project_id}/parity-runs
GET    /api/projects/{project_id}/parity-runs/{run_id}
GET    /api/projects/{project_id}/app
POST   /api/projects/{project_id}/app/quotes
POST   /api/projects/{project_id}/app/quotes/{id}/transitions
GET    /health
```

Uploads multipart usam `UploadFile`, mas o ficheiro tem de ser persistido antes de o request terminar. Jobs longos são executados pelo worker, não por `BackgroundTasks` no processo web.

## 8. Experiência do produto

### Ecrã 1 — Upload

Promessa clara, limites, workbook de exemplo e progresso real por etapas.

### Ecrã 2 — Workbook X-Ray

Mapa das sheets e dependências, regras encontradas, folhas escondidas, riscos e funcionalidades não suportadas. Selecionar uma regra destaca a evidência.

### Ecrã 3 — Resolve Ambiguities

Fila curta de perguntas de elevado impacto. Mostrar “porque estamos a perguntar” e “o que muda”.

### Ecrã 4 — System Blueprint

Entidades, cálculos, validações e workflow numa vista legível. Botão de compilação apenas quando não existirem bloqueios críticos.

### Ecrã 5 — Generated App

Aplicação funcional de propostas: lista, criação, cálculo de preço/margem, estado de aprovação e detalhe. Deve parecer produto final, não painel de developer.

### Ecrã 6 — Parity Lab

Resumo 11/12, tabela de cenários e diff preciso. Corrigir a regra de fronteira e repetir para 12/12 é o clímax da demo.

## 9. Workbook de demonstração

Criar `samples/industrial-quotes/industrial-quotes.xlsx` com dados inteiramente fictícios:

- `Clients`: cliente, segmento e desconto máximo;
- `Products`: SKU, custo, preço-base e categoria;
- `Quotes`: cabeçalho, linhas, total e margem;
- `Approvals`: limiares e estado;
- `Config`: sheet escondida com taxas e limites.

Incluir deliberadamente:

- `XLOOKUP` ou `VLOOKUP` para preço/custo;
- `IF`, `AND`, `SUM` e percentagens;
- validação de dados;
- formatação condicional com significado de negócio;
- uma regra de aprovação dependente da margem;
- uma fronteira ambígua que gere o caso 11/12;
- uma funcionalidade detetada mas não suportada, para provar honestidade do sistema.

Gerar também 12 cenários dourados, incluindo valores exatamente nos limites, zero, arredondamento e desconto máximo.

## 10. Segurança e privacidade do MVP

- nunca executar macros;
- bloquear ligações externas e atualização de dados;
- LibreOffice num processo/container sem rede, diretório temporário e limites;
- prevenir ZIP bombs e path traversal;
- nomes de ficheiro nunca usados como paths físicos;
- apagar temporários após o job;
- API key apenas no servidor;
- logs sem valores de células por defeito;
- sample workbook sem informação real;
- banner claro: protótipo, não usar para decisões financeiras sem validação humana.

## 11. Estratégia de testes

### Unitários

- extração de sheets visíveis/escondidas;
- fórmulas e cached values mantidos separados;
- named ranges, validações e formatação condicional;
- normalização de datas, moedas e percentagens;
- validação dos schemas;
- comparação com tolerâncias;
- rejeição de extensões e workbooks perigosos.

### Golden/snapshot

- `WorkbookIR` do workbook de demonstração;
- `SystemBlueprint` esperado após respostas fixas;
- 12 cenários e respetivos resultados.

### Evals do modelo

Conjunto pequeno e versionado de fragments de `WorkbookIR`:

- regra evidente;
- regra com conflito;
- estilo sem significado comprovável;
- sheet escondida;
- evidência insuficiente;
- prompt injection dentro de uma célula.

Critérios: schema válido, nenhuma regra sem evidência, conflito gera pergunta, texto da célula nunca altera instruções do sistema.

### Integração

- upload → job → análise;
- respostas → blueprint;
- blueprint → proposta criada;
- parity runner → diff esperado.

### E2E

Um teste Playwright cobre todo o percurso principal com o workbook de amostra.

## 12. Plano diário e gates

### 14 julho — Fase 0: fundação

- [x] inicializar Git e monorepo;
- [x] criar FastAPI, Next.js, Docker Compose e health checks;
- [x] criar documentação e CI local;
- [x] criar esqueleto dos modelos Pydantic.

Gate: **concluído**. `docker compose up --build -d` construiu as duas imagens; API e frontend responderam 200 e ambos os containers ficaram `healthy`. Como a porta 8000 já estava ocupada pelo stack SOFICO local, a verificação usou `API_HOST_PORT=18000` e `WEB_HOST_PORT=13000`. A Fase 1 está agora desbloqueada.

### 15 julho — Fase 1: workbook real

- [x] criar workbook de demonstração;
- [x] implementar validação e storage de uploads;
- [x] extrair `WorkbookIR` com `openpyxl`;
- [x] construir X-Ray básico com evidência;
- [x] adicionar fixtures e snapshot tests.

Gate: **concluído**. O upload real do sample pela API Docker respondeu 200 e mostrou 5 sheets, `Config` hidden, 39 fórmulas em `Quotes`, três validações, dois formatos condicionais, 102 dependências e o warning `Declared unsupported feature: PowerQueryRefresh`. O mesmo fluxo foi validado através do proxy Next.js. A Fase 2 ficou desbloqueada e foi concluída no passo seguinte.

### 16 julho — Fase 2: interpretação GPT-5.6

- [x] criar schemas Pydantic para regras e perguntas;
- [x] integrar Responses API e Structured Outputs;
- [x] minimizar/redigir payload;
- [x] guardar proveniência e telemetria;
- [x] implementar evals essenciais.

Gate: **concluído**. O sample foi carregado e interpretado com a chave reutilizada através do Docker: resposta HTTP 200, `gpt-5.6`, Structured Output aceite, 9 regras inferidas, 4 perguntas de ambiguidade e referências de evidência validadas. O eval do caso industrial confirmou regras de `calculation` e `approval` e a pergunta sobre a fronteira de 15%. A Fase 3 ficou desbloqueada e foi concluída no passo seguinte.

### 17 julho — Fase 3: confirmação e blueprint

- [x] construir Resolve Ambiguities;
- [x] persistir respostas;
- [x] compilar e validar `SystemBlueprint` versionado;
- [x] criar vista legível do blueprint.

Gate: **concluído**. A UI permite responder perguntas e gerar o blueprint; a API persiste respostas e blueprints versionados. O teste de gate compila a mesma interpretação com `AUTO_APPROVED at 15%` e `REVIEW at 15%` e verifica fingerprints/versões diferentes, a alteração determinística de `<` para `<=`, estado `confirmed` e evidência humana. O fluxo real no Docker interpretou o sample com 9 regras e 4 perguntas, bloqueou até as três perguntas obrigatórias serem respondidas e persistiu `v1-365b9a632c39` com 9 regras e 4 entidades. A persistência é JSON atómica no MVP; SQLite continua adiado para quando houver jobs multiutilizador.

### 18 julho — Fase 4: aplicação gerada

- [x] implementar runtime schema-driven;
- [x] lista, criação e detalhe de propostas;
- [x] cálculos de margem/desconto;
- [x] workflow simples de aprovação;
- [x] acabamento dos estados de loading/error/empty.

Gate: **concluído**. A runtime lê as entidades e regras do `SystemBlueprint`, usa os dados tabulares do workbook para clientes/produtos/configuração e calcula receita, custo, margem, desconto e estado de aprovação sem executar fórmulas Excel. O teste real criou uma proposta de margem 10% como `NEEDS_APPROVAL`, transitou-a para `APPROVED`, criou uma proposta auto-aprovada através do proxy Next.js e confirmou os endpoints em Docker. A Fase 5 permanece por iniciar.

### 19 julho — Fase 5: paridade

- [ ] criar runner LibreOffice isolado;
- [ ] executar os 12 cenários no workbook e runtime;
- [ ] normalizar resultados e produzir diffs;
- [ ] construir Parity Lab;
- [ ] validar a sequência 11/12 → correção → 12/12.

Gate: a falha é real, explicável e desaparece apenas após corrigir a regra.

### 20 julho — Fase 6: produto e submissão

- [ ] E2E completo e revisão de segurança;
- [ ] UI polish e responsividade desktop;
- [ ] README reproduzível;
- [ ] `docs/AI_USAGE.md` e `docs/EVALS.md` completos;
- [ ] script de demo inferior a 3 minutos;
- [ ] gravar plano B da demo local sem depender da rede.

Gate: clone limpo → configuração → aplicação funcional; ensaio da demo abaixo de 2m50s.

### 21 julho — Fase 7: buffer e entrega

- [ ] corrigir apenas bloqueios;
- [ ] gerar versão/release demonstrável;
- [ ] vídeo público com áudio;
- [ ] repositório, README e descrição final;
- [ ] incluir session ID obtido através de `/feedback`;
- [ ] submeter várias horas antes do limite.

Gate: todos os URLs públicos funcionam numa janela anónima e a submissão está completa.

## 13. Critérios de aceitação do MVP

O MVP está pronto apenas se:

1. aceita o workbook real de demonstração;
2. mostra a estrutura e pelo menos cinco regras com evidência navegável;
3. identifica a sheet escondida e uma funcionalidade não suportada;
4. usa GPT-5.6 através da Responses API com Structured Outputs;
5. faz pelo menos uma pergunta cuja resposta altera o blueprint;
6. gera uma aplicação funcional, não apenas screenshots;
7. cria e calcula uma proposta;
8. executa 12 testes de paridade reais;
9. demonstra uma falha de fronteira e a respetiva correção;
10. passa unit, integration, type-check, lint e E2E principal;
11. arranca de forma documentada com Docker Compose;
12. documenta claramente limitações, Codex, GPT-5.6 e evals.

## 14. Plano de redução de risco

### Se a interpretação de fórmulas for demasiado ampla

Suportar apenas o subconjunto usado no workbook de demonstração: operadores aritméticos/comparação, `IF`, `AND`, `OR`, `SUM`, `VLOOKUP`/`XLOOKUP` e referências simples. Todo o resto fica `unsupported`.

### Se o LibreOffice divergir do Excel

Reduzir os cenários às funções compatíveis. Como fallback honesto, usar outputs cached de linhas históricas e rotular a execução como “cached-output regression”; não alegar recálculo.

### Se a chamada GPT for lenta

Executar como job, apresentar progresso e usar background mode apenas se necessário. Manter um artefacto de análise previamente gerado para a gravação, mas demonstrar claramente qual é o modo replay.

### Se faltar tempo para UI secundária

Preservar Upload, X-Ray, Ambiguities, Generated App e Parity Lab. Remover dashboard, export e visualizações ornamentais.

## 15. Fora do MVP

- conversão genérica de qualquer workbook;
- `.xls`, `.xlsm`, VBA e Power Query;
- colaboração em tempo real;
- autenticação empresarial e permissões granulares;
- geração de código-fonte para download;
- integração direta com ERP/CRM;
- edição visual livre do blueprint;
- deployment automático da aplicação gerada;
- suporte móvel completo.

## 16. Demo de 3 minutos

1. **0:00–0:20 — problema:** “Esta folha é o sistema comercial de uma fábrica, mas ninguém consegue explicar todas as regras.”
2. **0:20–0:50 — upload/X-Ray:** mostrar fórmulas, sheet escondida, dependências e evidência.
3. **0:50–1:15 — inteligência:** regras propostas e pergunta sobre o limite de margem.
4. **1:15–1:45 — compilação:** abrir a aplicação gerada e criar uma proposta.
5. **1:45–2:25 — prova:** executar paridade e obter 11/12; abrir o diff na fronteira de 15%.
6. **2:25–2:45 — correção:** confirmar `<= 15%`, recompilar e obter 12/12.
7. **2:45–3:00 — impacto:** migrações mais rápidas, auditáveis e com menor risco operacional.

## 17. Como o Codex deve executar este plano

Em cada nova sessão:

1. ler `AGENTS.md` e este plano;
2. inspecionar o estado real do repositório;
3. selecionar a primeira checklist incompleta cujo gate anterior esteja verde;
4. criar um plano curto de execução;
5. implementar uma fatia verificável;
6. correr testes proporcionais ao risco;
7. atualizar checklists, decisões e limitações;
8. parar se uma decisão alterar a tese, a arquitetura central ou o âmbito do MVP.

Prompt inicial recomendado para o Codex App:

> Lê integralmente `AGENTS.md` e `IMPLEMENTATION_PLAN.md`. Inspeciona o workspace e implementa a primeira fase incompleta, sem avançar para a fase seguinte. Mantém o âmbito do MVP, cria os testes definidos para a fase e só marca o gate como concluído depois de o verificares. No fim, indica o que implementaste, os comandos executados, os resultados e qualquer limitação real.

## 18. Referências técnicas

- OpenAI — GPT-5.6 Sol: https://developers.openai.com/api/docs/models/gpt-5.6-sol
- OpenAI — Structured Outputs: https://developers.openai.com/api/docs/guides/structured-outputs
- OpenAI — Responses API: https://developers.openai.com/api/docs/guides/migrate-to-responses
- OpenAI — Background mode: https://developers.openai.com/api/docs/guides/background
- OpenAI — File inputs: https://developers.openai.com/api/docs/guides/file-inputs
- OpenAI — Images and vision: https://developers.openai.com/api/docs/guides/images-vision
- openpyxl — tutorial: https://openpyxl.readthedocs.io/en/stable/tutorial.html
- openpyxl — formulas: https://openpyxl.readthedocs.io/en/stable/formula.html
- FastAPI — file uploads: https://fastapi.tiangolo.com/tutorial/request-files/
- FastAPI — background tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
- Next.js — App Router: https://nextjs.org/docs/app
- Hackathon — rules: https://openai.devpost.com/rules
- Hackathon — resources: https://openai.devpost.com/resources

## 19. Matriz de prova para o júri

| Critério | O que o produto prova | Momento da demo |
|---|---|---|
| Technological Implementation | Extração real com `openpyxl`, schemas tipados, GPT-5.6, compiler determinístico e execução de paridade | X-Ray, regras com evidência e 12 cenários executados |
| Design | Percurso completo entre upload, decisão humana, aplicação utilizável e diagnóstico de diferenças | transição contínua entre os seis ecrãs; estados de erro e progresso reais |
| Potential Impact | Redução concreta do risco e do tempo de migração de processos críticos para PMEs e consultores | regra invisível descoberta antes de a migração ser aceite |
| Quality of the Idea | Não é um conversor genérico: combina engenharia reversa, proveniência, human-in-the-loop e verificação comportamental | falha 11/12 explicada, corrigida e comprovada em 12/12 |

Nenhuma afirmação da apresentação deve exceder o que a demo executa. A melhor prova do projeto é o ciclo completo e real, não o número de funcionalidades.
