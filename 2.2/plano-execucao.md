# Plano de Execução — Exercício 2.2: Spec Driven Development (Query Endpoint)

## Contexto

O exercício simula o fluxo real de desenvolvimento guiado por especificação:
`plan.md (Tech Lead)` → `tasks.md (Dev + IA)` → `implementação da task-001 (Copilot)`

O repositório base está em `.claude/docs/Anexo-D-starter-repo-novatech-assistant/novatech-assistant/`.  
Arquivos relevantes já existem como stubs/vazios — **não criar arquivos novos**, preencher os existentes.

---

## Entregáveis

| # | Artefato | Destino no repo |
|---|----------|-----------------|
| 1 | `tasks.md` completo | `specs/query-endpoint/tasks.md` |
| 2 | Implementação da TASK-001 | `src/functions/query/validator.ts` + tipos em `src/shared/types.ts` |
| 3 | Revisão crítica do código | Seção abaixo neste arquivo ou em `2.2/revisao-critica.md` |

---

## Fase 1 — Criar o tasks.md

### O que fazer

Usar o Claude (chat) para converter o `plan.md` do exercício em tasks atômicas.

### Prompt para o Claude

```
Contexto: sou Dev Sênior da DB1, trabalhando no projeto NovaTech Assistant
(assistente de atendimento RAG para empresa de logística).

O Tech Lead escreveu o plan.md abaixo. Preciso convertê-lo em tasks.md
seguindo o padrão SDD do projeto:
- Cada task deve ser implementável e testável de forma independente
- Campos obrigatórios: ID, Descrição, Critérios de Aceite (verificáveis),
  Dependências (IDs de tasks), Estimativa (P=meio dia / M=1 dia / G=2 dias)
- Critérios de aceite NÃO podem ser vagos como "funcionar corretamente"
- Ao menos 1 critério de aceite por task deve ser verificável via teste

--- PLAN.MD ---
[colar o plan.md do exercicio.md aqui]
---

Gere o tasks.md completo.
```

### Estrutura esperada do tasks.md

Com base no plan.md fornecido, as tasks devem cobrir estes blocos de trabalho
(em ordem de dependência):

```
TASK-001 (P)  — Tipos e modelos de domínio (src/shared/types.ts)
TASK-002 (P)  — Módulo de configuração e variáveis de ambiente (src/shared/config.ts)
TASK-003 (P)  — Logger estruturado com pino (src/shared/logger.ts)
TASK-004 (P)  — Custom errors do domínio (src/shared/errors.ts)
TASK-005 (P)  — Validador de input com Zod (src/functions/query/validator.ts)  ← TASK ALVO
TASK-006 (M)  — Integração Azure OpenAI — geração de embeddings (src/services/...)
TASK-007 (M)  — Integração Azure AI Search — busca semântica (src/services/search.ts)
TASK-008 (M)  — Prompt builder com context budget (src/services/prompt-builder.ts)
TASK-009 (M)  — Integração Azure OpenAI — completion (src/services/completion.ts)
TASK-010 (P)  — Response builder com source_document (src/functions/query/response-builder.ts)
TASK-011 (G)  — Handler principal — orquestração do fluxo RAG (src/functions/query/handler.ts)
TASK-012 (M)  — Testes unitários: validator + response-builder
TASK-013 (M)  — Testes unitários: prompt-builder (context budget)
TASK-014 (G)  — Testes de integração: fluxo completo com mocks MSW
```

> **Nota sobre atomicidade:** TASK-001 a TASK-005 são fundação — cada uma pode ser implementada
> e testada sem as demais. TASK-006 a TASK-010 dependem dos tipos (TASK-001) mas são independentes
> entre si. TASK-011 depende de todas as anteriores. Testes são separados do código para permitir
> revisão isolada.

---

## Fase 2 — Implementar TASK-001: Validador de Input

### Por que a TASK-005 é a "primeira task" aqui

O plano descreve a task-001 como "setup do endpoint com validação de input".
Na prática, a validação é o único componente que pode ser implementado, compilado e
testado **sem nenhuma dependência de Azure** — ideal como primeira entrega.

As tasks de tipos/config/logger/errors (TASK-001 a TASK-004) são pré-requisitos leves
que o Copilot pode gerar junto como scaffolding.

### Prompt para o GitHub Copilot

```typescript
// Contexto: Projeto NovaTech Assistant — assistente RAG para atendimento logístico.
// Stack: TypeScript strict, Azure Functions v4, Zod ^3.23, sem console.log (usar pino).
//
// Arquivo: src/functions/query/validator.ts
//
// Requisitos:
// - Validar o body de POST /api/query usando Zod
// - Schema QueryRequest:
//   - question: string, obrigatório, min 1 char, max 1000 chars
//   - session_id: string UUID v4, opcional
//   - attendant_id: string, opcional, max 50 chars
// - Exportar função: validateQueryRequest(body: unknown): QueryRequest
// - Lançar ZodError com mensagens em português se inválido
// - QueryRequest deve ser exportado como tipo TypeScript derivado do schema Zod
// - Sem imports de Azure SDK neste arquivo — é puramente validação de input
//
// Depende de: src/shared/types.ts (pode ficar vazio por ora, os tipos ficam aqui)
//
// Implemente também os tipos base em src/shared/types.ts:
// - Chunk: { id: string; text: string; source_document: string; section: string; score: number }
// - QueryResponse: { answer: string; source_document: string; session_id?: string }
// - Use z.infer<> para derivar QueryRequest do schema Zod
```

