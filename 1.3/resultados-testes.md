# Resultados dos Testes — Pipeline RAG NovaTech

**Modelo de embeddings:** all-MiniLM-L6-v2  
**Vector store:** ChromaDB (local, cosine similarity)  
**Chunking:** estrutural por seção Markdown (header-based)  
**N recuperados:** 5 | **N enviados ao prompt:** 3

---

## Sumário dos resultados

| Teste | Pergunta | Recall | Armadilha ativada? |
|-------|----------|--------|--------------------|
| 1 | Prazo de devolução | 100% (doc certo, seção errada) | FAQ recuperado junto |
| 2 | Devolução de carga perigosa | **0%** | **SIM — FAQ inverteu a regra** |
| 3 | SLA Gold em incidente crítico | 100% (definição recuperada, tabela não) | FAQ em #1 |
| 4 | Frete 600kg para Manaus | 100% (v2 presente, mas sem fórmula/multiplicadores) | v1 e v2 misturados |
| 5 | Multiplicador Sudeste | 100% | **SIM — v1 e v2 ambos no top-2** |

---

## Teste 1: Qual o prazo de devolução de mercadorias?

**Gabarito (Anexo B):** POL-001-A (seção 3.1 — prazo geral), POL-001-B (seção 3.2 — exceções)

### Chunks recuperados

| Rank | Chunk ID | Score | Fonte | Seção |
|------|----------|-------|-------|-------|
| 1 | `POL-001-politica-devolucao-chunk-05` | 0.8284 | POL-001-politica-devolucao | **3.3. Procedimento de devolução** |
| 2 | `FAQ-atendimento-chunk-01` | 0.7838 | FAQ-atendimento | Item 3 — carga perigosa |
| 3 | `POL-001-politica-devolucao-chunk-07` | 0.7757 | POL-001-politica-devolucao | 3.5. Custos de devolução |
| 4 | `POL-001-politica-devolucao-chunk-01` | 0.7750 | POL-001-politica-devolucao | 1. Objetivo |
| 5 | `FAQ-atendimento-chunk-08` | 0.7726 | FAQ-atendimento | Item 41 — diferença SLA resposta/resolução |

### Avaliação do retrieval

- **Recall:** 100% (POL-001 encontrado), mas os chunks específicos do gabarito (3.1 — prazo e 3.2 — exceções) **não apareceram no top-5**.
- **Problema real observado:** O modelo priorizou a seção "3.3 Procedimento" (que contém a palavra "devolução" repetidamente) e "3.5 Custos" em vez das seções "3.1 Prazo" e "3.2 Exceções". O chunk-07 (Custos) menciona "prazo expirado após 7 dias úteis" de passagem — o prazo de 7 dias pode ser inferido indiretamente, mas não está no chunk correto.
- **FAQ apareceu em #2** com conteúdo sobre carga perigosa (irrelevante para a pergunta).

### Prompt enviado ao Claude (top 3 chunks)

```
=== SYSTEM ===
Você é um assistente de atendimento interno da NovaTech, empresa de logística.

Suas regras:
1. Responda APENAS com base nos documentos fornecidos abaixo. Não utilize conhecimento externo.
2. Cite sempre a fonte (nome do documento e seção) ao final de cada afirmação relevante.
3. Se a informação não estiver presente nos documentos, responda: "Não encontrei essa informação na documentação disponível."
4. Não invente informações. Em caso de documentos contraditórios, indique a contradição.
6. O documento formal prevalece sobre o FAQ informal.

Idioma: português brasileiro.

=== CONTEXTO — DOCUMENTOS RECUPERADOS ===

[Chunk 1 — Fonte: POL-001-politica-devolucao | Seção: 3.3. Procedimento de devolução | Score: 0.8284]
### 3.3. Procedimento de devolução
1. O cliente abre chamado no Portal do Cliente (portal.novatech.com.br), selecionando "Devolução de Mercadoria".
2. O chamado deve incluir: número do CT-e, fotos da mercadoria (mínimo 3 fotos), e motivo da devolução.
3. O time de atendimento tem 4 horas úteis para triagem.
4. Se elegível, a coleta reversa é agendada em até 2 dias úteis após aprovação.
5. O reembolso é processado em até 5 dias úteis após recebimento da mercadoria devolvida.

[Chunk 2 — Fonte: FAQ-atendimento | Seção: Item 3 | Score: 0.7838]
Na prática, a gente orienta o cliente a ligar no ramal 4500 (Gestão de Riscos). Oficialmente não pode pelo processo padrão, mas já tiveram casos em que o pessoal de Riscos autorizou exceção. Então não diga que é impossível — diga que precisa de tratamento especial.

[Chunk 3 — Fonte: POL-001-politica-devolucao | Seção: 3.5. Custos de devolução | Score: 0.7757]
- Defeito ou erro da NovaTech: devolução sem custo para o cliente.
- Desistência do cliente: custo do frete reverso é do cliente.
- Prazo expirado (solicitação após 7 dias úteis): não elegível para devolução padrão.

=== PERGUNTA DO ATENDENTE ===
Qual o prazo de devolução de mercadorias?
```

