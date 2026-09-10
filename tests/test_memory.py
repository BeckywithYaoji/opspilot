import asyncio
import json
import pytest
from app.memory.session import SessionMemory, RedisSessionMemoryStore, update_memory, render_context
from app.models import RunResponse, TrajectoryStep

class FakeRedis:
    def __init__(self): self.data={}; self.ttls={}
    async def get(self,key): return self.data.get(key)
    async def set(self,key,value,ex): self.data[key]=value; self.ttls[key]=ex
    async def delete(self,key): self.data.pop(key,None)
    async def aclose(self): pass


def test_store_roundtrip_isolation_ttl():
    async def check():
        client=FakeRedis(); store=RedisSessionMemoryStore(client,ttl=123,max_messages=10)
        await store.save('A',SessionMemory(entities={'last_host':'alpha'}))
        await store.save('B',SessionMemory(entities={'last_host':'beta'}))
        assert (await store.load('A')).entities=={'last_host':'alpha'}
        assert (await store.load('B')).entities=={'last_host':'beta'}
        assert client.ttls['opspilot:session:A']==123
        await store.clear('A'); assert not (await store.load('A')).entities
    asyncio.run(check())


def test_window_entities_and_failed_turn_preserve_history():
    memory=SessionMemory()
    result=RunResponse(task_id='x',status='COMPLETED',answer='checked',success=False,environment={},trajectory=[TrajectoryStep(step=1,tool='check_port',arguments={'host':'alpha','port':8080},observation={'status':'open'})])
    for i in range(8): memory=update_memory(memory,str(i),result,max_messages=10)
    assert len(memory.messages)==10 and memory.messages[0]['content']=='3'
    assert memory.entities=={'last_host':'alpha','last_port':8080}
    result.status='FAILED'; result.trajectory=[]
    memory=update_memory(memory,'again',result,max_messages=10)
    assert memory.entities['last_host']=='alpha'
    assert 'alpha' in render_context(memory)
    assert 'trajectory' not in memory.model_dump()

from app.agent import run_agent
from tests.test_agent import ScriptedModel, call
from langchain_core.messages import AIMessage

class FakeSessionMemoryStore:
    max_messages=10
    def __init__(self): self.data={}
    async def load(self,sid): return self.data.get(sid,SessionMemory()).model_copy(deep=True)
    async def save(self,sid,memory): self.data[sid]=memory.model_copy(deep=True)
    async def clear(self,sid): self.data.pop(sid,None)


def test_context_injection_and_session_isolation(tmp_path):
    store=FakeSessionMemoryStore()
    store.data['A']=SessionMemory(entities={'last_host':'alpha'})
    model=ScriptedModel([AIMessage(content='Which operation?')])
    result=run_agent('That server?', 'repairable', model,session_id='A',memory_store=store,trajectory_path=tmp_path/'runs')
    assert result.memory_loaded and result.session_id=='A'
    assert 'last_host: alpha' in model.seen[0][1].content
    other=ScriptedModel([AIMessage(content='Which server?')])
    isolated=run_agent('That server?', 'repairable',other,session_id='B',memory_store=store,trajectory_path=tmp_path/'runs')
    assert not isolated.memory_loaded
    assert 'alpha' not in other.seen[0][1].content


def test_redis_load_failure_still_runs_and_does_not_overwrite(tmp_path):
    class Broken(FakeSessionMemoryStore):
        async def load(self,sid): raise ConnectionError('private error')
        async def save(self,*args): raise AssertionError('must not overwrite failed load')
    model=ScriptedModel([call('check_port',{'host':'dev-server','port':22}),AIMessage(content='Closed.')])
    result=run_agent('Check port', 'repairable',model,session_id='A',memory_store=Broken(),trajectory_path=tmp_path/'runs')
    assert result.status=='COMPLETED' and result.memory_error=='memory_load_failed'
    assert 'private error' not in result.model_dump_json()


def test_redis_save_failure_does_not_fail_task(tmp_path):
    class Broken(FakeSessionMemoryStore):
        async def save(self,*args): raise ConnectionError('private error')
    result=run_agent('Hello','repairable',ScriptedModel([AIMessage(content='Hello')]),memory_store=Broken(),trajectory_path=tmp_path/'runs')
    assert result.status=='COMPLETED' and result.memory_error=='memory_save_failed'
    assert result.session_id


