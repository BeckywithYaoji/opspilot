import json

from langchain_core.messages import AIMessage

from app.agent import run_agent
from tests.test_agent import ScriptedModel, call


def test_agent_uses_discovered_mcp_schema_and_observations(tmp_path):
    class ObservationModel:
        def invoke(self, messages, tools):
            # The model gets discovered wire schemas, not executable Python tools.
            assert {tool['function']['name'] for tool in tools} == {
                    'check_port', 'check_service', 'restart_service', 'create_ticket', 'search_runbook', 'search_incident_memory'
            }
            last = messages[-1]
            if last.type == 'human':
                return call('restart_service', {'host': 'dev-server', 'service': 'sshd'})
            observation = json.loads(last.content)
            if observation.get('error') == 'permission denied':
                return call('create_ticket', {'title': 'SSH unavailable', 'description': 'permission denied'}, '2')
            assert observation['status'] == 'created'
            return AIMessage(content='Escalated: ' + observation['ticket_id'])

    result = run_agent('处理 SSH', 'permission_denied', ObservationModel(), trajectory_path=tmp_path / 'runs.jsonl')
    assert result.agent_status == 'COMPLETED'
    assert result.resolution_status == 'ESCALATED'
    assert result.environment_restored is False
    assert result.handled is True
    assert result.success is False  # V0 semantics retained.
    assert [s.transport for s in result.trajectory] == ['mcp', 'mcp']
    assert result.tickets[0]['ticket_id'] in result.answer


def test_repaired_result_adds_unambiguous_resolution_fields(tmp_path):
    model = ScriptedModel([
        call('restart_service', {'host': 'dev-server', 'service': 'sshd'}),
        AIMessage(content='Repaired.'),
    ])
    result = run_agent('repair', 'repairable', model, trajectory_path=tmp_path / 'runs.jsonl')
    assert result.resolution_status == 'RESOLVED'
    assert result.environment_restored is result.success is True
    assert result.handled is True


def test_unavailable_server_returns_failed_and_saves_trajectory(monkeypatch, tmp_path):
    from app.mcp.client import OpsMCPClient
    monkeypatch.setattr('app.agent.OpsMCPClient',
                        lambda scenario: OpsMCPClient(scenario, command='/nonexistent/opspilot-python'))
    path = tmp_path / 'runs.jsonl'
    result = run_agent('test', 'repairable', ScriptedModel([]), trajectory_path=path)
    assert result.status == 'FAILED'
    assert result.resolution_status == 'FAILED'
    assert result.handled is result.success is False
    assert result.environment == {}
    assert json.loads(path.read_text())['status'] == 'FAILED'


def test_disconnection_observation_reaches_model_and_steps_survive(monkeypatch, tmp_path):
    from tests.test_mcp import fault_client
    monkeypatch.setattr('app.agent.OpsMCPClient', lambda scenario: fault_client())
    model = ScriptedModel([
        call('probe', {'mode': 'disconnect'}),
        AIMessage(content='MCP unavailable.'),
    ])
    path = tmp_path / 'runs.jsonl'
    result = run_agent('test', 'repairable', model, trajectory_path=path)
    assert json.loads(model.seen[-1][-1].content)['error'] == 'MCP server unavailable'
    assert result.status == 'FAILED'  # Final environment cannot be read after disconnect.
    assert result.success is result.handled is False
    assert len(result.trajectory) == 1
    assert json.loads(path.read_text())['steps'][0]['observation']['error'] == 'MCP server unavailable'
