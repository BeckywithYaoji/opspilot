import asyncio
from fastapi.testclient import TestClient
from app.main import app as fastapi_app, get_approval_store, get_incident_store, get_memory_store, get_model
from app.approval import ApprovalStore
from tests.test_agent import ScriptedModel, call

class FakeClient:
    executions = 0
    def __init__(self, scenario): self.scenario=scenario
    async def __aenter__(self): return self
    async def __aexit__(self,*a): pass
    async def list_tools(self): return [{'name':'restart_service'}]
    async def call_tool(self,name,args):
        type(self).executions += 1
        return {'status':'success','tool':name}
    async def snapshot(self): return {'environment':{},'environment_restored':True,'tickets':[]}

def test_reject_and_replay_execute_zero_then_one(monkeypatch):
    import app.agent, app.main
    store=ApprovalStore(); FakeClient.executions=0
    monkeypatch.setattr(app.agent, 'OpsMCPClient', FakeClient)
    import app.mcp.client
    monkeypatch.setattr(app.mcp.client, 'OpsMCPClient', FakeClient)
    fastapi_app.dependency_overrides[get_model]=lambda: ScriptedModel([call('restart_service', {'host':'dev-server','service':'sshd'})])
    fastapi_app.dependency_overrides[get_approval_store]=lambda: store
    fastapi_app.dependency_overrides[get_memory_store]=lambda: None
    fastapi_app.dependency_overrides[get_incident_store]=lambda: None
    try:
        with TestClient(fastapi_app) as c:
            pending=c.post('/api/agent/run',json={'message':'repair','scenario':'repairable'}).json()
            aid=pending['pending_approval']['approval_id']
            assert c.post('/api/agent/approval',json={'approval_id':aid,'decision':'REJECT'}).status_code==200
            assert FakeClient.executions==0
            # A rejected approval cannot be replayed or approved later.
            assert c.post('/api/agent/approval',json={'approval_id':aid,'decision':'APPROVE'}).status_code==409
            pending2=c.post('/api/agent/run',json={'message':'repair','scenario':'repairable'}).json()
            aid2=pending2['pending_approval']['approval_id']
            assert c.post('/api/agent/approval',json={'approval_id':aid2,'decision':'APPROVE'}).status_code==200
            assert FakeClient.executions==1
            assert c.post('/api/agent/approval',json={'approval_id':aid2,'decision':'APPROVE'}).status_code==409
            assert FakeClient.executions==1
    finally:
        fastapi_app.dependency_overrides.clear()
