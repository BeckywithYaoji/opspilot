"""Summarize reliability metrics from trajectory JSONL."""
import json, sys
from pathlib import Path

def evaluate(path: str) -> dict:
    rows = [json.loads(line) for line in Path(path).read_text().splitlines() if line.strip()]
    calls = [s for r in rows for s in r.get('steps', [])]
    total = len(calls)
    repeated = sum(bool(s.get('repeated')) for s in calls)
    blocked = sum(bool(s.get('blocked')) for s in calls)
    post = sum(bool(s.get('post_resolution_action')) for s in calls)
    return {'tasks': len(rows), 'total_tool_calls': total, 'retrieval_calls': sum(s.get('tool') == 'search_runbook' for s in calls),
            'repeated_tool_calls': repeated, 'blocked_tool_calls': blocked, 'post_resolution_actions': post,
            'average_tool_calls': total / len(rows) if rows else 0, 'repeated_tool_rate': repeated / total if total else 0,
            'post_resolution_action_rate': post / total if total else 0,
            'task_completion_rate': sum(r.get('status') == 'COMPLETED' for r in rows) / len(rows) if rows else 0}

if __name__ == '__main__':
    if len(sys.argv) < 2: raise SystemExit('usage: python scripts/eval_reliability.py TRAJECTORY.jsonl [OUTPUT.json]')
    result = evaluate(sys.argv[1]); print(json.dumps(result, ensure_ascii=False, indent=2))
    if len(sys.argv) > 2: Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
