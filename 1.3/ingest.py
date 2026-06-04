# Copilot suggested: Pipeline de RAG para documentação interna da NovaTech (logística).
# Objetivo: ingestão de documentos markdown no ChromaDB com embeddings open-source.
#
# Estratégia de chunking: estrutural por seção Markdown (header-based).
# Cada seção delimitada por ## ou ### é uma unidade semântica completa.
# Evita cortar tabelas e listas de requisitos no meio (problema do chunking fixo por tokens).

import os
import re
import chromadb
from sentence_transformers import SentenceTransformer

DOCS_DIR = os.path.join(os.path.dirname(__file__), "docs")
CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "novatech_docs"
MODEL_NAME = "all-MiniLM-L6-v2"

# Usa o stem completo do arquivo como doc_id para garantir unicidade entre versões.
# Ex: "PROC-042-frete-especial-v1" e "PROC-042-v2-frete-especial-revisado" ficam distintos.
def extract_doc_id(filename: str) -> str:
    return os.path.splitext(filename)[0]


# Copilot suggested: dividir markdown em blocos delimitados por headers ## ou ###
def chunk_markdown(text: str, source: str) -> list[dict]:
    doc_id = extract_doc_id(source)
    lines = text.split("\n")
    chunks = []
    current_header = ""
    current_lines = []
    chunk_index = 0

    header_pattern = re.compile(r"^#{2,3}\s+")

    def flush_chunk():
        nonlocal chunk_index
        content = "\n".join(current_lines).strip()
        if len(content) < 50:  # descarta chunks muito pequenos (metadados, separadores)
            return
        chunk_text = f"{current_header}\n\n{content}" if current_header else content
        chunk_id = f"{doc_id}-chunk-{chunk_index:02d}"
        chunks.append({
            "id": chunk_id,
            "text": chunk_text,
            "metadata": {
                "source": os.path.splitext(source)[0],
                "section": current_header.strip("#").strip(),
                "doc_id": doc_id,
            }
        })
        chunk_index += 1

    for line in lines:
        if header_pattern.match(line):
            if current_lines or current_header:
                flush_chunk()
            current_header = line
            current_lines = []
        else:
            current_lines.append(line)

    # flush último bloco
    if current_lines or current_header:
        flush_chunk()

    return chunks


def ingest_all():
    print(f"Carregando modelo de embeddings: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    client = chromadb.PersistentClient(path=CHROMA_DIR)

    # Recria a coleção para garantir estado limpo
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"Coleção '{COLLECTION_NAME}' existente removida.")
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"}  # Copilot suggested: cosine é mais adequado para texto
    )

    md_files = [f for f in os.listdir(DOCS_DIR) if f.endswith(".md")]
    total_chunks = 0

    for filename in sorted(md_files):
        filepath = os.path.join(DOCS_DIR, filename)
        with open(filepath, encoding="utf-8") as f:
            text = f.read()

        chunks = chunk_markdown(text, filename)
        if not chunks:
            print(f"  {filename}: nenhum chunk gerado")
            continue

        texts = [c["text"] for c in chunks]
        ids = [c["id"] for c in chunks]
        metadatas = [c["metadata"] for c in chunks]

        # Copilot suggested: gerar embeddings em batch para eficiência
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        print(f"  {filename}: {len(chunks)} chunks ingeridos")
        for c in chunks:
            print(f"    [{c['id']}] {c['metadata']['section'][:60]}")
        total_chunks += len(chunks)

    print(f"\nTotal: {total_chunks} chunks armazenados na coleção '{COLLECTION_NAME}'")
    print(f"ChromaDB persistido em: {CHROMA_DIR}")


if __name__ == "__main__":
    ingest_all()
