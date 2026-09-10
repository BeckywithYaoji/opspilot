import json
from unittest.mock import patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from app.config import CompatibleChatModel, Settings
from app.environment import MockEnvironment
from app.tools import build_tools


class HTTPReply:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def read(self):
        return json.dumps(self.payload).encode()


def test_client_sends_tools_history_and_ignores_reasoning_fields():
    history = [SystemMessage(content='system'), HumanMessage(content='fix'),
               AIMessage(content='', tool_calls=[{
                   'id': '1', 'name': 'check_port', 'args': {'host': 'dev-server', 'port': 22}}]),
               ToolMessage(content='{"status":"closed"}', tool_call_id='1')]
    payload = {'choices': [{'message': {'role': 'assistant', 'content': None,
               'reasoning_content': 'PRIVATE', 'tool_calls': [{'id': '2', 'type': 'function',
               'function': {'name': 'check_service', 'arguments': '{"host":"dev-server","service":"sshd"}'}}]}}]}
    captured = {}

    def transport(request, timeout):
        captured['url'] = request.full_url
        captured['body'] = json.loads(request.data)
        return HTTPReply(payload)

    model = CompatibleChatModel(Settings(api_key='test', base_url='https://example.test/v1/', model='any-model'))
    with patch('app.config.urlopen', transport):
        reply = model.invoke(history, list(build_tools(MockEnvironment('repairable')).values()))
    assert captured['url'] == 'https://example.test/v1/chat/completions'
    assert captured['body']['model'] == 'any-model'
    assert len(captured['body']['tools']) == 4
    assert captured['body']['messages'][-1]['tool_call_id'] == '1'
    assert json.loads(captured['body']['messages'][-2]['tool_calls'][0]['function']['arguments'])['port'] == 22
    assert reply.tool_calls[0]['name'] == 'check_service'
    assert 'PRIVATE' not in reply.model_dump_json()


def test_settings_reads_environment_without_provider_defaults(monkeypatch, tmp_path):
    for key in ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL'):
        monkeypatch.delenv(key, raising=False)
    with pytest.raises(ValueError, match='LLM_API_KEY'):
        Settings.from_env(tmp_path / '.env')
    env = tmp_path / '.env'
    env.write_text('LLM_API_KEY=test\nLLM_BASE_URL=https://example.test/v1\nLLM_MODEL=custom\n')
    assert Settings.from_env(env).model == 'custom'


@pytest.mark.parametrize('reason', ['length', 'content_filter'])
def test_incomplete_provider_response_is_not_a_final_answer(reason):
    model = CompatibleChatModel(Settings(api_key='test', base_url='https://example.test', model='any'))
    payload = {'choices': [{'finish_reason': reason,
                           'message': {'role': 'assistant', 'content': 'partial'}}]}
    with patch('app.config.urlopen', return_value=HTTPReply(payload)):
        with pytest.raises(ValueError, match='incomplete'):
            model.invoke([HumanMessage(content='fix')], [])


def test_bare_dotenv_key_is_reported_as_missing(monkeypatch, tmp_path):
    for key in ('LLM_API_KEY', 'LLM_BASE_URL', 'LLM_MODEL'):
        monkeypatch.delenv(key, raising=False)
    env = tmp_path / '.env'
    env.write_text('LLM_API_KEY\nLLM_BASE_URL=https://example.test\nLLM_MODEL=any\n')
    with pytest.raises(ValueError, match='LLM_API_KEY'):
        Settings.from_env(env)
