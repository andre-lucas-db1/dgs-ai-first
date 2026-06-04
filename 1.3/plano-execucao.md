# Plano de Execução — Exercício 1.3: Pipeline de RAG open-source

## Visão geral

Construir um pipeline de RAG mínimo em Python, usando ChromaDB + sentence-transformers, que ingira os 5 documentos da NovaTech, busque por similaridade semântica e monte prompts prontos para envio ao Claude.

---

## Estrutura de arquivos

```
1.3/
├── docs/                          ← cópia dos 5 docs (Anexo A)
│   ├── POL-001-politica-devolucao.md
│   ├── PROC-042-frete-especial-v1.md
│   ├── PROC-042-v2-frete-especial-revisado.md
│   ├── SLA-2024-tabela-sla-clientes.md
│   └── FAQ-atendimento.md
├── ingest.py                      ← Step 1: chunking + embeddings + ChromaDB
├── search.py                      ← Step 2: busca por similaridade
├── prompt_builder.py              ← Step 3: montagem do prompt final
├── test_pipeline.py               ← Step 4: 5 testes documentados
├── chroma_db/                     ← banco vetorial local (gerado em runtime)
└── resultados-testes.md           ← análise dos 5 testes
```

---

## Dependências

```bash
pip install chromadb sentence-transformers
```

> Sem LangChain: o pipeline será orquestrado manualmente para manter o código simples e legível. LangChain seria overhead desnecessário para um POC com 5 documentos.

---

## Estratégia de chunking (justificada)

**Abordagem: chunking estrutural por seção Markdown (header-based)**

Os documentos da NovaTech são markdowns com hierarquia clara de `##` e `###`. Cada seção carrega uma unidade semântica completa (ex: "3.1 Prazo geral", "2.1 Multiplicadores regionais"). Cortar em tamanho fixo (512 tokens) quebraria tabelas de multiplicadores ou listas de requisitos no meio, perdendo coesão.

**Regras de chunking:**
- Dividir em blocos delimitados por headers `##` ou `###`
- Preservar o header dentro do chunk (contexto de onde a informação está)
- Incluir metadados: `source` (nome do arquivo), `section` (header), `doc_id` (ex: `POL-001`)
- Chunks muito pequenos (< 50 chars de conteúdo) são descartados
- Sem sobreposição (overlap): as seções já são unidades coesas; overlap artificial introduziria ruído

**Por que NÃO usar tamanho fixo:**
A tabela de multiplicadores regionais do PROC-042 tem 7 linhas. Um corte em 512 tokens poderia incluir apenas metade da tabela num chunk e a outra metade em outro, gerando recuperação parcial e resposta errada sobre "multiplicador para o Nordeste".

---

## Etapa 1 — `ingest.py`

### Prompt para GitHub Copilot

```
# Contexto: Pipeline de RAG para documentação interna da NovaTech (logística).
# Objetivo: ingestão de documentos markdown no ChromaDB com embeddings open-source.
#
# Requisitos:
# - Ler os arquivos .md da pasta ./docs/
# - Fazer chunking por seção markdown (dividir em blocos delimitados por headers ## ou ###)
# - Incluir no chunk: texto da seção + o header como prefixo
# - Metadados de cada chunk: source (nome do arquivo sem extensão), section (texto do header), doc_id (prefixo do arquivo ex: POL-001)
# - Usar sentence-transformers com modelo "all-MiniLM-L6-v2" para gerar embeddings
# - Armazenar no ChromaDB (persistido em ./chroma_db/)
# - Coleção chamada "novatech_docs"
# - Imprimir quantos chunks foram gerados por arquivo
# - Não usar LangChain — implementar manualmente
#
# Implemente a função chunk_markdown(text, source) que retorna lista de dicts com
# {id, text, metadata} e a função ingest_all() que processa todos os arquivos.
```

### Lógica esperada (pseudocódigo)

```python
def chunk_markdown(text: str, source: str) -> list[dict]:
    # dividir por linhas que começam com ## ou ###
    # para cada bloco: id = f"{doc_id}-{índice}", text = header + conteúdo, metadata = {...}

def ingest_all():
    # para cada .md em ./docs/
    # chamar chunk_markdown()
    # gerar embeddings em batch com SentenceTransformer
    # adicionar ao ChromaDB com chroma_collection.add()
```

---

## Etapa 2 — `search.py`

### Prompt para GitHub Copilot

```
# Contexto: Pipeline de RAG da NovaTech — módulo de busca vetorial.
#
# Requisitos:
# - Receber uma pergunta (string) como input
# - Gerar embedding da pergunta com sentence-transformers ("all-MiniLM-L6-v2")
# - Buscar os N chunks mais similares no ChromaDB (coleção "novatech_docs", pasta ./chroma_db/)
# - Retornar lista de dicts com: chunk_id, text, score (distância), source, section
# - N padrão = 3, configurável por parâmetro
# - Imprimir os resultados formatados (chunk_id, score, primeiros 200 chars do texto)
# - Função principal: search(query: str, n_results: int = 3) -> list[dict]
# - Não usar LangChain
#
# Nota: ChromaDB retorna distância (quanto menor, mais similar). Converter para
# score de similaridade: similarity = 1 - distance (para distância L2 normalizada).
```

