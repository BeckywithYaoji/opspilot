"""The graph controls the loop, not the domain-specific tool sequence."""
import asyncio
import json
from pathlib import Path
from typing import Annotated, Protocol, TypedDict
from uuid import uuid4

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages

from app.models import RunResponse, Status, TrajectoryStep
from app.mcp.client import OpsMCPClient
from app.trajectory import DEFAULT_PATH, save_trajectory
from app.reliability import ReliabilityRuntime
from app.completion import verify_goal


SYSTEM_PROMPT = """你是 IT Operations Agent，处理模拟服务器的运维任务。
理解用户问题，根据已有信息自主决定是否调用工具以及调用哪个工具。
使用最少但足够的工具诊断与恢复；每次收到 Observation 后重新判断下一步。
只有在问题需要操作手册或缺少可靠操作依据时才调用 search_runbook；简单、明确的检查直接调用运维工具。将检索结果视为 Observation，并据此决定后续操作。
不得假设工具成功，修复后应尽量验证问题是否真正解决。优化完成用户目标，而不是最大化诊断；目标满足并充分验证后停止，不做无关检查。复用已有 Observation 和检索证据。工具调用有成本，优先使用最小充分序列；仅验证确认用户目标所需的状态。权限阻止时才升级，已解决后不要创建工单。
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
    return asyncio.run(_run_agent(query, scenario, model, max_steps, trajectory_path))


async def _run_agent(query, scenario, model, max_steps, trajectory_path) -> RunResponse:
    state = {
        'messages': [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=query)],
        'task_id': str(uuid4()), 'step_count': 0, 'max_steps': max_steps,
    'status': 'RUNNING', 'answer': '', 'steps': [],
    }
    # Keep executed steps even if the MCP connection fails before the graph returns.
    steps: list[TrajectoryStep] = []
    runtime = ReliabilityRuntime(max_total_tool_calls=max_steps)
    goal_satisfied_at_step = None
    snapshot = {'environment': {}, 'environment_restored': False, 'tickets': []}

    async def llm_node(state: AgentState) -> dict:
        try:
            reply = await asyncio.to_thread(model.invoke, state['messages'], tools)
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

    async def tool_node(state: AgentState) -> dict:
        messages = []
        count = state['step_count']
        for call in state['messages'][-1].tool_calls:
            if count >= state['max_steps']:
                return {'messages': messages, 'steps': steps, 'step_count': count,
                        'status': 'MAX_STEPS_EXCEEDED', 'answer': '已达到工具调用上限，任务尚未完成。'}
            decision = runtime.admit(call['name'], call['args'])
            if decision['blocked']:
                observation = decision['observation']
                count += 1
                steps.append(TrajectoryStep(step=count, tool=call['name'], arguments=call['args'], observation=observation,
                                            transport='mcp', blocked=True, block_reason=decision['block_reason'], state_revision=runtime.state_revision))
            else:
                observation = await client.call_tool(call['name'], call['args'])
                runtime.record_observation(call['name'], observation)
                count += 1
                steps.append(TrajectoryStep(step=count, tool=call['name'], arguments=call['args'], observation=observation,
                                            transport='mcp', repeated=decision.get('repeated', False), state_revision=runtime.state_revision))
                # Completion checks are most useful for explicit verification requests;
                # preserve ordinary repair loops for callers that still need a final model response.
                verdict = None
                if ('顺便' in query or '规范' in query or '端口' in query):
                    snap = await client.snapshot()
                    verdict = verify_goal(query, steps, snap['environment'])
                if verdict is not None:
                    steps[-1].goal_satisfied_after_step = verdict.goal_satisfied
                if verdict is not None and verdict.goal_satisfied and goal_satisfied_at_step is None:
                    goal_satisfied_at_step = count
                    return {'messages': messages, 'steps': steps, 'step_count': count, 'status': 'COMPLETED', 'answer': '已完成并验证用户请求。'}
            messages.append(ToolMessage(content=json.dumps(observation, ensure_ascii=False),
                                        tool_call_id=call['id'], name=call['name']))
        return {'messages': messages, 'steps': steps, 'step_count': count}

    try:
        async with OpsMCPClient(scenario) as client:
            tools = await client.list_tools()
            if not tools:
                raise ValueError('MCP server has no tools')
            graph = StateGraph(AgentState)
            graph.add_node('llm', llm_node)
            graph.add_node('tools', tool_node)
            graph.add_edge(START, 'llm')
            graph.add_conditional_edges('llm', lambda state: 'tools' if state['status'] == 'RUNNING' else END)
            graph.add_conditional_edges('tools', lambda state: 'llm' if state['status'] == 'RUNNING' else END)
            state = await graph.compile().ainvoke(state, config={'recursion_limit': 2 * max_steps + 4})
            snapshot = await client.snapshot()
    except Exception:
        state['status'] = 'FAILED'
        state['answer'] = 'MCP runtime failed: server, discovery or environment snapshot unavailable.'

    result = RunResponse(task_id=state['task_id'], answer=state['answer'], status=state['status'],
                         success=snapshot['environment_restored'], environment=snapshot['environment'],
                         trajectory=steps, tickets=snapshot['tickets'])
    save_trajectory(query, scenario, result, trajectory_path)
    return result
