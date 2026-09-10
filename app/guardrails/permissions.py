from typing import Literal
from pydantic import BaseModel

class PermissionDecision(BaseModel):
    decision: Literal['ALLOW','REQUIRE_APPROVAL','DENY']
    risk_level: Literal['READ_ONLY','STATE_CHANGING','SENSITIVE']
    reason_code: str

TOOL_POLICIES = {
    'check_port': ('READ_ONLY','ALLOW'), 'check_service': ('READ_ONLY','ALLOW'),
    'search_runbook': ('READ_ONLY','ALLOW'), 'search_incident_memory': ('READ_ONLY','ALLOW'),
    'create_ticket': ('READ_ONLY','ALLOW'), 'restart_service': ('STATE_CHANGING','REQUIRE_APPROVAL'),
}

def decide_permission(tool_name: str, arguments: dict) -> PermissionDecision:
    risk, decision = TOOL_POLICIES.get(tool_name, ('SENSITIVE','DENY'))
    reason = 'state_changing_operation' if decision == 'REQUIRE_APPROVAL' else ('unknown_tool' if decision == 'DENY' else 'read_only_operation')
    return PermissionDecision(decision=decision, risk_level=risk, reason_code=reason)
