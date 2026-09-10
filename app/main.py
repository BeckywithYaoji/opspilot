from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException

from app.agent import run_agent
from app.config import CompatibleChatModel, MemorySettings
from app.memory.session import RedisSessionMemoryStore
from app.models import RunRequest, RunResponse
from app.trajectory import DEFAULT_PATH


app = FastAPI(title='OpsPilot V1 MCP', docs_url=None, redoc_url=None, openapi_url=None)


def get_model() -> CompatibleChatModel:
    return CompatibleChatModel()


def get_trajectory_path() -> Path:
    return DEFAULT_PATH


def get_memory_store():
    settings = MemorySettings.from_env()
    return RedisSessionMemoryStore.from_settings(settings) if settings.redis_url else None


@app.get('/health')
def health() -> dict:
    return {'status': 'ok'}


@app.post('/api/agent/run', response_model=RunResponse)
def run(request: RunRequest, model=Depends(get_model), path: Path = Depends(get_trajectory_path), memory_store=Depends(get_memory_store)) -> RunResponse:
    try:
        return run_agent(request.message, request.scenario, model, trajectory_path=path, session_id=request.session_id, memory_store=memory_store)
    except OSError:
        raise HTTPException(status_code=500, detail='Unable to save trajectory') from None
