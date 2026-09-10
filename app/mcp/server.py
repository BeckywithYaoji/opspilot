"""Independent MCP process. Only this side imports the operations implementation."""
import argparse
import json
from pathlib import Path
from typing import Annotated, Any

from mcp.server import MCPServer
from pydantic import Field

from app.environment import MockEnvironment
from app.rag.retriever import RunbookRetriever
from app.tools import build_tools


def create_server(scenario: str, index_path: str | Path = 'data/qdrant') -> MCPServer:
    environment = MockEnvironment(scenario)
    retriever = RunbookRetriever(index_path)
    server = MCPServer('ops-mcp-server', log_level='ERROR')
    for tool in build_tools(environment).values():
        server.add_tool(tool.func, name=tool.name, description=tool.description,
                        structured_output=True)

    def search_runbook(query: Annotated[str, Field(min_length=1)],
                       top_k: Annotated[int, Field(ge=1, le=20)] = 4) -> dict[str, Any]:
        """Search runbooks when policy or missing operational knowledge is needed. Reuse existing evidence instead of repeating retrieval."""
        return retriever.search(query, top_k)
    server.add_tool(search_runbook, name='search_runbook',
                    description=search_runbook.__doc__, structured_output=True)

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
    parser.add_argument('--index-path', default='data/qdrant')
    args = parser.parse_args()
    create_server(args.scenario, args.index_path).run(transport='stdio')
