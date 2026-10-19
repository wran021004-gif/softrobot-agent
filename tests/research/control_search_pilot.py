"""Explicit P0/P1 pilot; ordinary discovery never launches scientific work."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from tools.research import core
from tools.research.candidate_portfolio import historical_records, portfolio, compatible_schedule, ranking_key
from tools.research.numerics import ROOT, archived
from tools.research.physical_replay import evaluate_schedule
from tools.research.feedback import task_gap
from tools.research.state import state, save
from tools.state_io import atomic_json, read
from tests.research.sorosim_s56_refinement import plan


def source_hashes():
    paths=[]
    for prefix in ('sorosim_s56','sorosim_s58','sorosim_s59','sorosim_s510'):
        paths.extend(p for p in (ROOT/'evidence'/prefix).rglob('*') if p.is_file())
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def materialize(host,row):
    old=archived(row['source_folder'],row['source_candidate'])
    parameters=deepcopy(old['parameters']);parameters['family_space_identity']=state(host)['spec']['family_space_identity']
    candidate=core.dispatch(host,plan('generate',generation=parameters),
        'source-design-'+row['source_candidate']['artifact_id'],origin='engineering')['result']['candidate']
    return candidate,compatible_schedule(row,host.store.artifact(candidate)['configuration'])


def evaluate(host,candidate,source):
    result,cached=evaluate_schedule(host,candidate,source,plan)
    core.read_evidence(host,dict(reference=result['reference']))
    gap=task_gap(result)
    if not gap['valid_complete']:gap['normalized_gap']=None
    row=dict(reference=result['reference'],source=result['source_reference'],candidate=candidate,
        task_gap=gap,original_acceptance=result['acceptance'],cache_hit=cached,
        metrics=result['acceptance'].get('metrics'),cost_s=0. if cached else result['charged_numerical_s'],
        cumulative_used=host.store.remaining()['used'],cumulative_numerical_s=state(host)['numerical_s'])
    if gap['valid_complete'] and gap['accepted'] and not state(host).get('selected'):
        core.dispatch(host,plan('select',selected_execution=result['reference'],supporting_evidence=[result['reference']]),
            'select-first-pass',origin='engineering')
    return row


def finish(host,destination,summary):
    ref=save(host,summary,'control_search_summary')
    if state(host)['research_status']!='stopped':
        core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=[ref,*state(host)['physical_replays']]),
            'control-search-stop',origin='engineering')
    core.export(host,destination/'study')
    atomic_json(destination/'summary.json',dict(summary,summary_reference=ref,ledger=host.store.remaining()))


def run_search(host,rows,destination):
    from tools.research.local_control_search import search, SearchStopped
    from tools.research.control_correction import task_outputs
    from tools.research_tasks import task_adapter
    starts=[]
    p0=read(ROOT/'evidence/control_search_p0/summary.json')
    for prefix in ('96615db5','a323c937'):
        row=next(r for r in rows if r['source_result']['artifact_id'].startswith(prefix))
        verified=next(p['new_result'] for p in p0['paired'] if p['historical']['source_result']==row['source_result'])
        result=archived('evidence/control_search_p0/study',verified['reference'])
        src=archived('evidence/control_search_p0/study',result['source_reference'])
        if not task_gap(result)['valid_complete'] or src['trajectory']!=row['schedule']['trajectory']:
            raise ValueError('INDEPENDENT_VALID_START_REQUIRED')
        candidate,source=materialize(host,row);source['provenance']['independent_p0_result']=verified['reference']
        cfg=host.store.artifact(candidate)['configuration'];adapter=task_adapter(cfg);limits=adapter.ranking_limits()
        starts.append(dict(id=prefix,candidate=candidate,schedule=source,limits=[8]*4,
            task_options=dict(target=cfg['task']['goal']['data']['target_m'],holding_start=adapter.holding_start_s(),
                position_limit=limits['holding_max_error_m'],speed_limit=limits['holding_max_speed_m_s'])))
    def callback(start,source,metadata):
        try:row=evaluate(host,start['candidate'],source)
        except ValueError as exc:
            if str(exc)=='PHYSICAL_REPLAY_LAUNCH_BUDGET_EXHAUSTED':raise SearchStopped('Store physical budget exhausted') from exc
            raise
        result=host.store.artifact(row['reference']);raw=host.store.artifact(result['raw_reference'])
        row['outputs']=task_outputs(raw) if row['task_gap']['valid_complete'] else None
        print(json.dumps(dict(algorithm=metadata['algorithm'],label=metadata['label'],
            cache_hit=row['cache_hit'],gap=row['task_gap'],used=row['cumulative_used']['backend_solves'])),flush=True)
        return row
    methods=[]
    for settings in state(host)['spec']['local_control_search']:
        if state(host).get('success_gate'):break
        methods.append(search(starts,callback,settings))
        atomic_json(destination/'search_progress.json',dict(methods=methods))
    ranked=sorted((r for m in methods for r in m['candidates']),key=ranking_key)
    return dict(stage='p1',freeze=state(host)['freeze'],methods=methods,best=ranked[0] if ranked else None,
        original_task_passed=bool(state(host).get('success_gate')),
        stop_reason='first_original_task_pass' if state(host).get('success_gate') else 'finite_search_complete',
        interpretation='Limited pilot; no structure infeasibility or method superiority claim.')


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['p0','p1'],default='p0')
    parser.add_argument('--audit-only',action='store_true');args=parser.parse_args()
    destination=ROOT/f'evidence/control_search_{args.stage}';before=source_hashes()
    rows=historical_records();atomic_json(destination/'portfolio.json',portfolio(rows))
    if args.audit_only:
        atomic_json(destination/'source_audit.json',dict(before=before,after=source_hashes(),unchanged=before==source_hashes()))
        print(json.dumps([(r['source_result']['artifact_id'][:8],r['replay_status'],r['rejection_reasons']) for r in rows]));return
    host=core.prepare(ROOT/f'configs/research/study_control_search_{args.stage}.json')
    if state(host)['research_status']=='stopped':print('sealed; no science relaunched');return
    if 'freeze' not in state(host):core.bind(host)
    if state(host).get('pending'):raise ValueError('RECOVER_EXISTING_STUDY_BEFORE_RESUMING')
    if args.stage=='p1':
        summary=run_search(host,rows,destination);after=source_hashes()
        atomic_json(destination/'source_audit.json',dict(before=before,after=after,unchanged=before==after))
        if before!=after:raise ValueError('HISTORICAL_SOURCE_CHANGED')
        finish(host,destination,summary);return
    prefixes=['96615db5','a323c937','15cce211','8e7ee1af'];paired=[]
    for prefix in prefixes:
        row=next(r for r in rows if r['source_result']['artifact_id'].startswith(prefix))
        if row['replay_status']=='replay_unavailable':
            paired.append(dict(historical=row,new_result='NOT_RUN',reason=row['rejection_reasons']));continue
        if state(host).get('success_gate'):break
        candidate,source=materialize(host,row)
        observed=evaluate(host,candidate,source);paired.append(dict(historical=row,new_result=observed))
        atomic_json(destination/'progress.json',dict(paired=paired))
        print(json.dumps(dict(source=prefix,result=observed)),flush=True)
    after=source_hashes();atomic_json(destination/'source_audit.json',dict(before=before,after=after,unchanged=before==after))
    if before!=after:raise ValueError('HISTORICAL_SOURCE_CHANGED')
    finish(host,destination,dict(stage=args.stage,freeze=state(host)['freeze'],paired=paired,
        original_task_passed=bool(state(host).get('success_gate')),
        stop_reason='first_original_task_pass' if state(host).get('success_gate') else 'bounded_replay_complete'))


if __name__=='__main__':main()
