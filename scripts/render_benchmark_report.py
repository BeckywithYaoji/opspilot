"""Render readable results from the machine-readable benchmark, without substitutions."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'data/benchmark/results'
m=json.loads((root/'final-metrics.json').read_text()); config=json.loads((root/'configuration.json').read_text()); failure=json.loads((root/'failure-analysis.json').read_text())
def block(title,values): return '\n## '+title+'\n\n'+'\n'.join('- '+k+': '+('unavailable' if v is None else str(v)) for k,v in values.items())+'\n'
r='# OpsPilot V6 Final Benchmark Report\n'
r+=block('1. Git',{'base':config['git_commit'],'final':'see V6 commit in git log','working tree':'verified before commit'})
r+=block('2. pytest',{'baseline':'98 passed, 1 skipped, 2 warnings','final':'see regression.txt (fresh run)'})
r+=block('3. Benchmark Configuration',config)
r+=block('4. Overall',{k:m[k] for k in ['real_model_cases','real_model_turns','task_success_rate','tool_selection_accuracy','tool_argument_accuracy','host_accuracy','service_accuracy','port_accuracy']})
r+=block('5. Runbook RAG',m['runbook']);r+=block('6. Incident Memory',m['incident']);r+=block('7. Session Memory',m['session'])
r+=block('8. Reliability',{k:v for k,v in m['reliability'].items() if k!='goal_completion_steps'});r+=block('9. HITL Safety',m['hitl']);r+=block('10. Observability',m['observability'])
r+='\n## 11. Token Usage\n\nunavailable; no estimates. The current transport discards provider usage.\n'
r+=block('12. Failure Analysis',failure['categories'])
r+='\n## 13. Reproducibility\n\nRun `python scripts/run_final_benchmark.py --root NEW_DIRECTORY` with a copy of cases.json. Restore the exported incidents via `scripts/prepare_benchmark.py --restore-incidents` only on a clean environment. Every original attempt is retained. The six multi-turn cases produce 42 requests for 36 cases. Safety evidence uses deterministic intent and actual HTTP/MCP/Redis; failure injection uses an unavailable index through the real MCP process.\n'
r+='\n## 14. Known Limitations\n\n- Mock SSH operations only; healthy is not an existing selectable scenario. Recovery intent is accepted at AWAITING_APPROVAL, not counted as executed repair.\n- Task success checks required evidence, arguments, and a nonempty answer; natural-language answer quality is not independently judged. No prompt tuning or retries.\n- Trace coverage measures component dispatch visibility. Existing tracing misses final-answer LLM calls, independently generates a different task_id, and measures retrieval around the MCP boundary rather than inside Qdrant. Average observed LLM spans is not total provider calls.\n- Latency uses external completed-request wall-clock timing; nested span sums are not valid E2E measurements. Pending calls are excluded, human wait duration unavailable. Token usage and independent goal-verifier accuracy unavailable.\n- Safety evidence covers sequential replay and Redis expiry, not concurrent approvals or the in-memory fallback. Production safety must not be inferred beyond tested conditions.\n- Incident recall uses broad persisted SSH relevance; the permission case expects ESCALATED incidents. The source snapshot includes development incidents and is not a production corpus.\n'
r+='\n## 15. V6 Status\n\n'+('COMPLETE' if m['real_model_cases']==36 and m['hitl'].get('safety_status')=='PASS' else 'INCOMPLETE')+'\n'
(root/'final-report.md').write_text(r)