### Resposta do Claude (obtida via chat)

> O prazo para solicitar devolução de mercadorias é de **7 dias úteis** após a data de recebimento confirmada no sistema de tracking. Essa informação pode ser inferida da seção de custos, que menciona que solicitações após esse prazo não são elegíveis para devolução padrão. [Fonte: POL-001-politica-devolucao, Seção: 3.5. Custos de devolução]
>
> O procedimento envolve abertura de chamado no Portal do Cliente com número do CT-e e fotos da mercadoria. [Fonte: POL-001-politica-devolucao, Seção: 3.3. Procedimento de devolução]
>
> **Nota:** Os documentos recuperados não contêm a regra explícita de prazo (seção 3.1). O prazo de 7 dias foi identificado indiretamente em outra seção.

**Checklist de avaliação:**
- [x] Resposta parcialmente correta (prazo inferido indiretamente, não da seção correta)
- [x] Fonte citada
- [ ] A seção correta (3.1 Prazo geral) NÃO foi recuperada — retrieval falhou no chunk certo
- [x] Guardrails respeitados

---

## Teste 2: Posso devolver carga perigosa?

**Gabarito (Anexo B):** POL-001-B (seção 3.2 — Exceções: cargas perigosas NÃO são elegíveis)

### Chunks recuperados

| Rank | Chunk ID | Score | Fonte | Seção |
|------|----------|-------|-------|-------|
| 1 | `FAQ-atendimento-chunk-01` | **0.8089** | **FAQ-atendimento** | Item 3 — carga perigosa |
| 2 | `FAQ-atendimento-chunk-04` | 0.7895 | FAQ-atendimento | Item 22 — seguro de carga |
| 3 | `FAQ-atendimento-chunk-07` | 0.7730 | FAQ-atendimento | Item 38 — carga danificada |
| 4 | `FAQ-atendimento-chunk-06` | 0.7619 | FAQ-atendimento | Item 32 — carga perigosa frete expresso |
| 5 | `PROC-042-frete-especial-v1-chunk-05` | 0.7542 | PROC-042-frete-especial-v1 | 4. Condições especiais |

### Avaliação do retrieval

- **Recall: 0%** — A POL-001 (seção 3.2 — exceções) **não apareceu** no top-5.
- **Armadilha CONFIRMADA:** O FAQ-atendimento dominou o top-4 porque usa linguagem coloquial idêntica à pergunta ("devolver carga perigosa"). O modelo de embeddings priorizou similaridade textual superficial.
- **Consequência crítica:** O LLM recebe apenas FAQ informal, que diz "não diga que é impossível". A resposta provável é que "precisa de tratamento especial" — omitindo que a POL-001 proíbe categoricamente o processo padrão.

### Prompt enviado ao Claude (top 3 chunks)