---

## Etapa 3 — `prompt_builder.py`

### Prompt para GitHub Copilot

```
# Contexto: Pipeline de RAG da NovaTech — montagem do prompt para o LLM.
#
# Requisitos:
# - Receber: pergunta (str) + lista de chunks recuperados (list[dict] com text, source, section, score)
# - Montar um prompt completo com:
#   1. System prompt: papel do assistente, regras de citação de fonte, guardrails
#   2. Contexto: blocos formatados de cada chunk (com fonte e seção)
#   3. Pergunta do atendente
# - Retornar: string completa do prompt pronta para copiar e colar no Claude
# - Função: build_prompt(query: str, chunks: list[dict]) -> str
#
# Regras do system prompt que DEVEM estar presentes:
# - "Você é um assistente de atendimento da NovaTech. Responda apenas com base nos documentos fornecidos."
# - "Cite sempre a fonte (nome do documento e seção) ao final de cada afirmação relevante."
# - "Se a informação não estiver nos documentos fornecidos, diga explicitamente que não encontrou."
# - "Não invente informações. Em caso de documentos contraditórios, indique a contradição."
# - Idioma: português brasileiro
```

### Template do prompt montado

```
=== SYSTEM ===
Você é um assistente de atendimento interno da NovaTech, empresa de logística.
Responda apenas com base nos documentos fornecidos abaixo. Não utilize conhecimento externo.
Cite sempre a fonte (nome do documento e seção) ao final de cada afirmação relevante.
Se a informação não estiver presente nos documentos, responda: "Não encontrei essa informação na documentação disponível."
Em caso de documentos com informações contraditórias, aponte a contradição explicitamente e indique qual versão é mais recente.
Idioma: português brasileiro.

=== CONTEXTO — DOCUMENTOS RECUPERADOS ===

[Chunk 1 — Fonte: {source}, Seção: {section} | Score: {score:.3f}]
{text}

[Chunk 2 — Fonte: {source}, Seção: {section} | Score: {score:.3f}]
{text}

...

=== PERGUNTA DO ATENDENTE ===
{query}
```

---

## Etapa 4 — Testes com 5 perguntas

### Prompt para GitHub Copilot (`test_pipeline.py`)

```
# Contexto: Pipeline de RAG da NovaTech — script de testes documentados.
#
# Requisitos:
# - Importar search() de search.py e build_prompt() de prompt_builder.py
# - Executar 5 perguntas de teste (ver lista abaixo)
# - Para cada pergunta, imprimir:
#   1. A pergunta
#   2. Os chunks recuperados (id, source, section, score)
#   3. Os chunks ESPERADOS (gabarito do Anexo B)
#   4. Avaliação: quais chunks corretos foram recuperados, quais estão faltando
#   5. O prompt completo montado
# - Salvar resultado completo em resultados-testes.md
#
# Perguntas de teste:
PERGUNTAS = [
    {
        "query": "Qual o prazo de devolução de mercadorias?",
        "chunks_esperados": ["POL-001-A", "POL-001-B"],
        "observacao": "Deve recuperar prazo (7 dias úteis) e exceções"
    },
    {
        "query": "Posso devolver carga perigosa?",
        "chunks_esperados": ["POL-001-B"],
        "chunks_secundarios": ["FAQ-03", "POL-001-A"],
        "observacao": "Deve recuperar a seção de exceções. Armadilha: FAQ-03 pode inverter a regra"
    },
    {
        "query": "Qual o SLA para cliente Gold em incidente crítico?",
        "chunks_esperados": ["SLA-2024-C"],
        "chunks_secundarios": ["SLA-2024-B", "SLA-2024-A"],
        "observacao": "Deve recuperar tabela de incidentes críticos especificamente"
    },
    {
        "query": "Quanto custa o frete especial para 600kg com destino a Manaus?",
        "chunks_esperados": ["PROC-042v2-A", "PROC-042v2-B"],
        "chunks_secundarios": ["PROC-042-B"],
        "observacao": "Armadilha: pipeline pode recuperar PROC-042-B (v1, Norte=1.6) junto com v2 (Norte=1.8), gerando contradição"
    },
    {
        "query": "Qual o multiplicador regional para o Sudeste no frete especial?",
        "chunks_esperados": ["PROC-042v2-B"],
        "chunks_secundarios": ["PROC-042-B"],
        "observacao": "Armadilha clássica: v1 diz 1.0, v2 diz 1.1. Se ambos forem recuperados, há contradição"
    },
]
```

---

## Gabarito dos 5 testes (para comparação manual)

