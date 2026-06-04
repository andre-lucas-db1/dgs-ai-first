# Análise Técnica de Viabilidade — Pipeline RAG NovaTech

**Projeto:** Assistente de IA para Atendimento ao Cliente
**Elaborado por:** Arquitetura de Soluções DB1
**Data:** 2026-06-04
**Versão:** 2.0 — revisada após revisão crítica adversarial

---

## 1. Análise por Tipo de Fonte

---

### 1.1 PDFs com Tabelas Complexas (15+ colunas)

**Desafio principal — Extração e representação estrutural**

Parsers de PDF convencionais (PyPDF2, pdfminer) serializam tabelas como texto linear sem estrutura. Uma tabela de frete com colunas *Região | Faixa de peso | Tarifa base | Multiplicador | Fator expresso | Adicional ANTT | ...* se transforma em fluxo de números sem contexto de coluna.

**Impacto se não tratado**

O modelo associa valores incorretamente e gera cálculos errados. O FAQ de atendimento item 8 documenta esse risco na prática: a coexistência de multiplicadores diferentes entre PROC-042 v1 e v2 já causa confusão humana — um parsing deficiente de tabelas amplifica o problema ao escala.

**Estratégia de tratamento**

| Etapa | Abordagem | Ferramenta |
|-------|-----------|-----------|
| Extração | Azure AI Document Intelligence — preserva estrutura de tabelas como Markdown/JSON | Azure AI Services (M365 E3) |
| Chunking tabela pequena (≤600 tokens) | Tabela inteira como chunk único | — |
| Chunking tabela grande (>600 tokens) | Uma linha = um chunk com cabeçalhos embutidos: `"Frete especial | Região: Norte | Peso: 500–1.000kg | Multiplicador: 1,8 | Fator de peso: 1,0"` | Pipeline customizado |

**Atenção — fluxogramas embutidos como imagens:** PDFs de procedimento logístico frequentemente contêm fluxogramas de decisão embutidos como imagem (ex.: "se carga perigosa → Gestão de Riscos; se prazo > 7 dias → Comercial"). Esses elementos são **invisíveis** para extratores de texto. Estratégia: Azure AI Document Intelligence tem capacidade de Figure Analysis para OCR em imagens dentro de PDFs. Para fluxogramas complexos onde a lógica condicional é crítica (compliance, segurança de carga), anotar manualmente como metadado descritivo antes de indexar.

**Documentos Word (.docx):** O SharePoint contém PDFs *e* Word. Documentos Word têm desafios específicos: controle de revisão com texto tachado pode ser extraído como conteúdo válido; estrutura de Heading 1/2/3 baseada em estilos não é preservada por parsers ingênuos. Usar python-docx ou Azure AI Document Intelligence com mapeamento explícito de estilos para chunking semântico correto.

---

### 1.2 PDFs Escaneados (OCR necessário)

**Desafio principal — Ausência de texto extraível**

Documentos escaneados são imagens rasterizadas — sem OCR, são completamente invisíveis para o pipeline. Com OCR de qualidade ruim, erros corrompem a semântica: *"Nordeste"* vira *"N0rdeste"*, *"1.500 kg"* vira *"l 500 kg"*.

**Impacto se não tratado**

Documentos de compliance e normas ANTT podem ser os mais antigos e, portanto, mais provavelmente escaneados. A ausência deles no índice significa que perguntas sobre segurança de carga e regulações são respondidas com base apenas em documentação incompleta.

**Estratégia de tratamento**

1. **Detecção automática:** PyMuPDF identifica PDFs sem camada de texto
2. **OCR com confiança:** Azure AI Document Intelligence retorna score de confiança por palavra
3. **Threshold realista:** planejar para 20-35% dos documentos escaneados necessitando revisão humana — documentos corporativos arquivados frequentemente são fotocopiados de fotocopiados, com qualidade OCR degradada. O threshold de aceitação automática deve ser ≥0,90 para documentos críticos (compliance, ANTT), não 0,85 como estimativas otimistas sugerem
4. **Fila de revisão:** documentos abaixo do threshold entram em fila de revisão humana antes de ser indexados
5. **Metadado de qualidade:** `source_quality: ocr`, `ocr_confidence: float`, `reviewed_by_human: bool`

