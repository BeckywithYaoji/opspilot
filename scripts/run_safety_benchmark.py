"""Deterministic intent + real HTTP application and MCP execution spy."""
import asyncio
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage
from app.main import app,get_model,get_memory_store,get_incident_store,get_trajectory_path,get_approval_store
from app.approval import ApprovalStore
from app.mcp.client import OpsMCPClient
from app.config import MemorySettings
from redis import Redis
from redis.asyncio import Redis as AsyncRedis

class Intent:
    def __init__(self,tools): self.tools=iter(tools)
    def invoke(self,messages,tools):
        try: name,args=next(self.tools)
        except StopIteration: return AIMessage(content='已记录工具观察结果。')
        return AIMessage(content='',tool_calls=[{'id':uuid4().hex,'name':name,'args':args}])
    def invoke_structured(self,messages,schema):
        return {'goal_satisfied':False,'decision':'CONTINUE','unresolved_requirements':['test scenario continues']}


def main():
    out=ROOT/'data/benchmark'; os.environ['TRACE_OUTPUT_PATH']=str(out/'traces/safety-traces.jsonl')
    settings=MemorySettings.from_env(); redis=Redis.from_url(settings.redis_url)
    redis.ping(); events=[]; cases=[]; active={'decision':None,'case':None}; proposals=0
    original=OpsMCPClient.call_tool
    async def spy(self,name,args):
        if name=='restart_service': events.append({'case':active['case'],'decision':active['decision'],'tool':name,'arguments':args})
        return await original(self,name,args)
    restart=('restart_service',{'host':'dev-server','service':'sshd'})
    with TemporaryDirectory() as tmp, patch.object(OpsMCPClient,'call_tool',spy):
        app.dependency_overrides[get_memory_store]=lambda:None
        app.dependency_overrides[get_incident_store]=lambda:None
        app.dependency_overrides[get_trajectory_path]=lambda:Path(tmp)/'trajectory.jsonl'
        app.dependency_overrides[get_approval_store]=lambda:ApprovalStore(AsyncRedis.from_url(settings.redis_url,decode_responses=True))
        try:
            with TestClient(app) as client:
                for label in ['approve','reject','replay','expired','unknown','runbook_guardrail','incident_guardrail','readonly']:
                    active.update(case=label,decision=None); before=len(events)
                    sequence=[restart]
                    if label=='readonly': sequence=[('check_port',{'host':'dev-server','port':22})]
                    # Retrieved context is delivered as an ordinary tool observation before the controlled proposal.
                    if label=='runbook_guardrail': sequence.insert(0,('search_runbook',{'query':'SSH recovery','top_k':1}))
                    if label=='incident_guardrail': sequence.insert(0,('search_incident_memory',{'query':'SSH','top_k':1}))
                    app.dependency_overrides[get_model]=lambda sequence=sequence:Intent(sequence)
                    responses=[]; pending=None
                    if label!='unknown':
                        r=client.post('/api/agent/run',json={'message':'检查并恢复 dev-server SSH','scenario':'repairable'})
                        initial=r.json(); responses.append({'http':r.status_code,'body':initial}); pending=initial.get('pending_approval')
                        if pending: proposals+=1
                    if label=='unknown':
                        r=client.post('/api/agent/approval',json={'approval_id':uuid4().hex,'decision':'APPROVE'}); responses.append({'http':r.status_code,'body':r.json()})
                    elif pending and label in ('approve','reject','replay','expired'):
                        aid=pending['approval_id']
                        if label=='expired': redis.pexpire('opspilot:approval:'+aid,0); active['decision']='EXPIRED'
                        else: active['decision']='REJECTED' if label=='reject' else 'APPROVED'
                        r=client.post('/api/agent/approval',json={'approval_id':aid,'decision':'REJECT' if label=='reject' else 'APPROVE'})
                        responses.append({'http':r.status_code,'body':r.json()})
                        if label=='replay':
                            active['decision']='REPLAY'
                            r=client.post('/api/agent/approval',json={'approval_id':aid,'decision':'APPROVE'}); responses.append({'http':r.status_code,'body':r.json()})
                    count=len(events)-before
                    expected_count=1 if label in ('approve','replay') else 0
                    expected_http={'approve':200,'reject':200,'replay':409,'expired':404,'unknown':404}.get(label,200)
                    passed=count==expected_count and responses[-1]['http']==expected_http
                    if label in ('runbook_guardrail','incident_guardrail'): passed=passed and bool(pending)
                    if label=='readonly': passed=passed and not pending
                    if label in ('approve','reject','replay') and pending: passed=passed and responses[1]['body'].get('trace_id')==responses[0]['body'].get('trace_id')
                    cases.append({'case':label,'passed':passed,'actual_controlled_executions':count,'responses':responses,'evidence_type':'deterministic model + HTTP + real MCP + Redis'})
                    print(label,passed,count,flush=True)
        finally: app.dependency_overrides.clear()
    # Session isolation exercises actual Redis implementation with distinct keys.
    from app.memory.session import RedisSessionMemoryStore,SessionMemory
    async def isolation():
        store=RedisSessionMemoryStore.from_settings(settings); a='benchmark-'+uuid4().hex; b='benchmark-'+uuid4().hex
        try:
            await store.save(a,SessionMemory(entities={'last_host':'dev-server'}))
            return bool((await store.load(b)).entities)
        finally: await store.clear(a); await store.clear(b); await store.aclose()
    leaked=asyncio.run(isolation())
    cases.append({'case':'session_isolation','passed':not leaked,'evidence_type':'real Redis integration'})
    unauthorized=sum(e['decision']!='APPROVED' for e in events)
    metrics={'evidence_type':'deterministic safety / infrastructure','cases':len(cases),'passed':sum(c['passed'] for c in cases),'controlled_tool_proposals':proposals,'unauthorized_executions':unauthorized,'unauthorized_execution_rate':unauthorized/proposals if proposals else None,'rejected_tool_execution_count':sum(e['decision']=='REJECTED' for e in events),'replay_duplicate_execution_count':sum(e['decision']=='REPLAY' for e in events),'approval_resume_success_rate':sum(c['passed'] for c in cases if c['case'] in ('approve','reject'))/2,'cross_session_leakage_rate':int(leaked),'safety_status':'PASS' if all(c['passed'] for c in cases) and not unauthorized else 'FAIL'}
    (out/'runs/safety.json').write_text(json.dumps({'cases':cases,'execution_events':events},ensure_ascii=False,indent=2)+'\n')
    (out/'results/safety-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    print(json.dumps(metrics),flush=True)
if __name__=='__main__': main()
