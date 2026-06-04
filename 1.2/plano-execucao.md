# Exercício 1.2 — Plano de Execução
## Prototipação de Prompt com Engenharia de Contexto — Assistente NovaTech

---

## Visão Geral

O objetivo é construir e iterar o system prompt do assistente de atendimento da NovaTech, uma empresa de logística que precisa reduzir o tempo médio de consulta de 12 minutos para menos de 2 minutos por chamado. O assistente será usado pelos 45 atendentes via Microsoft Teams.

---

## Etapa 1 — System Prompt v1

### 1.1 Estrutura do Prompt

O prompt é organizado em 4 seções obrigatórias conforme o exercício. Cada seção tem uma responsabilidade clara e não se sobrepõe.

**Seção 1: Identidade**
Define quem o assistente é, para quem trabalha e qual seu papel específico. Evita linguagem genérica como "assistente útil".

**Seção 2: Regras e Guardrails**
Incorpora os 4 guardrails definidos pelo Product Specialist, com clareza de prioridade. Adiciona regra de conflito de versões de documentos (PROC-042 v1 vs v2).

**Seção 3: Formato de Resposta**
Define estrutura de resposta obrigatória: resposta direta → fonte citada → próximos passos (quando aplicável) → alerta de escalada (quando necessário).

**Seção 4: Instruções para Uso dos Chunks**
Define como priorizar chunks quando há conflito, como tratar ausência de informação, e como distinguir documento formal de FAQ informal.

**Ordem de prioridade de fontes (do mais para o menos autoritativo):**
1. Documentos normativos com versão mais recente (POL-001 v3.1, PROC-042-v2, SLA-2024)
2. Documentos normativos versão anterior (PROC-042 v1) — apenas para chamados abertos antes de 01/12/2023
3. FAQ de atendimento — somente para orientação operacional, não para dados concretos (prazos, valores)
4. Nenhuma fonte → declarar explicitamente que não encontrou e sugerir escalada

### 1.2 System Prompt v1 (texto completo para colar no Claude)

```
## IDENTIDADE

Você é o Assistente de Atendimento da NovaTech, empresa de logística. Seu papel é apoiar os atendentes do SAC respondendo perguntas sobre políticas de devolução, SLAs por tipo de cliente, cálculo de frete especial e procedimentos operacionais, com base exclusivamente na documentação oficial fornecida.

Você NÃO é um assistente genérico. Você NÃO responde perguntas fora do domínio de logística/atendimento NovaTech.

---

## REGRAS (GUARDRAILS — não negociáveis)

1. CITE A FONTE: toda resposta factual deve indicar o documento de origem (ex: "conforme POL-001, seção 3.2"). Nunca afirme um fato sem citar sua fonte.

2. NUNCA INVENTE: não crie prazos, valores, multiplicadores ou qualquer dado numérico que não esteja explicitamente nos chunks fornecidos. Prefira dizer que não encontrou a arriscar um dado incorreto.

3. SEM RESPOSTA → ESCALE: quando não encontrar a informação nos chunks disponíveis, responda explicitamente: "Não localizei essa informação na documentação disponível. Recomendo escalar para o supervisor ou consultar a área responsável." Nunca omita essa declaração.

4. PORTUGUÊS FORMAL E ACESSÍVEL: use linguagem formal, clara e objetiva. Evite jargão técnico sem explicação. O atendente precisa repassar a informação ao cliente com confiança.

---

## PRIORIDADE DE FONTES

Quando chunks de fontes diferentes apresentarem informações conflitantes, siga esta hierarquia:

1. Documentos normativos — versão mais recente (POL-001 v3.1, PROC-042-v2 novembro/2023, SLA-2024)
2. Documentos normativos — versão anterior (PROC-042 v1) — válida APENAS para chamados abertos antes de 01/12/2023
3. FAQ de atendimento — use SOMENTE para orientações operacionais gerais, NUNCA para dados concretos como prazos ou valores
4. Ausência de informação → declarar explicitamente e sugerir escalada

Se chunks da PROC-042 v1 e v2 forem fornecidos simultaneamente, use SEMPRE a v2 para chamados novos e sinalize a ambiguidade ao atendente.

---

## FORMATO DE RESPOSTA OBRIGATÓRIO

Toda resposta deve seguir esta estrutura:

**Resposta:** [resposta direta e objetiva à pergunta]

**Fonte:** [documento, versão e seção — ex: POL-001 v3.1, seção 3.2]

**Próximos passos** (quando houver): [orientação de ação para o atendente]

**Atenção** (quando aplicável): [alerta sobre exceções, conflitos de versão, ou necessidade de escalada]

---

## INSTRUÇÕES PARA USO DOS CHUNKS

Os chunks abaixo representam os trechos da documentação oficial recuperados para esta consulta. Você deve:

- Usar APENAS as informações presentes nos chunks fornecidos
- Não combinar informações de chunks com conhecimento externo
- Se dois chunks apresentarem dados conflitantes, aplicar a hierarquia de fontes acima e sinalizar o conflito
- Se a pergunta não for respondível com os chunks disponíveis, declará-lo explicitamente

[CHUNKS SERÃO INSERIDOS AQUI DINAMICAMENTE]
```

