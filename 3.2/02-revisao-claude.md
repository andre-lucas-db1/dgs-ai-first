# Revisão Crítica — Perspectiva Claude (IA)

**Arquivo revisado:** `feedback-handler.ts` (gerado pelo Copilot)  
**Destino no projeto:** `src/functions/feedback/handler.ts`  
**Revisor:** Claude (segunda opinião — após revisão humana)  
**Data:** 2026-07-03

> Esta revisão é feita com acesso ao AGENTS.md completo, ao Anexo C e ao contexto do projeto NovaTech.
> A IA analisa por categorias, não por linha, e pode cruzar informações de múltiplos artefatos simultaneamente.

---

## Análise por categoria

### Categoria 1 — Violações do AGENTS.md (conformidade de padrões)

#### A. Proibição de `any` e ausência de Zod

O campo `const body = await request.json() as any` viola duas regras simultaneamente:
- Regra 1 do AGENTS.md: `strict: true` proíbe `any` explícito
- Regra 4: toda entrada HTTP deve passar por schema Zod antes da lógica interna

O handler deveria chamar `validateFeedbackRequest(body)` importado de `validator.ts`, que encapsularia a validação e lançaria `ValidationError` (não `ZodError` diretamente — seguindo o padrão do exercício 2.2 de `revisao-critica.md`).

Impacto adicional: sem Zod, o campo `rating` pode ser qualquer valor. O AGENTS.md Product Rules define `rating` como obrigatório entre 1 e 5. Com o código atual, `rating: null`, `rating: "excelente"` e `rating: 999` passam silenciosamente para o Cosmos DB.

#### B. `require()` dinâmico e violação ESM

O `require('@azure/cosmos')` na linha 18 viola a Regra 2 (ESM puro) e a Regra 3 (imports estáticos no topo). Em ambiente ESM, `require is not defined` é um erro de **runtime** — não de compilação. Isso significa que o código passa no `tsc --noEmit` mas quebra na primeira invocação real.

Diferente de outros problemas de estilo, este é um **bug de deploy**: o módulo não inicializa.

#### C. `console.log` e PII nos logs

`console.log('Feedback recebido:', JSON.stringify(feedback))` viola:
- Regra 5 (proibição de `console.log`)
- Regra 6 (proibição de logar PII)

O `feedback` inclui `attendantEmail`. A serialização `JSON.stringify(feedback)` expõe o e-mail completo no output do console. Este problema persiste mesmo se o `console.log` for substituído por `logger.info({ ...feedback })` — o objeto inteiro não pode ser espalhado em logs.

O logger correto seria:
```typescript
logger.info({ queryId: feedback.queryId, rating: feedback.rating }, 'Feedback registrado');
```

#### D. Strings hardcoded e `process.env` direto

`client.database('novatech')` e `database.container('feedbacks')` são strings hardcoded que violam a regra de configuração do AGENTS.md. `process.env.COSMOS_CONNECTION_STRING` acessa o ambiente diretamente — o padrão do projeto é `config.cosmosConnectionString` (validado via Zod no startup).

---

### Categoria 2 — Problemas de segurança e privacidade (LGPD)

#### A. Persistência de e-mail no banco de dados

O `feedback` persistido no Cosmos DB inclui `attendantEmail`. O AGENTS.md Product Rules especifica: *"NÃO DEVE logar ou persistir dados pessoais de atendentes além do `attendant_id`"*.

Persiste no banco um dado pessoal (e-mail) que não é necessário para a funcionalidade de feedback. Para rastrear o atendente, `attendant_id` (identificador opaco) é suficiente. Armazenar e-mail sem necessidade é violação do princípio de minimização de dados da LGPD.

**Este problema não foi identificado na revisão manual** como um item separado — o foco foi no log. A persistência no banco é um vetor diferente e mais permanente de exposição.

#### B. Ausência de sanitização de `comment`

O campo `comment` aceita string livre sem limite de tamanho. Sem validação Zod:
- Pode receber strings de tamanho arbitrário (risco de DoS via payload)
- Pode receber caracteres especiais que, dependendo de como o campo é exibido no painel web, geram XSS

Não é necessário sanitizar HTML no backend de uma API REST, mas o Zod schema deve impor `z.string().max(2000)` para limitar o tamanho.

#### C. Connection string potencialmente undefined passada ao construtor

`new CosmosClient(process.env.COSMOS_CONNECTION_STRING)` — em TypeScript strict, `process.env.*` é `string | undefined`. O `CosmosClient` não espera `undefined`. Se a variável não existir no ambiente, o comportamento é indefinido — pode inicializar com `undefined` convertida para a string `"undefined"` e falhar apenas na primeira operação de escrita, sem mensagem clara.

