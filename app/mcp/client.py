"""Thin official-SDK client. No operations implementation or fallback lives here."""
import json
import os
import sys
from pathlib import Path

from jsonschema import ValidationError, validate
from mcp import Client, StdioServerParameters
from mcp.types import TextContent
from pydantic import BaseModel
from app.storage import qdrant_url


class MCPUnavailable(RuntimeError):
    pass


class ServerSnapshot(BaseModel):
    reachable: bool
    ports: dict[int, bool]
    services: dict[str, str]
    restart_permission: bool


class EnvironmentSnapshot(BaseModel):
    environment: dict[str, ServerSnapshot]
    environment_restored: bool
    tickets: list[dict[str, str]]


class OpsMCPClient:
    def __init__(self, scenario: str, *, command: str | None = None,
                 index_path: str | Path | None = None):
        args = ['-m', 'app.mcp.server', '--scenario', scenario]
        if index_path is not None:
            args.extend(['--index-path', str(index_path)])
        parameters = StdioServerParameters(
            command=command or sys.executable,
            args=args,
            cwd=str(Path(__file__).resolve().parents[2]),
            env={**({'QDRANT_URL': qdrant_url()} if qdrant_url() else {}),
                 **{key: os.environ[key] for key in ('HF_HOME', 'HF_HUB_OFFLINE') if key in os.environ}},
        )
        self.client = Client(parameters, read_timeout_seconds=5)
        self.tools: list[dict] | None = None

    async def __aenter__(self):
        try:
            await self.client.__aenter__()
        except Exception:
            raise MCPUnavailable('MCP server unavailable') from None
        return self

    async def __aexit__(self, *exc):
        return await self.client.__aexit__(*exc)

    async def list_tools(self) -> list[dict]:
        if self.tools is None:
            try:
                result = await self.client.list_tools()
                self.tools = [
                    {'type': 'function', 'function': {
                        'name': tool.name, 'description': tool.description or '',
                        'parameters': tool.input_schema,
                    }} for tool in result.tools
                ]
            except Exception:
                raise MCPUnavailable('MCP tool discovery failed') from None
        return self.tools

    async def call_tool(self, name: str, arguments: dict) -> dict:
        try:
            definitions = await self.list_tools()
            definition = next((t['function'] for t in definitions if t['function']['name'] == name), None)
            if definition is None:
                return {'status': 'failed', 'error': 'tool not found'}
            try:
                validate(arguments, definition['parameters'])
            except ValidationError:
                return {'status': 'failed', 'error': 'invalid tool arguments'}
            result = await self.client.call_tool(name, arguments, read_timeout_seconds=60 if name in {'search_runbook', 'search_incident_memory'} else 5)
        except Exception:
            return {'status': 'failed', 'error': 'MCP server unavailable'}
        observation = self.observation(result)
        if name == 'search_runbook' and observation.get('status') == 'error':
            return {'status': 'failed', 'error': 'runbook retrieval unavailable'}
        return observation

    @staticmethod
    def observation(result) -> dict:
        if result.is_error:
            return {'status': 'failed', 'error': 'MCP tool call failed'}
        try:
            observation = result.structured_content
            if observation is None:
                if len(result.content) != 1 or not isinstance(result.content[0], TextContent):
                    raise ValueError('expected one JSON text block')
                observation = json.loads(result.content[0].text)
            if not isinstance(observation, dict) or not isinstance(observation.get('status'), str):
                raise ValueError('expected structured status')
            return observation
        except (ValueError, TypeError):
            return {'status': 'failed', 'error': 'malformed MCP tool result'}

    async def snapshot(self) -> dict:
        try:
            result = await self.client.read_resource('ops://environment')
            if len(result.contents) != 1:
                raise ValueError('expected one snapshot')
            # Pydantic restores integer port keys after the JSON process boundary.
            return EnvironmentSnapshot.model_validate_json(result.contents[0].text).model_dump()
        except Exception:
            raise MCPUnavailable('MCP environment snapshot unavailable') from None
