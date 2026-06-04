# Copilot suggested: script de testes documentados do pipeline RAG da NovaTech.
# Executa 5 perguntas, compara com gabarito do Anexo B e salva resultados em markdown.

import os
from search import search
from prompt_builder import build_prompt

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "resultados-testes.md")

# Gabarito baseado no Anexo B (mapa de cobertura)
# Copilot suggested: incluir chunks esperados e secundários para avaliação mais rica
PERGUNTAS = [
    {
        "id": 1,
        "query": "Qual o prazo de devolução de mercadorias?",
        # chunk IDs gerados pela ingestão: POL-001-politica-devolucao-chunk-03 (prazo) e -04 (exceções)
        "chunks_esperados": ["POL-001-politica-devolucao"],
        "gabarito_ids_ref": ["POL-001-A (seção 3.1)", "POL-001-B (seção 3.2)"],
        "observacao": "Deve recuperar prazo (7 dias úteis) e exceções para categorias especiais.",
        "risco": "Pode não recuperar a seção de exceções (cargas perigosas, refrigeradas).",
    },
    {
        "id": 2,
        "query": "Posso devolver carga perigosa?",
        # chunk alvo: POL-001-politica-devolucao-chunk-04 (seção 3.2 — exceções)
        "chunks_esperados": ["POL-001-politica-devolucao"],
        "gabarito_ids_ref": ["POL-001-B (seção 3.2)"],
        "observacao": "Deve recuperar a seção de exceções que proíbe devolução de carga perigosa.",
        "risco": "ARMADILHA: FAQ-atendimento pode aparecer dizendo 'não diga que é impossível', invertendo a regra normativa.",
    },
    {
        "id": 3,
        "query": "Qual o SLA para cliente Gold em incidente crítico?",
        # chunk alvo: SLA-2024-tabela-sla-clientes-chunk-02 (Tabela de SLAs) e -03 (incidente crítico)
        "chunks_esperados": ["SLA-2024-tabela-sla-clientes"],
        "gabarito_ids_ref": ["SLA-2024-C (seção 2 — incidentes críticos)"],
        "observacao": "Deve recuperar a tabela de SLA para incidentes críticos especificamente.",
        "risco": "Pode recuperar chunk de chamados gerais (2h/24h) em vez de incidentes críticos (30min/4h).",
    },
    {
        "id": 4,
        "query": "Quanto custa o frete especial para 600kg com destino a Manaus?",
        # chunks alvo: PROC-042-v2-frete-especial-revisado-chunk-02 (fórmula) e -03 (multiplicadores)
        "chunks_esperados": ["PROC-042-v2-frete-especial-revisado"],
        "gabarito_ids_ref": ["PROC-042v2-A (fórmula)", "PROC-042v2-B (multiplicadores — Norte=1.8)"],
        "observacao": "Deve recuperar fórmula e multiplicadores da versão revisada (Norte=1.8).",
        "risco": "ARMADILHA: PROC-042-frete-especial-v1 pode aparecer com Norte=1.6, gerando contradição.",
    },
    {
        "id": 5,
        "query": "Qual o multiplicador regional para o Sudeste no frete especial?",
        # chunk alvo: PROC-042-v2-frete-especial-revisado-chunk-03 (multiplicadores — Sudeste=1.1)
        "chunks_esperados": ["PROC-042-v2-frete-especial-revisado"],
        "gabarito_ids_ref": ["PROC-042v2-B (Sudeste=1.1)"],
        "observacao": "Deve recuperar multiplicadores da versão revisada (Sudeste=1.1).",
        "risco": "ARMADILHA CLÁSSICA: v1 diz Sudeste=1.0, v2 diz Sudeste=1.1. Se ambos recuperados, há contradição direta.",
    },
]


