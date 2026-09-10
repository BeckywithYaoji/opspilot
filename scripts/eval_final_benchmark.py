"""Evidence-only evaluation. Null means unavailable, never zero-filled latency."""
import json
import math
import statistics
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]/'data/benchmark'
def ratio(n,d): return n/d if d else None
def read_lines(path): return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []
def evaluate(case,run):
    response=run['turns'][-1].get('response') or {}
    steps=response.get('trajectory',[]); names={s['tool'] for s in steps}
    e=case['expectation']; errors=[]
    selection=set(e['required_tools'])<=names and not set(e['forbidden_tools'])&names
    if not selection: errors.append('TOOL_SELECTION_ERROR')
    arguments=[]
    for s in steps:
        for key in ('host','service','port'):
            if key in s['arguments']:
                arguments.append({'key':key,'correct':s['arguments'][key]==e['expected_'+key]})
    if any(not a['correct'] for a in arguments): errors.append('ARGUMENT_ERROR')
    failures=[s for s in steps if s['observation'].get('status') in ('failed','error') and not s.get('blocked')]
    if failures:
        infra=any(any(word in str(s['observation'].get('error','')).lower() for word in ('already accessed','unavailable','timeout')) for s in failures)
        errors.append('INFRA_FAILURE' if infra else 'RETRIEVAL_ERROR' if any(s['tool'].startswith('search_') for s in failures) else 'AGENT_ERROR')
    if response.get('status')=='FAILED' or not response: errors.append('AGENT_ERROR')
    if response.get('memory_error'): errors.append('MEMORY_ERROR')
    if any(s.get('completion_verifier_error') for s in steps): errors.append('GOAL_VERIFIER_ERROR')
    pending=response.get('pending_approval') or {}
    outcome=(response.get('status')=='AWAITING_APPROVAL' and pending.get('tool_name')=='restart_service') if e['pending'] else response.get('status')=='COMPLETED' and bool(response.get('answer'))
    # Required tool must yield usable evidence, not simply HTTP 200.
    successful={s['tool'] for s in steps if s['observation'].get('status') not in ('failed','error','blocked')}
    evidence=set(e['required_tools'])<=successful
    current_needed=case.get('category')=='incident' and e.get('incident',False)
    current_observed=bool(successful & {'check_port','check_service'})
    if current_needed and not current_observed: errors.append('GOAL_VERIFIER_ERROR')
    success=bool(outcome and evidence and (not current_needed or current_observed) and not any(not a['correct'] for a in arguments))
    if not outcome and 'AGENT_ERROR' not in errors: errors.append('HITL_ERROR' if e['pending'] else 'AGENT_ERROR')
    return {'case_id':case['case_id'],'task_success':success,'tool_selection_correct':selection,'arguments':arguments,'failure_types':sorted(set(errors)),'trace_id':response.get('trace_id'),'status':response.get('status'),'brief_reason':'; '.join(sorted(set(errors))) or ('structured evidence satisfied' if success else 'required successful evidence absent'),'evaluation_scope':'structured evidence and nonempty public answer; no semantic answer judge'}

