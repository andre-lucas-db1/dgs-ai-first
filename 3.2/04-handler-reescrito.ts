// src/functions/feedback/handler.ts
// Handler do endpoint de feedback — reescrito seguindo o AGENTS.md do projeto NovaTech.
// Correções aplicadas em relação ao módulo gerado pelo Copilot:
//   - Imports estáticos no topo (sem require dinâmico)
//   - Zod via validator.ts separado (sem `as any`)
//   - pino via shared/logger.ts (sem console.log)
//   - attendantEmail removido: campo aceito é attendantId (nunca logar/persistir e-mail)
//   - CosmosClient como singleton fora do handler
//   - Configuração via config.ts (sem process.env direto e sem strings hardcoded)
//   - Tratamento de erro com status 400/500 adequado
//   - Resposta JSON com status 201 (Created)

import { app, HttpRequest, HttpResponseInit } from "@azure/functions";
import { CosmosClient } from "@azure/cosmos";
import { validateFeedbackRequest } from "./validator.js";
import { logger } from "../../shared/logger.js";
import { config } from "../../shared/config.js";
import { ValidationError } from "../../shared/errors.js";

// Singleton — instanciado uma vez no módulo, reusado entre invocações aquecidas
const cosmosClient = new CosmosClient(config.cosmosConnectionString);
const container = cosmosClient
  .database(config.cosmosDatabaseName)
  .container(config.feedbackContainerName);

export async function feedbackHandler(
  request: HttpRequest
): Promise<HttpResponseInit> {
  let body: unknown;

  try {
    body = await request.json();
  } catch {
    return {
      status: 400,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: "Body inválido: JSON malformado" }),
    };
  }

  let feedback: ReturnType<typeof validateFeedbackRequest>;
  try {
    feedback = validateFeedbackRequest(body);
  } catch (error) {
    if (error instanceof ValidationError) {
      return {
        status: 400,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ errors: error.issues }),
      };
    }
    throw error;
  }

  const record = {
    id: feedback.queryId,
    queryId: feedback.queryId,
    rating: feedback.rating,
    comment: feedback.comment,
    attendantId: feedback.attendantId,
  };

  try {
    await container.items.create(record);
  } catch (error) {
    // Log sem PII: apenas IDs de correlação e rating
    logger.error(
      { queryId: feedback.queryId, rating: feedback.rating },
      "Falha ao persistir feedback no Cosmos DB"
    );
    return {
      status: 500,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ error: "Erro interno ao registrar feedback" }),
    };
  }

  // Log estruturado: somente campos não-PII (sem attendantEmail, sem e-mail)
  logger.info(
    { queryId: feedback.queryId, rating: feedback.rating },
    "Feedback registrado"
  );

  return {
    status: 201,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: feedback.queryId }),
  };
}

app.http("feedback", {
  methods: ["POST"],
  handler: feedbackHandler,
});
