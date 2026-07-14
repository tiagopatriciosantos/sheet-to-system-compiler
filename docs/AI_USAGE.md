# Utilização de IA

Ainda não existem chamadas à OpenAI na Fase 1. O upload e o X-Ray atual são determinísticos: a aplicação lê a estrutura do workbook, fórmulas, dependências, validações e evidência local sem enviar o ficheiro para um modelo.

Nas fases seguintes, a integração deverá usar a Responses API com `gpt-5.6` e Structured Outputs. O payload será um `WorkbookIR` minimizado, nunca o workbook integral por defeito. Prompts, schemas, versões e resultados de eval serão registados sem segredos ou dados sensíveis.
