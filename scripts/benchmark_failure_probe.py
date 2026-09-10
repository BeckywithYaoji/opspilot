"""Exercise existing MCP failure observation path without adding a tool."""
import json
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from app.agent import run_agent
from app.mcp.client import OpsMCPClient
from scripts.run_safety_benchmark import Intent
os.environ['TRACE_OUTPUT_PATH']=str(ROOT/'data/benchmark/traces/failure-traces.jsonl')
original=OpsMCPClient.__init__
def missing_index(self,scenario,*args,**kwargs):
    original(self,scenario,index_path=empty)
with TemporaryDirectory() as empty, TemporaryDirectory() as tmp, patch.object(OpsMCPClient,'__init__',missing_index):
    result=run_agent('根据 SSH 规范说明排障建议','repairable',Intent([('search_runbook',{'query':'SSH','top_k':1})]),trajectory_path=Path(tmp)/'trajectory.jsonl')
rows=[json.loads(x) for x in Path(os.environ['TRACE_OUTPUT_PATH']).read_text().splitlines()]
trace=next(t for t in rows if t['trace_id']==result.trace_id)
error=any(s['name']=='retrieval.runbook' and s['status']=='ERROR' and s['metadata'].get('error_type')=='retrieval_error' for s in trace['spans'])
payload={'evidence_type':'deterministic model + real MCP unavailable index + automatic trace','passed':result.status=='COMPLETED' and error,'response':result.model_dump(),'trace_id':result.trace_id}
(ROOT/'data/benchmark/runs/failure-probe.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n')
print(payload['passed'])
