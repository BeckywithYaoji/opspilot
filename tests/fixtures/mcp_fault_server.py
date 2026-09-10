"""Test-only MCP peer for failures; never used by the production application."""
import os

from mcp.server import MCPServer
from mcp.types import CallToolResult, TextContent

server = MCPServer('fault-test-peer', log_level='ERROR')


@server.tool()
def probe(mode: str) -> CallToolResult:
    if mode == 'disconnect':
        os._exit(1)
    if mode == 'error':
        return CallToolResult(content=[TextContent(type='text', text='private implementation details')], is_error=True)
    if mode == 'json_text':
        return CallToolResult(content=[TextContent(type='text', text='{"status":"open"}')])
    if mode == 'invalid_json':
        return CallToolResult(content=[TextContent(type='text', text='not-json')])
    return CallToolResult(content=[], structured_content={'unexpected': 42})


@server.resource('ops://environment')
def snapshot() -> str:
    return '{}'


if __name__ == '__main__':
    server.run(transport='stdio')