---

### 1.3 Wiki Confluence com Links Internos e Macros Customizadas

**Desafio principal — Fragmentação semântica e conteúdo não-renderizado**

**Problema A — Macros:** exportação padrão deixa macros como texto bruto (`{include:PROC-042}` → `[include:PROC-042]`). A informação incorporada fica ausente.

**Problema B — Links internos:** páginas que referenciam outras perdem o conteúdo referenciado ao serem indexadas isoladamente.

**Impacto se não tratado**

Respostas incompletas sistêmicas. O LLM recebe chunks que citam informação sem incluí-la, e precisa ou alucinar o conteúdo ou declarar que não sabe.

**Estratégia de tratamento**

| Problema | Solução |
|----------|---------|
| Macros | Confluence REST API (`/rest/api/content/{id}?expand=body.view`) — HTML renderizado com macros resolvidas |
| Links internos | Ao indexar página A que linka página B: incluir título + primeiro parágrafo de B como metadata `related_content` de A |
| Hierarquia | Preservar `space_key`, `parent_page`, `page_title` para filtragem por área (Operações, Compliance, Comercial) |

---

### 1.4 Planilhas com Fórmulas Interdependentes

**Desafio principal — Conhecimento computado, não declarado**

O conhecimento da planilha está no **resultado** das fórmulas. `=VLOOKUP(A1,FreightTable,3,FALSE)*HLOOKUP(B1,RegionalMultipliers,2,FALSE)` é inútil para um LLM. Planilhas atualizadas mensalmente criam adicionalmente um problema de sincronização do índice.

**Impacto se não tratado**

Planilhas de SLA e frete tornam-se inutilizáveis. Um atendente perguntando *"Qual o SLA de resolução para Silver?"* recebe uma fórmula ao invés de *"48 horas úteis"*.

**Estratégia de tratamento**

1. **Exportação com valores calculados:** Microsoft Graph API (M365 E3) lê valores calculados, não fórmulas
2. **Conversão para linguagem natural estruturada:** cada linha → sentença: `"Tier Silver | Resposta geral: 4h úteis | Resolução geral: 48h úteis | Resposta incidente crítico: 1h | Resolução incidente crítico: 8h"`
3. **Re-indexação mensal:** SharePoint webhooks acionam re-extração na modificação do arquivo — mas webhooks podem falhar silenciosamente; um job de reconciliação periódico (semanal) é necessário como garantia adicional
4. **Metadado de versão:** `data_extracao`, `versao_planilha` em cada chunk

---

## 2. Estimativa do Tamanho da Base em Tokens

### Cálculo por fonte

**PDFs do SharePoint — estimativa conservadora (revisada)**

PDFs corporativos de logística contêm páginas de capa (~50-80 palavras), páginas de tabela (~100-150 palavras serializadas), fluxogramas como imagem (zero texto), e headers/footers/watermarks como ruído. A estimativa inicial de 250 palavras/página foi otimista. Estimativa revisada: **165 palavras/página** em média.

```
800 documentos × 10 páginas = 8.000 páginas
8.000 páginas × 165 palavras = 1.320.000 palavras
1.320.000 ÷ 0,75 = 1.760.000 tokens
```

**Wiki Confluence**

```
400 páginas × 1.500 palavras = 600.000 palavras
600.000 ÷ 0,75 = 800.000 tokens
```

**Planilhas — estimativa revisada**

Planilhas de logística são densas em números mas esparsas em texto. Examinando documentos reais (SLA-2024 tem ~400 palavras de dados; PROC-042 v1 tem tabela com 5 linhas × 2 colunas). Estimativa revisada: 50 planilhas × 3 abas × 50 linhas com dados × 15 palavras/linha.

```
50 × 3 × 50 × 15 = 112.500 palavras
112.500 ÷ 0,75 = 150.000 tokens
```

