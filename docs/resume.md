# Resume material

**项目名称：** OpsPilot — Tool-Using IT Operations Agent

**一句话介绍：** 基于 LangGraph 与 MCP 的模拟 IT 运维 Agent，结合按需检索、分层记忆、人工审批和可审计评估。

**技术栈：** Python、FastAPI、LangGraph、DeepSeek/OpenAI-compatible API、MCP、Redis、Qdrant、BGE、Pydantic、Docker Compose、pytest、Custom Local Tracing。Langfuse 未实际接入。

- 构建 LangGraph + MCP 运维 Agent，使模型依据工具 Observation 选择诊断和检索操作，支持模拟故障处理与结构化轨迹记录。
- 实现 BGE + Qdrant Runbook/Incident 检索和 Redis 多轮会话上下文，区分规范、历史经验与当前状态证据。
- 引入工具预算、重复检测、Goal Verifier 与 HITL 边界；通过确定性 HTTP/MCP/Redis 测试验证顺序审批、拒绝和重放行为。
- 建立 36 个真实模型任务、42 次请求的一次性 Benchmark，记录 75.00% 结构化任务成功率、86.11% 工具选择准确率和 94.19% 参数准确率，同时保留所有失败；完成容器与 CLI 演示打包。

The following table is generated from V6 metrics and checked against README/docs. Dispatch coverage does not mean all provider calls are traced. Safety results apply to the tested sequential paths only.

| Metric | V6 result |
|---|---:|
| Task Success Rate | 75.00% |
| Tool Selection Accuracy | 86.11% |
| Tool Argument Accuracy | 94.19% |
| Runbook Recall@3 | 83.33% |
| Incident Recall@3 | 100.00% |
| Context Recall Accuracy | 100.00% |
| Post-resolution Action Rate | 0.00% |
| Unauthorized Execution Rate | 0.00% |
| Dispatch Trace Coverage | 100.00% |
| P50 / P95 completed-request latency | 7.76 / 36.28 s |
