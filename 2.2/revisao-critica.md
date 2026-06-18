# Revisão Crítica — Código Gerado pelo Copilot (TASK-005)

**Arquivo revisado:** `src/functions/query/validator.ts`  
**Data:** 2026-06-17  
**Revisor:** Dev Sênior (exercício 2.2)

---

## Problema 1 — `validateQueryRequest` lança `ZodError` em vez de `ValidationError`

**Linha afetada:** linha 23

```typescript
// Como está (Copilot gerou)
export function validateQueryRequest(body: unknown): QueryRequest {
  return queryRequestSchema.parse(body);  // lança ZodError diretamente
}
```

**Impacto:** O handler (TASK-011) precisa distinguir erros de validação (→ HTTP 400) de erros de serviço Azure (→ HTTP 502). A forma correta de fazer isso é via `instanceof`:

```typescript
// No handler — como o Dev da TASK-011 vai escrever
try {
  const request = validateQueryRequest(body);
} catch (err) {
  if (err instanceof ValidationError) return response400(err.issues);
  if (err instanceof AzureSearchError) return response502(err);
  throw err;
}
```

Com `ZodError` vazando, esse `instanceof ValidationError` sempre retorna `false`. O handler ou tratará o erro de validação como erro 500 (regressão silenciosa) ou o dev da TASK-011 precisará importar `ZodError` do pacote `zod` para tratar — acoplando o handler com o detalhe de implementação do validator.

**Correção proposta:**

```typescript
import { z } from "zod";
import { ValidationError } from "../../../shared/errors";

export function validateQueryRequest(body: unknown): QueryRequest {
  const result = queryRequestSchema.safeParse(body);
  if (!result.success) {
    throw new ValidationError(result.error.issues);
  }
  return result.data;
}
```

Usar `safeParse` em vez de `parse` permite encapsular o `ZodError` no `ValidationError` sem precisar de `try/catch`.

---

## Problema 2 — `QueryRequest` é um tipo manual em vez de derivado com `z.infer<>`

**Linhas afetadas:** linhas 4–8

```typescript
// Como está (Copilot gerou)
export type QueryRequest = {
  question: string;
  session_id?: string;
  attendant_id?: string;
};
```

**Impacto:** O tipo e o schema Zod são duas fontes de verdade independentes. Se alguém adicionar um campo novo ao `queryRequestSchema` (ex: `language: z.enum(["pt", "en"]).optional()`), o tipo `QueryRequest` não reflete a mudança automaticamente. O TypeScript não alerta sobre isso — o drift é silencioso.

**Verificação do problema:** basta adicionar um campo ao schema e chamar o validador: `result.data` vai ter o novo campo, mas `QueryRequest` não vai. Downstream, qualquer código que tipa a variável como `QueryRequest` vai perder o campo novo.

**Correção proposta:**

```typescript
export const queryRequestSchema = z.object({ /* ... */ });

// Derivar o tipo do schema — garantia de que os dois ficam sincronizados
export type QueryRequest = z.infer<typeof queryRequestSchema>;
```

Essa é a forma idiomática do Zod e elimina a segunda fonte de verdade completamente.

---

## Problema 3 (bônus) — Mensagens de erro incompletas em português

**Linhas afetadas:** linhas 17–22

```typescript
session_id: z
  .string()
  .uuid()          // ← mensagem padrão Zod: "Invalid uuid" (inglês)
  .optional(),
attendant_id: z
  .string()
  .max(50)         // ← mensagem padrão Zod: "String must contain at most 50 character(s)" (inglês)
  .optional(),
```

**Impacto:** O requisito explícito da TASK-005 é "mensagens de erro em português". As mensagens para `question` foram localizadas, mas os campos opcionais ficaram com os padrões em inglês. Se as issues do `ZodError` forem expostas para o frontend ou logadas para o atendente, ele verá mensagens em inglês — inconsistência que seria reprovada em code review.

**Correção proposta:**

```typescript
session_id: z
  .string({ invalid_type_error: "O campo 'session_id' deve ser uma string" })
  .uuid("O campo 'session_id' deve ser um UUID v4 válido")
  .optional(),
attendant_id: z
  .string({ invalid_type_error: "O campo 'attendant_id' deve ser uma string" })
  .max(50, "O campo 'attendant_id' deve ter no máximo 50 caracteres")
  .optional(),
```

---

## Resumo

| # | Severidade | Categoria | Impacto se não corrigido |
|---|-----------|-----------|--------------------------|
| 1 | Alta | Contrato de erro | Handler não consegue retornar 400 vs 502 corretamente |
| 2 | Média | Manutenibilidade | Drift silencioso entre schema e tipo em futuras mudanças |
| 3 | Baixa | Requisito funcional | Mensagens de erro em inglês para campos opcionais |

Os problemas 1 e 2 seriam bloqueantes em um code review real. O problema 3 seria solicitado como ajuste antes do merge.