### Consolidado (estimativas conservadoras)

| Fonte | Palavras estimadas | Tokens estimados | Premissa |
|-------|-------------------|-----------------|----------|
| PDFs SharePoint | 1.320.000 | **~1.760.000** | 165 palavras/página |
| Wiki Confluence | 600.000 | **~800.000** | 1.500 palavras/página |
| Planilhas | 112.500 | **~150.000** | 50 linhas × 15 palavras/aba |
| **Total** | **2.032.500** | **~2.710.000** | — |

**A base completa estimada é de aproximadamente 2,7 milhões de tokens** (~5.420 chunks de 500 tokens).

> **Nota sobre precisão:** Estimativas de tokens para documentação corporativa têm incerteza de ±30-40%. Uma análise amostral de 20-30 documentos reais antes do início da ingestão reduziria essa incerteza e permitiria planejar a capacidade do vector store com maior precisão.

---

## 3. Análise de Orçamento de Contexto

### Partição da janela de 128.000 tokens por query

| Componente | Tokens consumidos | Justificativa |
|------------|------------------|---------------|
| System prompt + instruções | ~2.000 | Persona, regras de citação, tom, restrições |
| Resposta gerada | ~1.500 reservados | 2-3 parágrafos de resposta de atendimento |
| Histórico de conversa (3 trocas) | ~3.000 | Necessário para perguntas de follow-up |
| **Disponível para chunks** | **~121.500** | 128.000 − 6.500 |

**Atenção — degradação em conversas longas:** para chamados complexos com 6-8 trocas, o histórico pode consumir 6.000-8.000 tokens, reduzindo o espaço para documentação em 4-5%. O sistema deve implementar compressão ou truncagem do histórico para chamados longos.

### Capacidade de chunks por query

```
121.500 tokens disponíveis ÷ 500 tokens/chunk = 243 chunks (capacidade máxima)
```

### Cobertura da base

```
Total estimado de chunks: 2.710.000 ÷ 500 = ~5.420 chunks
Capacidade máxima por query: 243 chunks
Cobertura máxima por query: 243 / 5.420 = ~4,5%
```

**O LLM pode enxergar no máximo ~4,5% da base em cada pergunta.** Mas injetar todos os 243 slots disponíveis é contraproducente — o efeito *lost in the middle* cresce com o volume de contexto irrelevante. Na prática, o número ideal de chunks por query é muito menor (ver Seção 4).

### Implicações para a estratégia de retrieval

**Retrieval de dois estágios (obrigatório)**
- Estágio 1 — Recall amplo: top-50 a top-100 candidatos por similaridade semântica (Azure AI Search, vector + BM25 hybrid)
- Estágio 2 — Re-ranking por relevância: cross-encoder ordena os candidatos antes de injetar no contexto

**Filtros de metadados pré-retrieval**
Para documentos versionados, filtrar `status: active` antes da busca vetorial evita que chunks obsoletos ocupem slots.

**Cobertura insuficiente para perguntas multi-fonte**
Perguntas que exigem síntese de múltiplos documentos (*"Como calcular frete de carga perigosa acima de 5.000kg para o Norte, incluindo seguro?"* — envolve PROC-042, PROC-043, FAQ item 22) têm risco de cobertura superior ao das perguntas factuais simples. O retrieval precisa acertar na intersecção de múltiplos documentos simultaneamente, e a probabilidade de falha cresce com o número de fontes necessárias.

**Atenção — latência arquitetural**
A cadeia retrieval de dois estágios + chamada ao GPT-4o acumula latência estimada de 4-10 segundos por query:
- Vector search (Azure AI Search): ~100-300ms
- Re-ranking (cross-encoder, top-50): ~500-1.500ms
- Chamada GPT-4o: ~3.000-8.000ms

Para um atendente com cliente na linha, 10 segundos é limiar de aceitabilidade. Estratégias de mitigação: cache de respostas para perguntas frequentes, warm-up de modelos, streaming da resposta (exibir ao atendente conforme gerada).

