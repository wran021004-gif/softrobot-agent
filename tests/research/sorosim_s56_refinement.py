"""Explicit real S5.6 driver; not discovered by ordinary unit tests."""
import argparse
import json
from pathlib import Path
import tarfile

import numpy as np
from extensions.tendon_family.sorosim_codesign import compare_refinements
from tests.research.sorosim_s5t_pilot import sealed
from tools.research import core
from tools.research.design import numerical_binding, verify_candidate
from tools.research.state import state, save
from tools.state_io import atomic_json, read

ROOT=Path(__file__).resolve().parents[2]


def plan(action,**data):
    return dict(action=action,
        hypothesis='Improved numerical fidelity and candidate-bound controls may improve the frozen task.',
        expected_observation='Exact source identity, complete numerical or physical evidence and original predicates.',
        weakening_observation='Numerical failure, unresolved fidelity, task violation or incompatible source.',
        fixed_conditions='Frozen task, physical force bounds, topology and exact candidate binding.',
        stopping_condition='The owning prospective stage count grant; no repetitions or provider requests.',
        interpretation='Numerical validity, local optimality and independent physical acceptance are distinct.',**data)


def initialize(stage):
    host=core.prepare(ROOT/f'configs/research/study_sorosim_{stage}.json')
    if 'freeze' not in state(host):core.bind(host)
    old=read(ROOT/'evidence/sorosim_s4b/recovered_pilot/summary.json')['rows'][1]
    with tarfile.open(ROOT/'evidence/sorosim_s4b/recovered_pilot/immutable_artifacts.tar.gz') as archive:
        params=sealed(archive,old['candidate'])['parameters']
    candidate=core.dispatch(host,plan('generate',generation=params),stage+'-generate-B')['result']['candidate']
    current=verify_candidate(host,candidate)
    if numerical_binding(current['configuration'],state(host)['spec'])['physical_design_identity']!=old['physical_design_identity']:
        raise ValueError('S56_DESIGN_B_CHANGED')
    index=read(ROOT/'evidence/sorosim_s5a/summary.json')
    with tarfile.open(ROOT/'evidence/sorosim_s5a/study/immutable_artifacts.tar.gz') as archive:
        source=sealed(archive,index['source'])
    return host,candidate,save(host,source,'imported_verified_source')


def finish(host,summary,destination):
    ref=save(host,summary,'stage_summary')
    s=state(host)
    citations=[ref,*s['mechanics_results'],*s['results'],*s.get('physical_replays',[]),
        *s.get('analysis_results',[]),*s.get('rl_evaluations',[]),*s.get('rl_training_summaries',[])]
    core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=citations),'stage-stop')
    core.export(host,ROOT/destination/'study')
    atomic_json(ROOT/destination/'summary.json',dict(summary,stage_summary_reference=ref))


def run(optional64=False):
    host,candidate,source=initialize('s56_refinement')
    rows={};pairs={};historical=read(ROOT/'evidence/sorosim_s55/p1_refinement.json')
    for count in (4,8):
        old=historical['results'][str(count)]
        rows[count]=dict(complete=old['complete'],times_s=old['time_s'],
            tip_positions_m=old['tip_positions_m'],tip_velocities_m_s=old['tip_velocities_m_s'])
    results={}
    for count in (16,32,64) if optional64 else (16,32):
        if count==64:
            if not all(rows.get(k,{}).get('complete') for k in (16,32)):break
            gap=pairs['16_to_32']
            if gap['maximum_position_m']<=.01 and gap['maximum_velocity_m_s']<=.02:break
        result=core.dispatch(host,plan('refine',refinement=dict(candidate=candidate,source=source,substeps=count)),
            f's56-refine-{count}')['result']
        value=host.store.artifact(result['reference']);rows[count]=value['raw']
        roots=np.asarray(value['raw']['roots'])
        results[count]=dict(reference=result['reference'],complete=value['complete'],status=value['status'],
            elapsed_s=value['charged_numerical_s'],root_count=len(roots),
            max_root_residual_inf=float(max(roots[:,2])),
            maximum_absolute_state=float(np.max(np.abs(value['raw']['states']))),
            **{k:value.get(k) for k in ('terminal_position_error_m','holding_max_position_error_m',
                'holding_max_speed_m_s','original_task_satisfied','time_localized_task_violations')})
        previous=count//2
        if rows[count]['complete'] and rows.get(previous,{}).get('complete'):
            pairs[f'{previous}_to_{count}']=compare_refinements(rows[previous],rows[count])
        atomic_json(host.store.root/'partial_summary.json',dict(results=results,comparisons=pairs))
        print(json.dumps(dict(substeps=count,**results[count])),flush=True)
    decreasing={key:all(b['maximum_'+key]<a['maximum_'+key] for a,b in zip(list(pairs.values()),list(pairs.values())[1:]))
        for key in ('position_m','velocity_m_s')}
    summary=dict(stage='S5.6-A',source_freeze=state(host)['freeze'],candidate=candidate,source=source,
        results=results,comparisons=pairs,successive_global_maxima_decrease=decreasing,
        reliability='observed_refinement_only_no_continuous_time_certificate',
        costs=dict(integrations=state(host)['bdf_replays'],numerical_s=state(host)['numerical_s'],
            physical_launches=0,ppo_actions=0,provider_requests=0))
    finish(host,summary,'evidence/sorosim_s56/refinement')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--optional64',action='store_true')
    run(parser.parse_args().optional64)
