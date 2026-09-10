import json

import pytest
from langchain_core.messages import AIMessage, ToolMessage

from app.agent import run_agent


def call(name, args, ident='call-1'):
    return AIMessage(content='', tool_calls=[{'name': name, 'args': args, 'id': ident}])


class ScriptedModel:
    """Only a test double: never loaded by the production API."""
    def __init__(self, replies):
        self.replies = iter(replies)
        self.seen = []

    def invoke(self, messages, tools):
        self.seen.append(list(messages))
        reply = next(self.replies)
        if isinstance(reply, Exception):
            raise reply
        return reply


def test_model_can_choose_service_first_and_observations_return_to_model(tmp_path):
    model = ScriptedModel([
        call('check_service', {'host': 'dev-server', 'service': 'sshd'}),
        call('restart_service', {'host': 'dev-server', 'service': 'sshd'}, 'call-2'),
        call('check_port', {'host': 'dev-server', 'port': 22}, 'call-3'),
        AIMessage(content='SSH 已恢复并验证。'),
    ])
    path = tmp_path / 'trajectories.jsonl'
    result = run_agent('恢复 SSH', 'repairable', model, trajectory_path=path)
    assert result.status == 'COMPLETED'
    assert result.success is True
    assert result.environment['dev-server']['ports'][22] is True
    observations = [m for m in model.seen[-1] if isinstance(m, ToolMessage)]
    assert [json.loads(m.content)['status'] for m in observations] == ['stopped', 'success', 'open']
    assert [m.tool_call_id for m in observations] == ['call-1', 'call-2', 'call-3']
    saved = json.loads(path.read_text())
    assert saved['total_steps'] == 3
    assert saved['steps'][0] == {
        'step': 1, 'tool': 'check_service',
        'arguments': {'host': 'dev-server', 'service': 'sshd'},
        'observation': {'host': 'dev-server', 'service': 'sshd', 'status': 'stopped'},
    }
    assert saved['answer'] == result.answer
    assert saved['task_id'] == result.task_id


def test_denied_observation_enables_model_escalation(tmp_path):
    model = ScriptedModel([
        call('restart_service', {'host': 'dev-server', 'service': 'sshd'}),
        call('create_ticket', {'title': 'SSH down', 'description': 'Restart permission denied'}, 'call-2'),
        AIMessage(content='权限不足，已创建工单。'),
    ])
    result = run_agent('处理 SSH', 'permission_denied', model, trajectory_path=tmp_path / 'runs.jsonl')
    assert json.loads(model.seen[1][-1].content)['error'] == 'permission denied'
    assert result.status == 'COMPLETED'
    assert result.success is False
    assert result.environment['dev-server']['services']['sshd'] == 'stopped'
    assert [s.tool for s in result.trajectory] == ['restart_service', 'create_ticket']
    assert len(result.tickets) == 1


def test_batch_tool_calls_cannot_exceed_budget(tmp_path):
    replies = AIMessage(content='', tool_calls=[
        {'name': 'create_ticket', 'args': {'title': 'x', 'description': 'y'}, 'id': str(i)}
        for i in range(3)
    ])
    result = run_agent('test', 'repairable', ScriptedModel([replies]), max_steps=2,
                       trajectory_path=tmp_path / 'runs.jsonl')
    assert result.status == 'MAX_STEPS_EXCEEDED'
    assert len(result.trajectory) == len(result.tickets) == 2


@pytest.mark.parametrize('final,status', [
    (AIMessage(content='端口关闭，尚未恢复。'), 'COMPLETED'),
    (call('check_port', {'host': 'dev-server', 'port': 22}, 'next'), 'MAX_STEPS_EXCEEDED'),
])
def test_budget_allows_final_answer_but_no_more_tools(tmp_path, final, status):
    model = ScriptedModel([call('check_port', {'host': 'dev-server', 'port': 22}), final])
    result = run_agent('test', 'repairable', model, max_steps=1, trajectory_path=tmp_path / 'runs.jsonl')
    assert result.status == status
    assert len(result.trajectory) == 1


def test_provider_failure_retains_prior_steps_without_exception_secrets(tmp_path):
    model = ScriptedModel([
        call('check_port', {'host': 'dev-server', 'port': 22}),
        RuntimeError('secret-api-key'),
    ])
    path = tmp_path / 'runs.jsonl'
    result = run_agent('test', 'repairable', model, trajectory_path=path)
    assert result.status == 'FAILED'
    assert len(result.trajectory) == 1
    assert 'secret-api-key' not in path.read_text()


def test_unknown_tool_and_invalid_arguments_are_observations(tmp_path):
    model = ScriptedModel([
        call('unknown', {}),
        call('check_port', {'host': 'dev-server', 'port': -1}, 'call-2'),
        AIMessage(content='无法继续。'),
    ])
    result = run_agent('test', 'repairable', model, trajectory_path=tmp_path / 'runs.jsonl')
    assert result.status == 'COMPLETED'
    assert [s.observation['status'] for s in result.trajectory] == ['failed', 'failed']
    assert json.loads(model.seen[-1][-1].content)['error'] == 'invalid tool arguments'


@pytest.mark.parametrize('ident', [None, ''])
def test_missing_tool_call_id_fails_before_mutation_and_is_logged(tmp_path, ident):
    model = ScriptedModel([call('restart_service', {'host': 'dev-server', 'service': 'sshd'}, ident)])
    path = tmp_path / 'runs.jsonl'
    result = run_agent('test', 'repairable', model, trajectory_path=path)
    assert result.status == 'FAILED'
    assert result.trajectory == []
    assert result.environment['dev-server']['services']['sshd'] == 'stopped'
    assert json.loads(path.read_text())['status'] == 'FAILED'
