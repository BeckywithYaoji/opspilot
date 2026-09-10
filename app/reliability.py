"""Small, domain-neutral controls for agent tool execution."""
import json
from dataclasses import dataclass, field
from typing import Any


def tool_signature(name: str, arguments: dict[str, Any], revision: int) -> tuple[str, str, int]:
    normalized = json.dumps(arguments, sort_keys=True, separators=(',', ':'), ensure_ascii=False).strip().lower()
    return name.strip().lower(), normalized, revision


@dataclass
class ReliabilityRuntime:
    max_total_tool_calls: int = 8
    max_retrieval_calls: int = 2
    max_same_tool_signature_calls: int = 2
    tool_call_count: int = 0
    retrieval_call_count: int = 0
    state_revision: int = 0
    blocked_actions: int = 0
    signatures: dict[tuple[str, str, int], int] = field(default_factory=dict)

    def admit(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        if self.tool_call_count >= self.max_total_tool_calls:
            self.blocked_actions += 1
            return {'blocked': True, 'block_reason': 'tool_budget_exceeded', 'observation': {'status': 'blocked', 'reason': 'tool_budget_exceeded', 'message': 'Tool budget exhausted.'}}
        if name == 'search_runbook' and self.retrieval_call_count >= self.max_retrieval_calls:
            self.blocked_actions += 1
            return {'blocked': True, 'block_reason': 'retrieval_budget_exceeded', 'observation': {'status': 'blocked', 'reason': 'retrieval_budget_exceeded', 'message': 'Existing retrieved evidence should be reused unless the task has changed.'}}
        sig = tool_signature(name, arguments, self.state_revision)
        repeats = self.signatures.get(sig, 0)
        if repeats >= self.max_same_tool_signature_calls:
            self.blocked_actions += 1
            return {'blocked': True, 'block_reason': 'repeated_action', 'observation': {'status': 'blocked', 'reason': 'repeated_action', 'message': 'This tool call substantially duplicates an earlier action. Reuse the existing observation or choose a different action.'}}
        self.signatures[sig] = repeats + 1
        self.tool_call_count += 1
        if name == 'search_runbook': self.retrieval_call_count += 1
        return {'blocked': False, 'repeated': repeats > 0, 'state_revision': self.state_revision}

    def record_observation(self, name: str, observation: dict[str, Any]) -> None:
        if name in {'restart_service'} and observation.get('status') == 'success':
            self.state_revision += 1
