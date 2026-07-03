# Exercício 3.1 — Structured Output e Guardrails: Entregável

## 1. Schema Zod

Definido inline em `3.1/response-validator.ts` (ver seção 4).

```ts
export const AssistantResponseSchema = z.object({
  answer: z.string().min(1),
  source_document: z.string().min(1),
  confidence_score: z.number().min(0).max(1),
}).strict();
```

Campos obrigatórios: `answer` (string não-vazia), `source_document` (string não-vazia),
`confidence_score` (número entre 0 e 1 inclusive).

---

## 2. Versão inicial gerada pelo Copilot (com bugs)

```ts
import { z } from 'zod';

// sem .strict() — aceita campos extras silenciosamente
const AssistantResponseSchema = z.object({
  answer: z.string().min(1),
  source_document: z.string().min(1),
  confidence_score: z.number().min(0).max(1),
});

type AssistantResponse = z.infer<typeof AssistantResponseSchema>;

const SAFE_RESPONSE: AssistantResponse = {
  answer: 'Não foi possível processar sua solicitação. Por favor, contate o suporte.',
  source_document: 'N/A',
  confidence_score: 0,
};

// regex case-sensitive, order-dependent, sem variações de acento
const DANGEROUS_RETURN_REGEX = /carga perigosa.*devolução/s;

export function validateResponse(raw: unknown): AssistantResponse {
  const result = AssistantResponseSchema.safeParse(raw);

  if (!result.success) {
    console.error('[validator] Schema inválido:', result.error.message);
    return SAFE_RESPONSE;
  }

  const response = result.data;

  // Guardrail 1: source_document
  if (!response.source_document) {
    console.error('[guardrail-1] source_document ausente');
    return SAFE_RESPONSE;
  }

  // Guardrail 2: bloqueia qualquer menção a ambas as palavras (sem checar negação)
  if (DANGEROUS_RETURN_REGEX.test(response.answer)) {
    console.error('[guardrail-2] Resposta bloqueada: menção a carga perigosa + devolução');
    return SAFE_RESPONSE;
  }

  return response;
}
```

---

## 3. Code Review — Problemas identificados

### Problema 1 — Schema aceita campos extras (bug de segurança)

**Arquivo:** `response-validator.ts` — definição do `AssistantResponseSchema`

**Diagnóstico:**  
O comportamento padrão de `z.object()` no Zod é **strip**: campos extras enviados pelo
modelo são silenciosamente descartados, sem erro. Isso significa que se o modelo enviar
`{ answer, source_document, confidence_score, raw_completion: "..." }`, o campo extra passa
pelo parse sem rejeição. Em um harness de validação, qualquer estrutura fora do contrato
deve ser recusada — o objetivo do structured output é exatamente isso.

**Antes:**
```ts
const AssistantResponseSchema = z.object({
  answer: z.string().min(1),
  source_document: z.string().min(1),
  confidence_score: z.number().min(0).max(1),
});
```

**Depois:**
```ts
export const AssistantResponseSchema = z.object({
  answer: z.string().min(1),
  source_document: z.string().min(1),
  confidence_score: z.number().min(0).max(1),
}).strict(); // rejeita com ZodError se qualquer campo extra aparecer
```

**Por que isso importa:** Um modelo que começa a enviar campos extras sinaliza drift de
comportamento. O harness precisa detectar isso, não ignorar.

---

### Problema 2 — Regex do guardrail 2 não cobre variações do idioma

**Arquivo:** `response-validator.ts` — constante `DANGEROUS_RETURN_REGEX`

**Diagnóstico:**  
O padrão `/carga perigosa.*devolução/s` falha em três situações reais:

| Caso | Texto de exemplo | Resultado esperado | Resultado real |
|------|-----------------|-------------------|----------------|
| Case insensitive | "Carga Perigosa pode ser devolvida" | BLOQUEADO | passa (não detecta) |
| Sem acento | "devolucao de carga perigosa" | BLOQUEADO | passa (não detecta) |
| Ordem inversa | "devolução de carga perigosa é proibida" | passa (correto) | BLOQUEADO (falso positivo) |