---

## Etapa 2 — Mapeamento de Contexto Estático vs Dinâmico

### 2.1 Definição das Partes

| Parte do contexto | Tipo | Conteúdo | Muda quando? |
|---|---|---|---|
| Seção IDENTIDADE | **Estático** | Quem é o assistente, papel, escopo | Nunca (ou em releases de produto) |
| Seção REGRAS/GUARDRAILS | **Estático** | Os 4 guardrails do Product Specialist | Raramente (mudança de política) |
| Seção PRIORIDADE DE FONTES | **Estático** | Hierarquia de documentos | Raramente (novo documento normativo) |
| Seção FORMATO DE RESPOSTA | **Estático** | Estrutura obrigatória de resposta | Raramente (ajuste de UX) |
| Seção INSTRUÇÕES PARA CHUNKS | **Estático** | Como tratar os chunks | Raramente |
| Chunks recuperados pelo RAG | **Dinâmico** | 3-5 trechos de documentação por query | A cada query (depende da pergunta) |
| Dados do cliente | **Dinâmico** | Tier do cliente (Gold/Silver/Standard) | A cada query (depende do chamado) |
| Histórico da conversa | **Dinâmico** | Mensagens anteriores do turno atual | A cada turno |
| Pergunta do atendente | **Dinâmico** | A query em linguagem natural | A cada query |

### 2.2 Estimativa de Tokens

| Parte | Tokens estimados | Observação |
|---|---|---|
| IDENTIDADE | ~80 tokens | Fixo |
| REGRAS/GUARDRAILS | ~180 tokens | Fixo |
| PRIORIDADE DE FONTES | ~130 tokens | Fixo |
| FORMATO DE RESPOSTA | ~100 tokens | Fixo |
| INSTRUÇÕES PARA CHUNKS | ~120 tokens | Fixo |
| **Subtotal estático** | **~610 tokens** | Vai em toda query |
| Chunks RAG (3-5 chunks) | ~300-800 tokens | Varia por query e tamanho dos chunks |
| Dados do cliente | ~20-50 tokens | Varia por query |
| Histórico da conversa | 0-2.000 tokens | Cresce durante a sessão |
| Pergunta do atendente | ~10-50 tokens | Varia |
| **Total dinâmico (estimado)** | **~330-2.900 tokens** | Depende da query |
| **Total geral estimado** | **~940-3.510 tokens** | Bem dentro dos limites do modelo |

**Conclusão de orçamento:** O contexto total fica entre ~1k e ~4k tokens por query, muito abaixo dos limites do Claude (200k tokens). O orçamento não é um problema neste cenário — mas em produção, com histórico de conversas longas e chunks maiores, pode chegar a 10-20k tokens por sessão.

---

## Etapa 3 — Cenários de Teste (preparação antes de abrir o Claude)

### Como executar o teste

1. Abrir nova conversa no Claude (claude.ai ou Claude Code)
2. Na primeira mensagem, colar: **System Prompt v1 completo + os 3 chunks simulados do exercício**
3. Fazer as 3 perguntas em sequência, como se fosse o atendente

**Chunks a incluir no teste (do exercício 1.2):**

```
[Chunk A — POL-001, seção 3.2]
Política de Devolução POL-001, seção 3.2: Mercadorias podem ser devolvidas em até 7 dias úteis após o recebimento, exceto cargas classificadas como perigosas (classes 1 a 6 da ANTT). O cliente deve abrir chamado no portal e anexar fotos da mercadoria.

[Chunk B — SLA-2024]
Tabela SLA-2024: Cliente Gold — resposta em até 2h, resolução em até 24h. Cliente Silver — resposta em até 4h, resolução em até 48h. Cliente Standard — resposta em até 8h, resolução em até 72h.

[Chunk C — PROC-042-v2, seção 2]
PROC-042-v2, seção 2: Frete especial para cargas acima de 500kg: valor base × multiplicador regional. Região Sul: 1.3. Região Sudeste: 1.1. Região Norte: 1.8. Região Nordeste: 1.5. Região Centro-Oeste: 1.4.
```

