import asyncio

import pytest

from app.mcp.client import OpsMCPClient, MCPUnavailable


def test_mcp_discovery_port_and_state_mutation():
    async def exercise():
        async with OpsMCPClient('repairable') as client:
            tools = await client.list_tools()
            assert {t['function']['name'] for t in tools} == {
            'check_port', 'check_service', 'restart_service', 'create_ticket', 'search_runbook', 'search_incident_memory'
            }
            port_tool = next(t['function'] for t in tools if t['function']['name'] == 'check_port')
            assert set(port_tool['parameters']['required']) == {'host', 'port'}
            assert port_tool['parameters']['properties']['port']['minimum'] == 1
            assert (await client.call_tool('check_port', {'host': 'dev-server', 'port': 22}))['status'] == 'closed'
            assert (await client.call_tool('restart_service', {'host': 'dev-server', 'service': 'sshd'}))['status'] == 'success'
            snapshot = await client.snapshot()
            assert snapshot['environment']['dev-server']['services']['sshd'] == 'running'
            assert snapshot['environment']['dev-server']['ports'][22] is True
            assert snapshot['environment_restored'] is True
    asyncio.run(exercise())


def test_mcp_permission_denied_and_ticket():
    async def exercise():
        async with OpsMCPClient('permission_denied') as client:
            assert await client.call_tool('restart_service', {'host': 'dev-server', 'service': 'sshd'}) == {
                'status': 'failed', 'error': 'permission denied'
            }
            ticket = await client.call_tool('create_ticket', {'title': 'SSH down', 'description': 'Permission denied'})
            snapshot = await client.snapshot()
            assert snapshot['environment']['dev-server']['services']['sshd'] == 'stopped'
            assert snapshot['environment']['dev-server']['ports'][22] is False
            assert snapshot['tickets'][0]['ticket_id'] == ticket['ticket_id']
    asyncio.run(exercise())


def test_mcp_unknown_tool_and_invalid_arguments():
    async def exercise():
        async with OpsMCPClient('repairable') as client:
            assert await client.call_tool('missing', {}) == {'status': 'failed', 'error': 'tool not found'}
            assert await client.call_tool('check_port', {'host': 'dev-server', 'port': -1}) == {
                'status': 'failed', 'error': 'invalid tool arguments'
            }
    asyncio.run(exercise())


def test_mcp_processes_isolate_state():
    async def exercise():
        async with OpsMCPClient('repairable') as first, OpsMCPClient('repairable') as second:
            await first.call_tool('restart_service', {'host': 'dev-server', 'service': 'sshd'})
            assert (await second.call_tool('check_port', {'host': 'dev-server', 'port': 22}))['status'] == 'closed'
    asyncio.run(exercise())


def test_mcp_server_unavailable():
    async def exercise():
        with pytest.raises(MCPUnavailable, match='MCP server unavailable'):
            async with OpsMCPClient('repairable', command='/nonexistent/opspilot-python'):
                pytest.fail('unavailable server connected')
    asyncio.run(exercise())


def fault_client():
    import sys
    from pathlib import Path
    from mcp import Client, StdioServerParameters
    client = OpsMCPClient('repairable')
    client.client = Client(StdioServerParameters(
        command=sys.executable,
        args=[str(Path(__file__).parent / 'fixtures' / 'mcp_fault_server.py')],
    ), read_timeout_seconds=2)
    return client


@pytest.mark.parametrize('mode,expected', [
    ('error', {'status': 'failed', 'error': 'MCP tool call failed'}),
    ('malformed', {'status': 'failed', 'error': 'malformed MCP tool result'}),
    ('invalid_json', {'status': 'failed', 'error': 'malformed MCP tool result'}),
    ('json_text', {'status': 'open'}),
    ('disconnect', {'status': 'failed', 'error': 'MCP server unavailable'}),
])
def test_real_mcp_failure_results_are_normalized(mode, expected):
    async def exercise():
        async with fault_client() as client:
            assert await client.call_tool('probe', {'mode': mode}) == expected
    asyncio.run(exercise())


def test_malformed_snapshot_cannot_claim_restoration():
    async def exercise():
        async with fault_client() as client:
            with pytest.raises(MCPUnavailable, match='snapshot unavailable'):
                await client.snapshot()
    asyncio.run(exercise())
