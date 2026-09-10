import json

import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage

from app.main import app, get_model, get_trajectory_path
from tests.test_agent import ScriptedModel, call


@pytest.fixture
def client(tmp_path):
    app.dependency_overrides[get_model] = lambda: ScriptedModel([
        call('restart_service', {'host': 'dev-server', 'service': 'sshd'}),
        AIMessage(content='操作结束。'),
    ])
    app.dependency_overrides[get_trajectory_path] = lambda: tmp_path / 'runs.jsonl'
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_health(client):
    assert client.get('/health').json() == {'status': 'ok'}


def test_api_initializes_independent_scenarios_and_appends_logs(client, tmp_path):
    for scenario, restored in [('repairable', True), ('permission_denied', False)]:
        response = client.post('/api/agent/run', json={'message': '修复 SSH', 'scenario': scenario})
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is restored
        assert data['environment']['dev-server']['ports']['22'] is restored
    records = [json.loads(line) for line in (tmp_path / 'runs.jsonl').read_text().splitlines()]
    assert len(records) == 2
    assert records[0]['task_id'] != records[1]['task_id']
    assert records[1]['steps'][0]['observation']['error'] == 'permission denied'


@pytest.mark.parametrize('payload', [
    {'message': ''}, {'message': '   '}, {'message': 'x', 'scenario': 'other'},
    {'message': 'x', 'workflow': 'ssh'},
])
def test_invalid_request_rejected(client, payload):
    assert client.post('/api/agent/run', json=payload).status_code == 422
