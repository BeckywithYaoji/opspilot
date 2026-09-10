"""One attempt per case, real configured provider, isolated output. No Agent tuning."""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.agent import run_agent
from app.approval import ApprovalStore
from app.config import CompatibleChatModel, Settings, MemorySettings
from app.memory.session import RedisSessionMemoryStore


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',default='data/benchmark')
    args=parser.parse_args(); out=Path(args.root)
    for folder in ('runs','traces','results','expected'): (out/folder).mkdir(parents=True,exist_ok=True)
    os.environ['TRACE_OUTPUT_PATH']=str(out/'traces/final-traces.jsonl')
    cases=json.loads((out/'cases.json').read_text())
    runfile=out/'runs/final-real-model.jsonl'
    done={json.loads(x)['case_id'] for x in runfile.read_text().splitlines()} if runfile.exists() else set()
    settings=Settings.from_env()
    meta={'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'model':settings.model,'temperature':'provider default (unchanged)','timestamp':datetime.now(timezone.utc).isoformat(),'benchmark_case_count':len(cases),'embedding_model':'BAAI/bge-small-en-v1.5','redis':'configured via environment; isolated benchmark UUID sessions','evidence_type':'real_model','attempt_policy':'one attempt; resume skips recorded cases'}
    metafile=out/'results/configuration.json'
    if not metafile.exists(): metafile.write_text(json.dumps(meta,indent=2)+'\n')
    for case in cases:
        if case['case_id'] in done: continue
        session='benchmark-'+uuid4().hex
        rows=[]
        for index,turn in enumerate(case['turns']):
            model=CompatibleChatModel(settings)
            memory=RedisSessionMemoryStore.from_settings(MemorySettings.from_env())
            begin=time.perf_counter()
            try:
                result=run_agent(turn['message'],case['scenario'],model,session_id=session,memory_store=memory,approval_store=ApprovalStore(),trajectory_path=out/'runs/trajectories.jsonl')
                row={'response':result.model_dump(),'execution_duration_ms':(time.perf_counter()-begin)*1000,'turn':index+1}
            except Exception as exc:
                row={'response':None,'error_type':type(exc).__name__,'execution_duration_ms':(time.perf_counter()-begin)*1000,'turn':index+1}
            rows.append(row)
            print(case['case_id'],index+1,(row['response'] or {}).get('status',row.get('error_type')),flush=True)
        record={'case_id':case['case_id'],'session_id':session,'category':case['category'],'evidence_type':'real_model','turns':rows}
        with runfile.open('a') as f: f.write(json.dumps(record,ensure_ascii=False)+'\n'); f.flush()

if __name__=='__main__': main()
