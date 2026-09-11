# OpsPilot Benchmark and Release Implementation Plan

**Goal:** Measure the unchanged Agent on 36 real-model cases and infrastructure checks, then package the measured system for demonstration.
**Architecture:** Standalone runner calls existing public interfaces, saves one attempt per case and dedicated traces; evaluator uses predetermined evidence expectations. V7 follows V6 verification and uses only its metrics.
**Constraints:** No Agent/prompt/guardrail tuning. Never substitute scripted models for real-model cases. Preserve failures. No remote push.

- [x] Baseline: git status/log and pytest -v; inspect existing infrastructure.
- [x] Create 36 fixed cases, six per category, including six multi-turn sessions. Save provenance and expected documents before running.
- [x] Implement scripts/run_final_benchmark.py: append-only execution, unique Redis sessions, current configured real model, perf_counter timing, clean trace output, no retry by default.
- [x] Implement scripts/eval_final_benchmark.py and focused tests: required/forbidden tools, argument checks, retrieval decisions/Recall@K, weighted trace coverage, missing latency excluded, failures retained.
- [x] Run deterministic HTTP safety cases with execution spies, including approve/reject/replay/expired/unknown and memory isolation. Record failures honestly; do not fix production behavior in V6.
- [x] Run all real cases once; aggregate clean artifacts, inspect failure classifications and run full pytest. Commit V6.
- [x] Package Docker/Compose, configuration, health/readiness, index/smoke/demo/release scripts and final docs. Preserve real architecture limitations.
- [x] Verify release, secret hygiene and documentation metric consistency; commit V7 and tag only when release acceptance permits.