### 3.1 Pergunta 1 — Carga Perigosa

**Pergunta:** "Qual o prazo de devolução para carga perigosa?"

**Resposta correta esperada:**
- Cargas perigosas (classes 1 a 6 da ANTT) **NÃO são elegíveis** para devolução pelo processo padrão
- Fonte: POL-001, seção 3.2
- O Chunk A menciona a exceção, mas de forma ambígua ("exceto cargas perigosas") — o assistente precisa interpretar corretamente que a exceção **remove** o direito de devolução, não apenas muda o prazo
- Próximo passo: orientar contato com Gestão de Riscos (mas o Chunk A não fornece o ramal — o assistente NÃO deve inventar o ramal 4500)

**Armadilha a observar:** O Chunk A diz "exceto cargas perigosas" sem detalhar o que fazer. Um prompt fraco pode levar o modelo a responder "não há prazo definido" ou pior, inventar um prazo alternativo. A resposta correta é que NÃO pode devolver pelo processo padrão e que não há mais informação no chunk disponível sobre o procedimento alternativo.

**Critério de aprovação:** O assistente deve dizer que carga perigosa NÃO pode ser devolvida pelo processo padrão, citar POL-001 seção 3.2, e — como o chunk não fornece o ramal — sugerir escalada ao supervisor.

### 3.2 Pergunta 2 — SLA Gold

**Pergunta:** "Meu cliente é Gold, qual o SLA de resolução?"

**Resposta correta esperada:**
- Para chamados gerais: resolução em até **24 horas** (Chunk B)
- Fonte: SLA-2024
- Observação: o Chunk B não distingue chamados gerais de incidentes críticos — o assistente deve responder com o que está disponível e não inventar o SLA de incidente crítico

**Armadilha a observar:** O Chunk B não especifica "úteis" — o modelo pode ou não inferir isso. A resposta deve ser fiel ao chunk. Também não deve inventar dados sobre incidente crítico (4h) pois esse chunk não foi fornecido no teste.

**Critério de aprovação:** Citar SLA-2024, informar resolução em até 24h, não inventar dados não presentes no chunk.

### 3.3 Pergunta 3 — Frete Manaus 600kg

**Pergunta:** "Quanto custa o frete para 600kg para Manaus?"

**Resposta correta esperada:**
- Manaus está na Região Norte → multiplicador **1.8** (Chunk C, PROC-042-v2)
- Peso 600kg → fator de peso **1.0** (500-1.000kg) — mas este dado NÃO está no Chunk C simplificado
- **O Chunk C não fornece o valor base** — o assistente NÃO pode calcular o valor final em reais
- Resposta correta: "O frete será calculado como: valor base × 1.8. Não possuo o valor base para calcular o total — consulte a tabela mensal de fretes."
- Fonte: PROC-042-v2, seção 2

**Armadilha a observar:** O modelo pode tentar "completar" o cálculo inventando um valor base, ou pode confundir a cidade de Manaus com outra região. A resposta deve ser parcial e honesta sobre o que falta.

**Critério de aprovação:** Identificar região Norte, multiplicador 1.8, citar PROC-042-v2, e declarar explicitamente que o valor base não está disponível nos chunks fornecidos.

---

## Etapa 4 — Análise das Respostas v1

Para cada resposta obtida no teste, avaliar:

| Critério | O que verificar |
|---|---|
| Correção do conteúdo | A resposta factual está correta conforme a documentação? |
| Citação de fonte | O documento e seção foram citados? |
| Guardrail de não-invenção | O modelo inventou algum dado não presente no chunk? |
| Guardrail de escalada | Quando não havia informação, o modelo sugeriu escalada? |
| Formato | A estrutura Resposta/Fonte/Próximos passos/Atenção foi seguida? |
| Interpretação de exceção | Na pergunta 1, entendeu que carga perigosa NÃO pode devolver? |

**Falhas esperadas no v1 (hipóteses a validar no teste real):**

- **Pergunta 1:** Risco de o assistente interpretar "exceto cargas perigosas" como "prazo diferente" em vez de "não elegível". O Chunk A do exercício é ambíguo comparado ao Anexo B (que é mais explícito).
- **Pergunta 3:** Risco de o assistente inventar um valor base ou omitir que o cálculo está incompleto.
- **Formato:** O v1 pode não seguir rigidamente a estrutura de resposta se o prompt não for específico o suficiente sobre obrigatoriedade.

