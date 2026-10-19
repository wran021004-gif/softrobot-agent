"""Explicit read-only S6 outcome audit/export; never launches scientific computation."""
import argparse
from pathlib import Path
from tools.platform_host import Host
from tools.research import core
from tools.research.state import state
from tools.research.research_context import context
from tools.research.feedback import task_gap
from tools.research.candidate_portfolio import ranking_key
from tools.state_io import atomic_json

ROOT=Path(__file__).resolve().parents[2]


def audit(host,destination):
    s=state(host);destination=Path(destination);core.export(host,destination/'study')
    rows=[]
    for ref in [*s.get('results',[]),*s.get('physical_replays',[]),*s.get('rl_evaluations',[])]:
        result=host.store.artifact(ref);candidate=host.store.artifact(result['candidate'])
        row=dict(reference=ref,candidate=result['candidate'],task_gap=task_gap(result),acceptance=result.get('acceptance'),
            execution_id=result.get('execution_id'),task_identity=candidate.get('effective_task_identity'),
            structure=candidate['configuration']['robot'],source=result.get('source_reference'),
            numerical_s=result.get('charged_numerical_s'),implementation=result.get('implementation'),
            original_result=result)
        rows.append(row)
    best=min(rows,key=ranking_key) if rows else None
    if best and best.get('source'):
        atomic_json(destination/'best_control.json',dict(evaluation=best['reference'],candidate=best['candidate'],
            schedule=host.store.artifact(best['source']),configuration=host.store.artifact(best['candidate'])['configuration'],
            task_gap=best['task_gap'],acceptance=best['acceptance']))
    events=host.store.events(host.run_id);decisions=[];feedback=[];usage=[]
    for e in events:
        if e['kind'] in ('model_original_tool_request','model_original_tool_feedback','r3_response'):
            value=host.store.artifact(e['outputs'][0])
            if e['kind']=='model_original_tool_request':decisions.append(value)
            elif e['kind']=='model_original_tool_feedback':feedback.append(value)
            elif value.get('usage') is not None:usage.append(dict(request_id=e.get('request_id'),usage=value['usage']))
    atomic_json(destination/'decisions.json',dict(requests=decisions,feedback=feedback))
    disposition=host.store.artifact(s['final_disposition']) if s.get('final_disposition') else {}
    action=disposition.get('original_plan',{}).get('action')
    summary=dict(study_id=host.run_id,freeze=s.get('freeze'),status=s['research_status'],
        original_task_passed=bool(s.get('success_gate')),selected=s.get('selected'),
        native_model_stop=disposition.get('origin')=='model' and action=='stop',
        native_model_selection=disposition.get('origin')=='model' and action=='select',
        engineering_closeout=disposition if disposition.get('kind')=='engineering_count_budget_closure' else None,pending=s.get('pending'),
        ledger=host.store.remaining(),provider_requests=s['pilot']['live_model_requests'],provider_usage=usage,
        mathematical_evaluations=s.get('mathematical_evaluations',0),nmpc=s.get('nmpc_launches',0),
        ppo_stages=s.get('admitted_training_stages',0),physical_replays=s.get('physical_replay_launches',0),
        numerical_s=s['numerical_s'],control_search_results=s.get('control_search_results',[]),
        results=rows,best=best,inherited_best=context(host)['best_valid'],
        remaining_hypotheses=context(host)['unresolved_hypotheses'],
        interpretation='Only original registered acceptance establishes physical success. Finite search failure does not establish structural infeasibility; no method superiority, robustness or hardware claim.')
    atomic_json(destination/'summary.json',summary)
    print(dict(study_id=host.run_id,status=s['research_status'],provider_requests=summary['provider_requests'],
        physical_replays=summary['physical_replays'],passed=summary['original_task_passed'],
        best_gap=best['task_gap']['normalized_gap'] if best else None))
    return summary


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('run_id');p.add_argument('destination',type=Path);args=p.parse_args()
    audit(Host(ROOT/'runs/research'/args.run_id,args.run_id,actor='unified-research'),args.destination)
