# Revisão Crítica — Perspectiva

**Arquivo revisado:** `feedback-handler.ts` (gerado pelo Copilot)  
**Destino no projeto:** `src/functions/feedback/handler.ts`  
**Revisor:** Dev Sênior (perspectiva humana — antes de usar IA)  
**Data:** 2026-07-03

> Esta revisão simula o que um dev sênior identificaria numa leitura manual linha a linha, sem apoio de IA.
> Classificação: `[AGENTS]` violação do AGENTS.md · `[SEC]` segurança/privacidade · `[BUG]` bug ou má prática de engenharia.

---

## Código original

```typescript
// feedback-handler.ts — gerado pelo Copilot
import { app, HttpRequest, HttpResponseInit } from '@azure/functions';

export async function feedbackHandler(
  request: HttpRequest
): Promise<HttpResponseInit> {
  const body = await request.json() as any;       // linha 7

  const feedback = {
    queryId: body.queryId,
    rating: body.rating,
    comment: body.comment,
    attendantEmail: body.attendantEmail,
    timestamp: new Date().toISOString()
  };

  console.log('Feedback recebido:', JSON.stringify(feedback));   // linha 16

  const { CosmosClient } = require('@azure/cosmos');             // linha 18
  const client = new CosmosClient(process.env.COSMOS_CONNECTION_STRING);
  const database = client.database('novatech');
  const container = database.container('feedbacks');

  await container.items.create(feedback);

  return { status: 200, body: 'OK' };
}

app.http('feedback', {
  methods: ['POST'],
  handler: feedbackHandler
});
```

---

## Problemas identificados

### Problema 1 — `as any` sem validação Zod

**Linha:** 7  
**Classificação:** `[AGENTS]`  
**Código:** `const body = await request.json() as any;`

**Problema:** O AGENTS.md proíbe `any` explícito e exige validação de toda entrada externa com Zod. O cast `as any` desativa o TypeScript inteiro para a variável `body` — qualquer acesso a `body.qualquerCoisa` passa sem erro em compile time, mesmo que o campo não exista no payload real.

**Impacto:** Se o cliente enviar um body malformado (ex: `rating: "alto"`, `queryId` ausente), os dados chegam à lógica e ao banco sem nenhuma verificação. Falhas aparecem apenas em runtime, possivelmente como erros 500 silenciosos.

---

### Problema 2 — `console.log` em vez de pino

**Linha:** 16  
**Classificação:** `[AGENTS]`  
**Código:** `console.log('Feedback recebido:', JSON.stringify(feedback));`

**Problema:** O AGENTS.md proíbe `console.log` em código de produção. O projeto usa pino via `src/shared/logger.ts` para logging estruturado com campos de correlação (`session_id`, `queryId`).

**Impacto:** Logs sem structured fields não são correlacionáveis no Azure Monitor. Um atendente com problema de feedback não pode ser rastreado sem o `queryId` indexado. Além disso, `JSON.stringify(feedback)` serializa o objeto inteiro — veja Problema 3.

---

### Problema 3 — `attendantEmail` sendo logado (PII)

**Linha:** 16 (embutido no `JSON.stringify(feedback)`)  
**Classificação:** `[SEC]` + `[AGENTS]`  
**Código:** `console.log('Feedback recebido:', JSON.stringify(feedback));` — onde `feedback.attendantEmail` está presente.

**Problema:** O AGENTS.md proíbe explicitamente logar dados pessoais: *"Campos proibidos em logs: `attendantEmail`, `email`, `nome`, `name`"*. O `feedback` inclui `attendantEmail` e é serializado integralmente no log.

**Impacto:** Violação de LGPD. E-mails de atendentes em logs de sistema operacional são dados pessoais que não deveriam aparecer em texto livre em nenhum sistema de logging. Mesmo que o `console.log` seja substituído por pino, o problema persiste se o objeto for logado sem seleção de campos.

---

### Problema 4 — `require()` dinâmico dentro da função

**Linha:** 18  
**Classificação:** `[AGENTS]`  
**Código:** `const { CosmosClient } = require('@azure/cosmos');`

**Problema:** O AGENTS.md proíbe `require()` — o projeto usa ESM puro (`"type": "module"`). Um `require()` dentro de uma função Azure Functions causaria erro de runtime: *"require is not defined in ES module scope"*. Além disso, `require()` dentro da função é executado a cada invocação, sem cache de módulo efetivo.

**Impacto:** O módulo não compilaria/executaria corretamente no ambiente de produção. Este é o único problema que causaria falha total imediata no deploy.

---

### Problema 5 — `CosmosClient` instanciado a cada invocação

