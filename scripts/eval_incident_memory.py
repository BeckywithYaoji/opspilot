"""Evaluate incident retrieval decisions from saved demos."""
import json
from pathlib import Path

def evaluate(path):
    rows=json.loads(Path(path).read_text())
    relevant=[r for r in rows if r['expected']=='relevant']
    irrelevant=[r for r in rows if r['expected']=='irrelevant']
    relevant_hit=sum(r['retrieved'] for r in relevant)
    unnecessary=sum(r['retrieved'] for r in irrelevant)
    return {'cases':len(rows),'incident_retrieval_decision_accuracy':(relevant_hit+len(irrelevant)-unnecessary)/len(rows) if rows else 0,'unnecessary_incident_retrieval_rate':unnecessary/len(irrelevant) if irrelevant else 0,'incident_recall@1':relevant_hit/len(relevant) if relevant else 0,'incident_recall@3':relevant_hit/len(relevant) if relevant else 0}

if __name__=='__main__': print(json.dumps(evaluate('data/eval/incident_memory_cases.json'),ensure_ascii=False,indent=2))
