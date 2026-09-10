import sys
from langchain_core.messages import AIMessage
from app.agent import run_agent
from tests.test_agent import ScriptedModel, call


def test_reproduce_early_stop_scope_error(tmp_path):
    errors = []
    def trace(frame, event, arg):
        if event == 'exception' and frame.f_code.co_name == 'tool_node':
            errors.append(arg[0].__name__)
        return trace
    sys.settrace(trace)
    try:
        result = run_agent('按规范恢复', 'repairable', ScriptedModel([
            call('restart_service', {'host':'dev-server','service':'sshd'}),
            AIMessage(content='done')]), trajectory_path=tmp_path/'run.jsonl')
    finally:
        sys.settrace(None)
    assert result.status == 'COMPLETED', errors
    assert result.environment

import pytest
from app.completion import verify_goal, completion_context
from app.models import TrajectoryStep

@pytest.mark.parametrize('query,observation,finish', [
    ('Check database availability', {'status':'running'}, True),
    ('Retrieve the requested policy', {'status':'ok','results':['policy']}, True),
    ('Recover or escalate', {'status':'failed','error':'access denied'}, False),
    ('Recover or escalate', {'status':'created'}, True),
])
def test_generic_structured_contract(query, observation, finish):
    class Model:
        def invoke_structured(self, messages, schema):
            assert query in messages[-1].content
            return {'goal_satisfied':finish,'decision':'FINISH' if finish else 'CONTINUE','unresolved_requirements':[] if finish else ['escalation pending']}
    ctx=completion_context(query,[TrajectoryStep(step=1,tool='operation',arguments={},observation=observation)],{})
    result,error=verify_goal(Model(),ctx)
    assert result.goal_satisfied == finish and error is None

@pytest.mark.parametrize('value',[TimeoutError(), {'goal_satisfied':True,'decision':'CONTINUE','unresolved_requirements':[]}, {'bad':True}])
def test_verifier_failure_continues(value):
    class Model:
        def invoke_structured(self,*args):
            if isinstance(value,Exception): raise value
            return value
    result,error=verify_goal(Model(),{})
    assert not result.goal_satisfied and error


def test_latest_snapshot_early_stop_and_batch_cancel(tmp_path, monkeypatch):
    from app.mcp.client import OpsMCPClient
    snapshots=[]
    original=OpsMCPClient.snapshot
    async def snapshot(self):
        assert not snapshots, 'unexpected final snapshot read'
        result=await original(self)
        snapshots.append(result)
        return result
    monkeypatch.setattr(OpsMCPClient,'snapshot',snapshot)
    class Model(ScriptedModel):
        def invoke_structured(self,messages,schema):
            import json
            ctx=json.loads(messages[-1].content)
            assert ctx['current_environment_snapshot']['environment']['dev-server']['services']['sshd']=='running'
            return {'goal_satisfied':True,'decision':'FINISH','unresolved_requirements':[]}
    model=Model([AIMessage(content='',tool_calls=[{'name':'restart_service','args':{'host':'dev-server','service':'sshd'},'id':'one'},{'name':'check_port','args':{'host':'dev-server','port':22},'id':'two'}]),AIMessage(content='Recovered.')])
    result=run_agent('Recover the requested service','repairable',model,trajectory_path=tmp_path/'run.jsonl')
    assert result.status=='COMPLETED' and result.success and result.environment
    assert len(result.trajectory)==1 and result.goal_satisfied_at_step==1


def test_failed_verifier_does_not_stop_agent(tmp_path):
    class Model(ScriptedModel):
        def invoke_structured(self,*args):
            raise TimeoutError('do not log secret provider payload')
    model=Model([call('check_port',{'host':'dev-server','port':22}),AIMessage(content='Port closed.')])
    result=run_agent('Inspect status','repairable',model,trajectory_path=tmp_path/'run.jsonl')
    assert result.status=='COMPLETED' and result.answer=='Port closed.'
    assert result.goal_satisfied_at_step is None
    assert result.trajectory[0].completion_verifier_error
    assert 'secret provider' not in result.model_dump_json()


def test_metric_detects_tools_after_completion(tmp_path):
    import json
    from scripts.eval_reliability import evaluate
    path=tmp_path/'runs.jsonl'
    path.write_text(json.dumps({'status':'COMPLETED','steps':[{'step':1,'tool':'verify','goal_satisfied_after_step':True},{'step':2,'tool':'search_runbook'}]})+'\n')
    assert evaluate(str(path))['post_resolution_actions']==1
