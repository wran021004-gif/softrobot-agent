"""Bounded Stage A engineering cases through the production analysis worker.

Read S142's sealed Store and S144's verified native checkpoint only. No Provider,
formal autonomous Study, full NMPC, full-task replay or training is launched.
Run once in a clean committed worktree with the existing .mainline5-env Python.
"""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time

import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.platform_store import plain
from tools.state_io import read,atomic_json,digest
from tools.research import core,analysis,reporter
from tools.research.state import state,save,update
from tools.research.design import construct,set_parameter,parameter_value
from tools.research.evidence_views import result_card
from tools.research.research_context import mathematical_decision_view,agent_decision_brief
from tools.research.task_constraints import mathematical_method_view
from extensions.tendon_family.mujoco_analysis import NativeModel


def main():
    started=time.perf_counter()
    source=ROOT.parent/'s142-reach-hold-autonomous/runs/research/s142-reach-hold-coldstart-20261023'
    checkpoint=ROOT.parent/'s144-terminal-control-diagnosis/runs/s144'
    destination=ROOT/'runs/mujoco-native-stage-a';destination.mkdir(exist_ok=True)
    dbpath=source/'platform.sqlite';before=(dbpath.stat().st_size,dbpath.stat().st_mtime_ns)
    with sqlite3.connect(dbpath.as_uri()+'?mode=ro&immutable=1',uri=True) as db:
        db.execute('PRAGMA query_only=ON')
        original=json.loads(db.execute('select state from sessions where run_id=?',(source.name,)).fetchone()[0])
        def artifact(ref):return json.loads(db.execute('select body from artifacts where id=?',(ref['artifact_id'],)).fetchone()[0])
        measured=next((r,artifact(r)) for r in original['results'] if artifact(r).get('execution_id')=='3c78b551965f443abd966bfb68b969dd')
        old_candidate=artifact(measured[1]['candidate'])
        counts={t:db.execute('select count(*) from '+t).fetchone()[0] for t in ('events','artifacts','calls')}
    assert original['research_status']=='stopped' and original['pending'] is None
    backend=next(source.glob('sessions/*/executions/'+measured[1]['execution_id']+'/backend'))
    rows=json.loads(gzip.decompress((backend/'trajectory.json.gz').read_bytes()))
    paired=read(checkpoint/'result.json');assert paired['store_unchanged'] and paired['reconstruction']['clone_integration_exact']
    # Compose through the original loader, using frozen source inputs, not mutable defaults.
    original_spec=original['spec'];nominal=original['nominal_configuration']
    study=read(ROOT/'configs/research/study.json')
    for key in study.keys() & original_spec.keys():
        if key not in ('robot','task','control','runtime','reference_parameters','validation_profiles'):study[key]=deepcopy(original_spec[key])
    inputs=dict(robot=dict(robot=nominal['robot'],backend=nominal['policy']['backend'],
        dynamics_model=nominal['policy']['dynamics_model'],discretization=nominal['policy']['discretization'],
        provenance=original_spec['source_provenance']),
        task=dict(seed=nominal['seed'],task=nominal['task'],settling=nominal['policy']['controller']['parameters']['data']['settling']),
        control=original_spec['control'],runtime=original_spec['runtime'])
    for key,value in inputs.items():
        path=destination/(key+'.json');atomic_json(path,value);study[key]=str(path)
    study.update(study_id='mujoco-native-stage-a-20261024',mode='engineering_numerical',
        authorization='User-authorized Stage A: native math, short responses and two legal structure pairs; zero Provider and autonomous Study.',
        capabilities=['analysis'],allowed_plan_actions=['stop'],
        reference_parameters={k:original_spec['reference_parameters'][k] for k in ('holding_tip_speed_weight','terminal_tip_speed_weight')})
    study['budgets'].update(provider_requests=0,protected_provider_requests=0,public_operations=40,
        protected_public_operations=0,physical_launches=0,mathematical_evaluations=8,local_solves=0,offline_nlp=0,bdf_replays=0)
    study['nmpc_limits']['executions']=0
    study['rl_limits'].update(training_stages=0,evaluation_episodes=0)
    specpath=destination/'study.json';atomic_json(specpath,study)
    host=core.prepare(specpath,directory=destination/'store')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if state(host).get('freeze')!=commit:
        core.bind(host,reason='Stage A serialization correction; existing results, failed request and consumed counts retained.' if state(host).get('freeze') else None)
    candidate=construct(host,old_candidate['parameters'],dict(origin='Stage A same legal S142 stiff structure'))
    cfg=host.store.artifact(candidate)['configuration']
    assert cfg['robot']==old_candidate['configuration']['robot'] and cfg['task']==old_candidate['configuration']['task']
    native=NativeModel(cfg);data=mujoco.MjData(native.model)
    saved=np.load(checkpoint/'native_start.npz')
    mujoco.mj_setState(native.model,data,saved['integration'],mujoco.mjtState.mjSTATE_INTEGRATION)
    native.forward(data);point=native.checkpoint(data)
    assert point['physics_identity']==read(backend/'resolved_physics.json')['identity']
    np.testing.assert_array_equal(point['qpos_rad'],rows[33]['qpos_rad'])
    np.testing.assert_array_equal(point['qvel_rad_s'],rows[33]['qvel_rad_s'])
    point.update(candidate=candidate,configuration_identity=digest(cfg),u=rows[34]['tension_n'],
        provenance=dict(execution=measured[0],native_checkpoint=str(checkpoint/'native_start.npz'),
            verification=str(checkpoint/'result.json'),original_backend=str(backend)))
    pointref=save(host,point,'imported_verified_native_state');update(host,scoped_context=[*state(host).get('scoped_context',[]),pointref])
    queries={}
    base=dict(candidate=candidate,operating_point='saved_state',model_source='mujoco',saved_state=pointref,protocol=state(host)['spec']['analysis_protocol'])
    queries['mechanics']=dict(base,operation='native_dynamics_v1')
    queries['input']=dict(base,operation='short_input_response_v1',native=dict(horizon_s=.01,difference_step_n=.1,correction_radius_n=.25))
    variables=[('young','segments.distal1.young_pa',(-.01,-.005)),('section','segments.distal1.sections.0.height_z_m',(.01,))]
    for label,variable,fractions in variables:
        comparisons=[]
        for fraction in fractions:
            p=deepcopy(old_candidate['parameters']);set_parameter(p,variable,parameter_value(p,variable)*(1+fraction))
            comparisons.append(construct(host,p,dict(origin='Stage A legal paired perturbation',variable=variable,fraction=fraction)))
        queries[label]=dict(base,operation='fixed_input_structure_v1',native=dict(horizon_s=.01),
            structure_response=dict(variable=variable,candidates=comparisons))
    results={};views={};deliveries={}
    for name,query in queries.items():
        key='stage-a-input-serialized' if name=='input' else 'stage-a-'+name
        out=analysis.dispatch(host,query,key,guard=core.guard,origin='engineering_preflight')
        raw=host.store.artifact(out['reference']);results[name]=dict(reference=out['reference'],value=raw)
        atomic_json(destination/(name+'.json'),results[name])
        if raw['status']!='computed':raise ValueError((name,raw))
        assert raw['scoped_claim']['conclusion']=='diagnostic' and not raw['analysis_applicability']['full_task_supported']
        card=plain(result_card(host,out['reference']));views[name]=mathematical_decision_view(card)
        assert len(json.dumps(views[name]))<9000 and '"mass_matrix_kg_m2":' not in json.dumps(views[name])
        for q in card['mathematics']['quantities']:
            assert core.read_evidence(host,q['source'],record_read=False)==q['value']
        deliveries[name]=reporter.scientific_feedback(host,out)
        assert deliveries[name]['interpretation_status']=='deferred'
        print(name,raw['native_analysis']['cost'],flush=True)
    terminal=results['input']['value']['native_dynamics']['input_response']['baseline']
    reproduction={key:float(np.max(abs(np.asarray(terminal[key])-rows[34][sourcekey]))) for key,sourcekey in
        [('qpos_rad','qpos_rad'),('qvel_rad_s','qvel_rad_s'),('tip_position_m','tip_m'),('tip_velocity_m_s','tip_velocity_m_s')]}
    assert max(reproduction.values())<=1e-10
    assert abs(terminal['time_s']-rows[34]['time_s'])<=1e-12
    # The original Store receipt protects repeat execution, even after reopening.
    before_reuse=deepcopy(state(host));reused=analysis.dispatch(host,queries['input'],'stage-a-input-serialized',guard=core.guard,origin='engineering_preflight')
    assert reused['operation_reuse']['additional_analysis_evaluations']==0 and state(host)==before_reuse
    catalog=mathematical_method_view(host,candidate)
    assert all(key in catalog['methods'] for key in ('native_dynamics_v1','short_input_response_v1','fixed_input_structure_v1','controllability'))
    brief=agent_decision_brief(host)
    assert '"integration_state":' not in json.dumps(brief) and '"mass_matrix_kg_m2":' not in json.dumps(brief)
    assert (dbpath.stat().st_size,dbpath.stat().st_mtime_ns)==before
    failures=[r for r in state(host)['analysis_results'] if host.store.artifact(r)['status']!='computed']
    assert state(host)['mathematical_evaluations']==7+len(failures) and state(host)['pending'] is None
    assert host.store.remaining()['used']['model_calls']==host.store.remaining()['used']['backend_solves']==0
    summary=dict(source_execution=measured[0],source_candidate=measured[1]['candidate'],candidate=candidate,
        store=str(host.store.root),source_store_unchanged=True,source_store_counts=counts,
        source_store_size_mtime=before,reproduction=reproduction,checkpoint_preparation_cost=native.cost,
        results={k:dict(reference=v['reference'],summary=v['value']['native_analysis']) for k,v in results.items()},
        mathematical_evaluations=state(host)['mathematical_evaluations'],store_budget=host.store.remaining(),
        failed_results=failures,
        receipt_reuse=reused['operation_reuse'],decision_views=views,reporter_deliveries=deliveries,
        decision_brief_bytes=len(json.dumps(brief).encode()),elapsed_s=time.perf_counter()-started)
    atomic_json(destination/'summary.json',summary)
    atomic_json(destination/'decision_brief.json',brief)
    print(json.dumps(dict(status='verified',reproduction=reproduction,analyses=4,model_evaluations=8,elapsed_s=summary['elapsed_s'])))


if __name__=='__main__':main()
