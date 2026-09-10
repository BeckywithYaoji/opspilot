"""The graph controls the loop, not the domain-specific tool sequence."""
import json
from pathlib import Path
from typing import Annotated, Protocol, TypedDict
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from pydantic import ValidationError

from app.environment import MockEnvironment
from app.models import RunResponse, Status, TrajectoryStep
from app.tools import build_tools
from app.trajectory import DEFAULT_PATH, save_trajectory


SYSTEM_PROMPT = """你是 IT Operations Agent，处理模拟服务器的运维任务。
理解用户问题，根据已有信息自主决定是否调用工具以及调用哪个工具。
使用最少但足够的工具诊断与恢复；每次收到 Observation 后重新判断下一步。
不得假设工具成功，修复后应尽量验证问题是否真正解决。
如果权限等原因阻止继续，采用安全替代方案，例如创建人工运维工单。
环境未发生变化时不要重复已经失败的操作。问题解决或无法继续时停止并给出最终回答。
最终回答区分已验证事实、已完成操作和剩余问题；工单创建不等于服务恢复。
不输出思维链或隐藏推理，只使用工具调用以及简明的最终回答。
"""


class ChatModel(Protocol):
    def invoke(self, messages: list[BaseMessage], tools: list) -> AIMessage: ...


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    task_id: str
    step_count: int
    max_steps: int
    status: Status
    answer: str
    steps: list[TrajectoryStep]


def run_agent(query: str, scenario: str, model: ChatModel, *, max_steps: int = 8,
              trajectory_path: Path = DEFAULT_PATH) -> RunResponse:
    if max_steps < 1:
        raise ValueError('max_steps must be positive')
    environment = MockEnvironment(scenario)
    tools = build_tools(environment)

    def llm_node(state: AgentState) -> dict:
        try:
            reply = model.invoke(state['messages'], list(tools.values()))
            if not isinstance(reply, AIMessage) or reply.invalid_tool_calls:
                raise ValueError('invalid model response')
            if reply.tool_calls:
                if any(not isinstance(call.get('id'), str) or not call['id'].strip()
                       for call in reply.tool_calls):
                    raise ValueError('tool call id must be a nonempty string')
                # Intermediate assistant prose is neither retained nor exposed.
                reply = AIMessage(content='', tool_calls=reply.tool_calls)
                if state['step_count'] >= state['max_steps']:
                    return {'status': 'MAX_STEPS_EXCEEDED', 'answer': '已达到工具调用上限，任务尚未完成。'}
                return {'messages': [reply]}
            if not isinstance(reply.content, str) or not reply.content.strip():
                raise ValueError('empty final answer')
            return {'messages': [AIMessage(content=reply.content)],
                    'status': 'COMPLETED', 'answer': reply.content}
        except Exception:
            # Provider errors can contain credentials or raw reasoning; do not persist them.
            return {'status': 'FAILED', 'answer': '模型调用失败或响应无效，请检查 LLM 配置、网络及工具调用兼容性。'}

    def tool_node(state: AgentState) -> dict:
        messages, steps = [], list(state['steps'])
        count = state['step_count']
        for call in state['messages'][-1].tool_calls:
            if count >= state['max_steps']:
                return {'messages': messages, 'steps': steps, 'step_count': count,
                        'status': 'MAX_STEPS_EXCEEDED', 'answer': '已达到工具调用上限，任务尚未完成。'}
            selected = tools.get(call['name'])
            try:
                observation = ({'status': 'failed', 'error': 'unknown tool'} if selected is None
                               else selected.invoke(call['args']))
            except ValidationError:
                observation = {'status': 'failed', 'error': 'invalid tool arguments'}
            except Exception:
                observation = {'status': 'failed', 'error': 'tool execution failed'}
            count += 1
            steps.append(TrajectoryStep(step=count, tool=call['name'],
                                        arguments=call['args'], observation=observation))
            messages.append(ToolMessage(content=json.dumps(observation, ensure_ascii=False),
                                        tool_call_id=call['id'], name=call['name']))
        return {'messages': messages, 'steps': steps, 'step_count': count}

    graph = StateGraph(AgentState)
    graph.add_node('llm', llm_node)
    graph.add_node('tools', tool_node)
    graph.add_edge(START, 'llm')
    graph.add_conditional_edges('llm', lambda state: 'tools' if state['status'] == 'RUNNING' else END)
    graph.add_conditional_edges('tools', lambda state: 'llm' if state['status'] == 'RUNNING' else END)
    state = graph.compile().invoke({
        'messages': [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=query)],
        'task_id': str(uuid4()), 'step_count': 0, 'max_steps': max_steps,
        'status': 'RUNNING', 'answer': '', 'steps': [],
    }, config={'recursion_limit': 2 * max_steps + 4})
    result = RunResponse(task_id=state['task_id'], answer=state['answer'], status=state['status'],
                         success=environment.ssh_restored, environment=environment.snapshot(),
                         trajectory=state['steps'], tickets=environment.tickets)
    save_trajectory(query, scenario, result, trajectory_path)
    return result
