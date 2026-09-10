"""Provider-neutral Chat Completions transport, configured only by environment."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

from dotenv import dotenv_values
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from pydantic import BaseModel, Field, SecretStr


ENV_PATH = Path(__file__).resolve().parent.parent / '.env'


class Settings(BaseModel):
    api_key: SecretStr
    base_url: str = Field(min_length=1)
    model: str = Field(min_length=1)

    @classmethod
    def from_env(cls, path: Path = ENV_PATH) -> 'Settings':
        values = {**dotenv_values(path), **os.environ}
        keys = ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL')
        missing = [key for key in keys if not (values.get(key) or '').strip()]
        if missing:
            raise ValueError('Missing configuration: ' + ', '.join(missing))
        return cls(api_key=values[keys[0]], base_url=values[keys[1]].strip(), model=values[keys[2]].strip())


class CompatibleChatModel:
    def __init__(self, settings: Settings | None = None):
        self.settings = settings

    def invoke(self, messages: list, tools: list) -> AIMessage:
        settings = self.settings or Settings.from_env()
        wire_messages = []
        for message in messages:
            if isinstance(message, SystemMessage):
                wire = {'role': 'system', 'content': message.content}
            elif isinstance(message, HumanMessage):
                wire = {'role': 'user', 'content': message.content}
            elif isinstance(message, ToolMessage):
                wire = {'role': 'tool', 'content': message.content, 'tool_call_id': message.tool_call_id}
            elif isinstance(message, AIMessage):
                wire = {'role': 'assistant', 'content': message.content or None}
                if message.tool_calls:
                    wire['tool_calls'] = [
                        {'id': call['id'], 'type': 'function', 'function': {
                            'name': call['name'], 'arguments': json.dumps(call['args'], ensure_ascii=False)}}
                        for call in message.tool_calls
                    ]
            else:
                raise ValueError('unsupported message type')
            wire_messages.append(wire)
        payload = {'model': settings.model, 'messages': wire_messages,
                   'tools': [convert_to_openai_tool(tool) for tool in tools],
                   'tool_choice': 'auto', 'stream': False}
        request = Request(settings.base_url.rstrip('/') + '/chat/completions',
                          data=json.dumps(payload, ensure_ascii=False).encode('utf-8'),
                          headers={'Authorization': 'Bearer ' + settings.api_key.get_secret_value(),
                                   'Content-Type': 'application/json'}, method='POST')
        with urlopen(request, timeout=60) as response:
            choice = json.loads(response.read())['choices'][0]
        if choice.get('finish_reason') in ('length', 'content_filter'):
            raise ValueError('incomplete model response')
        message = choice['message']
        # Select only public content and function calls. Ignore reasoning_content etc.
        calls = []
        for call in message.get('tool_calls') or []:
            arguments = json.loads(call['function']['arguments'])
            if not isinstance(arguments, dict):
                raise ValueError('tool arguments must be a JSON object')
            calls.append({'id': call['id'], 'name': call['function']['name'], 'args': arguments})
        return AIMessage(content='' if calls else (message.get('content') or ''), tool_calls=calls)