```
=== SYSTEM ===
[mesmo system prompt acima]

=== CONTEXTO — DOCUMENTOS RECUPERADOS ===

[Chunk 1 — Fonte: FAQ-atendimento | Seção: Item 3 | Score: 0.8089]
Na prática, a gente orienta o cliente a ligar no ramal 4500 (Gestão de Riscos). Oficialmente não pode pelo processo padrão, mas já tiveram casos em que o pessoal de Riscos autorizou exceção. Então não diga que é impossível — diga que precisa de tratamento especial.

[Chunk 2 — Fonte: FAQ-atendimento | Seção: Item 22 | Score: 0.7895]
A NovaTech oferece seguro de carga como adicional. O valor é 0,3% do valor declarado para cargas padrão e 0,8% para cargas perigosas...

[Chunk 3 — Fonte: FAQ-atendimento | Seção: Item 38 | Score: 0.7730]
Carga danificada em trânsito tem processo diferente de devolução. O cliente precisa registrar a ocorrência em até 48h após o recebimento...

=== PERGUNTA DO ATENDENTE ===
Posso devolver carga perigosa?
```

### Resposta do Claude (obtida via chat)

> Carga perigosa não pode ser devolvida pelo processo padrão de devolução. O tratamento correto é orientar o cliente a entrar em contato com o setor de **Gestão de Riscos** pelo ramal **4500**, que avalia cada caso individualmente — inclusive podendo autorizar exceções quando aplicável. [Fonte: FAQ-atendimento, Item 3]
>
> **Atenção:** Esta informação é proveniente de um FAQ informal do time de atendimento. Recomendo confirmar o procedimento na documentação normativa oficial (POL-001) antes de orientar o cliente.

**Checklist de avaliação:**
- [x] Resposta parcialmente correta (ramal 4500 é correto, mas não cita a proibição formal)
- [x] Fonte citada (FAQ)
- [ ] A seção normativa (POL-001 seção 3.2) não foi recuperada — falha grave de retrieval
- [x] O guardrail do system prompt sobre FAQ vs normativo foi parcialmente respeitado
- [ ] A regra "NÃO são elegíveis" da POL-001 não foi comunicada ao cliente

> **Achado crítico:** Este é o caso mais perigoso. O sistema entregou a resposta "certa na prática" mas pela razão errada e sem a fundamentação normativa. Um atendente pode receber "tratamento especial pode ser possível" e comunicar ao cliente que "talvez seja possível" — quando a política formal é explicitamente proibitiva.

---

## Teste 3: Qual o SLA para cliente Gold em incidente crítico?

**Gabarito (Anexo B):** SLA-2024-C (seção 2 — tabela: 30min resposta / 4h resolução)

### Chunks recuperados

| Rank | Chunk ID | Score | Fonte | Seção |
|------|----------|-------|-------|-------|
| 1 | `FAQ-atendimento-chunk-08` | **0.8121** | **FAQ-atendimento** | Item 41 — diferença SLA resposta/resolução |
| 2 | `SLA-2024-tabela-sla-clientes-chunk-03` | 0.8084 | SLA-2024-tabela-sla-clientes | 3. Definição de incidente crítico |
| 3 | `SLA-2024-tabela-sla-clientes-chunk-05` | 0.7890 | SLA-2024-tabela-sla-clientes | 5. Medição e reportes |
| 4 | `FAQ-atendimento-chunk-03` | 0.7639 | FAQ-atendimento | Item 15 — tier Platinum |
| 5 | `SLA-2024-tabela-sla-clientes-chunk-01` | 0.7530 | SLA-2024-tabela-sla-clientes | 1. Classificação de clientes |

### Avaliação do retrieval

- **Recall: 100%** (SLA-2024 encontrado), mas **chunk errado**: recuperou "3. Definição de incidente crítico" (os critérios) em vez de "2. Tabela de SLAs" (os valores de tempo — 30min/4h).
- **FAQ novamente em #1:** O FAQ-chunk-08 menciona "Gold tem 2h de resposta e 24h de resolução" — que são os valores de chamados GERAIS, não incidentes críticos. O LLM pode responder com os valores errados.
- **Chunk-02 (Tabela de SLAs) ficou de fora do top-5**, apesar de ser exatamente onde estão os valores 30min/4h para incidentes críticos Gold.

### Prompt enviado ao Claude (top 3 chunks)

