# Plano de Execução — Exercício 1.1
## Análise de viabilidade técnica com fundamentos de LLM e engenharia de contexto

> **Como usar:** Cole o **Prompt 1** no Claude chat e aguarde a análise completa. Em seguida, cole o **Prompt 2** na mesma conversa para a etapa de revisão crítica. Salve o histórico completo como entregável.

---

## Prompt 1 — Análise Técnica Inicial

```
Você é um arquiteto de soluções de IA especializado em pipelines RAG (Retrieval-Augmented Generation) e engenharia de contexto.

## Contexto do projeto

A DB1 foi contratada pela NovaTech, empresa de logística com 1.200 funcionários, para construir um assistente de IA para o time de atendimento ao cliente (45 pessoas). O objetivo é reduzir o tempo médio de busca por chamado de 12 minutos para menos de 2 minutos. O assistente será integrado ao Microsoft Teams e utilizará Azure AI Services (licenças M365 E3 disponíveis).

## Fontes de documentação a indexar

| Fonte | Conteúdo | Volume |
|-------|----------|--------|
| SharePoint corporativo | Manuais de procedimento, políticas de compliance, normas de segurança de carga | ~800 documentos PDF/Word |
| Confluence (wiki interna) | Conhecimento operacional | ~400 páginas |
| Pasta de rede | Planilhas de SLA e tabelas de frete | ~50 planilhas (atualização mensal) |

## Características técnicas da documentação

- **PDFs do SharePoint:** incluem tabelas complexas com 15+ colunas (ex: tabelas de frete por rota/peso/região), fluxogramas embutidos como imagens (não texto), e documentos escaneados que precisam de OCR
- **Wiki do Confluence:** possui links internos entre páginas e usa macros customizadas do Confluence (não são HTML puro)
- **Planilhas:** contêm fórmulas interdependentes entre células e abas (ex: tabela de SLA com cálculos automáticos de prazo)
- **Risco documentado:** existem documentos com versões conflitantes no SharePoint sem processo de deprecação formal (ex: PROC-042 v1 e PROC-042 v2 coexistem com multiplicadores de frete diferentes). Também existe um FAQ informal do time de atendimento que pode contradizer os documentos normativos.

## Conceito de context engineering aplicado a RAG

O contexto que o LLM recebe a cada pergunta é limitado pela janela de contexto do modelo. A qualidade da resposta depende de:
- **Relevância:** quais chunks são selecionados pelo retrieval
- **Orçamento de atenção:** quantos chunks cabem no contexto disponível
- **Posicionamento:** informação no meio de contextos longos é "esquecida" — o efeito *lost in the middle*
- **Competição:** o que mais está no contexto (system prompt, histórico de conversa, instruções) reduz o espaço para documentação

## Sua tarefa

Produza uma análise técnica formal e estruturada cobrindo os quatro pontos abaixo. Seja específico com números e trade-offs — contextualize cada recomendação para o caso NovaTech, não respostas genéricas.

---

### 1. Análise por tipo de fonte

Para cada um dos quatro tipos de conteúdo, detalhe em formato de tabela ou subseções:
- **Desafio principal** para o pipeline de RAG (extração, chunking ou retrieval)
- **Impacto na qualidade das respostas** se o desafio não for tratado
- **Estratégia de tratamento** recomendada (ferramentas, abordagens, trade-offs)

Tipos a analisar:
1. PDFs com tabelas complexas (15+ colunas)
2. PDFs escaneados (OCR necessário)
3. Wiki Confluence com links internos e macros customizadas
4. Planilhas com fórmulas interdependentes

---

### 2. Estimativa do tamanho da base em tokens

Estime o tamanho total da base de conhecimento em tokens considerando:
- ~800 documentos PDF com média de 10 páginas cada (documentos de procedimento logístico têm texto denso e tabelas; estime uma média razoável de palavras por página)
- ~400 páginas wiki com média de 1.500 palavras cada
- ~50 planilhas (estime volume baseado em contexto de logística: tabelas de SLA, tabelas de frete, ~5 abas por planilha, ~200 células com dados por aba)
- Regra prática: **1 token ≈ 0,75 palavras** (ou seja, 1.000 palavras ≈ 1.333 tokens)

Apresente o cálculo explícito por fonte e o total consolidado.

---

### 3. Análise de orçamento de contexto

Dado que o GPT-4o tem janela de 128.000 tokens e que em cada query o contexto é distribuído assim:
- System prompt + instruções do assistente: ~2.000 tokens
- Resposta gerada pelo modelo: ~1.500 tokens reservados
- Histórico de conversa do atendente (últimas 3 trocas): ~3.000 tokens
- **Restante disponível para chunks de documentação**

Responda:
1. Quantos tokens sobram para injetar documentação por query?
2. Com chunks de ~500 tokens cada, quantos chunks chegam ao LLM em cada pergunta?
3. Que percentual da base total isso representa? O que isso implica para a qualidade do retrieval?
4. Como o limite de chunks por query deve influenciar a estratégia de retrieval (re-ranking, diversidade de fontes, filtragem por data)?

---

### 4. Estratégia de chunking recomendada

Os atendentes da NovaTech farão perguntas como:
- "Qual o prazo para devolução de carga refrigerada?"
- "Como calcular o frete para 800kg com destino à região Norte?"
- "Qual o SLA de resposta para cliente Gold em incidente crítico?"
- "O cliente pode devolver carga perigosa?"
- "Qual a diferença entre os multiplicadores de frete da PROC-042 v1 e v2?"

Recomende uma estratégia de chunking que:
1. Justifique o tamanho ideal de chunk considerando o tipo de pergunta (perguntas factuais pontuais vs. perguntas que exigem entender um fluxo completo)
2. Aborde o efeito *lost in the middle* e como posicionar os chunks mais relevantes para mitigá-lo
3. Proponha como lidar com documentos de versões conflitantes no contexto do sistema RAG (metadados, filtragem, apresentação ao atendente)
4. Avalie se diferentes tipos de fonte precisam de estratégias de chunking diferentes (ex: chunking de tabela vs. chunking de texto narrativo)
```

