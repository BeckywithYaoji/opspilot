# v1.0 release verification

- V6 benchmark commit: `6803d87` (36 real-model cases / 42 requests; 9 deterministic safety cases plus failure probe).
- V7 baseline: clean working tree at `6803d87`; 101 passed, 2 warnings with real Redis integration enabled.
- Current local regression: **105 passed, 2 warnings**. See [test log](verification/pytest.txt).
- Compose configuration: PASS (`docker compose config --quiet`).
- Tracked secret pattern scan: PASS; `.env` remains ignored and is not copied into the image.
- Benchmark README/docs/resume consistency: PASS.
- Native smoke: PASS; Redis/Qdrant ready, actual configured model calls check_port, trace_id returned. See [result](verification/native-smoke.json).
- Native four-path CLI demo: PASS; direct, RAG, multi-turn session, and approval. See [public output](verification/native-demo.txt).
- Docker runtime verification: PASS on host port 18000. Redis 7.2, Qdrant 1.19.0 and `opspilot:1.0.0` were healthy; `/health` returned `ok`, `/ready` reported both dependencies healthy, container smoke completed a real `check_port` request with trace `trace-6867d254-d9ad-4645-be8d-f554d182c449`, and container RAG/HITL demos completed. See [container smoke](verification/container-smoke.json), [RAG demo](verification/container-demo-rag.txt), and [HITL demo](verification/container-demo-hitl.txt).
- Runbook indexing: PASS with the cached BGE model. A clean container needs network access to download `BAAI/bge-small-en-v1.5`; this verification used the existing local cache because the container could not resolve `huggingface.co`.

Build history: an initial Debian package download stalled; the unneeded OS-package installation was removed. A subsequent standard ARM PyTorch download timed out, so the image installs the CPU wheel from the official PyTorch CPU index with a pip cache. Neither incident changed Agent behavior or V6 results.

Docker is tested on host port 18000 because the user's original API already owns port 8000. The native verification server uses 18001. Verification will stop only the services it started, preserving the original API and named volumes.
