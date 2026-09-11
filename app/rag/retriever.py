from __future__ import annotations
from pathlib import Path
from qdrant_client import QdrantClient
from app.storage import qdrant_client
from .indexer import BGEEncoder, RunbookIndex

class RunbookRetriever:
    def __init__(self, path: str | Path, encoder=None):
        self.path, self.encoder = str(path), encoder or BGEEncoder()
    def search(self, query: str, top_k: int = 4) -> dict:
        if not query or not query.strip(): return {"status": "ok", "query": query, "results": []}
        try:
            client = qdrant_client(self.path)
            if not client.collection_exists(RunbookIndex.collection): raise RuntimeError("runbook collection is unavailable")
            vector = self.encoder.encode([query])[0]
            if hasattr(client, "query_points"):
                hits = client.query_points(RunbookIndex.collection, query=vector, limit=max(1, min(int(top_k), 20))).points
            else:
                hits = client.search(RunbookIndex.collection, query_vector=vector, limit=max(1, min(int(top_k), 20)))
            return {"status": "ok", "query": query, "results": [{"source": h.payload["source"], "section": h.payload["section"], "content": h.payload["content"], "score": h.score} for h in hits]}
        except Exception as exc:
            return {"status": "error", "query": query, "results": [], "error": str(exc)}
