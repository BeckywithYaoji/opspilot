"""Deployment selection only; collection names and retrieval semantics stay unchanged."""
import os
from qdrant_client import QdrantClient
from dotenv import dotenv_values
from app.config import ENV_PATH


def qdrant_url():
    return ({**dotenv_values(ENV_PATH), **os.environ}.get('QDRANT_URL') or '').strip()


def qdrant_client(path, factory=QdrantClient):
    url = qdrant_url()
    if url:
        return factory(url=url, timeout=10)
    return factory(path=str(path))