---

## Prompt 2 — Revisão Crítica (usar na mesma conversa, após o Prompt 1)

```
Agora revise a análise técnica que você produziu acima com olhar crítico e adversarial. Seu papel agora é encontrar os problemas, não validar o que foi escrito.

Identifique e detalhe:

### 1. Pontos fracos ou lacunas técnicas
Aspectos do pipeline RAG que a análise não cobriu ou cobriu de forma superficial. Existe algo crítico para a implementação que ficou de fora?

### 2. Estimativas otimistas demais
Onde os números ou projeções assumem um cenário favorável que provavelmente não se realizará? Considere:
- Qualidade real de PDFs corporativos (vs. PDFs limpos usados em benchmarks)
- Taxa de sucesso de OCR em documentos escaneados de qualidade variada
- Cobertura real do retrieval com o orçamento de chunks calculado

### 3. Riscos específicos do contexto NovaTech não considerados
- O FAQ informal do time de atendimento contradiz os documentos normativos — como o RAG lida com isso?
- As planilhas são atualizadas mensalmente — como manter o índice sincronizado sem degradar a qualidade?
- Documentos com versões conflitantes (PROC-042 v1/v2) sem deprecação formal — qual o risco real para o atendente?
- 3 áreas distintas atualizam documentação sem processo unificado — como isso afeta a confiabilidade do sistema ao longo do tempo?

### 4. Omissões de implementação
Componentes que precisarão ser construídos mas não foram mencionados na análise (ex: pipeline de atualização incremental, monitoramento de drift, mecanismo de feedback do atendente, tratamento de alucinação).

Para cada ponto identificado, indique como a análise original deveria ser ajustada ou ampliada.
```

---

## Estrutura do Entregável Final

Após executar os dois prompts, organize o entregável `1.1/analise-tecnica.md` com:

1. **Análise técnica final** — versão consolidada incorporando o feedback do Prompt 2
2. **Histórico de iteração** — prints ou cópia do chat mostrando a evolução da análise (Prompt 1 → revisão crítica → versão final)
