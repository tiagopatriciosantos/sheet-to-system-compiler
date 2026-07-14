# Sheet-to-System Compiler

O Sheet-to-System Compiler transforma folhas de cálculo críticas em sistemas verificáveis. O MVP começa por um workbook de orçamentação e combina extração determinística, interpretação com GPT-5.6, confirmação humana e testes de paridade.

## Estado atual

Fase 0 — fundação. Nesta fase existem:

- API FastAPI com `/health`;
- modelos Pydantic base para os contratos do produto;
- frontend Next.js mínimo;
- Docker Compose para API e frontend;
- testes unitários da API;
- configuração local para `OPENAI_API_KEY` sem incluir a chave no Git.

O parser de Excel e a integração OpenAI pertencem às fases seguintes e ainda não estão implementados.

## Pré-requisitos

- Docker Desktop com Compose;
- ou Python 3.12+, Node.js 22+ e pnpm 11+ para execução local;
- uma chave OpenAI colocada em `.env.local`.

## Executar com Docker

```powershell
docker compose up --build
```

Abrir http://localhost:3000 e verificar http://localhost:8000/health.

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

Consultar [IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md) e [AGENTS.md](AGENTS.md) antes de implementar a Fase 1.
