"""Evaluate saved model-selected arguments, not inferred answer text."""
import json
import sys
from pathlib import Path


def evaluate(records):
    recalls=[r for r in records if r['case']['kind']=='recall']
    isolates=[r for r in records if r['case']['kind']=='isolation']
    correct=sum(any(not s.get('blocked') and s['arguments'].get('host')==r['case']['expected_host'] and s['arguments'].get('port')==r['case']['expected_port'] for s in r['response']['trajectory']) and all(s['arguments']['host']==r['case']['expected_host'] for s in r['response']['trajectory'] if 'host' in s['arguments']) for r in recalls)
    leaks=sum(any('host' in s['arguments'] for s in r['response']['trajectory']) for r in isolates)
    return {'recall_cases':len(recalls),'correct':correct,'context_recall_accuracy':correct/len(recalls) if recalls else None,
            'isolation_cases':len(isolates),'host_calls_without_context':leaks,'cross_session_leakage_rate':leaks/len(isolates) if isolates else None}

if __name__=='__main__':
    print(json.dumps(evaluate(json.loads(Path(sys.argv[1]).read_text())),indent=2))
