from unittest.mock import Mock
from fastapi.testclient import TestClient
from app.main import app

def test_remote_qdrant_configuration(monkeypatch):
    from app.storage import qdrant_client
    factory=Mock();monkeypatch.setenv('QDRANT_URL','http://qdrant:6333')
    qdrant_client('unused-local',factory=factory)
    assert factory.call_args.kwargs['url']=='http://qdrant:6333'
    assert 'path' not in factory.call_args.kwargs

def test_local_qdrant_configuration(monkeypatch):
    from app.storage import qdrant_client
    factory=Mock();monkeypatch.delenv('QDRANT_URL',raising=False)
    qdrant_client('local-index',factory=factory)
    factory.assert_called_once_with(path='local-index')

def test_readiness_failure_does_not_break_liveness(monkeypatch):
    import app.readiness as readiness
    monkeypatch.setattr(readiness,'dependency_status',lambda:{'status':'degraded','redis':'unavailable','qdrant':'unavailable'})
    with TestClient(app) as client:
        assert client.get('/health').status_code==200
        response=client.get('/ready')
        assert response.status_code==503
        assert response.json()['redis']=='unavailable'

def test_mcp_subprocess_receives_deployment_configuration(monkeypatch):
    from app.mcp.client import OpsMCPClient
    import app.mcp.client as module
    captured=Mock();monkeypatch.setattr(module,'Client',captured)
    monkeypatch.setenv('QDRANT_URL','http://qdrant:6333')
    monkeypatch.setenv('HF_HOME','/app/.cache/huggingface')
    monkeypatch.setenv('LLM_API_KEY','must-not-be-forwarded')
    OpsMCPClient('repairable')
    env=captured.call_args.args[0].env
    assert env['QDRANT_URL']=='http://qdrant:6333'
    assert env['HF_HOME']=='/app/.cache/huggingface'
    assert 'LLM_API_KEY' not in env
