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
out.update({'Runbook Retrieval Calls':sum(sum(s['name']=='retrieval.runbook' for s in r['spans']) for r in rows),
 'Incident Retrieval Calls':sum(sum(s['name']=='retrieval.incident_memory' for s in r['spans']) for r in rows),
 'Approval Required Count':sum(sum(s['name']=='approval.created' for s in r['spans']) for r in rows),
 'Approval Rate':sum(any(s['name']=='approval.created' for s in r['spans']) for r in rows)/len(rows) if rows else 0,
 'Approval Resume Success Rate':sum(any(s['name']=='approval.resume' and s['metadata'].get('resume_success') for s in r['spans']) for r in rows)/len(rows) if rows else 0,
 'Replay Blocked Count':sum(sum(s['name']=='approval.replay_blocked' for s in r['spans']) for r in rows),
 'Tool Error Rate':sum(sum(s['span_type']=='TOOL' and s['status']=='ERROR' for s in r['spans']) for r in rows)/max(1,sum(sum(s['span_type']=='TOOL' for s in r['spans']) for r in rows)),
 'Retrieval Error Rate':sum(sum(s['span_type']=='RETRIEVAL' and s['status']=='ERROR' for s in r['spans']) for r in rows)/max(1,sum(sum(s['span_type']=='RETRIEVAL' for s in r['spans']) for r in rows)),
 'Trace Error Rate':sum(any(s['status']=='ERROR' for s in r['spans']) for r in rows)/len(rows) if rows else 0})
expected={
 'simple': {'agent.llm','tool.check_port','verifier.goal_completion'},
 'runbook': {'agent.llm','tool.search_runbook','retrieval.runbook','verifier.goal_completion'},
 'incident': {'agent.llm','tool.search_incident_memory','retrieval.incident_memory'},
 'hitl_approve': {'agent.llm','guardrail.permission','approval.created','approval.resolved','approval.resume','tool.restart_service'},
 'hitl_reject': {'guardrail.permission','approval.created','approval.resolved','approval.resume'},
 'failure': {'retrieval.incident_memory'},
}
cover=[]
for r in rows:
    scenario=r.get('summary',{}).get('scenario') or r.get('scenario')
    if scenario in expected:
        names={s['name'] for s in r['spans']}; cover.append(len(names & expected[scenario])/len(expected[scenario]))
out['Trace Coverage']=sum(cover)/len(cover) if cover else 0.0
print(json.dumps(out,indent=2))