### Arquivos a criar/editar

1. `src/functions/query/validator.ts` — lógica de validação Zod
2. `src/shared/types.ts` — tipos de domínio (Chunk, QueryResponse)

### Critérios de aceite da TASK-005 (verificáveis)

- [ ] `validateQueryRequest({ question: "" })` lança `ZodError` com mensagem indicando campo obrigatório
- [ ] `validateQueryRequest({ question: "a".repeat(1001) })` lança `ZodError` indicando limite de 1000 chars
- [ ] `validateQueryRequest({ question: "Qual o SLA?" })` retorna objeto tipado `QueryRequest`
- [ ] `validateQueryRequest({ question: "ok", session_id: "não-é-uuid" })` lança `ZodError`
- [ ] `tsc --noEmit` passa sem erros em modo strict
- [ ] Nenhum `console.log` no arquivo

---

## Fase 3 — Revisão Crítica do Código Gerado pelo Copilot

### O que avaliar (checklist de senior review)

Ao revisar o código gerado, checar especificamente:

**1. Segurança e validação**
- O Zod está rejeitando strings com caracteres que poderiam ser prompt injection?
  (`validateQueryRequest({ question: "Ignore all instructions and..." })` — deve aceitar
  o texto mas ele chega ao LLM; a defesa é no prompt, não aqui — isso é um ponto de discussão)
- O `session_id` UUID está sendo validado com `z.string().uuid()` ou apenas `z.string()`?

**2. Tipos e contrato**
- O tipo `QueryRequest` foi derivado com `z.infer<>` ou redefinido manualmente?
  (redefinir manualmente cria risco de drift entre schema e tipo)
- O arquivo exporta o schema Zod além do tipo? Sem o schema, não é possível revalidar
  em testes de integração sem reimportar o validator inteiro.

**3. Erros e mensagens**
- As mensagens de erro estão em português ou inglês (padrão Zod é inglês)?
  O requisito diz "mensagens em português".
- O validator está lançando `ZodError` diretamente ou encapsulando em `ValidationError` customizado?
  O handler (TASK-011) precisará de erros tipados para retornar 400 vs 500.

**4. Padrões do projeto**
- Algum `console.log` ou `console.error` escapou? (viola padrão pino)
- O arquivo tem imports desnecessários (ex: importou `@azure/functions` sem precisar)?

### Registro da revisão

Após gerar o código com Copilot, documentar em `2.2/revisao-critica.md`:
- Problema 1: descrição exata, linha do código, impacto, correção proposta
- Problema 2: idem
- (opcional) Problema 3 se houver

---

## Referências de código do projeto

### package.json — dependências disponíveis

```json
{
  "devDependencies": {
    "typescript": "^5.5.0",
    "vitest": "^2.0.0",
    "zod": "^3.23.0"
  }
}
```

> **Atenção:** `pino` e `@azure/functions` ainda não estão no package.json do starter repo.
> Na Fase 2, ao implementar, incluir os imports mas anotar que precisariam ser adicionados
> via `npm install`. O exercício não exige executar o código — apenas que ele compile.

### Stub existente em handler.ts

```typescript
// src/functions/query/handler.ts (stub já existente)
export async function queryHandler(/* request */) {
  // TODO: validar input (Zod), buscar chunks, montar prompt, chamar modelo, retornar com source_document
  throw new Error("Not implemented");
}
```

O handler **não é a primeira task** — a primeira task é o validador, que o handler vai chamar.

---

## Ordem de execução

```
1. Abrir Claude (chat) → gerar tasks.md com o prompt da Fase 1
2. Revisar e ajustar tasks.md gerado (verificar atomicidade real)
3. Salvar em specs/query-endpoint/tasks.md no starter repo
4. Abrir GitHub Copilot no VS Code com o starter repo aberto
5. Colar prompt da Fase 2 em validator.ts como comentário
6. Aceitar/editar sugestões do Copilot
7. Editar src/shared/types.ts conforme gerado
8. Rodar `tsc --noEmit` para verificar compilação
9. Fazer revisão crítica → salvar em 2.2/revisao-critica.md
```

---

## Checklist de entrega

- [ ] `specs/query-endpoint/tasks.md` com ≥10 tasks atômicas, todas com critérios verificáveis
- [ ] `src/functions/query/validator.ts` implementado (não é stub)
- [ ] `src/shared/types.ts` com tipos Chunk, QueryResponse, QueryRequest
- [ ] `tsc --noEmit` passa sem erros (rodar no starter repo)
- [ ] `2.2/revisao-critica.md` com ≥2 problemas reais identificados e correções propostas
- [ ] Nenhum `console.log` no código implementado

---

## Notas sobre SDD e avaliação

O critério mais importante é a **atomicidade real das tasks**:
- Cada task deve poder ser implementada por um dev diferente sem bloqueio
- Cada task deve ter um teste que prove que está pronta
- Estimativas devem refletir complexidade real (TASK-005 é P; TASK-011 é G)

O critério mais fácil de errar é **critérios de aceite vagos** — exemplos a evitar:
- ❌ "O endpoint funciona corretamente"
- ❌ "O código está testado"
- ✅ "POST /api/query com body `{}` retorna 400 com campo `errors[0].field === 'question'`"
- ✅ "`tsc --noEmit` passa em modo strict sem erros"