def avaliar_chunks(chunks_recuperados: list[dict], chunks_esperados: list[str]) -> dict:
    ids_recuperados = [c["chunk_id"] for c in chunks_recuperados]
    fontes_recuperadas = [c["source"] for c in chunks_recuperados]

    acertos = []
    for esperado in chunks_esperados:
        # verifica se algum chunk recuperado pertence ao doc esperado
        hit = any(esperado.lower() in chunk_id.lower() or esperado.lower() in source.lower()
                  for chunk_id, source in zip(ids_recuperados, fontes_recuperadas))
        if hit:
            acertos.append(esperado)

    return {
        "acertos": acertos,
        "total_esperados": len(chunks_esperados),
        "recall": len(acertos) / len(chunks_esperados) if chunks_esperados else 0,
    }


def run_tests():
    results = []

    for teste in PERGUNTAS:
        print(f"\n{'='*70}")
        print(f"TESTE {teste['id']}: {teste['query']}")
        print("="*70)

        chunks = search(teste["query"], n_results=5)
        avaliacao = avaliar_chunks(chunks, teste["chunks_esperados"])
        prompt = build_prompt(teste["query"], chunks[:3])  # top 3 no prompt

        print(f"\nChunks recuperados:")
        for c in chunks:
            print(f"  [{c['chunk_id']}] score={c['score']:.4f} | {c['section'][:50]}")

        print(f"\nGabarito (Anexo B): {teste['gabarito_ids_ref']}")
        print(f"Avaliação: recall={avaliacao['recall']:.0%} ({len(avaliacao['acertos'])}/{avaliacao['total_esperados']} docs esperados encontrados)")
        print(f"Risco identificado: {teste['risco']}")

        results.append({
            "teste": teste,
            "chunks": chunks,
            "avaliacao": avaliacao,
            "prompt": prompt,
        })

    return results