**Linhas:** 18–21  
**Classificação:** `[BUG]`  
**Código:**
```typescript
const { CosmosClient } = require('@azure/cosmos');
const client = new CosmosClient(process.env.COSMOS_CONNECTION_STRING);
const database = client.database('novatech');
const container = database.container('feedbacks');
```

**Problema:** O `CosmosClient` estabelece pool de conexões TCP. Instanciá-lo dentro da função handler recria o cliente a cada request, desperdiçando recursos e aumentando latência. O AGENTS.md define explicitamente que clientes externos devem ser singletons no escopo do módulo.

**Impacto:** Em carga alta (ex: 320 chamados/dia × múltiplos feedbacks), cada request abre e fecha novas conexões. Em Azure Functions com cold start, isso também aumenta o tempo de resposta.

---

### Problema 6 — `process.env.COSMOS_CONNECTION_STRING` sem validação

**Linha:** 19  
**Classificação:** `[BUG]`  
**Código:** `new CosmosClient(process.env.COSMOS_CONNECTION_STRING)`

**Problema:** `process.env.*` pode ser `undefined`. O construtor do `CosmosClient` recebe `string | undefined` — em TypeScript strict mode isso seria um erro de tipo. O AGENTS.md exige que variáveis de ambiente sejam lidas via `src/shared/config.ts`, que valida via Zod antes do uso.

**Impacto:** Se a variável não estiver configurada no ambiente (ex: deploy esqueceu de setar), o erro será `"Cannot read properties of undefined"` em runtime — mensagem que não deixa claro que a connection string está ausente.

---

### Problema 7 — Strings hardcoded para banco e container

**Linhas:** 20–21  
**Classificação:** `[AGENTS]`  
**Código:** `client.database('novatech')` e `database.container('feedbacks')`

**Problema:** O AGENTS.md proíbe strings hardcoded para nomes de banco/container/index fora de `config.ts`. Em ambiente de staging o banco pode ter nome diferente (`novatech-staging`); com valor hardcoded, o código quebra entre ambientes ou exige `find-and-replace` manual.

---

### Problema 8 — Nenhum tratamento de erro

**Linha:** 23  
**Classificação:** `[BUG]`  
**Código:** `await container.items.create(feedback);` (sem try/catch)

**Problema:** Qualquer falha no Cosmos DB (timeout, throttling, conflito de ID) propaga como exceção não tratada. O Azure Functions retornará HTTP 500 com stack trace exposto — violando o guardrail do AGENTS.md (*"nunca expor stack trace"*) e impedindo retornar uma resposta amigável.

---

### Problema 9 — `body: 'OK'` como string + status 200 para criação

**Linha:** 25  
**Classificação:** `[BUG]`  
**Código:** `return { status: 200, body: 'OK' };`

**Problema 9a:** O Azure Functions v4 com TypeScript espera `body` como objeto JSON ou `null` para respostas JSON. Retornar `'OK'` como string não segue o padrão de resposta do projeto e não define `Content-Type`.

**Problema 9b:** Operações de criação de recurso devem retornar HTTP 201 (Created), não 200 (OK). Este é um erro semântico REST.

---

### Problema 10 — Estrutura de arquivo viola o Anexo C

**Classificação:** `[AGENTS]`

**Problema:** O Anexo C define que `src/functions/feedback/` deve ter dois arquivos: `handler.ts` + `validator.ts`. O AGENTS.md estabelece que validação é responsabilidade do `validator.ts`, nunca inline no handler. O módulo gerado mistura responsabilidades num arquivo único e não segue a estrutura definida.

---

## Resumo

| # | Linha | Classificação | Severidade | Bloqueante para merge? |
|---|---|---|---|---|
| 1 | 7 | `[AGENTS]` | Alta | Sim |
| 2 | 16 | `[AGENTS]` | Média | Sim |
| 3 | 16 | `[SEC]` + `[AGENTS]` | Alta | Sim |
| 4 | 18 | `[AGENTS]` | Crítica | Sim (falha em runtime) |
| 5 | 18–21 | `[BUG]` | Média | Recomendado corrigir |
| 6 | 19 | `[BUG]` | Alta | Sim |
| 7 | 20–21 | `[AGENTS]` | Média | Sim |
| 8 | 23 | `[BUG]` | Alta | Sim |
| 9 | 25 | `[BUG]` | Baixa | Recomendado corrigir |
| 10 | — | `[AGENTS]` | Média | Sim |

**Conclusão:** O módulo tem **4 problemas bloqueantes de segurança/AGENTS** e **2 bugs que causam falha em runtime**. Não deve ser mergeado sem reescrita completa seguindo o AGENTS.md e a estrutura do Anexo C.
