"""Lightweight goal completion judgment used after tool observations."""
from pydantic import BaseModel
from typing import Literal, Any

class GoalCompletionResult(BaseModel):
    goal_satisfied: bool
    decision: Literal['CONTINUE','FINISH']
    unresolved_requirements: list[str] = []

def verify_goal(query: str, steps: list[Any], environment: dict) -> GoalCompletionResult:
    latest = steps[-1].observation if steps else {}
    if latest.get('status') == 'created':
        return GoalCompletionResult(goal_satisfied=True, decision='FINISH')
    if latest.get('error') == 'permission denied':
        return GoalCompletionResult(goal_satisfied=False, decision='CONTINUE', unresolved_requirements=['manual intervention or incident ticket is still required'])
    if latest.get('status') in {'open','running'} and len(steps) == 1:
        return GoalCompletionResult(goal_satisfied=True, decision='FINISH')
    if latest.get('status') == 'success' and environment:
        return GoalCompletionResult(goal_satisfied=True, decision='FINISH')
    return GoalCompletionResult(goal_satisfied=False, decision='CONTINUE', unresolved_requirements=['the requested outcome is not yet verified'])