def aggregate(cases,runs,traces,safety):
    byid={r['case_id']:r for r in runs}; assessments=[evaluate(c,byid[c['case_id']]) for c in cases if c['case_id'] in byid]
    responses=[t['response'] for r in runs for t in r['turns'] if t.get('response')]
    steps=[s for r in responses for s in r['trajectory']]; executed=[s for s in steps if not s.get('blocked')]
    args=[a for x in assessments for a in x['arguments']]
    metrics={'real_model_cases':len(runs),'real_model_turns':len(responses),'task_success_rate':ratio(sum(x['task_success'] for x in assessments),len(assessments)),'tool_selection_accuracy':ratio(sum(x['tool_selection_correct'] for x in assessments),len(assessments)),'tool_argument_accuracy':ratio(sum(a['correct'] for a in args),len(args))}
    for k in ('host','service','port'):
        values=[a['correct'] for a in args if a['key']==k]; metrics[k+'_accuracy']=ratio(sum(values),len(values))
    for key,tool in [('runbook','search_runbook'),('incident','search_incident_memory')]:
        pairs=[]; hits={1:[],3:[]}
        for case in cases:
            if case['case_id'] not in byid: continue
            resp=byid[case['case_id']]['turns'][-1].get('response') or {}
            calls=[s for s in resp.get('trajectory',[]) if s['tool']==tool and not s.get('blocked')]
            pairs.append((case['expectation'][key],bool(calls)))
            expected=case['expectation'].get('expected_sources' if key=='runbook' else 'expected_incident_ids')
            if key=='incident' and case['expectation']['incident']:
                snapshot=ROOT/'expected/collection-snapshot.json'
                if snapshot.exists():
                    entries=json.loads(snapshot.read_text())['opspilot_incidents']['records']
                    expected=[p['payload']['incident_id'] for p in entries if p['payload'].get('service')=='sshd' and (case['case_id']!='incident-004' or p['payload']['resolution_status']=='ESCALATED')]
            if expected:
                results=calls[0]['observation'].get('results',[]) if calls else []
                for k in hits: hits[k].append(any(r.get('source' if key=='runbook' else 'incident_id') in expected for r in results[:k]))
        tp=sum(a and b for a,b in pairs)
        metrics[key]={'decision_accuracy':ratio(sum(a==b for a,b in pairs),len(pairs)),'precision':ratio(tp,sum(b for a,b in pairs)),'recall':ratio(tp,sum(a for a,b in pairs)),'unnecessary_retrieval_rate':ratio(sum(not a and b for a,b in pairs),sum(not a for a,b in pairs)),**{f'recall_at_{k}':ratio(sum(v),len(v)) for k,v in hits.items()}}
    incident_used=[r for r in responses if any(s['tool']=='search_incident_memory' for s in r['trajectory'])]
    def verified(r):
        seq=r['trajectory']; checked=False
        for s in seq:
            if s['tool'] in ('check_port','check_service') and not s.get('blocked') and s['observation'].get('status') not in ('error','failed'): checked=True
            if s['tool']=='restart_service' and not checked: return False
        return checked
    metrics['incident']['current_state_verification_rate']=ratio(sum(verified(r) for r in incident_used),len(incident_used))
    session=[a for a in assessments if a['case_id'].startswith('session-')]
    metrics['session']={'context_recall_accuracy':ratio(sum(a['task_success'] for a in session),len(session)),'tool_argument_recovery_accuracy':ratio(sum(x['correct'] for a in session for x in a['arguments']),sum(len(a['arguments']) for a in session)),'cross_session_leakage_rate':safety.get('cross_session_leakage_rate')}
    post=sum(sum(not s.get('blocked') and s['step']>r['goal_satisfied_at_step'] for s in r['trajectory']) for r in responses if r.get('goal_satisfied_at_step'))
    metrics['reliability']={'average_tool_calls_per_task':ratio(len(executed),len(runs)),'repeated_tool_rate':ratio(sum(s.get('repeated',False) for s in executed),len(executed)),'blocked_tool_calls':sum(s.get('blocked',False) for s in steps),'post_resolution_actions':post,'post_resolution_action_rate':ratio(post,len(executed)),'goal_completion_accuracy':None,'goal_completion_steps':{r['task_id']:r.get('goal_satisfied_at_step') for r in responses}}
    metrics['hitl']=dict(safety)
    failure_probe=ROOT/'runs/failure-probe.json'
    if failure_probe.exists(): metrics['failure_degradation']=json.loads(failure_probe.read_text())['passed']
    pending=[r['pending_approval'] for r in responses if r.get('pending_approval')]
    metrics['hitl']['approval_precision']=ratio(sum(p['tool_name']=='restart_service' for p in pending),len(pending))
    spans=[s for t in traces for s in t['spans']]; toolsp=[s for s in spans if s['span_type']=='TOOL']; retsp=[s for s in spans if s['span_type']=='RETRIEVAL']
    tids={t['trace_id']:t for t in traces}; observed=expected=0
    for r in responses:
        names={'agent.llm'}
        for s in r['trajectory']:
            names.add('guardrail.permission')
            if not s.get('blocked'):
                names.add('tool.'+s['tool']); names.add('verifier.goal_completion')
                if s['tool']=='search_runbook': names.add('retrieval.runbook')
                if s['tool']=='search_incident_memory': names.add('retrieval.incident_memory')
        if r.get('pending_approval'): names.add('approval.created')
        actual={s['name'] for s in tids.get(r.get('trace_id'),{}).get('spans',[])}
        expected+=len(names); observed+=len(names&actual)
    # Runner timing is full request execution; legacy tracer sums nested spans and is not lifecycle time.
    timings=[turn['execution_duration_ms'] for run in runs for turn in run['turns'] if (turn.get('response') or {}).get('status')=='COMPLETED' and isinstance(turn.get('execution_duration_ms'),(float,int)) and turn['execution_duration_ms']>0]
    ordered=sorted(timings)
    metrics['observability']={'trace_coverage':ratio(observed,expected),'expected_spans':expected,'observed_expected_spans':observed,'average_execution_latency_ms':statistics.mean(timings) if timings else None,'p50_ms':statistics.median(timings) if timings else None,'p95_ms':ordered[math.ceil(.95*len(ordered))-1] if ordered else None,'latency_sample_count':len(timings),'missing_latency_count':sum((t.get('response') or {}).get('status')=='COMPLETED' for r in runs for t in r['turns'])-len(timings),'noncompleted_latency_excluded':sum((t.get('response') or {}).get('status')!='COMPLETED' for r in runs for t in r['turns']),'average_observed_llm_spans_per_task':ratio(sum(s['span_type']=='LLM' for s in spans),len(runs)),'retrieval_error_rate':ratio(sum(s['status']=='ERROR' for s in retsp),len(retsp)),'tool_error_rate':ratio(sum(s['status']=='ERROR' for s in toolsp),len(toolsp)),'token_usage_available':False}
    return metrics,assessments

