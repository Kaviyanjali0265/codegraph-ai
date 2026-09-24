import sys
import ollama
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from ingest.parser import parse_directory
from core.vectorstore import VectorStore
from core.graph_store import GraphStore
from core.models import CodeChunk

EMBED_MODEL = "nomic-embed-text"


def embed_text(text: str) -> list[float]:
    response = ollama.embed(model=EMBED_MODEL, input=text)
    return response.embeddings[0]


def chunk_to_document(chunk: CodeChunk) -> str:
    parts = [
        f"File: {chunk.file}",
        f"Type: {chunk.type}",
        f"Name: {chunk.name}",
    ]
    if chunk.docstring:
        parts.append(f"Description: {chunk.docstring}")
    parts.append(f"Code:\n{chunk.code}")
    return "\n".join(parts)


def ingest(directory: str):
    print(f"Parsing {directory}...")
    chunks = parse_directory(directory)
    print(f"Found {len(chunks)} code chunks\n")

    store = VectorStore()

    ids, embeddings, documents, metadatas = [], [], [], []

    for chunk in chunks:
        doc = chunk_to_document(chunk)
        embedding = embed_text(doc)

        ids.append(chunk.id)
        embeddings.append(embedding)
        documents.append(doc)
        metadatas.append({
            "file": chunk.file,
            "name": chunk.name,
            "type": chunk.type,
            "lineno": chunk.lineno,
            "calls": ",".join(chunk.calls),
        })
        print(f"  Embedded: [{chunk.type}] {chunk.name}")

    store.upsert(ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas)
    print(f"\nStored {store.count()} chunks in ChromaDB.")

    print("\nBuilding knowledge graph...")
    graph = GraphStore()
    graph.build_from_chunks(chunks)
    graph.save()
    print(f"Graph saved — {graph.node_count()} nodes, {graph.edge_count()} edges.")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "sample_code"
    ingest(target)
