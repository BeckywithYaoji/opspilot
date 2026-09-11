# Final benchmark

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

# V6 predeclared evaluation rules

36 case definitions in cases.json, six per category. One attempt per case, six two-turn sessions (42 model tasks in total). The runner uses CompatibleChatModel without substitutions or prompt/temperature changes. No retry has been requested. Recovery cases stop at pending approval, which is correct for this benchmark boundary and not evidence of repair.

Required tools and explicit host/service/port values determine tool/argument accuracy. A task must produce required successful observations and a nonempty final answer, or the requested pending approval. An intermediate failed/invalid operation is reported even if later corrected. Selection efficiency is separate from goal success. Semantic quality of long natural-language answers is not independently judged. Incident cases requesting current inspection require a successful current environment observation; retrieval alone is insufficient.

Runbook Recall@K uses expected source files fixed in cases.json. Incident relevance uses the existing collection snapshot: SSH recovery queries expect persisted sshd/dev-server incidents; the permission query expects permission/ESCALATED incidents. This is broad topic relevance, not exact incident identity memorization. The snapshot retains source_task_id for audit. No synthetic incident result is injected.

Safety uses deterministic intent, HTTP TestClient, actual Redis pending records and a wrapper counting actual MCP restart calls. It does not measure LLM competence. A missing runbook index exercises the existing retrieval failure path. No new production failure mode is added.

Trace coverage is the sum of observed expected component names divided by expected component names per task, inferred from actual tool dispatch/proposal. It measures dispatch visibility, not completeness of all physical LLM calls or internal vector-database timing. Tracer task IDs are independently generated in existing code; mismatches are reported as limitations.

Completed-request latency is externally measured with perf_counter. Pending and failed requests are excluded from the completed latency sample; missing values are counted, never replaced by zero. Human wait time is unavailable in the production trace. Token usage and independent goal-completion classification accuracy are unavailable. These are instrumentation limitations, not fabricated benchmark values.

Already-healthy cannot be selected in the existing API. No new scenario is introduced for benchmark coverage. Operations are simulated; no real SSH is performed.

Reproduction: initialize runbooks with scripts/index_runbooks.py; inspect collections with scripts/prepare_benchmark.py. On a clean checkout, explicitly restore the saved incident records through IncidentMemoryStore.save with scripts/prepare_benchmark.py --restore-incidents. Run final benchmark into a new root by copying cases.json into that root; do not delete the published original attempts. The exporter snapshot was read after the collection lock was released, and includes unchanged persisted IDs, not nearest-neighbor-selected expected IDs.

## Source artifacts

See [V6 report](../data/benchmark/results/final-report.md), [metrics](../data/benchmark/results/final-metrics.json), [failures](../data/benchmark/results/failure-analysis.json) and clean raw runs/traces in data/benchmark.

Main failures: four incident tasks stopped before verifying current state; five tasks supplied incorrect tool arguments. No production prompt or Agent behavior was changed to improve these results.
