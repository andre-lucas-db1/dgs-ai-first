# SKILL.md Foundation — TypeScript Conventions

> **Localização no repositório:** `skills/foundation/typescript-conventions.md`  
> Este arquivo é o entregável do exercício 2.3. O conteúdo abaixo é idêntico ao arquivo populado no starter repo.

---

```markdown
---
skill: typescript-conventions
layer: foundation
applies-to: all
version: 1.0
---

## Contexto

Projeto: **NovaTech Assistant** — assistente de IA para atendimento ao cliente em logística,
construído com Azure Functions (TypeScript), Azure AI Search e Azure OpenAI.

Stack: TypeScript 5.5, `strict: true`, ESM puro (`"type": "module"` no `package.json`),
Zod para validação de entrada, Vitest para testes, pino para logs.

Esta é a skill base de todo o projeto. Agentes (Copilot, Claude Code) devem ler este arquivo
antes de gerar qualquer arquivo `.ts`. As demais skills (domain, artifact) assumem que estas
convenções já foram assimiladas.

---

## Regras Prescritivas

1. **`strict: true` é inegociável.**  
   `tsconfig.json` ativa `noImplicitAny`, `strictNullChecks` e `strictFunctionTypes`.
   Nenhum `any` explícito é aceito. Use `unknown` quando o tipo for genuinamente desconhecido
   e faça narrowing com `typeof` ou `instanceof` antes de acessar propriedades.

2. **Use `type`, não `interface`.**  
   Tipos de domínio são declarados com `type`. `interface` é reservado para declaration merging
   (raro — justifique no PR se for usar).

3. **ESM puro — sem `require()` ou `module.exports`.**  
   O projeto usa `"type": "module"`. Use `import`/`export` ESM nativo em todos os arquivos.
   Imports internos incluem extensão `.js` (padrão ESM com TypeScript):
   `import { ValidationError } from "../../shared/errors.js"`.

4. **Exports nomeados — nunca `export default`.**  
   Use `export function`, `export type`, `export class`. Facilita refactoring automatizado
   e tree-shaking. `export default` está proibido.

5. **`readonly` em parâmetros de construtor que não devem mutar.**  
   Declare diretamente no construtor: `constructor(readonly statusCode: number)`.
   Evita a repetição de declarar a propriedade e depois atribuí-la no corpo.

6. **Custom errors exigem `Object.setPrototypeOf` e `this.name`.**  
   Sem `Object.setPrototypeOf(this, MinhaClasse.prototype)`, o `instanceof` falha silenciosamente
   em runtime após transpile para ES5/CommonJS. `this.name` é necessário para logs legíveis.

7. **Validação de entrada com Zod na borda do sistema.**  
   Toda entrada externa (HTTP body, variável de ambiente) passa por um schema Zod antes de
   entrar na lógica interna. Nunca use `as TipoQualquer` como substituto de validação.

8. **Sem `console.log` em código de produção.**  
   Use o logger estruturado em `src/shared/logger.ts` (pino). `console.log` não tem structured
   fields e polui os logs do Azure Functions sem correlação de `session_id` ou `attendant_id`.

9. **Tipagem explícita em assinaturas públicas.**  
   Funções exportadas devem ter tipos explícitos nos parâmetros e no retorno.
   Inferência é aceita apenas em escopo local (variáveis internas, callbacks).

10. **`unknown` em blocos `catch` — nunca `any`.**  
    Em TypeScript 5+, o tipo de `error` em `catch` é `unknown`. Faça narrowing com `instanceof`
    antes de acessar propriedades como `.message` ou `.statusCode`.

---

## Exemplos

### Tipos de domínio — DO / DON'T

```typescript
// ✅ DO — `type` para shapes de domínio
export type Chunk = {
  id: string;
  text: string;
  source_document: string;
  section: string;
  score: number;
};

export type QueryResponse = {
  answer: string;
  source_document: string;
  session_id?: string;
};

// ❌ DON'T — `interface` não é o padrão aqui
export interface Chunk {
  id: string;
  text: string;
  source_document: string;
  section: string;
  score: number;
}
```

---

### Custom Error classes — DO / DON'T

```typescript
// ✅ DO — prototype restaurado, name explícito, readonly params no construtor
export class AzureSearchError extends Error {
  constructor(
    message: string,
    readonly statusCode: number,
    readonly retryable: boolean,
  ) {
    super(message);
    this.name = "AzureSearchError";
    Object.setPrototypeOf(this, AzureSearchError.prototype);
  }
}

export class ValidationError extends Error {
  static readonly statusCode = 400;
  readonly issues: ZodIssue[];

