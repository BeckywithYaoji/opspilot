from app.observability import LocalTracer, redact

def test_span_timing_and_redaction(tmp_path):
    t=LocalTracer(task_id='t',path=tmp_path/'traces.jsonl')
    s=t.start('tool.check_port','TOOL',{'password':'123','host':'dev-server'})
    t.end(s); t.finish('COMPLETED',{'total_duration_ms':s.duration_ms})
    assert s.duration_ms >= 0
    assert s.metadata['password']=='***REDACTED***'
    assert 'dev-server' in s.metadata['host']