def test_context_reaches_completion_verifier(tmp_path):
    class Model(ScriptedModel):
        def invoke_structured(self,messages,schema):
            ctx=json.loads(messages[-1].content)
            assert 'last_host: dev-server' in ctx['session_context']
            return {'goal_satisfied':True,'decision':'FINISH','unresolved_requirements':[]}
    store=FakeSessionMemoryStore();store.data['A']=SessionMemory(entities={'last_host':'dev-server'})
    model=Model([call('check_port',{'host':'dev-server','port':22}),AIMessage(content='Closed')])
    result=run_agent('Its port now?', 'repairable',model,session_id='A',memory_store=store,trajectory_path=tmp_path/'runs')
    assert result.goal_satisfied_at_step==1 and result.memory_loaded


def test_real_redis_roundtrip_ttl_and_clear():
    import os
    from uuid import uuid4
    from redis.asyncio import Redis
    url=os.getenv('REDIS_TEST_URL')
    if not url: pytest.skip('set REDIS_TEST_URL for optional Redis integration')
    async def check():
        client=Redis.from_url(url,decode_responses=True)
        store=RedisSessionMemoryStore(client,ttl=60)
        sid='test-'+uuid4().hex
        try:
            await store.save(sid,SessionMemory(entities={'last_host':'integration'}))
            assert (await store.load(sid)).entities['last_host']=='integration'
            assert 0 < await client.ttl('opspilot:session:'+sid) <=60
            await store.clear(sid)
            assert not (await store.load(sid)).entities
        finally:
            await store.clear(sid); await store.aclose()
    asyncio.run(check())


def test_memory_settings_from_env(monkeypatch):
    from app.config import MemorySettings
    monkeypatch.setenv('REDIS_URL','redis://example.invalid:6380/2')
    monkeypatch.setenv('SESSION_MEMORY_TTL_SECONDS','90')
    monkeypatch.setenv('SESSION_MEMORY_MAX_MESSAGES','8')
    settings=MemorySettings.from_env()
    assert settings.ttl==90 and settings.max_messages==8
    assert settings.redis_url=='redis://example.invalid:6380/2'


def test_store_enforces_window_on_save():
    async def check():
        client=FakeRedis();store=RedisSessionMemoryStore(client,max_messages=4)
        await store.save('A',SessionMemory(messages=[{'role':'user','content':str(i)} for i in range(8)]))
        saved=await store.load('A')
        assert [m['content'] for m in saved.messages]==['4','5','6','7']
    asyncio.run(check())


def test_eval_counts_wrong_host_as_failure():
    from scripts.eval_memory import evaluate
    records=[{'case':{'kind':'recall','expected_host':'alpha','expected_port':22},'response':{'trajectory':[{'arguments':{'host':'beta','port':22}}]}},
             {'case':{'kind':'isolation'},'response':{'trajectory':[{'arguments':{'host':'alpha'}}]}}]
    assert evaluate(records)['context_recall_accuracy']==0
    assert evaluate(records)['cross_session_leakage_rate']==1


def test_api_session_id_and_compact_response(tmp_path):
    from fastapi.testclient import TestClient
    from app.main import app,get_model,get_memory_store,get_trajectory_path
    store=FakeSessionMemoryStore()
    app.dependency_overrides[get_model]=lambda:ScriptedModel([AIMessage(content='Hello')])
    app.dependency_overrides[get_memory_store]=lambda:store
    app.dependency_overrides[get_trajectory_path]=lambda:tmp_path/'runs'
    try:
        with TestClient(app) as client:
            first=client.post('/api/agent/run',json={'message':'Hello'}).json()
            assert first['session_id'] and not first['memory_loaded']
            second=client.post('/api/agent/run',json={'message':'Again','session_id':first['session_id']}).json()
            assert second['memory_loaded'] and second['session_id']==first['session_id']
            assert 'messages' not in second and 'entities' not in second
        saved=[json.loads(line) for line in (tmp_path/'runs').read_text().splitlines()]
        assert saved[1]['memory_loaded'] and saved[1]['session_id']==first['session_id']
    finally:
        app.dependency_overrides.clear()
