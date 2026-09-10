import json

from langchain_core.messages import AIMessage, ToolMessage

from app.agent import SYSTEM_PROMPT, run_agent
from tests.test_agent import ScriptedModel, call


def test_simple_port_task_does_not_retrieve(tmp_path):
    model = ScriptedModel([
        call('check_port', {'host': 'dev-server', 'port': 22}),
        AIMessage(content='端口已确认。'),
    ])
    result = run_agent('检查 22 端口', 'repairable', model, trajectory_path=tmp_path / 'runs.jsonl')
    assert result.status == 'COMPLETED'
    assert [step.tool for step in result.trajectory] == ['check_port']


def test_runbook_required_task_retrieves_then_calls_ops_tool(tmp_path):
    class SchemaCheckingModel(ScriptedModel):
        def invoke(self, messages, tools):
            assert {tool['function']['name'] for tool in tools} == {
                'check_port', 'check_service', 'restart_service', 'create_ticket', 'search_runbook'
            }
            return super().invoke(messages, tools)

    model = SchemaCheckingModel([
        call('search_runbook', {'query': 'SSH service recovery'}),
        call('check_service', {'host': 'dev-server', 'service': 'sshd'}, 'ops-1'),
        AIMessage(content='已根据运行手册完成检查。'),
    ])
    result = run_agent('按照运行手册诊断 SSH 服务', 'repairable', model,
                       trajectory_path=tmp_path / 'runs.jsonl')
    assert [step.tool for step in result.trajectory] == ['search_runbook', 'check_service']
    assert isinstance(model.seen[1][-1], ToolMessage)
    assert json.loads(model.seen[1][-1].content)['status'] in {'ok', 'error'}


def test_permission_flow_can_retrieve_then_escalate_after_denial(tmp_path):
    model = ScriptedModel([
        call('search_runbook', {'query': 'permission denied restart'}),
        call('restart_service', {'host': 'dev-server', 'service': 'sshd'}, 'restart-1'),
        call('create_ticket', {'title': 'SSH unavailable', 'description': 'permission denied'}, 'ticket-1'),
        AIMessage(content='权限不足，已创建工单。'),
    ])
    result = run_agent('SSH 重启被拒绝，请按手册处理', 'permission_denied', model,
                       trajectory_path=tmp_path / 'runs.jsonl')
    assert [step.tool for step in result.trajectory] == [
        'search_runbook', 'restart_service', 'create_ticket']
    assert json.loads(model.seen[2][-1].content)['error'] == 'permission denied'
    assert result.tickets


def test_prompt_describes_selective_retrieval_and_observation_loop():
    assert 'search_runbook' in SYSTEM_PROMPT
    assert '问题需要操作手册' in SYSTEM_PROMPT
    assert 'Observation' in SYSTEM_PROMPT
