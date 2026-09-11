"""Assert the same generated metric table is present in release documents."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def benchmark_table():
    m=json.loads((ROOT/'data/benchmark/results/final-metrics.json').read_text())
    values={'Task Success Rate':m['task_success_rate'],'Tool Selection Accuracy':m['tool_selection_accuracy'],'Tool Argument Accuracy':m['tool_argument_accuracy'],'Runbook Recall@3':m['runbook']['recall_at_3'],'Incident Recall@3':m['incident']['recall_at_3'],'Context Recall Accuracy':m['session']['context_recall_accuracy'],'Post-resolution Action Rate':m['reliability']['post_resolution_action_rate'],'Unauthorized Execution Rate':m['hitl']['unauthorized_execution_rate'],'Dispatch Trace Coverage':m['observability']['trace_coverage']}
    table='| Metric | V6 result |\n|---|---:|\n'
    table+=''.join(f'| {k} | {v:.2%} |\n' if v is not None else f'| {k} | unavailable |\n' for k,v in values.items())
    o=m['observability'];table+=f"| P50 / P95 completed-request latency | {o['p50_ms']/1000:.2f} / {o['p95_ms']/1000:.2f} s |\n"
    return table

def main():
    table=benchmark_table()
    for name in ('README.md','docs/benchmark.md','docs/resume.md'):
        assert table in (ROOT/name).read_text(),f'Benchmark mismatch: {name}'
    print('Benchmark document consistency: PASS')
if __name__=='__main__':main()
