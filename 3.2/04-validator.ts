// src/functions/feedback/validator.ts
// Validação de entrada para o endpoint de feedback.
// Separado do handler conforme estrutura definida no Anexo C e AGENTS.md.

import { z } from "zod";
import { ValidationError } from "../../shared/errors.js";

export const feedbackRequestSchema = z.object({
  queryId: z
    .string({ required_error: "O campo 'queryId' é obrigatório" })
    .uuid("O campo 'queryId' deve ser um UUID v4 válido"),

  rating: z
    .number({ required_error: "O campo 'rating' é obrigatório", invalid_type_error: "O campo 'rating' deve ser um número" })
    .int("O campo 'rating' deve ser um número inteiro")
    .min(1, "O campo 'rating' deve ser no mínimo 1")
    .max(5, "O campo 'rating' deve ser no máximo 5"),

  comment: z
    .string({ invalid_type_error: "O campo 'comment' deve ser uma string" })
    .max(2000, "O campo 'comment' deve ter no máximo 2000 caracteres")
    .optional(),

  attendantId: z
    .string({ required_error: "O campo 'attendantId' é obrigatório" })
    .max(50, "O campo 'attendantId' deve ter no máximo 50 caracteres"),
});

// Tipo derivado do schema — única fonte de verdade (AGENTS.md: regra 4)
export type FeedbackRequest = z.infer<typeof feedbackRequestSchema>;

export function validateFeedbackRequest(body: unknown): FeedbackRequest {
  const result = feedbackRequestSchema.safeParse(body);
  if (!result.success) {
    throw new ValidationError(result.error.issues);
  }
  return result.data;
}
