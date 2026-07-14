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

## Fase 3 — decisão humana e compilação

Esta fase não faz uma nova chamada à OpenAI. O utilizador escolhe entre opções previamente devolvidas pelo Structured Output; o backend valida a opção contra a pergunta, acrescenta a resposta como evidência humana e compila o `SystemBlueprint` com regras determinísticas. A nota e o timestamp são metadados de auditoria e não entram no fingerprint da versão.

## Fase 4 — runtime gerada

Esta fase também não faz chamadas à OpenAI. A runtime usa apenas o `SystemBlueprint` validado e dados tabulares do workbook. Não avalia fórmulas Excel, não executa código do modelo e não inventa campos; qualquer capacidade fora do subconjunto de propostas é tratada como limitação explícita até à paridade.

## Fase 5 — paridade

Esta fase não faz chamadas à OpenAI. Os 12 cenários são definidos deterministicamente e executados contra uma cópia recalculada pelo LibreOffice e contra a runtime compilada. A correção da fronteira de 15% foi feita no compilador determinístico a partir da resposta humana já persistida; não houve geração de código nem alteração autónoma de regras pelo modelo.
