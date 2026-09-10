"""Lightweight goal completion judgment used after tool observations."""
from pydantic import BaseModel
from typing import Literal, Any

class GoalCompletionResult(BaseModel):
    goal_satisfied: bool
    decision: Literal['CONTINUE','FINISH']
    unresolved_requirements: list[str] = []

def verify_goal(query: str, steps: list[Any], environment: dict) -> GoalCompletionResult:
    text = query.lower()
    latest = steps[-1].observation if steps else {}
    if latest.get('status') == 'created':
        return GoalCompletionResult(goal_satisfied=True, decision='FINISH')
    if latest.get('error') == 'permission denied':
        return GoalCompletionResult(goal_satisfied=False, decision='CONTINUE', unresolved_requirements=['manual intervention or incident ticket is still required'])
    if 'port' in text and latest.get('status') in {'open','closed','unreachable'} and 'restore' not in text and '恢复' not in query:
        return GoalCompletionResult(goal_satisfied=True, decision='FINISH')
    server = environment.get('dev-server', {})
    if server.get('services', {}).get('sshd') == 'running' and server.get('ports', {}).get(22) is True:
        return GoalCompletionResult(goal_satisfied=True, decision='FINISH')
    return GoalCompletionResult(goal_satisfied=False, decision='CONTINUE', unresolved_requirements=['the requested outcome is not yet verified'])