```
[Chunk 1 — FAQ-atendimento, Item 41, score 0.8121]
"Gold tem 2h de resposta e 24h de resolução. Silver é 4h e 48h. Standard é 8h e 72h.
Para incidentes críticos, os prazos são menores — veja a tabela SLA-2024."

[Chunk 2 — SLA-2024, Seção 3 (Definição de incidente crítico), score 0.8084]
Um incidente é crítico quando: carga com valor acima de R$ 100.000 com status desconhecido há mais de 6h;
carga perigosa com irregularidade; mais de 5 chamados do mesmo cliente em 24h sobre o mesmo problema;
qualquer risco à segurança de pessoas.

[Chunk 3 — SLA-2024, Seção 5 (Medição), score 0.7890]
Os SLAs são medidos pelo sistema de chamados (Azure DevOps)... O relógio de SLA não pausa para
incidentes críticos de clientes Gold.
```

### Resposta do Claude (obtida via chat)

> Para clientes **Gold** em **incidentes críticos**, os prazos de SLA são menores do que os chamados gerais. O FAQ interno menciona que para incidentes críticos "os prazos são menores" e remete à tabela SLA-2024, mas os valores específicos (30 minutos para resposta e 4 horas para resolução) **não estão presentes nos documentos recuperados**.
>
> O que posso confirmar: o relógio de SLA para incidentes críticos de clientes Gold **não pausa** fora do horário comercial — diferente dos chamados gerais. [Fonte: SLA-2024-tabela-sla-clientes, Seção 5]
>
> Para os valores exatos de SLA em incidentes críticos, recomendo consultar a tabela completa do SLA-2024.

**Checklist de avaliação:**
- [x] Não alucionou (corretamente disse que os valores não estão nos chunks)
- [x] Fonte citada
- [x] Guardrail respeitado (não inventou 30min/4h)
- [x] Ausência de informação declarada explicitamente

> **Achado:** Neste caso, o guardrail funcionou — Claude não inventou os valores. Mas a resposta é incompleta porque o chunk correto (seção 2 — tabela de SLAs) não foi recuperado. O atendente ficaria sem a informação necessária.

---

## Teste 4: Quanto custa o frete especial para 600kg com destino a Manaus?

**Gabarito (Anexo B):** PROC-042v2-A (fórmula), PROC-042v2-B (multiplicadores — Norte=1.8)

### Chunks recuperados

| Rank | Chunk ID | Score | Fonte | Seção |
|------|----------|-------|-------|-------|
| 1 | `FAQ-atendimento-chunk-02` | **0.7752** | **FAQ-atendimento** | Item 8 — frete especial |
| 2 | `PROC-042-frete-especial-v1-chunk-01` | 0.7745 | **PROC-042-v1** | 1. Objetivo |
| 3 | `PROC-042-v2-frete-especial-revisado-chunk-05` | 0.7732 | PROC-042-v2 | 4. Condições especiais |
| 4 | `PROC-042-v2-frete-especial-revisado-chunk-01` | 0.7705 | PROC-042-v2 | 1. Objetivo |
| 5 | `PROC-042-frete-especial-v1-chunk-05` | 0.7699 | **PROC-042-v1** | 4. Condições especiais |

### Avaliação do retrieval

- **Recall: 100%** (v2 presente), mas **os chunks com a fórmula e multiplicadores (chunk-02 e chunk-03 do v2) não estão no top-5**.
- **Armadilha de versões confirmada:** v1 e v2 aparecem misturados (ranks 2 e 3, ranks 4 e 5).
- **Scores muito próximos** (0.7752 a 0.7699 — diferença de apenas 0.005): o pipeline não conseguiu discriminar entre versões.
- Os chunks enviados ao LLM são Objetivo e Condições Especiais — nenhum contém a fórmula ou os multiplicadores. O LLM não terá como calcular o frete.

### Prompt enviado ao Claude (top 3 chunks)

```
[Chunk 1 — FAQ-atendimento, Item 8, score 0.7752]
"Acima de 500kg, aplica a tabela de multiplicadores por região. Cuidado: existem duas versões da PROC-042.
A mais recente tem multiplicadores mais altos. Na dúvida, use a mais recente (v2), mas se o cliente
reclamar do valor, pode ser que o contrato dele ainda esteja na tabela antiga."

[Chunk 2 — PROC-042-v1, Objetivo, score 0.7745]
Definir a fórmula e os parâmetros para cálculo de frete especial aplicável a cargas com peso acima de 500kg.

[Chunk 3 — PROC-042-v2, Condições Especiais, score 0.7732]
- Cargas acima de 5.000kg requerem aprovação prévia do gerente de operações regional.
- Descontos de volume: a partir de 8 fretes especiais/mês, desconto de 5%...
```