---

### Categoria 3 — Bugs de engenharia

#### A. `CosmosClient` instanciado por invocação (performance + resource leak)

O Azure Functions SDK v4 reutiliza o mesmo processo Node.js entre invocações aquecidas. Instanciar `CosmosClient` dentro do handler cria um novo pool de conexões TCP a cada request. Em carga normal (320 chamados/dia), cada feedback abre e abandona conexões, sem que o garbage collector as colete a tempo.

O padrão correto (documentado no AGENTS.md) é singleton no escopo do módulo, inicializado uma vez no cold start.

#### B. `await container.items.create(feedback)` sem tratamento de erro

O SDK do Cosmos DB lança exceções para:
- HTTP 429 (throttling — excedeu RU/s)
- HTTP 409 (conflito de ID se `queryId` não for único)
- HTTP 503 (serviço indisponível)

Sem `try/catch`, qualquer uma dessas situações propaga como exceção não tratada e gera HTTP 500 com stack trace exposto ao cliente — violando o guardrail *"nunca expor stack trace"*.

#### C. Resposta HTTP semanticamente incorreta

`return { status: 200, body: 'OK' }` tem dois problemas:

1. **Semântica REST:** POST que cria recurso deve retornar 201 (Created), opcionalmente com o recurso criado ou seu ID. Retornar 200 (OK) não é incorreto tecnicamente, mas vai contra as convenções REST e pode confundir consumidores da API.

2. **Formato do body:** O `body: 'OK'` é uma string. O padrão do projeto retorna JSON. A resposta deveria ser `{ body: JSON.stringify({ id: feedback.queryId }), status: 201, headers: { 'Content-Type': 'application/json' } }` ou equivalente usando o utilitário de resposta do projeto.

#### D. `timestamp` gerado no handler, não no banco

`timestamp: new Date().toISOString()` é gerado no servidor de aplicação antes de persistir. Se o Cosmos DB tiver latência alta, o `timestamp` do objeto persistido refletirá o horário de início do request, não de conclusão da escrita. Para rastreabilidade de auditoria, o ideal é usar o campo `_ts` do Cosmos DB (gerado pelo servidor de banco) ou deixar a geração do timestamp para o momento exato do `create`.

Esse é um problema de baixa severidade mas representa uma imprecisão de design.

---

### Categoria 4 — Conformidade estrutural (Anexo C)

O módulo existe como arquivo único `feedback-handler.ts` em vez de dois arquivos na pasta `src/functions/feedback/`:
- `handler.ts` — orquestração
- `validator.ts` — schema Zod + `validateFeedbackRequest`

Além disso, o arquivo é nomeado `feedback-handler.ts` em vez de `handler.ts` — o padrão definido no Anexo C e no AGENTS.md é `handler.ts` dentro de uma pasta com o nome do módulo.

---

## Resumo de problemas identificados pela IA

| ID | Categoria | Problema | Severidade | Bloqueante? |
|---|---|---|---|---|
| C-01 | AGENTS | `as any` sem Zod | Alta | Sim |
| C-02 | AGENTS | `require()` dinâmico / violação ESM | Crítica | Sim (runtime) |
| C-03 | AGENTS + SEC | `console.log` com PII | Alta | Sim |
| C-04 | AGENTS | Strings hardcoded + `process.env` direto | Média | Sim |
| C-05 | SEC + LGPD | E-mail persistido no banco | Alta | Sim |
| C-06 | SEC | `comment` sem limite de tamanho | Baixa | Recomendado |
| C-07 | SEC | Connection string `undefined` | Alta | Sim |
| C-08 | BUG | `CosmosClient` instanciado por request | Média | Recomendado |
| C-09 | BUG | Sem tratamento de erro no Cosmos DB | Alta | Sim |
| C-10 | BUG | Status 200 + body string | Baixa | Recomendado |
| C-11 | BUG | `timestamp` no handler (imprecisão) | Baixa | Não |
| C-12 | AGENTS | Estrutura de arquivo viola Anexo C | Média | Sim |

**Total:** 12 problemas. 8 bloqueantes para merge.

**Problema exclusivo da IA (não identificado na revisão manual):**
- C-05: persistência de `attendantEmail` no banco de dados (além do log)
- C-06: ausência de limite de tamanho no campo `comment`
- C-11: timestamp gerado antes da escrita (imprecisão de auditoria)
