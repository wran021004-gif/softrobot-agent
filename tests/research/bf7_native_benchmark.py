"""BF7 finite experiment organization through existing Study tools only."""
from copy import deepcopy
import json
import sys
import time
from types import SimpleNamespace

from tools.research import analysis, core
from tools.research.config import ROOT
from tools.research.state import state
from tools.research.mixed_moves import initial, generation
from tools.state_io import read, atomic_json
from tests.research.bf7_shared_structure import prepare, dispatch, stop

BASE = ROOT/'runs/bf7-native-v1'
PROTOCOL = ROOT/'configs/research/bf7_native_protocol_v1.json'


def optimize(host, root, condition, settings, key, tensions):
    started=time.perf_counter()
    seed=dispatch(host,'initialize_control',key+'-seed',control_seed=dict(
        candidate=root,condition_id=condition,tensions_n=tensions))
    out=analysis.dispatch(host,dict(candidate=seed['candidate'],operation='mujoco_nonlinear_task_capability_v1',
        model_source='mujoco',operating_point='standardized_initial_pretension',protocol=state(host)['spec']['analysis_protocol'],
        control_optimization=dict(source=seed['source'],settings=settings)),key+'-native',guard=core.guard,origin='engineering_preflight')
    core.read_evidence(host,dict(reference=out['reference'],view='full'))
    a=host.store.artifact(out['reference'])
    row=dict(candidate=seed['candidate'],analysis=out['reference'],status=a['status'],accepted=False,
        charged_numerical_s=a.get('charged_numerical_s'),charged_analysis_evaluations=a.get('charged_analysis_evaluations'))
    if a['status']=='computed':
        native=a['native_dynamics'];search=native['optimization']
        row.update(t1=a['nonlinear_capability'],control_source=a['control_schedule_reference'],native_cost=native['cost'],
            response_progress=[dict(callback=i+1,J=r['measure']['signed_maximum_excess'],label=r['label'])
                for i,r in enumerate(search['candidates']) if r['label'] in ('baseline','local_response_proposal')])
        replay=dispatch(host,'physical_replay',key+'-replay',physical_replay=dict(candidate=seed['candidate'],source=a['control_schedule_reference']))
        core.read_evidence(host,dict(reference=replay['reference'],view='full'))
        raw=host.store.artifact(replay['raw_reference'])
        row.update(replay=replay['reference'],acceptance=replay['acceptance'],accepted=replay['acceptance']['accepted'],
            replay_cost=raw.get('cost'),replay_steps=raw.get('physics_steps'),replay_step_attempts=raw.get('physics_step_attempts'))
    else:
        row.update(reason=a.get('reason'),native_progress=a.get('native_progress'))
    row['driver_elapsed_s']=time.perf_counter()-started
    return row


def snapshot(host, rows, started):
    s=state(host)
    return dict(structures=rows,implementation=s['freeze'],study_id=host.run_id,
        numerical_s=s['numerical_s'],construction_numerical_s=s.get('construction_numerical_s'),
        control_initialization_s=s.get('control_initialization_s'),analysis_preparation_s=s.get('analysis_preparation_s'),
        compatibility_preparation_s=s.get('compatibility_preparation_s'),mathematical_evaluations=s['mathematical_evaluations'],
        selected=s.get('selected'),research_status=s['research_status'],ledger=host.store.remaining(),
        driver_elapsed_s=time.perf_counter()-started)


def run_screen():
    folder=BASE/'screen';summary=folder/'summary.json'
    if summary.exists():return read(summary)
    started=time.perf_counter();protocol=read(PROTOCOL)
    host=prepare(protocol['study'],folder);spec=state(host)['spec']
    shape=SimpleNamespace(segment_counts=[2],tendon_counts=[6],span_strategies=['distributed_consecutive'],
        bounds={},section_types=[],family_space_identity=spec['family_space_identity'])
    progress=folder/'progress.json';rows=read(progress) if progress.exists() else []
    for structure in protocol['structures']:
        row=next((r for r in rows if r['id']==structure['id']),None)
        if row is None:
            point=initial(spec['family_space'],shape)
            for i,(length,young) in enumerate(zip(structure['lengths_m'],protocol['young_pa'])):
                point['segments'][str(i)].update(length_m=length,young_pa=young)
            request=generation(spec['family_space'],shape,point)
            root=dispatch(host,'generate','bf7-native-'+structure['id'],generation=request)['candidate']
            row=dict(id=structure['id'],generation=request,candidate=root,conditions={});rows.append(row)
            atomic_json(progress,rows)
        for condition in spec['task_conditions']:
            cid=condition['condition_id']
            if cid in row['conditions']:continue
            result=optimize(host,row['candidate'],cid,protocol['settings'],'bf7-native-'+row['id']+'-'+cid,[[protocol['initial_tension_n']]*6])
            row['conditions'][cid]=result;atomic_json(progress,rows)
            print(json.dumps(dict(structure=row['id'],condition=cid,status=result['status'],accepted=result['accepted'],
                initial_J=result.get('t1',{}).get('initial_J'),best_J=result.get('t1',{}).get('J'))),flush=True)
        row['shared_J']=max(r['t1']['J'] for r in row['conditions'].values()) if all(r['status']=='computed' for r in row['conditions'].values()) else None
    comparisons={}
    for condition in spec['task_conditions']:
        cid=condition['condition_id'];members=[r['conditions'][cid] for r in rows]
        if any(r['status']!='computed' for r in members):continue
        query=dict(candidate=members[0]['candidate'],operation='mujoco_reoptimized_structure_response_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
            nonlinear_response=dict(version='nonlinear_response_v2',directions=[dict(direction_id='distal_length',mode='finite_comparison',
                comparison_variables=['segments.1.length_m'],t1_results=[r['analysis'] for r in members])]))
        result=analysis.dispatch(host,query,'bf7-native-t2-'+cid,guard=core.guard,origin='engineering_preflight')
        core.read_evidence(host,dict(reference=result['reference'],view='full'))
        comparisons[cid]=dict(reference=result['reference'],result=host.store.artifact(result['reference']).get('nonlinear_response'))
    for row in rows:
        if all(r['accepted'] for r in row['conditions'].values()):
            dispatch(host,'select','bf7-native-joint-select',selected_execution=[r['replay'] for r in row['conditions'].values()],supporting_evidence=[r['analysis'] for r in row['conditions'].values()])
            break
    stop(host,'bf7-native-screen-stop')
    result=dict(**snapshot(host,rows,started),comparisons=comparisons)
    atomic_json(summary,result)
    return result


