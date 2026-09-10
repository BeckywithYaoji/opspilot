import asyncio
import inspect

from app.mcp.client import OpsMCPClient
from app.mcp.server import create_server


class _Result:
    is_error = False
    structured_content = {
        'status': 'ok', 'query': 'ssh', 'results': [],
    }
    content = []


def test_server_default_index_matches_index_script():
    assert inspect.signature(create_server).parameters['index_path'].default == 'data/qdrant'


def test_search_runbook_result_is_structured():
    async def exercise():
        client = OpsMCPClient('repairable')
        client.tools = [{
            'type': 'function',
            'function': {
                'name': 'search_runbook',
                'description': '',
                'parameters': {
                    'type': 'object',
                    'properties': {
                        'query': {'type': 'string', 'minLength': 1},
                        'top_k': {'type': 'integer', 'minimum': 1, 'maximum': 20},
                    },
                    'required': ['query'],
                },
            },
        }]
        async def call_tool(name, arguments, read_timeout_seconds=None):
            assert read_timeout_seconds == 60
            return _Result()
        client.client.call_tool = call_tool
        assert await client.call_tool('search_runbook', {'query': 'ssh', 'top_k': 3}) == {
            'status': 'ok', 'query': 'ssh', 'results': [],
        }
    asyncio.run(exercise())


def test_search_runbook_validates_top_k():
    async def exercise():
        client = OpsMCPClient('repairable')
        client.tools = [{
            'type': 'function', 'function': {
                'name': 'search_runbook', 'description': '',
                'parameters': {
                    'type': 'object', 'properties': {
                        'query': {'type': 'string', 'minLength': 1},
                        'top_k': {'type': 'integer', 'minimum': 1, 'maximum': 20},
                    }, 'required': ['query'],
                },
            },
        }]
        assert await client.call_tool('search_runbook', {'query': 'ssh', 'top_k': 0}) == {
            'status': 'failed', 'error': 'invalid tool arguments'
        }
    asyncio.run(exercise())


def test_search_runbook_unavailable_index_is_safe_error():
    async def exercise():
        client = OpsMCPClient('repairable')
        client.tools = [{
            'type': 'function', 'function': {
                'name': 'search_runbook', 'description': '',
                'parameters': {'type': 'object', 'properties': {'query': {'type': 'string'}}, 'required': ['query']},
            },
        }]
        class Failed:
            is_error = False
            structured_content = {'status': 'error', 'query': 'ssh', 'results': [], 'error': 'missing'}
            content = []
        async def call_tool(name, arguments, read_timeout_seconds=None):
            assert read_timeout_seconds == 60
            return Failed()
        client.client.call_tool = call_tool
        assert await client.call_tool('search_runbook', {'query': 'ssh'}) == {
            'status': 'failed', 'error': 'runbook retrieval unavailable'
        }
    asyncio.run(exercise())
