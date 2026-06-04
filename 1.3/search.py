# Copilot suggested: módulo de busca vetorial no ChromaDB para o pipeline RAG da NovaTech.
# Recebe uma pergunta, gera embedding e retorna os N chunks mais similares com score.

import os
import chromadb
from sentence_transformers import SentenceTransformer

CHROMA_DIR = os.path.join(os.path.dirname(__file__), "chroma_db")
COLLECTION_NAME = "novatech_docs"
MODEL_NAME = "all-MiniLM-L6-v2"

_model = None
_collection = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)
    return _model


def _get_collection():
    global _collection
    if _collection is None:
        client = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


# Copilot suggested: ChromaDB com espaço cosine retorna distância [0,2].
# Converter para similaridade: similarity = 1 - (distance / 2)
def _distance_to_similarity(distance: float) -> float:
    return round(1.0 - (distance / 2.0), 4)


def search(query: str, n_results: int = 3) -> list[dict]:
    model = _get_model()
    collection = _get_collection()

    query_embedding = model.encode([query])[0].tolist()

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    for i in range(len(results["ids"][0])):
        distance = results["distances"][0][i]
        chunks.append({
            "chunk_id": results["ids"][0][i],
            "text": results["documents"][0][i],
            "score": _distance_to_similarity(distance),
            "distance": round(distance, 4),
            "source": results["metadatas"][0][i].get("source", ""),
            "section": results["metadatas"][0][i].get("section", ""),
            "doc_id": results["metadatas"][0][i].get("doc_id", ""),
        })

    return chunks


def print_results(query: str, chunks: list[dict]):
    print(f"\nPergunta: {query}")
    print("-" * 70)
    for i, c in enumerate(chunks, 1):
        print(f"  [{i}] {c['chunk_id']} | Score: {c['score']:.4f}")
        print(f"       Fonte: {c['source']} | Seção: {c['section'][:50]}")
        print(f"       Texto: {c['text'][:200].replace(chr(10), ' ')}...")
        print()


if __name__ == "__main__":
    # Teste básico ao rodar diretamente
    query = "Qual o prazo de devolução de mercadorias?"
    chunks = search(query, n_results=3)
    print_results(query, chunks)
