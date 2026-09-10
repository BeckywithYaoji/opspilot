# OpsPilot V6 Final Benchmark Report

## 1. Git

- base: a29dcba7bbf203165ab5f43290a078a6931a7f00
- final: see V6 commit in git log
- working tree: verified before commit

## 2. pytest

- baseline: 98 passed, 1 skipped, 2 warnings
- final: see regression.txt (fresh run)

## 3. Benchmark Configuration

- git_commit: a29dcba7bbf203165ab5f43290a078a6931a7f00
- model: deepseek-flash
- temperature: provider default (unchanged)
- timestamp: 2026-09-10T16:58:36.823714+00:00
- benchmark_case_count: 36
- embedding_model: BAAI/bge-small-en-v1.5
- redis: configured via environment; isolated benchmark UUID sessions
- evidence_type: real_model
- attempt_policy: one attempt; resume skips recorded cases
- cases_sha256: 55c61a48779453dcb4f5c11bb47060bd6add63aefb406d25d77e2ce7312c4bbf
- qdrant: {'runbooks': {'count': 7, 'path': 'data/qdrant'}, 'opspilot_incidents': {'count': 14, 'path': 'data/qdrant-incidents'}}
- incident_preparation: Reused existing persisted incidents; full source_task_id payload snapshot retained; no direct trace injection.

## 4. Overall

- real_model_cases: 36
- real_model_turns: 42
- task_success_rate: 0.75
- tool_selection_accuracy: 0.8611111111111112
- tool_argument_accuracy: 0.9418604651162791
- host_accuracy: 1.0
- service_accuracy: 0.8333333333333334
- port_accuracy: 1.0

## 5. Runbook RAG

- decision_accuracy: 0.9722222222222222
- precision: 0.8571428571428571
- recall: 1.0
- unnecessary_retrieval_rate: 0.03333333333333333
- recall_at_1: 0.6666666666666666
- recall_at_3: 0.8333333333333334

## 6. Incident Memory

- decision_accuracy: 1.0
- precision: 1.0
- recall: 1.0
- unnecessary_retrieval_rate: 0.0
- recall_at_1: 0.5
- recall_at_3: 1.0
- current_state_verification_rate: 0.0

## 7. Session Memory

- context_recall_accuracy: 1.0
- tool_argument_recovery_accuracy: 1.0
- cross_session_leakage_rate: 0

## 8. Reliability

- average_tool_calls_per_task: 1.5277777777777777
- repeated_tool_rate: 0.0
- blocked_tool_calls: 8
- post_resolution_actions: 0
- post_resolution_action_rate: 0.0
- goal_completion_accuracy: unavailable

## 9. HITL Safety

- evidence_type: deterministic safety / infrastructure
- cases: 9
- passed: 9
- controlled_tool_proposals: 6
- unauthorized_executions: 0
- unauthorized_execution_rate: 0.0
- rejected_tool_execution_count: 0
- replay_duplicate_execution_count: 0
- approval_resume_success_rate: 1.0
- cross_session_leakage_rate: 0
- safety_status: PASS
- approval_precision: 1.0

## 10. Observability

- trace_coverage: 1.0
- expected_spans: 195
- observed_expected_spans: 195
- average_execution_latency_ms: 15401.427320999039
- p50_ms: 7763.374979025684
- p95_ms: 36282.26237487979
- latency_sample_count: 34
- missing_latency_count: 0
- noncompleted_latency_excluded: 8
- average_observed_llm_spans_per_task: 1.6388888888888888
- retrieval_error_rate: 0.0
- tool_error_rate: 0.09090909090909091
- token_usage_available: False

## 11. Token Usage

unavailable; no estimates. The current transport discards provider usage.

## 12. Failure Analysis

- GOAL_VERIFIER_ERROR: 4
- TOOL_SELECTION_ERROR: 5
- AGENT_ERROR: 5
- ARGUMENT_ERROR: 5

## 13. Reproducibility

Run `python scripts/run_final_benchmark.py --root NEW_DIRECTORY` with a copy of cases.json. Restore the exported incidents via `scripts/prepare_benchmark.py --restore-incidents` only on a clean environment. Every original attempt is retained. The six multi-turn cases produce 42 requests for 36 cases. Safety evidence uses deterministic intent and actual HTTP/MCP/Redis; failure injection uses an unavailable index through the real MCP process.

## 14. Known Limitations

- Mock SSH operations only; healthy is not an existing selectable scenario. Recovery intent is accepted at AWAITING_APPROVAL, not counted as executed repair.
- Task success checks required evidence, arguments, and a nonempty answer; natural-language answer quality is not independently judged. No prompt tuning or retries.
- Trace coverage measures component dispatch visibility. Existing tracing misses final-answer LLM calls, independently generates a different task_id, and measures retrieval around the MCP boundary rather than inside Qdrant. Average observed LLM spans is not total provider calls.
- Latency uses external completed-request wall-clock timing; nested span sums are not valid E2E measurements. Pending calls are excluded, human wait duration unavailable. Token usage and independent goal-verifier accuracy unavailable.
- Safety evidence covers sequential replay and Redis expiry, not concurrent approvals or the in-memory fallback. Production safety must not be inferred beyond tested conditions.
- Incident recall uses broad persisted SSH relevance; the permission case expects ESCALATED incidents. The source snapshot includes development incidents and is not a production corpus.

## 15. V6 Status

COMPLETE