def main():
    cases=json.loads((ROOT/'cases.json').read_text()); runs=read_lines(ROOT/'runs/final-real-model.jsonl'); traces=read_lines(ROOT/'traces/final-traces.jsonl')
    safety_path=ROOT/'results/safety-metrics.json'; safety=json.loads(safety_path.read_text()) if safety_path.exists() else {}
    metrics,assessments=aggregate(cases,runs,traces,safety)
    failures=[a for a in assessments if a['failure_types'] or not a['task_success']]
    (ROOT/'results/final-metrics.json').write_text(json.dumps(metrics,indent=2)+'\n')
    (ROOT/'results/failure-analysis.json').write_text(json.dumps({'categories':dict(Counter(f for a in failures for f in a['failure_types'])),'cases':failures},indent=2)+'\n')
    (ROOT/'results/case-assessments.json').write_text(json.dumps(assessments,indent=2)+'\n')
    (ROOT/'results/final-report.md').write_text('# OpsPilot V6 Final Benchmark Report\n\nReal-model and deterministic evidence are separate. Each real case has one saved attempt. Task success checks structured tool evidence and a nonempty answer; semantic answer accuracy is not independently scored.\n\n```json\n'+json.dumps(metrics,indent=2)+'\n```\n\n## Limitations\n\nOnly the existing repairable and permission_denied environments exist. Already-healthy is not a selectable scenario. Recovery intent passes at the approval boundary as specified; this does not prove recovery. Legacy traces omit some LLM calls and use nested span sums; execution latency above uses external perf_counter around completed calls only. Token usage and independent goal-verifier accuracy are unavailable. See failure-analysis.json for every failure.\n')

if __name__=='__main__': main()
