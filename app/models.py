from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


Status = Literal['RUNNING', 'COMPLETED', 'MAX_STEPS_EXCEEDED', 'FAILED']
Scenario = Literal['repairable', 'permission_denied']


class RunRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    message: str = Field(min_length=1, max_length=10000)
    scenario: Scenario = 'repairable'

    @field_validator('message')
    @classmethod
    def nonblank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('message cannot be blank')
        return value


class TrajectoryStep(BaseModel):
    step: int
    tool: str
    arguments: dict[str, Any]
    observation: dict[str, Any]


class RunResponse(BaseModel):
    task_id: str
    answer: str
    status: Status
    success: bool
    environment: dict[str, Any]
    trajectory: list[TrajectoryStep]
    tickets: list[dict[str, str]] = Field(default_factory=list)
