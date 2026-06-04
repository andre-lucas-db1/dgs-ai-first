# Copilot suggested: monta o prompt completo (system + contexto + pergunta) para envio ao LLM.
# O prompt gerado é uma string pronta para copiar e colar no Claude (chat manual).

SYSTEM_PROMPT = """Você é um assistente de atendimento interno da NovaTech, empresa de logística.

Suas regras:
1. Responda APENAS com base nos documentos fornecidos abaixo. Não utilize conhecimento externo.
2. Cite sempre a fonte (nome do documento e seção) ao final de cada afirmação relevante, no formato: [Fonte: NOME-DO-DOCUMENTO, Seção: NOME-DA-SEÇÃO]
3. Se a informação não estiver presente nos documentos, responda explicitamente: "Não encontrei essa informação na documentação disponível."
4. Não invente informações, percentuais, prazos ou procedimentos que não estejam nos documentos.
5. Se dois documentos apresentarem informações contraditórias, aponte a contradição explicitamente, indique qual versão é mais recente e recomende verificação com a área responsável.
6. Não afirme que algo é possível se o documento normativo disser que não é — o documento formal prevalece sobre o FAQ informal.

Idioma: português brasileiro."""


def build_prompt(query: str, chunks: list[dict]) -> str:
    lines = []
    lines.append("=== SYSTEM ===")
    lines.append(SYSTEM_PROMPT)
    lines.append("")
    lines.append("=== CONTEXTO — DOCUMENTOS RECUPERADOS ===")
    lines.append("")

    for i, chunk in enumerate(chunks, 1):
        lines.append(
            f"[Chunk {i} — Fonte: {chunk['source']} | Seção: {chunk['section']} | Score: {chunk['score']:.4f}]"
        )
        lines.append(chunk["text"])
        lines.append("")

    lines.append("=== PERGUNTA DO ATENDENTE ===")
    lines.append(query)

    return "\n".join(lines)


if __name__ == "__main__":
    # Exemplo de uso direto
    exemplo_chunks = [
        {
            "source": "POL-001-politica-devolucao",
            "section": "3.1. Prazo geral",
            "score": 0.91,
            "text": "O cliente pode solicitar a devolução de mercadorias em até 7 (sete) dias úteis após a data de recebimento confirmada no sistema de tracking.",
        }
    ]
    prompt = build_prompt("Qual o prazo de devolução?", exemplo_chunks)
    print(prompt)
