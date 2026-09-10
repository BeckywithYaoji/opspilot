from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException

from app.agent import run_agent
from app.config import CompatibleChatModel, MemorySettings
from app.memory.session import RedisSessionMemoryStore
from app.memory.incident import IncidentMemoryStore, IncidentExtractor
from app.approval import ApprovalStore
from redis.asyncio import Redis
from app.models import RunRequest, RunResponse
from app.trajectory import DEFAULT_PATH
from app.observability import LocalTracer


app = FastAPI(title='OpsPilot V1 MCP', docs_url=None, redoc_url=None, openapi_url=None)


def get_model() -> CompatibleChatModel:
    return CompatibleChatModel()


def get_trajectory_path() -> Path:
    return DEFAULT_PATH


def get_memory_store():
    settings = MemorySettings.from_env()
    return RedisSessionMemoryStore.from_settings(settings) if settings.redis_url else None

def get_incident_store():
    # Local Qdrant uses a process lock per storage directory; incidents have
    # their own directory while remaining on the same Qdrant implementation.
    return IncidentMemoryStore('data/qdrant-incidents')

def get_approval_store():
    settings=MemorySettings.from_env()
    return ApprovalStore(Redis.from_url(settings.redis_url, decode_responses=True), ttl=int(__import__('os').environ.get('APPROVAL_TTL_SECONDS','1800'))) if settings.redis_url else ApprovalStore()


@app.get('/health')
def health() -> dict:
    return {'status': 'ok'}


@app.post('/api/agent/run', response_model=RunResponse)
def run(request: RunRequest, model=Depends(get_model), path: Path = Depends(get_trajectory_path), memory_store=Depends(get_memory_store), incident_store=Depends(get_incident_store), approval_store=Depends(get_approval_store)) -> RunResponse:
    try:
        result = run_agent(request.message, request.scenario, model, trajectory_path=path, session_id=request.session_id, memory_store=memory_store, approval_store=approval_store)
        try:
            record = IncidentExtractor.extract(request.message, result)
            if record is not None: incident_store.save(record)
        except Exception:
            result.incident_memory_error = 'incident_memory_write_failed'
        return result
    except OSError:
        raise HTTPException(status_code=500, detail='Unable to save trajectory') from None

@app.post('/api/agent/approval')
async def approval(payload: dict, store=Depends(get_approval_store)) -> dict:
    aid=payload.get('approval_id'); decision=payload.get('decision')
    if decision not in {'APPROVE','REJECT'}: raise HTTPException(status_code=422, detail='decision must be APPROVE or REJECT')
    item=await store.load(aid) if aid else None
    if item is None: raise HTTPException(status_code=404, detail='approval_not_found')
    if item.status != 'PENDING':
        if item.trace_id: LocalTracer.append_event(item.trace_id, 'approval.replay_blocked', metadata={'approval_id':aid,'reason':'already_resolved'}, status='BLOCKED')
        raise HTTPException(status_code=409, detail='approval_already_resolved')
    final='APPROVED' if decision=='APPROVE' else 'REJECTED'
    await store.resolve(item, final)
    if item.trace_id:
        LocalTracer.append_event(item.trace_id, 'approval.resolved', metadata={'approval_id':aid,'decision':final})
        LocalTracer.append_event(item.trace_id, 'approval.resume', metadata={'approval_id':aid,'resume_success':True})
    if decision == 'REJECT':
        return {'status':'rejected','approval_id':aid,'trace_id':item.trace_id,'tool':item.tool_name,'observation':{'status':'rejected','reason':'human_rejected_action','tool':item.tool_name}}
    async def execute():
        from app.mcp.client import OpsMCPClient
        async with OpsMCPClient(item.scenario) as client:
            obs=await client.call_tool(item.tool_name,item.arguments)
            snap=await client.snapshot()
            return obs,snap
    obs,snap=await execute()
    if item.trace_id:
        LocalTracer.append_event(item.trace_id, 'tool.'+item.tool_name, 'TOOL', {'tool_name':item.tool_name}, status='ERROR' if obs.get('status') in {'failed','error'} else 'OK')
    return {'status':'approved','approval_id':aid,'trace_id':item.trace_id,'tool':item.tool_name,'observation':obs,'environment':snap['environment'],'environment_restored':snap['environment_restored']}
