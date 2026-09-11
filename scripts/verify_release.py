"""Local release checks; failures are preserved, Docker unavailability is explicit."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--smoke-url');parser.add_argument('--skip-tests',action='store_true');args=parser.parse_args()
    checks={}
    def run(name,command,env=None):
        result=subprocess.run(command,cwd=ROOT,env=env);checks[name]='PASS' if result.returncode==0 else 'FAIL'
    if not args.skip_tests:
        run('pytest',[sys.executable,'-m','pytest','-v'],{**os.environ,'TRACE_OUTPUT_PATH':'/tmp/opspilot-release-test-traces.jsonl'})
    run('benchmark_consistency',[sys.executable,'scripts/check_release_consistency.py'])
    for file in ('final-metrics.json','final-report.md','failure-analysis.json'):
        checks[file]='PASS' if (ROOT/'data/benchmark/results'/file).is_file() else 'FAIL'
    if shutil.which('docker'):
        run('docker_config',['docker','compose','config','--quiet'])
        result=subprocess.run(['docker','info'],capture_output=True)
        checks['docker_daemon']='available' if result.returncode==0 else 'unavailable'
    else: checks['docker_config']='unavailable'; checks['docker_daemon']='unavailable'
    files=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0')
    suspicious=[]
    pattern=re.compile(r'(?:sk-[A-Za-z0-9]{20,}|Bearer\s+[A-Za-z0-9._-]{24,})')
    for name in files:
        if not name:continue
        p=ROOT/name
        if not p.is_file():continue
        try: content=p.read_text()
        except UnicodeError:continue
        if pattern.search(content): suspicious.append(name)
    checks['secret_scan']='FAIL' if suspicious or '.env' in files else 'PASS'
    if suspicious:print('Potential secret locations (values hidden):',suspicious)
    if args.smoke_url:run('smoke',[sys.executable,'scripts/smoke_test.py','--url',args.smoke_url])
    print(json.dumps(checks,indent=2))
    sys.exit(1 if 'FAIL' in checks.values() else 0)
if __name__=='__main__':main()
