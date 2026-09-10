import json
from pathlib import Path
from uuid import uuid4
from fastapi.testclient import TestClient
from app.main import app, get_trajectory_path
from app.memory.incident import IncidentMemoryStore

root = Path.cwd()
app.dependency_overrides[get_trajectory_path] = lambda: root / 'data/demo-v3.1-runs.jsonl'
from qdrant_client import QdrantClient
qdrant = QdrantClient(path='data/qdrant-incidents')
if qdrant.collection_exists('opspilot_incidents'):
    qdrant.delete_collection('opspilot_incidents')
qdrant.close()

with TestClient(app) as client:
    req1 = {'session_id': 'v31-write-' + uuid4().hex, 'message': '帮我检查并恢复 dev-server 的 SSH。', 'scenario': 'repairable'}
    x1 = client.post('/api/agent/run', json=req1).json()
    hits = IncidentMemoryStore('data/qdrant').search('previous SSH connection failure', 3)
    (root / 'data/demo-v3.1-incident-write.json').write_text(json.dumps({'request': req1, 'response': x1, 'incident_search_after_write': hits}, ensure_ascii=False, indent=2) + '\n')
    req2 = {'session_id': 'v31-cross-' + uuid4().hex, 'message': 'staging-server 的 SSH 现在也连不上了，之前有没有出现过类似问题？如果有的话参考一下之前的处理经验再帮我检查。', 'scenario': 'repairable'}
    x2 = client.post('/api/agent/run', json=req2).json()
    (root / 'data/demo-v3.1-cross-session.json').write_text(json.dumps({'request': req2, 'response': x2, 'expected_historical_incident': hits.get('results', [None])[0]}, ensure_ascii=False, indent=2) + '\n')
    req3 = {'session_id': 'v31-simple-' + uuid4().hex, 'message': '检查一下 dev-server 的 22 端口。', 'scenario': 'repairable'}
    x3 = client.post('/api/agent/run', json=req3).json()
    (root / 'data/demo-v3.1-selective.json').write_text(json.dumps({'request': req3, 'response': x3}, ensure_ascii=False, indent=2) + '\n')
    for name, x in [('write', x1), ('cross', x2), ('simple', x3)]:
        print(name, x.get('status'), x.get('resolution_status'), [(s['tool'], s['arguments'], s['observation'].get('status')) for s in x.get('trajectory', [])], flush=True)