---

## 4. Estratégia de Chunking Recomendada

### Perfil das perguntas dos atendentes NovaTech

| Tipo | Exemplos | Fontes necessárias |
|------|----------|--------------------|
| **Factual pontual** | "Qual o prazo de devolução?", "Qual o SLA Gold para incidente crítico?" | 1 documento, 1-2 chunks |
| **Procedimental** | "Como calcular o frete para 800kg Norte?", "Como abrir chamado de devolução?" | 1 documento, 3-8 chunks sequenciais |
| **Multi-fonte** | "Como calcular frete de carga perigosa com seguro?" | 2-3 documentos, risco de cobertura elevado |
| **Comparativa** | "Qual a diferença entre PROC-042 v1 e v2?" | 2 documentos simultâneos |

### Tamanho de chunk por tipo de conteúdo

| Tipo de conteúdo | Tamanho recomendado | Justificativa |
|-----------------|--------------------|-|
| Texto normativo (POL, PROC) | 300–400 tokens | Abrange 1 seção completa — captura regra + exceções em unidade coesa |
| Tabelas (linhas individuais) | 40–80 tokens/linha | Cada linha auto-contida com cabeçalhos embutidos — retrieval cirúrgico |
| Tabelas pequenas (≤600 tokens) | Tabela inteira | SLA-2024 (3 tiers × 7 métricas): preservar a tabela inteira é superior ao chunking por linha |
| Wiki (por seção H2) | 300–500 tokens | Seções são tipicamente auto-contidas; links viram metadados |
| Planilhas (por linha convertida) | 50–100 tokens | Sentença estruturada com todos os atributos da linha |

**Overlap:** 10-15% entre chunks contíguos de texto normativo. Não aplicável a chunks de tabela (auto-contidos).

### Mitigação do efeito *Lost in the Middle*

**Estratégia de posicionamento:**
1. Chunks com maior score de re-ranking → **primeiras posições** do contexto
2. Para procedimentos sequenciais → chunks do mesmo documento **contíguos e no início**
3. Chunks complementares (FAQ, contexto adicional) → **final** do contexto

**Estratégia de volume dinâmico:**

| Tipo de pergunta | Chunks injetados | Critério |
|-----------------|-----------------|---------|
| Factual pontual | 5-10 | Score de re-ranking alto + 1 documento |
| Procedimental | 10-20 | Sequência completa do procedimento |
| Multi-fonte | 15-30 | Múltiplos documentos, re-ranking por diversidade |

Injetar 243 slots (capacidade máxima) para uma pergunta factual simples cria mais ruído competindo por atenção do que informação útil.

### Tratamento de documentos com versões conflitantes

O caso PROC-042 documenta diferenças materiais entre versões:

| Parâmetro | v1 (mar/2023) | v2 (nov/2023) | Diferença |
|-----------|--------------|--------------|-----------|
| Multiplicador Norte | 1,6 | 1,8 | +12,5% |
| Multiplicador Sul | 1,2 | 1,3 | +8,3% |
| Fator de peso 1.001–3.000kg | 1,2 | 1,15 | −4,2% |
| Prazo adicional | +2 dias | +3 dias | +50% |
| Desconto volume | >10 fretes/mês (Comercial) | 8+ fretes: 5% automático | Critério diferente |

**Metadados obrigatórios por chunk:**
```
document_id:    "PROC-042"
version:        "1.0" | "2.0"
effective_date: "2023-03-03" | "2023-11-10"
status:         "active" | "superseded" | "disputed"
superseded_by:  "PROC-042-v2"   # apenas para v1
```

**Comportamento do sistema:**
- Filtragem padrão: apenas chunks com `status: active`
- Quando versões conflitantes detectadas: superficiar ambas com labels explícitos, incluindo aviso ao atendente
- Exemplo de resposta: *"Atenção: existem duas versões ativas da PROC-042. Esta resposta usa v2 (nov/2023). Se o contrato do cliente é anterior a dez/2023, verifique a versão anterior."*

