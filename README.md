# Sheet-to-System Compiler

O Sheet-to-System Compiler transforma folhas de cálculo críticas em sistemas verificáveis. O MVP começa por um workbook de orçamentação e combina extração determinística, interpretação com GPT-5.6, confirmação humana e testes de paridade.

## Estado atual

Fase 1 — workbook X-Ray. Nesta fase existem:

- API FastAPI com `/health` e `POST /api/workbooks/analyze`;
- validação, hash e storage local seguro para uploads `.xlsx`;
- `WorkbookIR` determinístico extraído com `openpyxl`;
- identificação de sheets, fórmulas, dependências, validações, tabelas, formatos condicionais e evidência navegável;
- frontend Next.js com upload e X-Ray do workbook;
- workbook de demonstração industrial com cinco sheets, uma sheet escondida, regras de margem e uma funcionalidade não suportada declarada;
- testes unitários, snapshot e integração HTTP;
- configuração local para `OPENAI_API_KEY` sem incluir a chave no Git.

A interpretação semântica com OpenAI e a compilação para aplicação pertencem às fases seguintes. A Fase 1 não faz chamadas à OpenAI.

## Pré-requisitos

- Docker Desktop com Compose;
- ou Python 3.12+, Node.js 22+ e pnpm 11+ para execução local;
- uma chave OpenAI colocada em `.env.local`.

## Executar com Docker

```powershell
docker compose up --build
```

Abrir http://localhost:3000, carregar `samples/industrial-quotes/industrial-quotes.xlsx` e verificar http://localhost:8000/health.

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

Editar `.env.local` e preencher apenas:

```text
OPENAI_API_KEY=...
```

O backend é o único componente autorizado a usar a chave. O frontend não recebe variáveis `NEXT_PUBLIC_*` com segredos.

## Plano

Consultar [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) e [AGENTS.md](AGENTS.md) antes de avançar para a Fase 2.
