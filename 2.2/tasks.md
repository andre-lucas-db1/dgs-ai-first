# Tasks — Query Endpoint

> Gerado a partir de: `specs/query-endpoint/plan.md`  
> Estimativas: **P** = meio dia | **M** = 1 dia | **G** = 2 dias

---

## TASK-001 — Tipos e modelos de domínio

**Arquivo:** `src/shared/types.ts`

**Descrição:** Definir os tipos TypeScript centrais do domínio do query endpoint — Chunk (unidade de contexto recuperada), QueryResponse (contrato de resposta ao atendente) e QueryRequest (derivado do schema Zod do validator).

**Critérios de aceite:**
- `Chunk` possui exatamente os campos: `id: string`, `text: string`, `source_document: string`, `section: string`, `score: number`
- `QueryResponse` possui exatamente os campos: `answer: string`, `source_document: string`, `session_id?: string`
- Nenhum campo usa o tipo `any`
- `tsc --noEmit` passa sem erros em modo strict com os tipos isolados

**Dependências:** nenhuma

**Estimativa:** P

---

## TASK-002 — Módulo de configuração de ambiente

**Arquivo:** `src/shared/config.ts`

**Descrição:** Criar módulo que lê e valida as variáveis de ambiente obrigatórias para o query endpoint na inicialização do processo. Falha rápido com mensagem descritiva se alguma variável estiver ausente.

**Critérios de aceite:**
- Processo lança `Error` com mensagem `"Missing required env var: AZURE_OPENAI_ENDPOINT"` (nome da variável ausente na mensagem) antes de processar qualquer request se a variável não estiver presente
- Exporta objeto `config` tipado como `{ openai: { endpoint: string; apiKey: string; deploymentName: string }; search: { endpoint: string; apiKey: string; indexName: string } }` — sem campos `string | undefined`
- `tsc --noEmit` passa em modo strict
- Nenhum `console.log` no arquivo

**Dependências:** nenhuma

**Estimativa:** P

---

## TASK-003 — Logger estruturado com pino

**Arquivo:** `src/shared/logger.ts`

**Descrição:** Configurar instância pino compartilhada com nível de log controlado por variável de ambiente. Esta instância é a única fonte de logs do projeto — nenhum outro arquivo usa `console.log`.

**Critérios de aceite:**
- Exporta `logger` com interface compatível com pino (`info`, `warn`, `error`, `debug`, `child`)
- Nível padrão é `"info"`, substituível via `process.env.LOG_LEVEL`
- Saída em formato JSON (não pretty-print) quando `NODE_ENV !== 'test'`
- Teste manual: `logger.info({ foo: "bar" })` produz linha JSON com campo `level: 30`

**Dependências:** nenhuma

**Estimativa:** P

---

## TASK-004 — Custom errors do domínio

**Arquivo:** `src/shared/errors.ts`

**Descrição:** Definir hierarquia de erros customizados que permitem ao handler distinguir erros de validação (→ HTTP 400) de erros de serviços Azure (→ HTTP 502) sem inspecionar strings de mensagem.

**Critérios de aceite:**
- `ValidationError` estende `Error`, contém `issues: ZodIssue[]` e o campo estático `statusCode = 400`
- `AzureSearchError` estende `Error`, contém `statusCode: number` e `retryable: boolean`
- `AzureOpenAIError` estende `Error`, contém `statusCode: number` e `retryable: boolean`
- `new ValidationError([...]) instanceof ValidationError` retorna `true` (prototype chain correto)
- `new ValidationError([...]) instanceof Error` retorna `true`
- `tsc --noEmit` passa em modo strict

**Dependências:** nenhuma (importa `ZodIssue` do pacote `zod`)

**Estimativa:** P

---

## TASK-005 — Validador de input (Zod)

**Arquivo:** `src/functions/query/validator.ts`

**Descrição:** Implementar validação do body de `POST /api/query` usando Zod com mensagens de erro em português. Exportar o schema além do tipo para permitir reuso em testes de integração.