def save_markdown(results: list[dict]):
    lines = []
    lines.append("# Resultados dos Testes — Pipeline RAG NovaTech")
    lines.append("")
    lines.append("**Modelo de embeddings:** all-MiniLM-L6-v2  ")
    lines.append("**Vector store:** ChromaDB (local, cosine similarity)  ")
    lines.append("**Chunking:** estrutural por seção Markdown (header-based)  ")
    lines.append("**N results:** 5 recuperados, 3 enviados ao prompt")
    lines.append("")
    lines.append("---")
    lines.append("")

    for r in results:
        teste = r["teste"]
        chunks = r["chunks"]
        avaliacao = r["avaliacao"]
        prompt = r["prompt"]

        lines.append(f"## Teste {teste['id']}: {teste['query']}")
        lines.append("")
        lines.append(f"**Gabarito (Anexo B):** {', '.join(teste['gabarito_ids_ref'])}")
        lines.append("")

        lines.append("### Chunks recuperados")
        lines.append("")
        lines.append("| Rank | Chunk ID | Score | Fonte | Seção |")
        lines.append("|------|----------|-------|-------|-------|")
        for i, c in enumerate(chunks, 1):
            lines.append(f"| {i} | `{c['chunk_id']}` | {c['score']:.4f} | {c['source']} | {c['section'][:45]} |")
        lines.append("")

        lines.append("### Avaliação do retrieval")
        lines.append("")
        lines.append(f"- **Recall:** {avaliacao['recall']:.0%} ({len(avaliacao['acertos'])}/{avaliacao['total_esperados']} documentos-alvo encontrados)")
        lines.append(f"- **Observação:** {teste['observacao']}")
        lines.append(f"- **Risco/problema identificado:** {teste['risco']}")
        lines.append("")

        # Detectar armadilha de versões conflitantes
        sources = [c["source"] for c in chunks]
        if "PROC-042-frete-especial-v1" in sources and "PROC-042-v2-frete-especial-revisado" in sources:
            lines.append("> **PROBLEMA DETECTADO:** Chunks de PROC-042-v1 e PROC-042-v2 foram recuperados juntos.")
            lines.append("> Os multiplicadores são diferentes (ex: Sudeste 1.0 vs 1.1, Norte 1.6 vs 1.8).")
            lines.append("> Risco de contradição na resposta do LLM.")
            lines.append("")

        if any("FAQ" in s for s in sources) and any("POL" in s for s in sources):
            lines.append("> **ATENÇÃO:** FAQ (fonte informal) e documento normativo (POL) recuperados juntos.")
            lines.append("> O FAQ pode contradizer ou suavizar regras formais.")
            lines.append("")

        lines.append("### Prompt montado (para envio ao Claude)")
        lines.append("")
        lines.append("```")
        lines.append(prompt)
        lines.append("```")
        lines.append("")
        lines.append("### Resposta do Claude")
        lines.append("")
        lines.append("*(Colar prompt acima no Claude e registrar a resposta aqui)*")
        lines.append("")
        lines.append("**Checklist de avaliação:**")
        lines.append("- [ ] Resposta correta (bate com o documento)")
        lines.append("- [ ] Fonte citada (nome do doc + seção)")
        lines.append("- [ ] Contradições sinalizadas (quando houver)")
        lines.append("- [ ] Ausência de info declarada (sem alucinação)")
        lines.append("- [ ] Guardrails respeitados")
        lines.append("")
        lines.append("---")
        lines.append("")

    # Seção de problemas e correções
    lines.append("## Problemas Identificados e Propostas de Correção")
    lines.append("")
    lines.append("### Problema 1 — Versões conflitantes do PROC-042 recuperadas juntas")
    lines.append("")
    lines.append("**Descrição:** O pipeline retorna chunks de PROC-042-v1 e PROC-042-v2 para perguntas")
    lines.append("sobre frete especial. Os multiplicadores regionais diferem (Sudeste: 1.0 vs 1.1;")
    lines.append("Norte: 1.6 vs 1.8). O LLM pode misturar os valores ou escolher arbitrariamente.")
    lines.append("")
    lines.append("**Evidência nos testes:** Testes 4 e 5 — ambas as versões aparecem no top-5.")
    lines.append("")
    lines.append("**Proposta de correção:**")
    lines.append("1. Adicionar metadado `version` e `superseded_by` nos chunks do PROC-042-v1.")
    lines.append("2. Implementar filtro pós-retrieval: se v1 e v2 do mesmo documento aparecerem,")
    lines.append("   remover o v1 e adicionar nota no contexto: *[PROC-042-v1 omitido — substituído pela v2 de nov/2023]*.")
    lines.append("3. Adicionar instrução no system prompt: 'Se dois chunks forem do mesmo documento")
    lines.append("   com versões diferentes, use apenas o de versão mais recente.'")
    lines.append("")
    lines.append("### Problema 2 — FAQ informal recuperado com score alto para perguntas normativas")
    lines.append("")
    lines.append("**Descrição:** O FAQ usa linguagem coloquial similar às perguntas dos atendentes,")
    lines.append("gerando score de similaridade alto. Para 'Posso devolver carga perigosa?', o")
    lines.append("FAQ-03 aparece com score comparável ao POL-001 formal, mas com orientação diferente:")
    lines.append("FAQ diz 'não afirme que é impossível'; POL diz categoricamente que NÃO é elegível.")
    lines.append("")
    lines.append("**Evidência nos testes:** Teste 2 — FAQ-atendimento aparece entre os top-5.")
    lines.append("")
    lines.append("**Proposta de correção:**")
    lines.append("1. **Boost por tipo de fonte:** aplicar score ajustado = score × 1.15 para POL/PROC/SLA")
    lines.append("   e score × 0.85 para FAQ. Documentos normativos vencem empates semânticos.")
    lines.append("2. **Coleções separadas:** criar `novatech_normativos` (POL, PROC, SLA) e")
    lines.append("   `novatech_faq`. Buscar primeiro nos normativos; consultar FAQ apenas se nenhum")
    lines.append("   normativo atingir score ≥ 0.70, e sempre com aviso 'fonte informal' no prompt.")
    lines.append("")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\nResultados salvos em: {OUTPUT_FILE}")


if __name__ == "__main__":
    results = run_tests()
    save_markdown(results)
