import json, statistics, sys
from pathlib import Path

rows=[json.loads(x) for x in Path(sys.argv[1] if len(sys.argv)>1 else 'data/traces/traces.jsonl').read_text().splitlines() if x.strip()]
lat=[r.get('summary',{}).get('total_duration_ms',0) for r in rows]
def pct(p):
    return sorted(lat)[min(len(lat)-1, max(0, int(len(lat)*p/100)))] if lat else 0
out={'Task Count':len(rows),'Success Rate':sum(r.get('status')=='COMPLETED' for r in rows)/len(rows) if rows else 0,
     'Average E2E Latency':statistics.mean(lat) if lat else 0,'P50 Latency':pct(50),'P95 Latency':pct(95),
     'Average LLM Calls':statistics.mean(sum(s['span_type']=='LLM' for s in r['spans']) for r in rows) if rows else 0,
     'Average Tool Calls':statistics.mean(sum(s['span_type']=='TOOL' for s in r['spans']) for r in rows) if rows else 0}
print(json.dumps(out,indent=2))
