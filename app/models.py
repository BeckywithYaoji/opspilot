from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator


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
    transport: Literal['local', 'mcp'] = 'local'
    repeated: bool = False
    blocked: bool = False
    block_reason: str | None = None
    state_revision: int = 0
    goal_satisfied_after_step: bool = False
    completion_decision: str | None = None
    completion_verifier_error: str | None = None
    unresolved_requirements: list[str] = Field(default_factory=list)


class RunResponse(BaseModel):
    goal_satisfied_at_step: int | None = None
    task_id: str
    answer: str
    status: Status
    success: bool
    environment: dict[str, Any]
    trajectory: list[TrajectoryStep]
    tickets: list[dict[str, str]] = Field(default_factory=list)

    @computed_field
    @property
    def agent_status(self) -> Status:
        return self.status

    @computed_field
    @property
    def environment_restored(self) -> bool:
        return self.success

    @computed_field
    @property
    def resolution_status(self) -> Literal['RESOLVED', 'ESCALATED', 'FAILED']:
        if self.success:
            return 'RESOLVED'
        if self.tickets:
            return 'ESCALATED'
        return 'FAILED'

    @computed_field
    @property
    def handled(self) -> bool:
        return self.status == 'COMPLETED' and self.resolution_status != 'FAILED'
