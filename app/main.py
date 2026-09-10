from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException

from app.agent import run_agent
from app.config import CompatibleChatModel
from app.models import RunRequest, RunResponse
from app.trajectory import DEFAULT_PATH


app = FastAPI(title='OpsPilot V1 MCP', docs_url=None, redoc_url=None, openapi_url=None)


def get_model() -> CompatibleChatModel:
    return CompatibleChatModel()


def get_trajectory_path() -> Path:
    return DEFAULT_PATH


@app.get('/health')
def health() -> dict:
    return {'status': 'ok'}


@app.post('/api/agent/run', response_model=RunResponse)
def run(request: RunRequest, model=Depends(get_model), path: Path = Depends(get_trajectory_path)) -> RunResponse:
    try:
        return run_agent(request.message, request.scenario, model, trajectory_path=path)
    except OSError:
        raise HTTPException(status_code=500, detail='Unable to save trajectory') from None
