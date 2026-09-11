# Demonstration guide

1. Configure `.env` (never display the key during a demo), start Compose, and check `/health` and `/ready`.
2. Run `make index` once. This downloads BGE on a clean machine and builds the Runbook collection. Later API starts do not re-index.
3. Run `make smoke`: a real provider request must choose check_port and return a trace ID.
4. Run `make demo`: direct check, Runbook query, two-turn Redis context, and HITL. Terminal displays only public response and tool observations.
5. Approve the mock restart at the prompt, or reject it. This is a frozen-tool execution endpoint, not graph checkpoint restoration. Each fresh Agent request starts a fresh mock environment.
6. Open `data/benchmark/results/final-report.md` to discuss the 36-case benchmark, including the failed current-state verification and service-name errors. Do not quote a development demo as overall accuracy.

Compose stores traces in its runtime volume. Inspect them with `docker compose exec opspilot-api cat data/traces/traces.jsonl`. Native runs use the local path. The CLI can use `--url http://127.0.0.1:18000` when the default host port is occupied.

`docker compose down` stops only this project and preserves volumes. Avoid `down -v` unless intentionally discarding demo data. Do not run the old V3.1 script against valuable data; it resets its incident collection.
