PYTHON ?= .venv/bin/python
PORT ?= 8000

.PHONY: setup up down test index smoke demo benchmark verify
setup:
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements-lock.txt
	@test -f .env || cp .env.example .env
up:
	docker compose up -d --build
down:
	docker compose down
test:
	TRACE_OUTPUT_PATH=/tmp/opspilot-test-traces.jsonl $(PYTHON) -m pytest -v
index:
	docker compose exec opspilot-api python scripts/index_runbooks.py
smoke:
	$(PYTHON) scripts/smoke_test.py --url http://127.0.0.1:$(PORT)
demo:
	$(PYTHON) scripts/demo.py --url http://127.0.0.1:$(PORT)
benchmark:
	$(PYTHON) scripts/eval_final_benchmark.py
	$(PYTHON) scripts/render_benchmark_report.py
verify:
	$(PYTHON) scripts/verify_release.py
