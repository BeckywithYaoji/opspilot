from scripts.eval_final_benchmark import evaluate,aggregate

def test_pending_is_not_actual_execution_and_bad_service_is_argument_error():
    case={'case_id':'x','expectation':{'required_tools':['restart_service'],'forbidden_tools':[],'pending':True,'expected_host':'dev-server','expected_service':'sshd','expected_port':22}}
    response={'status':'AWAITING_APPROVAL','pending_approval':{'tool_name':'restart_service'},'trajectory':[{'tool':'restart_service','arguments':{'host':'dev-server','service':'ssh'},'observation':{'status':'pending_approval'},'blocked':True}]}
    result=evaluate(case,{'turns':[{'response':response}]})
    assert not result['task_success']
    assert 'ARGUMENT_ERROR' in result['failure_types']

def test_missing_latency_not_zero_and_coverage_weighted():
    case={'case_id':'x','category':'direct','expectation':{'required_tools':[],'forbidden_tools':[],'pending':False,'runbook':False,'incident':False}}
    response={'task_id':'task','trace_id':'trace','status':'COMPLETED','answer':'ok','trajectory':[]}
    metrics,_=aggregate([case],[{'case_id':'x','turns':[{'response':response}]}],[],{})
    assert metrics['observability']['latency_sample_count']==0
    assert metrics['observability']['missing_latency_count']==1
    assert metrics['observability']['p50_ms'] is None
    assert metrics['observability']['trace_coverage']==0
