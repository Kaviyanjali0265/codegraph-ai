import time
import chromadb
from pathlib import Path
from core.ollama_client import embed

CHROMA_PATH = Path(__file__).parent.parent / ".data" / "chroma"

# Short-term: in-process session buffer, lost on restart
_session_buffer: dict[str, list[dict]] = {}
MAX_SESSION_TURNS = 5

# Long-term: TTL-based retention — entries older than this are deleted
TTL_DAYS = 30
TTL_SECONDS = TTL_DAYS * 24 * 60 * 60


class MemoryStore:
    def __init__(self):
        CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        self.collection = self.client.get_or_create_collection(
            name="conversation_memory",
            metadata={"hnsw:space": "cosine"},
        )

    def save(self, session_id: str, query: str, answer: str):
        # Short-term session buffer
        if session_id not in _session_buffer:
            _session_buffer[session_id] = []
        _session_buffer[session_id].append({"query": query, "answer": answer})
        if len(_session_buffer[session_id]) > MAX_SESSION_TURNS:
            _session_buffer[session_id] = _session_buffer[session_id][-MAX_SESSION_TURNS:]

        # Long-term ChromaDB — timestamp stored for TTL enforcement
        doc = f"Question: {query}\nAnswer: {answer}"
        entry_id = f"{session_id}_{int(time.time() * 1000)}"
        self.collection.upsert(
            ids=[entry_id],
            embeddings=[embed(doc)],
            documents=[doc],
            metadatas=[{
                "session_id": session_id,
                "query": query,
                "timestamp": time.time(),
            }],
        )

        # Run TTL cleanup on every save
        self._cleanup_expired()

    def get_session_history(self, session_id: str) -> list[dict]:
        return _session_buffer.get(session_id, [])

    def retrieve_relevant(self, query: str, n_results: int = 2) -> list[str]:
        if self.collection.count() == 0:
            return []
        results = self.collection.query(
            query_embeddings=[embed(query)],
            n_results=min(n_results, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        relevant = []
        now = time.time()
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Skip expired entries and irrelevant ones
            age = now - meta.get("timestamp", 0)
            if age < TTL_SECONDS and dist < 0.5:
                relevant.append(doc)
        return relevant

    def _cleanup_expired(self):
        """Delete all entries older than TTL_DAYS from ChromaDB."""
        if self.collection.count() == 0:
            return

        all_entries = self.collection.get(include=["metadatas"])
        now = time.time()
        expired_ids = [
            entry_id
            for entry_id, meta in zip(all_entries["ids"], all_entries["metadatas"])
            if now - meta.get("timestamp", 0) > TTL_SECONDS
        ]

        if expired_ids:
            self.collection.delete(ids=expired_ids)