> **Recomendação crítica de governança — pré-condição de go-live:** A coexistência de PROC-042 v1 e v2 sem deprecação formal não é um problema que metadados ou UI resolvem adequadamente. Com 320 chamados/dia e ~60% exigindo consulta documental, mesmo 5% dos chamados envolvendo frete especial gera ~10 cotações/dia com risco de valor incorreto. A NovaTech deve formalizar qual versão está vigente e marcar a outra como `superseded` **antes** do go-live do assistente. Este é um pré-requisito de projeto, não uma melhoria futura.

### Tratamento do FAQ informal

O FAQ de atendimento deve ser tratado diferentemente dos documentos normativos:
- **Não indexar** o FAQ como fonte primária de retrieval
- **Usar o FAQ** como mapa de gaps documentais: cada item do FAQ sem correspondência normativa identificável deve gerar um alerta para o Tech Lead da NovaTech documentar formalmente aquele conhecimento (ex: item 22 sobre percentuais de seguro de carga — não localizado em nenhum documento normativo disponível)
- Para itens onde o FAQ fornece orientação prática correta que os normativos omitem (ex: item 8 sobre contratos na tabela antiga), garantir que o normativo seja atualizado para cobrir esse caso antes do go-live

### Estratégias diferenciadas por tipo de fonte (síntese)

| Fonte | Estratégia de chunking | Tamanho | Overlap |
|-------|----------------------|---------|---------|
| Texto normativo (POL, PROC) | Por seção H2/H3 | 300–400 tokens | 50 tokens |
| Tabelas de frete/SLA | Por linha com cabeçalhos embutidos | 50–80 tokens/linha | Nenhum |
| Wiki Confluence | Por seção H2 com metadados de links | 300–500 tokens | 30 tokens |
| Planilhas | Por linha convertida para linguagem natural | 50–100 tokens/linha | Nenhum |
| FAQ informal | Não indexado como fonte de retrieval — usado para mapear gaps documentais | — | — |

---

## 5. Componentes de Implementação Adicionais (Omissões da v1)

---

### 5.1 Modelo de Embedding para Português Técnico

A escolha do modelo de embedding não é um detalhe — é uma decisão arquitetural que afeta todo o pipeline. Jargão logístico brasileiro (CT-e, ANTT, SLA Gold/Silver, "conhecimento de transporte eletrônico") pode não ter representação vetorial adequada em modelos treinados predominantemente em inglês.

**Recomendação:** avaliar empiricamente antes de escolher. Criar um gold dataset de 50-100 pares pergunta/chunk-resposta derivados dos documentos reais e medir Recall@5 e Recall@10 para:
- `text-embedding-ada-002` (OpenAI/Azure)
- `multilingual-e5-large` (Microsoft)
- `text-embedding-3-large` (OpenAI)

O modelo com maior recall nos dados reais da NovaTech é o correto, independentemente de benchmarks genéricos.

### 5.2 Processamento da Query de Entrada

A análise anterior focou no processamento de documentos e ignorou o processamento da query. Para RAG, a query *"frete 800kg norte"* tem embedding semanticamente distante do chunk que a responde (*"Para cargas de 500kg a 1.000kg na região Norte, o multiplicador regional é 1,8"*). Técnicas para mitigar essa assimetria:

- **Query expansion:** enriquecer a query com sinônimos e termos do domínio antes de buscar
- **HyDE (Hypothetical Document Embeddings):** gerar um documento hipotético que responderia à pergunta e usar seu embedding para busca — reduz a assimetria query/documento
- **Query classification:** identificar se a query é factual, procedimental, comparativa ou de escalada para ajustar a estratégia de retrieval dinamicamente

### 5.3 Framework de Avaliação e Critérios de Go-Live

Sem avaliação sistemática, não há como saber se o sistema cumpre a meta de negócio (< 2 minutos por chamado) antes do go-live.

