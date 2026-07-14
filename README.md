# Sheet-to-System Compiler

O Sheet-to-System Compiler transforma folhas de cálculo críticas em sistemas verificáveis. O MVP começa por um workbook de orçamentação e combina extração determinística, interpretação com GPT-5.6, confirmação humana e testes de paridade.

## Estado atual

Fase 4 — aplicação gerada verificável. Nesta fase existem:

- API FastAPI com `/health` e `POST /api/workbooks/analyze`;
- validação, hash e storage local seguro para uploads `.xlsx`;
- `WorkbookIR` determinístico extraído com `openpyxl`;
- identificação de sheets, fórmulas, dependências, validações, tabelas, formatos condicionais e evidência navegável;
- frontend Next.js com upload e X-Ray do workbook;
- botão para interpretar o workbook com GPT-5.6 e Structured Outputs;
- regras inferidas, perguntas de ambiguidade, evidência e proveniência da chamada;
- Resolve Ambiguities com respostas persistidas por workbook;
- compilador determinístico de `SystemBlueprint`, com fingerprint, versão, regras confirmadas e limites visíveis;
- vista legível do blueprint no frontend;
- runtime schema-driven de propostas, sem código executável gerado pelo modelo;
- cálculo de preço, desconto, receita, custo e margem a partir do workbook e do blueprint;
- workflow de aprovação com estados `AUTO_APPROVED`, `NEEDS_APPROVAL`, `APPROVED` e `REJECTED`;
- lista, criação, detalhe e transição de propostas na interface.
- workbook de demonstração industrial com cinco sheets, uma sheet escondida, regras de margem e uma funcionalidade não suportada declarada;
- testes unitários, snapshot e integração HTTP;
- configuração local para `OPENAI_API_KEY` sem incluir a chave no Git.

A paridade pertence à fase seguinte. A aplicação nunca envia o workbook integral para a OpenAI: envia apenas um payload `WorkbookIR` minimizado e redigido.

## Pré-requisitos

- Docker Desktop com Compose;
- ou Python 3.12+, Node.js 22+ e pnpm 11+ para execução local;
- uma chave OpenAI colocada em `.env.local`.

## Executar com Docker

```powershell
docker compose up --build
```

Abrir http://localhost:3000, carregar `samples/industrial-quotes/industrial-quotes.xlsx`, executar o X-Ray, clicar em `Interpretar com GPT-5.6`, responder às ambiguidades, gerar o blueprint e criar uma proposta. Para provar o workflow, usar `STD-10` para obter `NEEDS_APPROVAL` e depois aprovar/rejeitar a proposta. Verificar também http://localhost:8000/health.

Se as portas padrão estiverem ocupadas, definir `API_HOST_PORT` e `WEB_HOST_PORT` no ambiente antes de arrancar o Compose.

## Executar testes locais

```powershell
python -m pip install -r services/api/requirements-dev.txt
python -m pytest services/api/tests

pnpm --dir apps/web install
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
```

## Configuração

Editar `.env.local` e preencher a chave; os restantes parâmetros são opcionais:

```text
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5.6
OPENAI_REASONING_EFFORT=low
OPENAI_TIMEOUT_SECONDS=120
OPENAI_MAX_OUTPUT_TOKENS=5000
```

O backend é o único componente autorizado a usar a chave. O frontend não recebe variáveis `NEXT_PUBLIC_*` com segredos.

## Plano

Consultar [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) e [AGENTS.md](AGENTS.md) antes de avançar para a Fase 5.
