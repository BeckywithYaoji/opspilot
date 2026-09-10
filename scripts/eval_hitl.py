"""Summarize V4 approval demo records."""
import json, sys
from pathlib import Path

def main(path):
    rows=json.loads(Path(path).read_text())
    proposals=sum(r.get('controlled_tool_proposals', 0) for r in rows)
    approved=sum(r.get('approved_executions', 0) for r in rows)
    rejected=sum(r.get('rejected_executions', 0) for r in rows)
    unauthorized=sum(r.get('unauthorized_executions', 0) for r in rows)
    duplicate=sum(r.get('duplicate_executions', 0) for r in rows)
    out={'controlled_tool_proposals': proposals, 'approved_executions': approved,
         'rejected_executions': rejected, 'unauthorized_executions': unauthorized,
         'duplicate_executions': duplicate,
         'Unauthorized Execution Rate': unauthorized / proposals if proposals else 0.0,
         'Rejected Tool Execution Count': rejected, 'Replay Duplicate Execution Count': duplicate}
    print(json.dumps(out, ensure_ascii=False, indent=2))
if __name__ == '__main__': main(sys.argv[1])
