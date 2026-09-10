"""Evaluate runbook retrieval against the checked-in case set."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def recall_at_k(cases: list[dict], k: int) -> float:
    if not cases:
        return 0.0
    hits = 0
    for case in cases:
        expected = set(case.get("expected_sources", []))
        ranked = {item.get("source") for item in case.get("results", [])[:k]}
        hits += bool(expected & ranked)
    return hits / len(cases)


def evaluate_cases(cases: list[dict], retriever) -> dict:
    evaluated = []
    for case in cases:
        result = retriever.search(case["query"], top_k=4)
        evaluated.append({**case, "results": result.get("results", [])})
    return {
        "cases": len(evaluated),
        "recall@1": recall_at_k(evaluated, 1),
        "recall@3": recall_at_k(evaluated, 3),
        "recall@4": recall_at_k(evaluated, 4),
        "details": evaluated,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate indexed runbook retrieval")
    parser.add_argument("--cases", default="data/eval/retrieval_cases.json")
    parser.add_argument("--index", default="data/qdrant")
    parser.add_argument("--output", help="write full evaluation JSON to this path")
    args = parser.parse_args()
    project_root = Path(__file__).resolve().parents[1]
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    from app.rag.retriever import RunbookRetriever

    cases = json.loads(Path(args.cases).read_text(encoding="utf-8"))
    report = evaluate_cases(cases, RunbookRetriever(args.index))
    print(f"Recall@1: {report['recall@1']:.3f}")
    print(f"Recall@3: {report['recall@3']:.3f}")
    print(f"Recall@4: {report['recall@4']:.3f}")
    if args.output:
        Path(args.output).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
