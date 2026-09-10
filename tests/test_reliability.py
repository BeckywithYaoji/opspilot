from app.reliability import ReliabilityRuntime


def test_tool_budget_blocks_next_action():
    r = ReliabilityRuntime(max_total_tool_calls=1)
    assert not r.admit('check_port', {'host': 'dev-server', 'port': 22})['blocked']
    assert r.admit('check_service', {'host': 'dev-server', 'service': 'sshd'})['block_reason'] == 'tool_budget_exceeded'


def test_retrieval_budget_blocks_third_search():
    r = ReliabilityRuntime(max_retrieval_calls=2)
    for _ in range(2): assert not r.admit('search_runbook', {'query': 'ssh'})['blocked']
    assert r.admit('search_runbook', {'query': 'ssh'})['block_reason'] == 'retrieval_budget_exceeded'


def test_repeated_action_and_revision_allows_verification():
    r = ReliabilityRuntime(max_same_tool_signature_calls=2)
    args = {'host': 'dev-server', 'service': 'sshd'}
    assert not r.admit('check_service', args)['blocked']
    assert r.admit('check_service', args)['repeated']
    assert r.admit('check_service', args)['block_reason'] == 'repeated_action'
    r.record_observation('restart_service', {'status': 'success'})
    assert not r.admit('check_service', args)['blocked']