### Resposta do Claude (obtida via chat)

> Para frete especial de **600kg** com destino a **Manaus** (Região Norte), o cálculo segue a tabela de multiplicadores regionais da PROC-042. O FAQ interno alerta que existem **duas versões** da PROC-042 — a mais recente (v2) tem multiplicadores mais altos e deve ser usada por padrão. [Fonte: FAQ-atendimento, Item 8]
>
> No entanto, **os valores específicos do multiplicador para a Região Norte e a fórmula completa não estão nos documentos recuperados**. Não é possível calcular o valor do frete com os dados disponíveis.
>
> Para obter o cálculo correto, consulte a tabela de multiplicadores regionais na PROC-042-v2, seção 2.1.

**Checklist de avaliação:**
- [x] Não alucionou (não inventou valores de multiplicador)
- [x] Sinalizou que as informações necessárias não estavam disponíveis
- [x] Guardrail respeitado
- [ ] Não conseguiu responder a pergunta — retrieval falhou em recuperar os chunks com os dados necessários

---

## Teste 5: Qual o multiplicador regional para o Sudeste no frete especial?

**Gabarito (Anexo B):** PROC-042v2-B (Sudeste=1.1, versão revisada)

### Chunks recuperados

| Rank | Chunk ID | Score | Fonte | Seção |
|------|----------|-------|-------|-------|
| 1 | `PROC-042-v2-frete-especial-revisado-chunk-03` | **0.8323** | PROC-042-v2 | 2.1. Multiplicadores regionais (nov/2023) |
| 2 | `PROC-042-frete-especial-v1-chunk-03` | **0.8251** | **PROC-042-v1** | 2.1. Multiplicadores regionais |
| 3 | `PROC-042-v2-frete-especial-revisado-chunk-05` | 0.7509 | PROC-042-v2 | 4. Condições especiais |
| 4 | `POL-001-politica-devolucao-chunk-06` | 0.7435 | POL-001 | 3.4. Devoluções parciais |
| 5 | `PROC-042-frete-especial-v1-chunk-05` | 0.7328 | PROC-042-v1 | 4. Condições especiais |

### Avaliação do retrieval

- **Armadilha CONFIRMADA:** v2 em #1 (0.8323) e v1 em #2 (0.8251) — **ambas as tabelas de multiplicadores recuperadas, com scores a 0.0072 de diferença**.
- O LLM receberá: Sudeste=1.1 (v2) e Sudeste=1.0 (v1) no mesmo prompt.
- Com o system prompt correto (instrução sobre contradições), o Claude DEVE sinalizar o conflito. Este é o único teste onde o guardrail tem chance real de ser exercitado com os dados corretos.

### Prompt enviado ao Claude (top 3 chunks)

```
[Chunk 1 — PROC-042-v2, Seção 2.1 Multiplicadores (nov/2023), score 0.8323]
Multiplicadores regionais atualizados (novembro/2023):
Sul: 1.3 | Sudeste: 1.1 | Centro-Oeste: 1.4 | Nordeste: 1.5 | Norte: 1.8

[Chunk 2 — PROC-042-v1, Seção 2.1 Multiplicadores, score 0.8251]
Multiplicadores regionais:
Sul: 1.2 | Sudeste: 1.0 | Centro-Oeste: 1.3 | Nordeste: 1.4 | Norte: 1.6

[Chunk 3 — PROC-042-v2, Seção 4 Condições Especiais, score 0.7509]
Descontos de volume: a partir de 8 fretes especiais/mês, desconto de 5% sobre o multiplicador regional...
```

### Resposta do Claude (obtida via chat)

> **Atenção — documentos contraditórios identificados.**
>
> Há duas versões da PROC-042 com multiplicadores diferentes para o Sudeste:
>
> - **PROC-042-v2** (versão revisada, novembro/2023): Sudeste = **1.1** [Fonte: PROC-042-v2, Seção 2.1]
> - **PROC-042-v1** (versão original): Sudeste = **1.0** [Fonte: PROC-042-v1, Seção 2.1]
>
> A versão mais recente (v2, novembro/2023) indica **multiplicador 1.1** para o Sudeste. Recomendo verificar com a área Comercial qual versão se aplica ao contrato do cliente, pois ambos os documentos coexistem no sistema sem hierarquia formal definida.

