"""Independent MCP process. Only this side imports the operations implementation."""
import argparse
import json

from mcp.server import MCPServer

from app.environment import MockEnvironment
from app.tools import build_tools


def create_server(scenario: str) -> MCPServer:
    environment = MockEnvironment(scenario)
    server = MCPServer('ops-mcp-server', log_level='ERROR')
    for tool in build_tools(environment).values():
        server.add_tool(tool.func, name=tool.name, description=tool.description,
                        structured_output=True)

    @server.resource('ops://environment', mime_type='application/json')
    def snapshot() -> str:
        """Read final state for API reporting; not an LLM tool or an action."""
        return json.dumps({'environment': environment.snapshot(),
                           'environment_restored': environment.ssh_restored,
                           'tickets': environment.tickets}, ensure_ascii=False)

    return server


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='OpsPilot MCP stdio tool server')
    parser.add_argument('--scenario', choices=['repairable', 'permission_denied'], default='repairable')
    create_server(parser.parse_args().scenario).run(transport='stdio')
