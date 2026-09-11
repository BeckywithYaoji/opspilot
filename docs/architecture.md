# Architecture and design decisions

## Why an Agent

The LLM selects tools from their schemas and each observation. LangGraph provides the loop, budget boundaries and terminal routing; it does not encode a fixed SSH troubleshooting sequence. A model can choose service-first or port-first. The V6 benchmark records failures as well as successful sequences.

## MCP boundary

Operations execute in a separate MCP stdio process using the official Python SDK. Tools never execute real shell/SSH commands: MockEnvironment models host, service, port and ticket state. The API reads a snapshot resource for reporting. Packaging preserves this process boundary.

## Three context sources

Runbooks are formal procedures retrieved from `runbooks`. Incidents are structured historical outcomes in `opspilot_incidents`, including `source_task_id`. Redis keeps bounded session history and entity references. None of these constitutes current-state evidence. The V6 incident cases demonstrate that the model sometimes stops after retrieval without doing required current checks.

## Reliability and completion

ReliabilityRuntime tracks tool budgets and repeated actions. The structured verifier judges completion from task context, current observations and snapshots. A FINISH verdict stops the graph and requests a final answer. It may be wrong; independent semantic verifier accuracy is not measured in V6.

## Guardrail and HITL

Deterministic policy separates model intent from permission. API calls with an approval store pause restart proposals and persist frozen arguments. Redis TTL limits record lifetime. Approval uses the original trace ID but executes a new MCP process. It does not restore prior graph messages/environment or automatically run a verifier afterward. Rejection is returned to the client. Sequential replay is rejected by status inspection; concurrent requests are not atomically claimed. The fallback store is request-local and lacks expiration, so the release demo requires Redis.

## Observability

Local TraceSpan and TraceRecord JSONL records coexist with trajectories. LLM, tool, retrieval, verifier, memory-load, guardrail and approval events are visible. Sensitive argument keys are redacted. Existing gaps include final-answer provider spans, lifecycle finalization, independent task IDs, and non-atomic trace append operations. Langfuse export is a stub. V6 measures completed requests externally and reports token usage unavailable.

## Deployment change

`QDRANT_URL` selects the HTTP Qdrant client; without it the existing local file client remains. Collections, embeddings, prompts, tool selection and approval policy are unchanged. API is single-worker, bound to localhost on the host; Redis/Qdrant stay on the Compose network. `/health` is process liveness, `/ready` checks dependency connectivity and does not call the external provider. First-time indexing is explicit.

The container deployment follows the [Qdrant Docker installation guidance](https://qdrant.tech/documentation/operations/installation/). No OTel, Langfuse deployment, Kubernetes or production SSH capability is included.
