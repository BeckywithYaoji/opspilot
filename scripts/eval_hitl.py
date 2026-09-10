"""Summarize V4 approval demo records."""
import json, sys
from pathlib import Path

def main(path):
    rows=json.loads(Path(path).read_text())
    calls=sum(len(r.get('trajectory', [])) for r in rows)
    pending=sum(1 for r in rows if r.get('status')=='AWAITING_APPROVAL')
    approved=sum(1 for r in rows if r.get('status')=='approved')
    rejected=sum(1 for r in rows if r.get('status')=='rejected')
    print(json.dumps({'total_tool_calls': calls, 'pending': pending, 'approved': approved, 'rejected': rejected}, ensure_ascii=False, indent=2))
if __name__ == '__main__': main(sys.argv[1])
