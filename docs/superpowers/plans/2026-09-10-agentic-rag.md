# Agentic RAG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add selective, agent-controlled runbook retrieval through a real MCP tool backed by local Markdown, BGE embeddings, and persistent Qdrant while preserving V1 behavior.

**Architecture:** Runbooks are chunked and embedded into a local Qdrant collection by an explicit indexing script. The MCP server owns a retriever and exposes `search_runbook` beside the existing tools; the Agent discovers it and the LLM chooses when to call it. Retrieval evidence returns through the same Observation and trajectory path as operations tools.

**Tech Stack:** Python 3.11+, FastAPI, LangGraph, MCP SDK, qdrant-client local mode, sentence-transformers BGE small, pytest.

**Spec:** User-provided V2 requirements in pasted-text.txt (Agentic RAG + Selective Retrieval).

## Global Constraints

- Only add `search_runbook`; retain the four existing Ops tools and two scenarios.
- Do not implement hybrid search, BM25, reranking, memory, additional APIs, frontend, or V3 features.
- Retrieval is never precomputed before the LLM; only the model selects the MCP tool.
- Indexing is explicit via `python scripts/index_runbooks.py`; runtime never silently downloads or rebuilds the index.
- Tool errors become safe Observations; no complex retry framework.
- Existing V1 trajectory and response fields remain backwards-compatible; transport remains `mcp`.

---

### Task 1: Runbook corpus and deterministic chunk/index primitives

**Files:**
- Create: `data/runbooks/ssh-troubleshooting.md`, `service-recovery.md`, `port-troubleshooting.md`, `permission-denied.md`, `incident-escalation.md`, `service-verification.md`
- Create: `app/rag/__init__.py`, `app/rag/indexer.py`, `app/rag/retriever.py`
- Create: `scripts/index_runbooks.py`
- Create: `tests/test_rag_indexer.py`
- Modify: `requirements.txt`

**Interfaces:** `chunk_markdown(path) -> list[Chunk]`; `RunbookIndex.build(paths)`; `RunbookRetriever.search(query, top_k) -> dict`.

- [ ] Write failing tests for heading/paragraph chunk metadata, deterministic IDs, required source hits for SSH and permission queries, empty/irrelevant query safety, and missing collection error.
- [ ] Run `pytest tests/test_rag_indexer.py -v` and observe import/behavior failures.
- [ ] Implement six short internal runbooks; parse headings and paragraphs, split oversized sections by character with bounded overlap; store source/title/section/chunk_id/content.
- [ ] Implement a BGE encoder wrapper with lazy loading and an injectable deterministic test encoder; create/recreate Qdrant local collection and upsert vectors; retriever returns status/query/results with source, section, content, score.
- [ ] Run the focused tests and `python scripts/index_runbooks.py --help`; verify no runtime network is required by tests.

### Task 2: MCP search tool and discovery

**Files:**
- Modify: `app/mcp/server.py`, `app/mcp/client.py`
- Create: `tests/test_mcp_rag.py`

**Interfaces:** MCP server exposes `search_runbook(query: str, top_k: int = 4)` and uses the configured local index; Client discovers and calls it through existing methods.

- [ ] Write failing tests for five discovered tools, successful structured search result, unavailable index error Observation, and malformed retrieval result normalization.
- [ ] Run focused tests and observe failure.
- [ ] Add the retriever to the server process, register only `search_runbook` in addition to four existing tools, and preserve server resource snapshot behavior.
- [ ] Add client validation for `top_k` and return safe errors for retrieval failures; do not import retriever implementation into Agent.
- [ ] Run all MCP tests and verify discovery is exactly five tools.

### Task 3: Agent-controlled selective retrieval

**Files:**
- Modify: `app/agent.py`, `app/models.py`, `app/trajectory.py`
- Create: `tests/test_selective_retrieval.py`

**Interfaces:** model receives discovered five-tool schemas; model-controlled calls route through MCP; `TrajectoryStep` continues to contain step/tool/arguments/observation/transport.

- [ ] Write failing deterministic tests: simple port task produces no `search_runbook`; runbook-required task calls `search_runbook` then an Ops tool; permission task can search, observe permission denial, and create a ticket.
- [ ] Run focused tests and observe failure.
- [ ] Update only the system prompt with retrieval guidance; rely on discovered schema and existing graph routing, with no query-string branch.
- [ ] Ensure retrieval evidence is serialized as a ToolMessage and recorded unchanged in the unified trajectory.
- [ ] Run the focused tests and all prior tests.

### Task 4: Retrieval evaluation and API/demo validation

**Files:**
- Create: `data/eval/retrieval_cases.json`, `data/eval/retrieval_decision_cases.json`, `scripts/eval_retrieval.py`, `tests/test_eval_retrieval.py`
- Modify: `app/main.py`, `README.md`, `requirements-lock.txt`
- Create: `data/demo-v2-no-rag.json`, `data/demo-v2-rag-verify.json`, `data/demo-v2-rag-escalation.json`, `data/demo-v2-retrieval-eval.json`

**Interfaces:** `python scripts/eval_retrieval.py` prints Recall@1/3/4 and writes JSON; API remains `POST /api/agent/run` with the same request schema.

- [ ] Write failing tests for metric computation, no added API routes, and demo response invariants.
- [ ] Run focused tests and observe failure.
- [ ] Implement 10-15 retrieval cases and a small metric script; keep selective-decision cases as evaluation data, not runtime rules.
- [ ] Run `python scripts/index_runbooks.py`, `pytest -v`, then start Uvicorn and execute real DeepSeek Case C/D/E plus V1 Case A/B. Save complete responses and verify calls, final state, resolution, and all `transport=mcp` markers.
- [ ] Update README with V2 architecture, indexing/startup, selective retrieval explanation, trajectories, metrics, and explicit limitations.
- [ ] Run `git diff --check`, `pip check`, full `pytest -v`, verify JSONL consistency, then commit `feat: add agentic runbook retrieval`.

---
