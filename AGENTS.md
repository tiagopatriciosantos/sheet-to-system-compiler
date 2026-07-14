# Sheet-to-System Compiler — instruções para o Codex

Antes de alterar código, ler integralmente `IMPLEMENTATION_PLAN.md`.

## Objetivo

Construir um MVP demonstrável que converta um workbook `.xlsx` de orçamentação numa aplicação web configurável, mantendo evidência de cada regra e verificando paridade comportamental entre a folha original e a aplicação.

O produto não é um conversor genérico Excel → CRUD. O núcleo diferenciador é:

1. extrair regras escondidas no workbook;
2. distinguir factos, inferências, ambiguidades e funcionalidades não suportadas;
3. pedir confirmação humana quando necessário;
4. compilar um `SystemBlueprint` tipado;
5. executar cenários de paridade contra o workbook original.

## Forma de trabalhar

- Implementar por fases, na ordem definida no plano.
- Manter no máximo uma fase em curso.
- Antes de iniciar uma fase, confirmar que o gate anterior está verde.
- Não alargar o MVP sem atualizar primeiro a secção “Fora do MVP”.
- Preferir uma fatia vertical funcional a várias componentes incompletas.
- Não esconder erros nem substituir integração real por dados simulados sem o indicar na UI e na documentação.
- Registar decisões não triviais em `docs/DECISIONS.md`.
- Registar prompts, modelos, parâmetros e evals em `docs/AI_USAGE.md`.

## Regras técnicas obrigatórias

- Python 3.12, FastAPI, Pydantic v2 e `openpyxl` no backend.
- Next.js 16, TypeScript estrito e App Router no frontend.
- OpenAI Responses API com `gpt-5.6` e Structured Outputs.
- Os modelos Pydantic são a fonte de verdade dos contratos; gerar tipos TypeScript a partir do OpenAPI.
- O modelo nunca escreve diretamente código executável da aplicação gerada.
- Toda a regra inferida tem `EvidenceRef`, confiança e estado de confirmação.
- Funcionalidade não suportada deve ser visível; nunca migrar silenciosamente.
- O ficheiro carregado é persistido antes de qualquer trabalho assíncrono.
- Aceitar apenas `.xlsx` no MVP; rejeitar `.xls`, `.xlsm` e ficheiros acima dos limites definidos.
- Nunca executar VBA, macros ou ligações externas do workbook.
- Não enviar o workbook integral à OpenAI: enviar apenas o `WorkbookIR` minimizado e imagens estritamente necessárias.

## Qualidade e verificação

Cada fase termina com:

1. testes relevantes verdes;
2. lint e type-check verdes;
3. critério de aceitação demonstrável;
4. atualização da checklist do plano;
5. lista explícita de limitações ainda existentes.

Comandos-alvo, depois do scaffolding:

```powershell
docker compose up --build
pnpm --dir apps/web lint
pnpm --dir apps/web typecheck
pnpm --dir apps/web test
python -m pytest services/api/tests
```

## Prioridade de implementação

Se o tempo apertar, preservar por esta ordem:

1. upload e extração real;
2. evidência e ambiguidades;
3. aplicação gerada funcional;
4. paridade real;
5. acabamento visual;
6. funcionalidades secundárias.
