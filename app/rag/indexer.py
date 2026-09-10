from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams


@dataclass(frozen=True)
class Chunk:
    source: str
    title: str
    section: str
    chunk_id: str
    content: str


def chunk_markdown(path: str | Path, max_chars: int = 1200, overlap: int = 120) -> list[Chunk]:
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    headings = list(re.finditer(r"(?m)^(#{1,6})\s+(.+?)\s*$", text))
    title = headings[0].group(2).strip() if headings else path.stem
    sections = []
    for i, match in enumerate(headings):
        end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
        body = text[match.end():end].strip()
        if body:
            sections.append((match.group(2).strip(), body))
    if not sections and text.strip(): sections = [(title, text.strip())]
    chunks = []
    for section, body in sections:
        pieces = [body] if len(body) <= max_chars else [body[i:i + max_chars] for i in range(0, len(body), max_chars - overlap)]
        for n, content in enumerate(pieces):
            raw = f"{path.name}|{section}|{n}|{content}"
            chunk_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
            chunks.append(Chunk(path.name, title, section, chunk_id, content))
    return chunks


class BGEEncoder:
    dimension = 384
    def __init__(self, model_name: str = "BAAI/bge-small-en-v1.5"):
        self.model_name, self._model = model_name, None
    def encode(self, texts):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
            self.dimension = self._model.get_sentence_embedding_dimension()
        return self._model.encode(list(texts), normalize_embeddings=True).tolist()


class RunbookIndex:
    collection = "runbooks"
    def __init__(self, path: str | Path, encoder=None):
        self.path, self.encoder = str(path), encoder or BGEEncoder()
    def build(self, paths):
        chunks = [chunk for path in paths for chunk in chunk_markdown(path)]
        client = QdrantClient(path=self.path)
        if client.collection_exists(self.collection): client.delete_collection(self.collection)
        client.create_collection(self.collection, vectors_config=VectorParams(size=self.encoder.dimension, distance=Distance.COSINE))
        vectors = self.encoder.encode([c.content for c in chunks])
        points = [PointStruct(id=int(c.chunk_id, 16), vector=v, payload=c.__dict__) for c, v in zip(chunks, vectors)]
        client.upsert(self.collection, points)
        return chunks