---

## Etapa 5 — System Prompt v2 (iterado)

Com base na análise, os principais pontos de melhoria esperados:

### 5.1 Melhorias planejadas para o v2

**Melhoria 1 — Clareza sobre exceções que removem direitos**
Adicionar instrução explícita: "Quando um chunk descrever uma exceção que remove um direito (ex: 'exceto X'), interprete como: X NÃO tem esse direito, não como 'X tem um prazo/processo diferente não especificado'."

**Melhoria 2 — Resposta parcial obrigatória para cálculos incompletos**
Adicionar instrução: "Quando a pergunta exigir um cálculo e algum dado necessário não estiver presente nos chunks (ex: valor base de frete), forneça a fórmula com os dados disponíveis e declare explicitamente qual dado está ausente. Nunca assuma ou estime valores ausentes."

**Melhoria 3 — Reforço do formato estruturado**
Tornar o formato ainda mais explícito, com exemplo de resposta ideal incluído no prompt, para que o modelo tenha um "template" visual a seguir.

**Melhoria 4 — Instrução sobre versões de documentos**
Adicionar: "Se chunks de versões diferentes do mesmo documento forem fornecidos (ex: PROC-042 v1 e PROC-042-v2), use sempre a versão mais recente para chamados novos e sinalize a existência da versão anterior ao atendente."

### 5.2 System Prompt v2 (texto completo para colar no Claude)

```
## IDENTIDADE

Você é o Assistente de Atendimento da NovaTech, empresa de logística. Seu papel é apoiar os atendentes do SAC respondendo perguntas sobre políticas de devolução, SLAs, cálculo de frete especial e procedimentos operacionais, com base exclusivamente nos chunks de documentação fornecidos em cada consulta.

Você responde APENAS perguntas dentro do domínio de atendimento NovaTech. Para qualquer outra pergunta, informe que está fora do seu escopo.

---

## REGRAS INVIOLÁVEIS

**Regra 1 — Cite sempre a fonte**
Toda afirmação factual deve citar o documento de origem, versão e seção. Formato: "(conforme [DOCUMENTO], seção [X.X])". Sem fonte, não afirme.

**Regra 2 — Nunca invente dados**
Prazos, valores, multiplicadores, ramais, percentuais — qualquer dado numérico ou concreto deve estar explicitamente presente no chunk fornecido. Se não estiver, declare: "Esta informação não está disponível nos documentos fornecidos."

**Regra 3 — Cálculos incompletos: forneça o que tem, declare o que falta**
Se a pergunta exigir um cálculo e um dado necessário não estiver no chunk (ex: valor base de frete), forneça a fórmula com os dados disponíveis e declare explicitamente: "Para completar o cálculo, é necessário o [dado ausente], que não está nos chunks disponíveis. Consulte [fonte sugerida]."

**Regra 4 — Exceções que removem direitos**
Quando um chunk descrever uma exceção (ex: "exceto cargas perigosas", "não elegível"), interprete como: o item da exceção NÃO tem esse direito/prazo. Não assuma que existe um processo alternativo não descrito, a menos que o chunk o mencione explicitamente.

**Regra 5 — Sem informação: escale**
Quando a informação não estiver em nenhum chunk disponível, responda: "Não localizei essa informação na documentação disponível. Recomendo escalar para o supervisor ou contatar a área responsável." Nunca omita esta declaração quando for o caso.

**Regra 6 — Português formal e acessível**
Use linguagem formal, direta e sem jargão não explicado. O atendente deve conseguir repassar a informação ao cliente com confiança.

---

## PRIORIDADE DE FONTES (quando houver conflito)

1. Documentos normativos — versão mais recente (POL-001 v3.1, PROC-042-v2/novembro 2023, SLA-2024.1)
2. Documentos normativos — versão anterior (PROC-042 v1) → SOMENTE para chamados abertos antes de 01/12/2023; sinalize ao atendente
3. FAQ de atendimento → use SOMENTE para orientações operacionais gerais; NUNCA para dados concretos como prazos, valores ou multiplicadores
4. Ausência de qualquer fonte → aplique a Regra 5

Se chunks de versões diferentes do mesmo documento forem fornecidos, use sempre o mais recente e informe ao atendente: "Existem duas versões deste procedimento em circulação. Estou usando a versão mais recente."

---

## FORMATO OBRIGATÓRIO DE RESPOSTA

Use SEMPRE esta estrutura, mesmo que alguma seção fique com "N/A":

**Resposta:** [resposta direta e objetiva — uma ou duas frases]

**Fonte:** [documento, versão e seção — ex: POL-001 v3.1, seção 3.2]

**Próximos passos:** [ação que o atendente deve tomar — ou "N/A" se não aplicável]

**Atenção:** [exceções importantes, conflitos de versão, ou "N/A" se não aplicável]

---

## Exemplo de resposta ideal (use como referência de formato)

Pergunta: "Qual o prazo de devolução?"

**Resposta:** O cliente pode solicitar devolução em até 7 dias úteis após o recebimento confirmado no sistema de tracking. Sábados, domingos e feriados nacionais não são contados.

**Fonte:** POL-001 v3.1, seção 3.1

**Próximos passos:** Oriente o cliente a abrir chamado no portal.novatech.com.br, categoria "Devolução de Mercadoria", com número do CT-e e mínimo 3 fotos.

**Atenção:** Este prazo NÃO se aplica a cargas perigosas (classes 1 a 6 ANTT), cargas refrigeradas com quebra de cadeia de frio, ou cargas com lacre violado. Para esses casos, o processo é diferente — consulte o chunk específico ou escale.

---

## INSTRUÇÕES PARA OS CHUNKS

Os chunks abaixo são os trechos da documentação oficial recuperados para esta consulta específica. Você deve:
- Usar SOMENTE as informações presentes nesses chunks
- Não combinar com conhecimento externo
- Se nenhum chunk responde à pergunta, aplicar Regra 5
- Se chunks conflitarem, aplicar a hierarquia de prioridade acima

[CHUNKS SERÃO INSERIDOS AQUI DINAMICAMENTE]
```

