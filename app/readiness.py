"""Read-only dependency probes, with no external LLM request."""
import os
from redis import Redis
from app.config import MemorySettings
from app.storage import qdrant_client, qdrant_url


def dependency_status():
    result = {'status': 'healthy', 'redis': 'unavailable', 'qdrant': 'unavailable'}
    try:
        with Redis.from_url(MemorySettings.from_env().redis_url,
                            socket_connect_timeout=1, socket_timeout=1) as client:
            client.ping()
        result['redis'] = 'healthy'
    except Exception:
        pass
    try:
        paths = ['data/qdrant'] if qdrant_url() else ['data/qdrant', 'data/qdrant-incidents']
        for path in paths:
            client = qdrant_client(path)
            try:
                client.get_collections()
            finally:
                client.close()
        result['qdrant'] = 'healthy'
    except Exception:
        pass
    if any(result[key] != 'healthy' for key in ('redis', 'qdrant')):
        result['status'] = 'degraded'
    return result
