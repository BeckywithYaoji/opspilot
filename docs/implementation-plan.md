# OpsPilot V0 Implementation Plan

User approved the minimal design on 2026-09-10. Execute inline with small pytest cycles; no subagents or further design gates.

Architecture: FastAPI invokes a request-local LangGraph LLM/tool loop. Scenario initializes only environment. Model selects tools. A standard-library OpenAI-compatible Chat Completions client avoids a provider SDK. No persistence except trajectory JSONL, no frontend or future features.

1. Environment and tools: write tests for successful mutation, permission rejection without mutation, unknown resources, isolation and tickets; run red; implement app/environment.py and app/tools.py; run green and commit.
2. Agent: write tests using injected fake chat responses for observation propagation, alternative order, permission failure then escalation, maximum tool calls and provider failure; run red; implement app/agent.py, app/models.py, app/config.py, app/trajectory.py; run green and commit.
3. API/client: test request validation, health, saved trajectories and OpenAI-compatible HTTP request/response with mocked transport; implement app/main.py and client; run green.
4. Verify: pytest -v; uvicorn app.main:app --reload; actual HTTP health and both scenarios. Real model credentials required for actual demo acceptance. Preserve actual evidence and label missing credentials as not passed. README includes setup, architecture, curl, case evidence, tests and future work only. Commit verified work; stop at V0.

Step count counts tool calls (default 8); a final LLM response after the last allowed observation is permitted, further tools are rejected. COMPLETED indicates a final answer; success measures reachable host + running sshd + open 22. Permission escalation may complete with success=false. Persist final answer, status, steps, total_steps, environment and tickets without reasoning fields or API secrets.

Execution evidence: environment/tools 5 tests passed, agent stage 12 passed, final API/protocol/regression suite 25 passed. Uvicorn --reload and actual HTTP health passed. Both actual scenario requests returned FAILED due to missing API key and were persisted. Real-model acceptance remains pending configuration; no V1 work started. Code review identified missing tool-call ID handling, reproduced and fixed before execution with regression tests.
