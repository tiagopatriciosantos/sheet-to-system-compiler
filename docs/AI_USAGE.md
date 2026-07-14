# Utilização de IA

## Fase 2 — interpretação

- API: Responses API;
- modelo por defeito: `gpt-5.6`;
- Structured Outputs: schema Pydantic `InterpretationOutput` através de `text_format`;
- prompt: `workbook-interpretation-v1`;
- esforço de raciocínio por defeito: `low`, configurável por `OPENAI_REASONING_EFFORT`;
- armazenamento da resposta: `store=False`;
- timeout: 120 segundos por defeito, configurável por `OPENAI_TIMEOUT_SECONDS`.

O workbook binário nunca é enviado ao modelo. O backend extrai primeiro um `WorkbookIR` e cria um payload limitado a estrutura, fórmulas, dependências, validações, funcionalidades não suportadas e evidência. Excerto de emails e telefones é redigido; o payload inclui hash, tamanho e contagem de evidência para proveniência.

O modelo só devolve `InterpretedRule` e `ClarificationQuestion`. A API atribui `origin=inferred` e `status=inferred`, valida IDs de evidência contra a fonte e rejeita referências inventadas. Uma normalização limitada aceita apenas um ID existente seguido de separador; não transforma uma referência sem correspondência numa evidência válida.

O eval essencial do workbook industrial exige regras de `calculation` e `approval`, referência a evidência de margem/configuração e uma pergunta sobre a fronteira de 15%. A execução real validada devolveu 9 regras, 4 perguntas e todos os links de evidência foram aceites pelo contrato.
