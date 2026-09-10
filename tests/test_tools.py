from app.environment import MockEnvironment
from app.tools import build_tools


def test_tools_operate_on_shared_environment_and_store_ticket():
    env = MockEnvironment('repairable')
    tools = build_tools(env)
    assert set(tools) == {'check_port', 'check_service', 'restart_service', 'create_ticket'}
    assert tools['check_service'].invoke({'host': 'dev-server', 'service': 'sshd'})['status'] == 'stopped'
    tools['restart_service'].invoke({'host': 'dev-server', 'service': 'sshd'})
    assert tools['check_port'].invoke({'host': 'dev-server', 'port': 22})['status'] == 'open'
    ticket = tools['create_ticket'].invoke({'title': 'SSH unavailable', 'description': 'Permission denied'})
    assert ticket['status'] == 'created'
    assert env.tickets[0]['ticket_id'] == ticket['ticket_id']
    assert env.tickets[0]['description'] == 'Permission denied'
