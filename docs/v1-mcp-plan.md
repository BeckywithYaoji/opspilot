# OpsPilot V1 MCP implementation plan

Approved design: request-local stdio MCP subprocess, dynamic discovery, four existing tools, read-only state resource, backwards-compatible API fields, transport marker, no new business capabilities.

Baseline: 9249abc, clean worktree, pytest -v: 25 passed / 1 upstream warning. Working branch: feat/opspilot-v1-mcp.

1. Add official MCP SDK. Write real subprocess tests for discovery, closed port, successful restart mutation, denied restart, unknown tool, invalid arguments and isolated scenarios; observe failure before adding app/mcp/server.py and client.py.
2. Server owns MockEnvironment and reuses app/tools.py definitions. Expose exactly four tools and ops://environment read-only resource containing snapshot, restored flag and tickets. Scenario passed only to server process initialization. Client uses SDK initialization/list_tools/call_tool/read_resource, with bounded timeouts and safe error results.
3. Migrate run_agent internals to asynchronous MCP operations while retaining the synchronous public entry point for the existing API/tests. Discover input schemas and pass standard tool definitions to model. Preserve the LLM-directed graph, step budget and final response. No local-tool fallback.
4. Keep original 25 test cases and coverage. Update only the expected additive transport field. Add real MCP-to-agent observation integration and transport-error coverage. Verify backwards-compatible status/success and additive agent_status/resolution_status/environment_restored/handled.
5. Run pytest -v and actual FastAPI + automatic MCP subprocesses. Re-run both existing DeepSeek tasks, verify environmental state, denied restart then ticket, and persisted JSONL. Save data/demo-v1-mcp-repairable.json and data/demo-v1-mcp-permission-denied.json. Append concise README section, commit as feat: migrate ops tools to MCP, stop.

Failure semantics: startup/discovery/resource failures yield FAILED with unknown/empty environment rather than fabricated state. Tool failures become observations for the model; no automatic retries. Tool calls remain bounded by max_steps=8. Resolution is RESOLVED when server snapshot confirms restoration, ESCALATED when a persisted ticket exists, otherwise FAILED; handled additionally requires a completed Agent run.


Validation evidence:
- MCP implementation initially failed registration because bare dict cannot advertise structured output in SDK 2.2; changed existing tool return annotations to dict[str, Any], without changing behavior. Real stdio discovery/mutation tests then passed.
- Original 25 tests retained (one expected dictionary gains transport=mcp); 15 additional MCP tests. Final pytest -v: 40 passed, 1 pre-existing Starlette/AnyIO warning. pip check clean.
- Real MCP discovery: ops-mcp-server exposes exactly check_port, check_service, restart_service, create_ticket. Saved complete schemas in data/demo-v1-mcp-tools.json.
- Real HTTP Case A: 0aaa9cd3-52a8-45e8-9331-7e11504019ce, 5 MCP calls, COMPLETED/RESOLVED, restored=true, handled=true; final running/open.
- Real HTTP Case B: 48441fb5-f71b-411c-93b7-e6c127478129, 4 MCP calls, one permission-denied restart then create_ticket INC-17ab0ec716e5, COMPLETED/ESCALATED, restored=false, handled=true.
- All tool steps marked mcp. Final state, answer, steps, counts and resolution fields matched persisted JSONL. SDK child processes exited after requests; FastAPI remains running.