**Critérios de aceite:**
- `validateQueryRequest({})` lança `ValidationError` com `issues[0].path` contendo `"question"`
- `validateQueryRequest({ question: "" })` lança `ValidationError` com mensagem em português indicando que a pergunta não pode ser vazia
- `validateQueryRequest({ question: "a".repeat(1001) })` lança `ValidationError` com mensagem em português indicando o limite de 1000 caracteres
- `validateQueryRequest({ question: "Qual o SLA Gold?" })` retorna objeto com tipo `QueryRequest` sem lançar exceção
- `validateQueryRequest({ question: "ok", session_id: "não-é-uuid" })` lança `ValidationError`
- `validateQueryRequest(null)` e `validateQueryRequest("string pura")` lançam `ValidationError`
- `queryRequestSchema` está exportado (além do tipo e da função)
- Nenhum `console.log` no arquivo

**Dependências:** TASK-001, TASK-004

**Estimativa:** P

---

## TASK-006 — Geração de embeddings (Azure OpenAI)

**Arquivo:** `src/services/embedder.ts`

**Descrição:** Implementar função que converte uma string em vetor de embedding via Azure OpenAI Embeddings API com retry automático e backoff exponencial.

**Critérios de aceite:**
- `generateEmbedding(text)` retorna `number[]` com dimensão 1536 para o modelo `text-embedding-3-small`
- Em resposta HTTP 429 ou 503, reexecuta até 3 vezes com backoff: 1s, 2s, 4s
- Erros HTTP 400 e 401 lançam `AzureOpenAIError` com `retryable: false` sem retry
- Logger registra `{ attempt, status }` em cada tentativa e `{ tokens, duration_ms }` no sucesso
- Teste unitário com mock HTTP confirma que 3 falhas consecutivas com 429 resultam em `AzureOpenAIError` após a 3ª tentativa

**Dependências:** TASK-002, TASK-003, TASK-004

**Estimativa:** M

---

## TASK-007 — Busca semântica (Azure AI Search)

**Arquivo:** `src/services/search.ts`

**Descrição:** Implementar função que busca os top-5 chunks mais relevantes no Azure AI Search dado um vetor de embedding.

**Critérios de aceite:**
- `searchChunks(embedding)` retorna `Chunk[]` com no máximo 5 itens
- Cada `Chunk` retornado possui `source_document` e `section` mapeados dos campos de metadados do índice (`metadata_source` e `metadata_section`)
- Retry com backoff exponencial em HTTP 503 (máximo 3 tentativas)
- Erros HTTP 400 lançam `AzureSearchError` com `retryable: false` sem retry
- Logger registra `{ results_count, top_score, duration_ms }` por chamada bem-sucedida

**Dependências:** TASK-001, TASK-002, TASK-003, TASK-004

**Estimativa:** M

---

## TASK-008 — Prompt builder com context budget

**Arquivo:** `src/services/prompt-builder.ts`

**Descrição:** Implementar função que monta o prompt final respeitando o context budget da ADR-0002: ~4K tokens para o system prompt e ~8K tokens para chunks.

**Critérios de aceite:**
- `buildPrompt(systemPrompt, chunks, question)` retorna string com total de tokens ≤ 12500 (estimativa via contagem de caracteres: 1 token ≈ 4 chars)
- Quando os chunks somados ultrapassam 8K tokens, o builder descarta os de menor `score` até caber
- O system prompt nunca é truncado (prioridade máxima no budget)
- Cada chunk no prompt tem cabeçalho no formato `[Fonte: {source_document} | Seção: {section}]`
- Teste com 5 chunks de 2000 tokens confirma que o resultado final tem ≤ 12500 tokens

**Dependências:** TASK-001

**Estimativa:** M

---

## TASK-009 — Completion GPT-4o (Azure OpenAI)

**Arquivo:** `src/services/completion.ts`

**Descrição:** Implementar função que envia o prompt ao GPT-4o via Azure OpenAI e retorna a resposta com metadados de uso.

**Critérios de aceite:**
- `generateCompletion(prompt)` retorna `{ answer: string; usage: { prompt_tokens: number; completion_tokens: number } }`
- Retry com backoff exponencial em HTTP 429 e 503 (máximo 3 tentativas, delay inicial 1s)
- Timeout de 30s por tentativa — lança `AzureOpenAIError` com `retryable: true` se expirar
- Erro HTTP 400 com mensagem "context_length_exceeded" lança `AzureOpenAIError` com `retryable: false`
- Logger registra `{ model, prompt_tokens, completion_tokens, duration_ms }` ao final de cada chamada bem-sucedida

**Dependências:** TASK-002, TASK-003, TASK-004

**Estimativa:** M

---

## TASK-010 — Response builder

**Arquivo:** `src/functions/query/response-builder.ts`