O terceiro caso é o mais crítico: a resposta correta ("devolução de carga perigosa é
**proibida**") seria bloqueada porque o regex detecta ambas as palavras independente de
haver negação. O guardrail puniria respostas corretas.

**Antes:**
```ts
const DANGEROUS_RETURN_REGEX = /carga perigosa.*devolução/s;

if (DANGEROUS_RETURN_REGEX.test(response.answer)) {
  return SAFE_RESPONSE; // bloqueia qualquer coexistência, mesmo com negação
}
```

**Depois:**
```ts
function normalize(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function mentionsDangerousCargoReturn(answer: string): boolean {
  const t = normalize(answer);
  const hasDangerousCargo =
    t.includes('carga perigosa') || t.includes('cargas perigosas');
  const hasDevolucao =
    t.includes('devolucao') || t.includes('devolv') || t.includes('retorno');
  return hasDangerousCargo && hasDevolucao;
}

function containsNegation(answer: string): boolean {
  const t = normalize(answer);
  return [
    'nao e possivel', 'nao pode', 'nao sao elegiveis',
    'nao e elegivel', 'nao e permitida', 'vedada',
    'vedado', 'impossivel', 'inelegivel', 'proibida',
  ].some((term) => t.includes(term));
}

// Guardrail 2 — só bloqueia quando NÃO há negação presente
if (mentionsDangerousCargoReturn(response.answer) && !containsNegation(response.answer)) {
  console.error('[guardrail-2] Bloqueado: resposta afirma devolução de carga perigosa');
  return SAFE_RESPONSE;
}
```

---

### Problema 3 (bônus) — Check de Guardrail 1 é código morto

**Arquivo:** `response-validator.ts` — bloco `if (!response.source_document)`

**Diagnóstico:**  
O schema já declara `source_document: z.string().min(1)`, então qualquer valor ausente ou
vazio já rejeita no `safeParse`. O if seguinte nunca pode ser verdadeiro — é código morto
que transmite falsa confiança de dupla proteção.

**Antes:**
```ts
if (!response.source_document) {          // nunca executa
  console.error('[guardrail-1] source_document ausente');
  return SAFE_RESPONSE;
}
```

**Depois:** Remover o bloco. Guardrail 1 está inteiramente implementado pelo schema. O
comentário no `validateResponse` deixa isso explícito:

```ts
// Guardrail 1 — estrutural: schema garante answer, source_document não-vazio e confidence_score
const result = AssistantResponseSchema.safeParse(raw);
```

---

## 4. Código final corrigido — `3.1/response-validator.ts`

```ts
import { z } from 'zod';

export const AssistantResponseSchema = z.object({
  answer: z.string().min(1),
  source_document: z.string().min(1),
  confidence_score: z.number().min(0).max(1),
}).strict();

export type AssistantResponse = z.infer<typeof AssistantResponseSchema>;

const SAFE_RESPONSE: AssistantResponse = {
  answer: 'Não foi possível processar sua solicitação. Por favor, contate o suporte.',
  source_document: 'N/A',
  confidence_score: 0,
};

function normalize(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
}

function mentionsDangerousCargoReturn(answer: string): boolean {
  const t = normalize(answer);
  const hasDangerousCargo =
    t.includes('carga perigosa') || t.includes('cargas perigosas');
  const hasDevolucao =
    t.includes('devolucao') || t.includes('devolv') || t.includes('retorno');
  return hasDangerousCargo && hasDevolucao;
}

function containsNegation(answer: string): boolean {
  const t = normalize(answer);
  return [
    'nao e possivel',
    'nao pode',
    'nao sao elegiveis',
    'nao e elegivel',
    'nao e permitida',
    'vedada',
    'vedado',
    'impossivel',
    'inelegivel',
    'proibida',
  ].some((term) => t.includes(term));
}

export function validateResponse(raw: unknown): AssistantResponse {
  // Guardrail 1 — estrutural: schema garante answer, source_document não-vazio e confidence_score
  const result = AssistantResponseSchema.safeParse(raw);

  if (!result.success) {
    console.error('[guardrail-1] Falha de schema:', JSON.stringify(result.error.flatten()));
    return SAFE_RESPONSE;
  }

  const response = result.data;

  // Guardrail 2 — semântico: bloqueia apenas quando afirma devolução (sem negação presente)
  if (mentionsDangerousCargoReturn(response.answer) && !containsNegation(response.answer)) {
    console.error('[guardrail-2] Bloqueado: resposta afirma devolução de carga perigosa', {
      excerpt: response.answer.slice(0, 120),
    });
    return SAFE_RESPONSE;
  }

  return response;
}
```

---

## 5. Distinção prompt (probabilístico) vs código (determinístico)

| Verificação | Mecanismo | Garantia |
|-------------|-----------|----------|
| Resposta citar a fonte | System prompt instrui o modelo | Probabilística — o modelo pode "esquecer" |
| `source_document` presente e não-vazio | `z.string().min(1)` no schema Zod | **Determinística** — qualquer resposta sem fonte é rejeitada antes de chegar ao usuário |
| Não afirmar devolução de carga perigosa | System prompt + POL-001 no contexto RAG | Probabilística — depende da qualidade do retrieval e da instrução |
| Bloquear afirmação de devolução de carga perigosa | `mentionsDangerousCargoReturn && !containsNegation` | **Determinística** — executa toda vez, independente do modelo |

O harness não substitui o prompt — ele adiciona uma camada de verificação que o prompt não
pode garantir sozinho. A combinação dos dois nivela o risco: o prompt reduz a probabilidade
de erro, o código garante que certos erros nunca chegam ao usuário.
