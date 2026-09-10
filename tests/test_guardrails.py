import asyncio
import pytest
from app.guardrails.permissions import decide_permission
from app.approval import ApprovalStore, PendingApproval
from app.agent import run_agent
from tests.test_agent import ScriptedModel, call
from langchain_core.messages import AIMessage

@pytest.mark.parametrize('tool,decision,risk',[('check_port','ALLOW','READ_ONLY'),('search_runbook','ALLOW','READ_ONLY'),('search_incident_memory','ALLOW','READ_ONLY'),('create_ticket','ALLOW','READ_ONLY'),('restart_service','REQUIRE_APPROVAL','STATE_CHANGING')])
def test_tool_policy(tool,decision,risk):
    result=decide_permission(tool,{})
    assert result.decision==decision and result.risk_level==risk

def test_approval_replay_is_rejected():
    async def check():
        store=ApprovalStore(); item=PendingApproval(task_id='t',tool_name='restart_service',arguments={},risk_level='STATE_CHANGING',reason_code='state_changing_operation')
        await store.save(item); await store.resolve(item,'APPROVED')
        with pytest.raises(ValueError,match='already_resolved'): await store.resolve(item,'APPROVED')
    asyncio.run(check())

def test_unknown_tool_denied():
    assert decide_permission('unknown',{}).decision=='DENY'

def test_restart_is_pending_before_mcp_execution(tmp_path):
    store=ApprovalStore()
    result=run_agent('repair', 'repairable', ScriptedModel([call('restart_service', {'host':'dev-server','service':'sshd'})]), trajectory_path=tmp_path/'run', approval_store=store)
    assert result.status=='AWAITING_APPROVAL' and result.pending_approval['tool_name']=='restart_service'
    item=asyncio.run(store.load(result.pending_approval['approval_id']))
    assert item.status=='PENDING'
