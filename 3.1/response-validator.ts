import { z } from 'zod';

export const AssistantResponseSchema = z
  .object({
    answer: z.string().min(1),
    source_document: z.string().min(1),
    confidence_score: z.number().min(0).max(1),
  })
  .strict();

export type AssistantResponse = z.infer<typeof AssistantResponseSchema>;

const SAFE_RESPONSE: AssistantResponse = {
  answer: 'Nao foi possivel processar sua solicitacao. Por favor, contate o suporte.',
  source_document: 'N/A',
  confidence_score: 0,
};

function normalize(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '');
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
  // Guardrail 1 - estrutural: schema garante answer, source_document nao-vazio e confidence_score
  const result = AssistantResponseSchema.safeParse(raw);

  if (!result.success) {
    console.error('[guardrail-1] Falha de schema:', JSON.stringify(result.error.flatten()));
    return SAFE_RESPONSE;
  }

  const response = result.data;

  // Guardrail 2 - semantico: bloqueia apenas quando afirma devolucao (sem negacao presente)
  if (mentionsDangerousCargoReturn(response.answer) && !containsNegation(response.answer)) {
    console.error('[guardrail-2] Bloqueado: resposta afirma devolucao de carga perigosa', {
      excerpt: response.answer.slice(0, 120),
    });
    return SAFE_RESPONSE;
  }

  return response;
}
