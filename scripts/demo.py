"""Human-readable CLI demo; displays public observations only."""
import argparse
import json
from uuid import uuid4
from smoke_test import request

def display(result):
    for step in result.get('trajectory',[]):
        print('AGENT TOOL:',step['tool'],json.dumps(step['arguments'],ensure_ascii=False))
        print('OBSERVATION:',json.dumps(step['observation'],ensure_ascii=False))
        if step.get('permission_decision'): print('GUARDRAIL:',step['permission_decision'])
    print('FINAL:',result.get('answer',result.get('observation')))
    print('TRACE ID:',result.get('trace_id'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--url',default='http://127.0.0.1:8000');p.add_argument('--case',choices=['all','direct','rag','memory','hitl'],default='all');p.add_argument('--approve',action='store_true',help='Explicitly approve the mock restart for noninteractive demonstration');a=p.parse_args()
    cases={'direct':['检查 dev-server 的 22 端口。'],'rag':['根据 SSH 运维规范，恢复后应该检查哪些内容？'],'memory':['检查 dev-server 的 sshd 状态。','刚才那台机器的 22 端口呢？'],'hitl':['请重启 dev-server 的 sshd。']}
    for label,queries in cases.items():
        if a.case not in ('all',label):continue
        session='demo-'+uuid4().hex
        for message in queries:
            print('\nUSER:',message,flush=True)
            result=request(a.url,'/api/agent/run',{'message':message,'scenario':'repairable','session_id':session});display(result)
            pending=result.get('pending_approval')
            if pending:
                approved=a.approve or input('Approve mock restart? [y/N] ').strip().lower()=='y'
                decision='APPROVE' if approved else 'REJECT';print('APPROVAL:',decision)
                resumed=request(a.url,'/api/agent/approval',{'approval_id':pending['approval_id'],'decision':decision});display(resumed)
if __name__=='__main__':main()
