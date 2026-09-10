import json
import subprocess
import sys
from pathlib import Path

from fastapi.routing import APIRoute

from app.main import app
from scripts.eval_retrieval import recall_at_k, evaluate_cases


def test_recall_at_k_counts_expected_source_in_ranked_results():
    cases = [
        {"expected_sources": ["ssh-troubleshooting.md"], "results": [{"source": "other.md"}, {"source": "ssh-troubleshooting.md"}]},
        {"expected_sources": ["permission-denied.md"], "results": [{"source": "permission-denied.md"}]},
        {"expected_sources": ["missing.md"], "results": []},
    ]
    assert recall_at_k(cases, 1) == 1 / 3
    assert recall_at_k(cases, 3) == 2 / 3


def test_evaluate_cases_calls_retriever_and_reports_all_metrics():
    class Retriever:
        def search(self, query, top_k):
            return {"status": "ok", "results": [{"source": "ssh-troubleshooting.md"}]}
    cases = [{"query": "ssh", "expected_sources": ["ssh-troubleshooting.md"]}]
    result = evaluate_cases(cases, Retriever())
    assert result["cases"] == 1
    assert result["recall@1"] == result["recall@3"] == result["recall@4"] == 1.0


def test_api_exposes_only_the_existing_routes():
    routes = {route.path for route in app.routes if isinstance(route, APIRoute)}
    assert routes == {"/health", "/api/agent/run"}


def test_eval_data_has_retrieval_and_decision_cases():
    retrieval = json.loads(Path("data/eval/retrieval_cases.json").read_text())
    decisions = json.loads(Path("data/eval/retrieval_decision_cases.json").read_text())
    assert 10 <= len(retrieval) <= 15
    assert 10 <= len(decisions) <= 20
    assert all(case.get("query") and case.get("expected_sources") for case in retrieval)


def test_eval_script_runs_as_a_file_from_project_root():
    result = subprocess.run(
        [sys.executable, "scripts/eval_retrieval.py", "--index", "/tmp/opspilot-eval-missing-index"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "Recall@1:" in result.stdout
    assert "Recall@3:" in result.stdout
    assert "Recall@4:" in result.stdout
