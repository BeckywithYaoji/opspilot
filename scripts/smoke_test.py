"""Small real-provider smoke test; never runs the full benchmark."""
import argparse
import json
from urllib.request import Request,urlopen

def request(base,path,payload=None):
    data=None if payload is None else json.dumps(payload).encode()
    req=Request(base.rstrip('/')+path,data=data,headers={'Content-Type':'application/json'})
    with urlopen(req,timeout=180) as response: return json.load(response)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--url',default='http://127.0.0.1:8000');args=parser.parse_args()
    health=request(args.url,'/health');ready=request(args.url,'/ready')
    result=request(args.url,'/api/agent/run',{'message':'检查 dev-server 的 22 端口，不做修复。','scenario':'repairable'})
    assert health['status']=='ok' and ready['status']=='healthy'
    assert result['trace_id'] and result['status']=='COMPLETED'
    assert any(s['tool']=='check_port' and not s['blocked'] and s['observation'].get('status') in ('open','closed') for s in result['trajectory'])
    print(json.dumps({'health':health,'readiness':ready,'status':result['status'],'trace_id':result['trace_id'],'tools':[s['tool'] for s in result['trajectory']]},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
