# Exemplo de Consumo de Skills — Geração do Endpoint de Feedback

> Este documento evidencia como as skills são consumidas por um agente (Copilot Chat) na prática.  
> Cenário: Dev Pleno recebe a task "implementar o endpoint de feedback" e usa Copilot Chat.

---

## Contexto da task

O Dev Pleno abre o arquivo `src/functions/feedback/handler.ts` (stub vazio) e aciona o Copilot Chat:

```
@workspace Implemente o handler do endpoint de feedback seguindo os padrões do projeto.
O endpoint recebe: session_id, question, answer, rating (1-5) e attendant_id.
Deve validar o input, logar a operação e retornar 201 em caso de sucesso.
```

---

## Skills carregadas pelo agente (ordem de precedência)

```
1. foundation/typescript-conventions.md   ← carregada primeiro, sempre
2. foundation/error-handling.md           ← carregada porque o handler chama serviços externos
3. domain/azure-functions-endpoint.md     ← carregada porque é um HTTP trigger
4. artifact/create-rag-endpoint.md        ← carregada como checklist de geração
```

---

## Código gerado COM as skills

O agente lê as skills e gera:

```typescript
// src/functions/feedback/handler.ts

import { z } from "zod";
import { ValidationError } from "../../shared/errors.js";
import { logger } from "../../shared/logger.js";

// ✅ type, não interface (typescript-conventions: regra 2)
type FeedbackRequest = {
  session_id: string;
  question: string;
  answer: string;
  rating: number;
  attendant_id: string;
};

// ✅ Zod valida na borda (typescript-conventions: regra 7)
const feedbackSchema = z.object({
  session_id: z.string().uuid(),
  question: z.string().min(1).max(1000),
  answer: z.string().min(1),
  rating: z.number().int().min(1).max(5),
  attendant_id: z.string().max(50),
});

// ✅ export nomeado, sem default (typescript-conventions: regra 4)
// ✅ parâmetros tipados explicitamente (typescript-conventions: regra 9)
export async function feedbackHandler(request: Request): Promise<Response> {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    // ✅ catch sem parâmetro — não precisamos do erro aqui
    return new Response(JSON.stringify({ error: "Invalid JSON" }), {
      status: 400,
      headers: { "Content-Type": "application/json" },
    });
  }

  // ✅ ValidationError lançado com Zod issues (error-handling: padrão de validação)
  const result = feedbackSchema.safeParse(body);
  if (!result.success) {
    throw new ValidationError(result.error.issues);
  }

  const feedback: FeedbackRequest = result.data;

  // ✅ logger estruturado, sem console.log (typescript-conventions: regra 8)
  logger.info({ session_id: feedback.session_id, rating: feedback.rating }, "Feedback recebido");

  // TODO: persistir feedback (Cosmos DB — task futura)

  return new Response(null, { status: 201 });
}
```

**Convenções aplicadas automaticamente pelo agente a partir das skills:**
- `type` em vez de `interface` para `FeedbackRequest`
- Zod + `ValidationError` na borda, não cast com `as`
- Export nomeado
- `logger.info` com structured fields, sem `console.log`
- Tipagem explícita em `feedbackHandler(request: Request): Promise<Response>`
- Catch de JSON sem `error: any`

---

## Código gerado SEM as skills (anti-padrão)

Sem as skills, o Copilot geraria algo assim:

```typescript
// ❌ default export
export default async function handler(req: any, res: any) {
  // ❌ sem validação — cast direto
  const body = req.body as {
    session_id: string;
    rating: number;
    // campos faltando...
  };

  // ❌ console.log em produção
  console.log("Feedback recebido:", body);

  // ❌ interface em vez de type
  interface FeedbackData {
    session_id: string;
    rating: number;
  }

  // ❌ catch com any — desativa strict
  try {
    await saveFeedback(body);
  } catch (e: any) {
    console.error(e.message);
    res.status(500).json({ error: e.message });
  }

  res.status(201).json({ ok: true });
}
```

**Problemas gerados sem guidance:**
| Problema | Consequência |
|---|---|
| `req: any, res: any` | Perde tipagem do Azure Functions v4, bugs silenciosos |
| `as FeedbackData` sem validação | Campos inválidos passam para a lógica — runtime error |
| `console.log` | Polui logs do Azure Functions, sem structured fields para correlação |
| `export default` | Quebra o padrão de import do projeto, dificulta tree-shaking |
| `catch (e: any)` | Desativa `strictNullChecks` no bloco — erros encobertos |
| `interface` | Inconsistência com o padrão de `type` do projeto (`types.ts`) |

---

## Cadeia de skills usada neste exemplo

```
typescript-conventions  →  error-handling  →  azure-functions-endpoint  →  create-rag-endpoint
        ↑                        ↑                       ↑                          ↑
  regras de tipo          ValidationError          estrutura do handler       checklist completo
  exports, catch          + propagação             + imports esperados        + itens a validar
```

A skill `typescript-conventions` foi a mais impactante: sozinha ela eliminou 4 dos 6 anti-padrões listados acima. É por isso que ela é a Foundation skill mais importante — os erros que ela previne são os que o Copilot gera por padrão, sem nenhuma instrução adicional.