def run_refinement():
    grant=read(ROOT/'configs/research/bf7_native_refinement_v1.json');folder=BASE/'refinement'
    summary=folder/'summary.json'
    if summary.exists():return read(summary)
    started=time.perf_counter();screen=read(BASE/'screen/summary.json')
    chosen=next(r for r in screen['structures'] if r['id']==grant['structure_id'])
    source=prepare('study_bf7_native_v1.json',BASE/'screen')
    host=prepare(grant['study'],folder)
    root=dispatch(host,'generate','bf7-refinement-design',generation=chosen['generation'])['candidate']
    progress=folder/'progress.json';rows=read(progress) if progress.exists() else {}
    for cid,prior in chosen['conditions'].items():
        if cid in rows:continue
        tensions=source.store.artifact(prior['control_source'])['trajectory']['tensions_n']
        rows[cid]=optimize(host,root,cid,grant['settings'],'bf7-refinement-'+cid,tensions)
        atomic_json(progress,rows)
        print(json.dumps(dict(condition=cid,accepted=rows[cid]['accepted'],best_J=rows[cid].get('t1',{}).get('J'))),flush=True)
    if all(r['accepted'] for r in rows.values()):
        dispatch(host,'select','bf7-refinement-joint-select',selected_execution=[r['replay'] for r in rows.values()],supporting_evidence=[r['analysis'] for r in rows.values()])
    stop(host,'bf7-refinement-stop')
    result=snapshot(host,[dict(id=chosen['id'],candidate=root,conditions=rows)],started)
    atomic_json(summary,result);return result


def audit_saved():
    """Exercise original recovery and exact receipt reuse; never launch science."""
    output=ROOT/'evidence/bf7_native_v1';output.mkdir(parents=True,exist_ok=True)
    records={}
    for phase,study in [('screen','study_bf7_native_v1.json'),('refinement','study_bf7_native_refinement_v1.json')]:
        host=prepare(study,BASE/phase);s=state(host)
        before=dict(mathematical_evaluations=s['mathematical_evaluations'],numerical_s=s['numerical_s'],ledger=host.store.remaining())
        recovered=core.recover(host)
        ref=s['analysis_results'][0];a=host.store.artifact(ref)
        key=a['operation_key'].removesuffix('-analysis')
        cached=analysis.dispatch(host,a['requested_operation'],key,guard=lambda *args:(_ for _ in ()).throw(AssertionError('No scientific admission allowed')),origin='engineering_preflight')
        replay_plan=next(host.store.artifact(r) for r in s['plans'] if host.store.artifact(r)['original_plan']['action']=='physical_replay')
        cached_replay=core.dispatch(host,replay_plan['original_plan'],replay_plan['request_id'],origin='engineering')
        after=dict(mathematical_evaluations=state(host)['mathematical_evaluations'],numerical_s=state(host)['numerical_s'],ledger=host.store.remaining())
        assert before==after and cached['reference']==ref
        records[phase]=dict(recovery=recovered,analysis_reuse=cached.get('operation_reuse'),
            replay_reused=bool(cached_replay),before=before,after=after,scientific_cost_delta=0)
        core.export(host,output/phase)
        atomic_json(output/(phase+'_summary.json'),read(BASE/phase/'summary.json'))
    atomic_json(output/'receipt_recovery.json',records)
    return records


if __name__=='__main__':
    if sys.argv[1:]==['screen']:run_screen()
    elif sys.argv[1:]==['refine']:run_refinement()
    elif sys.argv[1:]==['audit']:audit_saved()
    else:raise SystemExit('screen | refine | audit')