| # | Pergunta | Chunks esperados | Risco principal |
|---|----------|-----------------|-----------------|
| 1 | Prazo de devolução | POL-001-A, POL-001-B | Pode não recuperar POL-001-B (exceções) |
| 2 | Devolução de carga perigosa | POL-001-B | FAQ-03 pode inverter a regra ("diga que é possível") |
| 3 | SLA Gold em incidente crítico | SLA-2024-C | Pode recuperar SLA-2024-B (chamados gerais) em vez de críticos |
| 4 | Frete 600kg para Manaus | PROC-042v2-A, PROC-042v2-B | PROC-042-B (v1) com multiplicador diferente no mesmo resultado |
| 5 | Multiplicador Sudeste | PROC-042v2-B | Contradição v1 (1.0) vs v2 (1.1) se ambos recuperados |

---

## Etapa 5 — Prompt para Claude (copiar após rodar test_pipeline.py)

Após rodar o script, copiar o prompt gerado para cada pergunta e colar no Claude.

**Avaliação da resposta:** verificar se:
- [ ] A resposta está correta (bate com os documentos)
- [ ] A fonte foi citada (nome do documento + seção)
- [ ] Contradições foram sinalizadas (ex: PROC-042 v1 vs v2)
- [ ] Ausência de informação foi declarada (não alucinação)
- [ ] Guardrails foram respeitados (não inventou tiers, não ignorou exceções)

---

## Problemas antecipados e propostas de correção

### Problema 1 — Versões conflitantes do PROC-042 recuperadas juntas

**Descrição:** O pipeline retorna chunks de PROC-042-v1 e PROC-042-v2 para perguntas sobre frete especial. Os multiplicadores são diferentes (ex: Sudeste: 1.0 na v1 vs 1.1 na v2). O LLM pode misturar os valores ou escolher um arbitrariamente sem alertar o atendente.

**Evidência:** Pergunta "Qual o multiplicador para o Sudeste?" retorna PROC-042-B (score alto por similaridade de conteúdo) junto com PROC-042v2-B. O system prompt orienta a indicar contradição, mas isso depende do LLM reconhecer que são versões do mesmo documento.

**Proposta de correção:**
1. **Metadado de versão:** adicionar `{"version": "v1", "superseded_by": "PROC-042-v2"}` no metadado do PROC-042-v1 e, no prompt, incluir instrução: "Se dois chunks forem da mesma PROC com versões diferentes, use apenas o de versão maior e alerte o atendente."
2. **Filtro pós-recuperação:** após buscar N chunks, aplicar lógica de deduplicação de documentos: se PROC-042-v1 e PROC-042-v2 estiverem ambos no resultado, remover o v1 (ou movê-lo para contexto secundário com aviso). Isso é lógica de negócio, não do embedding.

---

### Problema 2 — FAQ informal recuperado com score alto para perguntas críticas

**Descrição:** O FAQ-Atendimento tem linguagem coloquial muito próxima das perguntas dos atendentes ("carga perigosa", "frete expresso", "Platinum"). O modelo de embeddings prioriza similaridade textual, então o FAQ aparece no top-3 mesmo sendo fonte informal e não validada. Para perguntas sobre devolução de carga perigosa, o FAQ-03 pode inverter a regra ao dizer "não diga que é impossível", enquanto o POL-001-B é categórico: carga perigosa NÃO é elegível.

**Evidência:** Pergunta "Posso devolver carga perigosa?" → FAQ-03 (score alto por vocabulário similar) pode aparecer antes de POL-001-B (score ligeiramente menor por linguagem formal).

**Proposta de correção:**
1. **Boost por confiabilidade da fonte:** aplicar um multiplicador de relevância no score conforme a classificação do documento. POL e PROC recebem boost de +0.15 no score final; FAQ recebe penalidade de -0.10. Isso garante que documentos normativos vençam o FAQ em empate semântico.
2. **Separação de coleções:** criar duas coleções no ChromaDB — `novatech_normativos` (POL, PROC, SLA) e `novatech_faq` (FAQ). A busca primária é nos normativos; o FAQ só é consultado se nenhum chunk normativo atingir score acima de 0.7. Isso reflete a hierarquia real dos documentos.

---

## Ordem de execução

```bash
# 1. Setup
pip install chromadb sentence-transformers

# 2. Copiar os docs (Anexo A) para 1.3/docs/
# (usar os arquivos de .claude/docs/)

# 3. Ingestão
python ingest.py
# Output esperado: "POL-001: 5 chunks | PROC-042-v1: 4 chunks | ..."

# 4. Teste de busca isolado
python search.py
# Output esperado: top 3 chunks com scores para "Qual o prazo de devolução?"

# 5. Testes completos
python test_pipeline.py
# Gera: resultados-testes.md com análise das 5 perguntas

# 6. Para cada prompt gerado: colar no Claude e avaliar a resposta
```

---

## Checklist de entrega

- [ ] `ingest.py` funcional (com evidência de uso do Copilot: screenshots ou comentários `# Copilot suggested:`)
- [ ] `search.py` funcional
- [ ] `prompt_builder.py` funcional
- [ ] `test_pipeline.py` funcional
- [ ] `resultados-testes.md` com as 5 análises (chunks recuperados vs gabarito, scores, avaliação da resposta do Claude)
- [ ] 2 problemas identificados com proposta de correção concreta
- [ ] Estratégia de chunking justificada (não "512 tokens fixos")