**Descrição:** Implementar função pura que monta a `QueryResponse` final incluindo o `source_document` do chunk mais relevante.

**Critérios de aceite:**
- `buildQueryResponse(answer, chunks, sessionId?)` retorna `QueryResponse` com `source_document` do chunk com maior `score`
- Se `chunks` estiver vazio, `source_document === "source not available"` (nunca `undefined` ou `null`)
- `session_id` é incluído no retorno somente quando `sessionId` for passado como argumento
- Função não produz side effects (sem logs, sem I/O)
- `tsc --noEmit` passa em modo strict

**Dependências:** TASK-001

**Estimativa:** P

---

## TASK-011 — Handler principal (orquestração RAG)

**Arquivo:** `src/functions/query/handler.ts`

**Descrição:** Implementar o Azure Function HTTP trigger que orquestra o fluxo completo: validação → embedding → busca → prompt → completion → resposta.

**Critérios de aceite:**
- `POST /api/query` com body `{ "question": "Qual o SLA Gold?" }` retorna HTTP 200 com `{ answer: string; source_document: string }`
- `POST /api/query` com body `{}` retorna HTTP 400 com `{ error: "validation_error"; issues: ZodIssue[] }`
- Erros `AzureSearchError` ou `AzureOpenAIError` retornam HTTP 502 com `{ error: "upstream_error"; code: string }`
- Stack traces nunca aparecem no body da resposta HTTP (apenas nos logs internos)
- Handler registrado como Azure Function v4: `app.http("query", { methods: ["POST"], authLevel: "function", handler: queryHandler })`
- Logger registra `{ session_id, question_length, source_document, duration_ms }` ao final de cada request bem-sucedido

**Dependências:** TASK-004, TASK-005, TASK-006, TASK-007, TASK-008, TASK-009, TASK-010

**Estimativa:** G

---

## TASK-012 — Testes unitários: validator e response-builder

**Arquivos:** `tests/unit/query/validator.test.ts`, `tests/unit/query/response-builder.test.ts`

**Descrição:** Escrever testes unitários cobrindo casos felizes, limites e erros dos dois módulos de menor dependência.

**Critérios de aceite:**
- Cobertura de branches ≥ 90% nos arquivos `validator.ts` e `response-builder.ts` (medida via `vitest --coverage`)
- Cenários obrigatórios: input vazio, question com 1000 chars (aceita), question com 1001 chars (rejeita), session_id UUID válido (aceita), session_id inválido (rejeita), chunks vazios no response builder
- Nenhum teste faz chamada HTTP real
- `vitest run` completa em < 5 segundos

**Dependências:** TASK-005, TASK-010

**Estimativa:** M

---

## TASK-013 — Testes unitários: prompt-builder (context budget)

**Arquivo:** `tests/unit/services/prompt-builder.test.ts`

**Descrição:** Escrever testes que verificam o comportamento do prompt builder ao atingir e ultrapassar o context budget.

**Critérios de aceite:**
- Teste confirma que 5 chunks de 2000 tokens resultam em output com ≤ 12500 tokens
- Teste confirma que 3 chunks dentro do budget têm todos incluídos no output
- Teste confirma que system prompt nunca é truncado mesmo com chunks grandes
- Teste confirma formato do cabeçalho: `[Fonte: POL-001 | Seção: ## Prazos]`
- Teste confirma que quando chunks são descartados, os de menor score são removidos primeiro

**Dependências:** TASK-008

**Estimativa:** M

---

## TASK-014 — Testes de integração: fluxo completo

**Arquivo:** `tests/integration/query/handler.test.ts`

**Descrição:** Escrever testes de integração que exercitam o handler completo com mocks de APIs Azure via MSW, verificando o contrato HTTP de ponta a ponta.

**Critérios de aceite:**
- Happy path: handler retorna HTTP 200 com `answer` não vazio e `source_document` preenchido
- Input inválido: handler retorna HTTP 400 sem acionar nenhum mock Azure (verificado por ausência de chamadas MSW)
- Search timeout: handler retorna HTTP 502 quando mock do Azure Search não responde em 30s
- Mocks MSW interceptam `https://*.search.windows.net/*` e `https://*.openai.azure.com/*`
- Nenhum teste usa credenciais ou endpoints Azure reais
- `vitest run tests/integration` completa em < 15 segundos

**Dependências:** TASK-011

**Estimativa:** G