**Gold dataset:** criar 80-120 pares {pergunta, resposta esperada, documento fonte} cobrindo:
- 30% perguntas factuais pontuais (SLA, prazos)
- 40% perguntas procedimentais (cálculo de frete, abertura de chamado)
- 20% casos de versões conflitantes (PROC-042)
- 10% perguntas sem resposta nos documentos (para testar comportamento de "não sei")

**Métricas mínimas para go-live:**
- Recall@5 ≥ 0,75 (chunk relevante nos top-5 em 75% das perguntas)
- Faithfulness ≥ 0,85 (respostas grounded nos chunks injetados, sem alucinação)
- Latência P95 ≤ 8 segundos

### 5.4 Mecanismo de Detecção de Alucinação

Para o domínio NovaTech, alucinações têm características detectáveis: valores numéricos citados na resposta (multiplicadores de frete, prazos de SLA, percentuais) que não aparecem em nenhum dos chunks injetados.

Verificação de grounding: após geração da resposta, extrair entidades numéricas e verificar sua presença literal nos chunks injetados. Respostas com entidades não-groundadas devem ser sinalizadas como "baixa confiança" antes de ser exibidas ao atendente.

### 5.5 Mecanismo de Escalada para Conhecimento Tribal

O atual estado da NovaTech resolve conflitos documentais *"perguntando para quem sabe"*. Parte desse conhecimento não está documentado e, portanto, não será indexado. O assistente não deve silenciar nesse caso — deve ter comportamento explícito:

- **"Não encontrei"** ≠ **"A resposta é não"**: quando o retrieval não encontra informação relevante com confiança suficiente, o sistema exibe: *"Não encontrei informação sobre isso na documentação indexada. Para este tipo de questão, contate: [área responsável / ramal]."*
- Manter mapeamento de domínio → área responsável (Operações: PROCs de frete; Compliance: normas ANTT; Comercial: SLA e contratos) para direcionar escaladas

### 5.6 Governança Documental Contínua

Com 3 áreas (Operações, Compliance, Comercial) atualizando documentação independentemente, a qualidade do índice se degrada com o tempo sem processo de governança. Recomendações:

1. **Notificação cruzada:** ao publicar documento que afeta domínio de outra área, notificar as áreas impactadas
2. **Revisão de consistência semestral:** job automatizado que detecta documentos com metadados conflitantes no mesmo domínio (mesmo `document_id`, status não definido)
3. **Ownership explícito:** cada documento indexado deve ter `owner_area` nos metadados para direcionar alertas de inconsistência

---

## 6. Histórico de Iteração

### v1 (análise inicial)
- Cobriu os 4 tipos de fonte com desafios, impactos e estratégias
- Estimou base em ~4 milhões de tokens
- Calculou capacidade de 243 chunks/query e cobertura de 3%
- Propôs estratégia de chunking diferenciada por tipo de conteúdo

### Revisão crítica identificou:
1. **Lacunas técnicas:** fluxogramas como imagens sem estratégia; documentos Word ignorados; modelo de embedding não especificado; processamento de query ausente; vector store não especificado; framework de avaliação ausente
2. **Estimativas otimistas:** 250 palavras/página corrigido para 165 (−34%); planilhas corrigidas de 600K para 150K tokens (−75%); threshold OCR de 0,85 revisado para ≥0,90 com 20-35% necessitando revisão humana
3. **Riscos NovaTech subestimados:** FAQ como fonte de retrieval cria risco de respostas não-normativas; PROC-042 v1/v2 é risco contratual que deve ser pré-condição de go-live, não ajuste de metadado; conhecimento tribal não documentado cria "buracos negros" silenciosos no sistema
4. **Omissões de implementação:** latência arquitetural (4-10s por query), detecção de alucinação, escalada para conhecimento tribal, governança documental contínua, mecanismo de feedback

### v2 (análise final)
- Incorporou todas as revisões acima
- Estimativa de base revisada para ~2,7 milhões de tokens
- Adicionadas Seções 5.1-5.6 com componentes omitidos
- Reposicionado FAQ como detector de gaps documentais
- Incluída recomendação crítica: resolução do PROC-042 v1/v2 como pré-condição de go-live
