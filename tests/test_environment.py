from app.environment import MockEnvironment


def test_restart_changes_service_and_port():
    env = MockEnvironment('repairable')
    assert env.restart_service('dev-server', 'sshd')['status'] == 'success'
    assert env.servers['dev-server']['services']['sshd'] == 'running'
    assert env.servers['dev-server']['ports'][22] is True


def test_permission_failure_does_not_mutate_environment():
    env = MockEnvironment('permission_denied')
    before = env.snapshot()
    assert env.restart_service('dev-server', 'sshd') == {
        'status': 'failed', 'error': 'permission denied'
    }
    assert env.snapshot() == before


def test_environments_are_isolated():
    first, second = MockEnvironment('repairable'), MockEnvironment('repairable')
    first.restart_service('dev-server', 'sshd')
    assert second.check_port('dev-server', 22)['status'] == 'closed'


def test_unreachable_and_unknown_resources():
    env = MockEnvironment('repairable')
    assert env.check_port('missing', 22)['status'] == 'failed'
    assert env.restart_service('dev-server', 'missing')['status'] == 'failed'
    env.servers['dev-server']['reachable'] = False
    assert env.check_port('dev-server', 22)['status'] == 'unreachable'
    assert env.restart_service('dev-server', 'sshd')['status'] == 'failed'
    assert env.servers['dev-server']['services']['sshd'] == 'stopped'