  constructor(issues: ZodIssue[]) {
    super("Validation failed");
    this.name = "ValidationError";
    this.issues = issues;
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

// ❌ DON'T — sem Object.setPrototypeOf, instanceof falha em prod; sem this.name, log fica "Error"
export class AzureSearchError extends Error {
  statusCode: number;
  constructor(message: string, statusCode: number) {
    super(message);
    this.statusCode = statusCode;
    // ❌ faltou: Object.setPrototypeOf(this, AzureSearchError.prototype)
    // ❌ faltou: this.name = "AzureSearchError"
  }
}
```

---

### Validação na borda — DO / DON'T

```typescript
// ✅ DO — Zod valida antes de entrar na lógica; função exportada com tipos explícitos
export const queryRequestSchema = z.object({
  question: z
    .string({ required_error: "O campo 'question' é obrigatório" })
    .min(1, "A pergunta não pode ser vazia")
    .max(1000, "A pergunta deve ter no máximo 1000 caracteres"),
  session_id: z.string().uuid().optional(),
  attendant_id: z.string().max(50).optional(),
});

export function validateQueryRequest(body: unknown): QueryRequest {
  return queryRequestSchema.parse(body);
}

// ❌ DON'T — cast sem validação expõe a lógica a dados inválidos em runtime
export function validateQueryRequest(body: unknown): QueryRequest {
  return body as QueryRequest; // ❌ não valida nada — questão vazia, rating inválido, tudo passa
}
```

---

### Blocos `catch` — DO / DON'T

```typescript
// ✅ DO — narrowing com instanceof antes de acessar propriedades
try {
  const chunks = await searchService.query(question);
  return chunks;
} catch (error) {
  if (error instanceof AzureSearchError) {
    logger.error({ statusCode: error.statusCode, retryable: error.retryable }, "Search falhou");
    throw error;
  }
  throw new Error("Unexpected error in search", { cause: error });
}

// ❌ DON'T — `any` desativa strictNullChecks no bloco inteiro
try {
  const chunks = await searchService.query(question);
} catch (error: any) {          // ❌ `any` — qualquer propriedade parece válida
  console.error(error.message); // ❌ console.log proibido; e se error for string, .message é undefined
}
```

---

### Módulos e exports — DO / DON'T

```typescript
// ✅ DO — ESM nativo, export nomeado, import com extensão .js
import { Chunk } from "../../shared/types.js";
import { logger } from "../../shared/logger.js";

export async function buildPrompt(chunks: Chunk[], question: string): Promise<string> {
  logger.debug({ chunkCount: chunks.length }, "Montando prompt");
  return chunks.map(c => c.text).join("\n\n") + "\n\nPergunta: " + question;
}

// ❌ DON'T — CommonJS + default export + sem extensão no import
const { Chunk } = require("../../shared/types");  // ❌ require() em "type": "module" causa erro de runtime

export default async function buildPrompt(chunks, question) {  // ❌ default export; sem tipos
  console.log("chunks:", chunks.length);  // ❌ console.log
  return chunks.map(c => c.text).join("\n\n") + "\n\n" + question;
}
```

---

## Anti-Padrões

Os erros abaixo são os que Copilot e Claude Code geram por padrão sem esta skill.
Cada um tem uma causa raiz e um impacto concreto.

| Anti-padrão | Por que acontece | Impacto no projeto |
|---|---|---|
| `interface` em vez de `type` | Padrão histórico TypeScript pré-4.x; maioria dos exemplos públicos usa `interface` | Inconsistência com `types.ts`; diff ruído nas PRs |
| `any` em `catch (error: any)` | Copilot "resolve" o erro de tipo com cast | Desativa `strictNullChecks` no bloco — erros encobertos, crashes em prod |
| `export default function` | Padrão do React/Next.js que Copilot carrega para qualquer projeto | Quebra tree-shaking; renaming automático falha; conflita com imports do time |
| `require()` / `module.exports` | Copilot treinado em volumes maiores de código CommonJS | Erro de runtime: `require is not defined in ES module scope` |
| Error sem `Object.setPrototypeOf` | Omissão comum — o TypeScript compile não acusa | `instanceof AzureSearchError` retorna `false` em produção; error handler não reconhece o tipo |
| `console.log` nos handlers | Hábito de debug | Polui logs do Azure Functions; sem `session_id` ou `attendant_id` para correlação |
| Parâmetros sem tipo em funções exportadas | Inferência "funciona" localmente | Quebra contrato público; mocks em teste precisam de cast; regressões invisíveis |
| `as TipoQualquer` sem schema | Copilot preenche o `unknown` do request.json() com cast | Dados inválidos chegam à lógica — rating 999, question vazia, session_id malformado |
```