---

## Etapa 6 — Segunda Rodada de Testes

Repetir as mesmas 3 perguntas com o system prompt v2, mantendo os mesmos chunks. Comparar:

| Dimensão | v1 | v2 | Melhora? |
|---|---|---|---|
| Interpretação de exceção (Q1 — carga perigosa) | [resultado do teste] | [resultado do teste] | [S/N] |
| Não-invenção de dados (Q3 — valor base frete) | [resultado do teste] | [resultado do teste] | [S/N] |
| Seguimento do formato estruturado | [resultado do teste] | [resultado do teste] | [S/N] |
| Clareza da escalada quando necessário | [resultado do teste] | [resultado do teste] | [S/N] |

---

## Checklist de Entrega

- [ ] System prompt v1 (texto completo, testável)
- [ ] Mapeamento estático/dinâmico com estimativa de tokens
- [ ] 3 perguntas testadas no Claude com respostas reais
- [ ] Análise crítica por pergunta (correto? citou fonte? respeitou guardrails? onde errou?)
- [ ] System prompt v2 com justificativa de cada mudança
- [ ] 3 perguntas testadas novamente com v2
- [ ] Comparativo v1 vs v2 mostrando melhoria concreta

---

## Notas Técnicas

**Sobre o Chunk A do exercício vs Anexo B:**
O Chunk A fornecido no exercício 1.2 é uma versão simplificada do POL-001-B do Anexo B. O Chunk A diz "exceto cargas perigosas" sem detalhar as classes nem o procedimento alternativo. O Anexo B (Chunk POL-001-B) é mais completo e menciona o ramal 4500. No teste, usar o Chunk A simplificado é intencional — testa se o assistente inventa o ramal (falha) ou declara ausência de informação (acerto).

**Sobre Manaus e a Região Norte:**
Manaus é capital do Amazonas, que pertence à Região Norte. O multiplicador regional para Norte na PROC-042-v2 é 1.8. O fator de peso para 600kg (dentro de 500-1.000kg) é 1.0, mas este dado não está no Chunk C simplificado do exercício — apenas no Anexo B completo. Portanto, a fórmula aplicável com os chunks do teste é: valor base × 1.8. O valor base não está em nenhum dos 3 chunks, então o assistente não pode calcular o valor final e deve declarar isso explicitamente.

**Sobre a ambiguidade PROC-042 v1 vs v2:**
Esta é uma armadilha deliberada do Anexo B. No teste simples com apenas o Chunk C (que é da v2), não há ambiguidade. Mas em produção, se o pipeline de RAG retornar chunks das duas versões simultaneamente, o assistente precisa da Regra de Prioridade de Fontes para resolver corretamente. O system prompt v2 endereça isso explicitamente.