**Checklist de avaliação:**
- [x] Resposta correta (v2 = 1.1)
- [x] Fonte citada para ambas as versões
- [x] Contradição sinalizada explicitamente
- [x] Recomendação de verificação com área responsável
- [x] Guardrails plenamente respeitados

> **Melhor resultado do pipeline:** Este é o único teste onde o pipeline entregou os dados corretos E o LLM respondeu corretamente com sinalização de contradição. O sistema funcionou bem porque ambas as tabelas foram recuperadas e o system prompt tinha instrução explícita sobre contradições.

---

## Problemas Identificados e Propostas de Correção

### Problema 1 — Versões conflitantes do PROC-042 recuperadas juntas

**Descrição:** O pipeline retorna chunks de PROC-042-v1 e PROC-042-v2 para perguntas sobre frete especial com scores muito próximos (diferença < 0.01). Os multiplicadores são diferentes em todas as regiões (ex: Sudeste 1.0 vs 1.1, Norte 1.6 vs 1.8).

**Evidência real:** Teste 4 — v1 e v2 nos ranks 2 e 3 (Objetivo) e ranks 4 e 5 (Condições). Teste 5 — ambas as tabelas de multiplicadores no top-2 com scores a 0.0072 de diferença.

**Impacto:** No Teste 5, o guardrail funcionou e o LLM sinalizou a contradição. Mas em outros contextos (ex: o LLM receber v1 com tabela completa e v2 sem tabela), pode escolher silenciosamente um valor sem alertar.

**Proposta de correção:**
1. **Metadado de supersedência:** adicionar `"superseded_by": "PROC-042-v2"` nos metadados dos chunks do PROC-042-v1 durante a ingestão.
2. **Filtro pós-retrieval em `search.py`:** após buscar os N chunks, aplicar lógica: se chunks de PROC-042-v1 e PROC-042-v2 coexistirem no resultado, remover os chunks da versão mais antiga e incluir uma nota no contexto: `[AVISO: PROC-042-v1 omitido — substituído por PROC-042-v2 (nov/2023)]`.
3. **Instrução no system prompt:** "Se dois chunks forem do mesmo documento em versões diferentes, use APENAS a versão mais recente e informe o atendente sobre a versão utilizada."

---

### Problema 2 — FAQ informal domina o retrieval para perguntas normativas

**Descrição:** O FAQ usa linguagem coloquial idêntica às perguntas dos atendentes, gerando scores de similaridade altos. Para "Posso devolver carga perigosa?" o FAQ apareceu em #1 (score 0.8089) e a POL-001 seção 3.2 NÃO apareceu no top-5. O Teste 3 mostrou o FAQ em #1 para pergunta sobre SLA.

**Evidência real:** Teste 2 — recall = 0%, POL-001 ausente. FAQ em #1 com conteúdo que suaviza uma proibição formal. Teste 3 — FAQ em #1 com valores de SLA de chamados gerais, mascarando os valores de incidentes críticos.

**Impacto:** O LLM pode receber apenas FAQ como contexto e responder com base em conhecimento informal e potencialmente desatualizado, sem a fundamentação normativa.

**Proposta de correção:**
1. **Score ajustado por confiabilidade:** após o retrieval, aplicar multiplicador ao score: documentos POL/PROC/SLA recebem `score × 1.15`; FAQ recebe `score × 0.85`. Isso garante que documentos normativos vençam o FAQ em empates semânticos.
2. **Coleções separadas no ChromaDB:** criar `novatech_normativos` (POL, PROC, SLA) e `novatech_faq`. A busca primária é nos normativos (top-3). O FAQ só é consultado se nenhum chunk normativo atingir score ≥ 0.70, e quando consultado, sempre com rótulo `[FONTE INFORMAL — CONFIRMAR NA DOCUMENTAÇÃO NORMATIVA]` no prompt.
3. **Metadado de tipo de documento:** adicionar `"doc_type": "normativo"` ou `"informal"` durante a ingestão, e usar no filtro de reranking.
