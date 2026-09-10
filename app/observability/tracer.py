import json, os, time
from pathlib import Path
from uuid import uuid4
from pydantic import BaseModel, Field

SENSITIVE_KEYS={'password','token','secret','api_key','authorization'}
def redact(value):
    if isinstance(value, dict): return {k: ('***REDACTED***' if k.lower() in SENSITIVE_KEYS else redact(v)) for k,v in value.items()}
    if isinstance(value, list): return [redact(v) for v in value]
    return value

class TraceSpan(BaseModel):
    span_id: str = Field(default_factory=lambda: str(uuid4()))
    trace_id: str
    parent_span_id: str|None=None
    name: str
    span_type: str
    start_time: float
    end_time: float|None=None
    duration_ms: float|None=None
    status: str='OK'
    metadata: dict = Field(default_factory=dict)
    metrics: dict = Field(default_factory=dict)
    error: str|None=None

class TraceRecord(BaseModel):
    trace_id: str
    task_id: str
    session_id: str|None=None
    status: str='RUNNING'
    spans: list[TraceSpan]=Field(default_factory=list)
    summary: dict=Field(default_factory=dict)

class LocalTracer:
    def __init__(self, trace_id=None, task_id=None, session_id=None, path=None):
        self.record=TraceRecord(trace_id=trace_id or 'trace-'+str(uuid4()), task_id=task_id or str(uuid4()), session_id=session_id)
        self.path=Path(path or os.getenv('TRACE_OUTPUT_PATH','data/traces/traces.jsonl'))
    def start(self,name,span_type,metadata=None,parent_span_id=None):
        s=TraceSpan(trace_id=self.record.trace_id,name=name,span_type=span_type,start_time=time.perf_counter(),metadata=redact(metadata or {}),parent_span_id=parent_span_id); self.record.spans.append(s); return s
    def end(self,s,status='OK',metrics=None,error=None):
        s.end_time=time.perf_counter(); s.duration_ms=max(0,(s.end_time-s.start_time)*1000); s.status=status; s.error=error; s.metrics.update(metrics or {}); return s
    def finish(self,status,summary=None):
        self.record.status=status; self.record.summary=summary or {}
        if self.record.spans:
            self.record.summary.setdefault('total_duration_ms', sum(s.duration_ms or 0 for s in self.record.spans))
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('a',encoding='utf-8') as f: f.write(self.record.model_dump_json()+'\n')
        return self.record

    @classmethod
    def append_event(cls, trace_id, name, span_type='APPROVAL', metadata=None, status='OK', error=None, path=None):
        t=cls(trace_id=trace_id, path=path)
        s=t.start(name, span_type, metadata); t.end(s, status=status, error=error)
        target=t.path
        records=[]
        if target.exists():
            records=[json.loads(x) for x in target.read_text().splitlines() if x.strip()]
        for record in reversed(records):
            if record.get('trace_id')==trace_id:
                record.setdefault('spans',[]).append(s.model_dump()); target.write_text('\n'.join(json.dumps(x,ensure_ascii=False) for x in records)+'\n'); return
        t.finish('RUNNING')
