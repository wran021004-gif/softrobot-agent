"""Bounded Stage B engineering case; no Provider, NMPC, PPO or autonomous Study.

Uses the sealed S142 Store read-only. Original inputs are an initialization,
never an inherited acceptance. Both complete schedules get fresh evaluation.
"""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from tools.state_io import read,atomic_json,digest
from tools.platform_store import plain
from tools.research import core,analysis,reporter
from tools.research.state import state,save,update
from tools.research.design import construct
from tools.research.physical_replay import model_context,binding,evaluate_schedule
from tools.research.evidence_views import result_card
from tools.research.research_context import mathematical_decision_view,agent_decision_brief
from tools.research.task_constraints import mathematical_method_view
from tools.research.feedback import task_gap
from tests.research.sorosim_s56_refinement import plan


def main():
    started=time.perf_counter()
    source=ROOT.parent/'s142-reach-hold-autonomous/runs/research/s142-reach-hold-coldstart-20261023'
    destination=ROOT/'runs/mujoco-direct-stage-b';destination.mkdir(exist_ok=True)
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
    study.update(study_id='mujoco-direct-stage-b-20261024',mode='engineering_numerical',
        authorization='User-authorized Stage B bounded native optimization and two complete fixed-control replays; no Provider or autonomous Study.',
        capabilities=['analysis','physical_replay','control_correction'],allowed_plan_actions=['physical_replay','select','stop'],
        evidence_destination='evidence/mujoco_direct_stage_b/study',
        reference_parameters={k:original_spec['reference_parameters'][k] for k in ('holding_tip_speed_weight','terminal_tip_speed_weight')})
    study['budgets'].update(provider_requests=0,protected_provider_requests=0,public_operations=40,
        protected_public_operations=0,physical_launches=2,mathematical_evaluations=4,local_solves=0,offline_nlp=0,bdf_replays=0)
    study['nmpc_limits']['executions']=0
    study['rl_limits'].update(training_stages=0,evaluation_episodes=0)
    specpath=destination/'study.json';atomic_json(specpath,study)
    host=core.prepare(specpath,directory=destination/'store')
    commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    if state(host).get('freeze')!=commit:
        core.bind(host,reason='Stage B implementation correction; preserve completed receipts, failures and cumulative budget.' if state(host).get('freeze') else None)
    if state(host)['research_status']=='stopped':
        print('Engineering Store sealed; no science relaunched.');return
    candidate=construct(host,old_candidate['parameters'],dict(origin='Stage B same legal S142 stiff structure'))
    cfg=host.store.artifact(candidate)['configuration']
    assert cfg['robot']==old_candidate['configuration']['robot'] and cfg['task']==old_candidate['configuration']['task']
    inp,physics,scene,spec=model_context(cfg)
    original_schedule=dict(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured',
        trajectory=dict(times_s=[i*.01 for i in range(36)],tensions_n=[r['tension_n'] for r in rows],
            tendon_order=[t['entity'] for t in physics['tendons']],task_identity=digest(plain(inp.task)),
            model_identity=spec['identity'],design_identity=spec['design_identity']),
        provenance=dict(initialization='S142 recorded actual ideal tensions',execution=measured[0],inherited_acceptance=False))
    binding(cfg,original_schedule['trajectory'])
    source_ref=save(host,original_schedule,'bound_applied_control_schedule')
    old_scene=read(backend/'experiment_scene.json');previous=rows[29]
    point=dict(candidate=candidate,configuration_identity=digest(cfg),physics_identity=physics['identity'],
        dof_order=physics['dofs'],tendon_order=original_schedule['trajectory']['tendon_order'],
        phase='interval_start_native',input_units='N',actual_time_s=previous['time_s'],
        qpos_rad=previous['qpos_rad'],qvel_rad_s=previous['qvel_rad_s'],u=rows[30]['tension_n'],
        native_replay=dict(rows=rows[:30],scene=old_scene),
        provenance=dict(execution=measured[0],update_id=30,backend=str(backend)))
    point_ref=save(host,point,'imported_verified_native_prefix')
    update(host,scoped_context=[*state(host).get('scoped_context',[]),point_ref,source_ref])
    query=dict(candidate=candidate,model_source='mujoco',operation='mujoco_direct_control_v1',
        operating_point='saved_state',saved_state=point_ref,protocol=state(host)['spec']['analysis_protocol'],
        control_optimization=dict(source=source_ref,settings=dict(version='local_control_search_v2',method='response',
            correction_window_s=[.30,.35],knots_s=[.30,.32,.34],coefficient_limit_n=.5,initial_radius_n=.1,
            difference_step_n=.005,minimum_radius_n=.0001,evaluation_requests=80,iterations=4,safety_margin_fraction=.05)))
    out=analysis.dispatch(host,query,'stage-b-native-sequence',guard=core.guard,origin='engineering_preflight')
    value=host.store.artifact(out['reference']);atomic_json(destination/'optimization.json',dict(reference=out['reference'],value=value))
    if value['status']!='computed':raise ValueError(value)
    raw=value['native_dynamics'];pred=raw['optimization']['candidates'][0]['outputs']
    reproduction={key:float(np.max(abs(np.asarray(pred[key])-np.asarray([r[sourcekey] for r in rows[29:]]))))
        for key,sourcekey in [('times_s','time_s'),('tip_positions_m','tip_m'),('tip_velocities_m_s','tip_velocity_m_s')]}
    assert max(reproduction.values())<1e-10
    view=mathematical_decision_view(plain(result_card(host,out['reference'])))
    for quantity in view['quantities']:assert core.read_evidence(host,quantity['source'],record_read=False)==quantity['value']
    assert len(json.dumps(view))<12000 and '"integration_state":' not in json.dumps(view) and '"tensions_n":' not in json.dumps(view)
    delivery=reporter.scientific_feedback(host,out)
    assert delivery['interpretation_status']=='deferred'
    assert 'mujoco_direct_control_v1' in mathematical_method_view(host,candidate)['methods']
    before_reuse=deepcopy(state(host))
    reused=analysis.dispatch(host,query,'stage-b-native-sequence',guard=core.guard,origin='engineering_preflight')
    assert state(host)==before_reuse and reused['operation_reuse']['additional_analysis_evaluations']==0
    replays={}
    for label,schedule in [('baseline',original_schedule),('optimized',host.store.artifact(value['control_schedule_reference']))]:
        result,cached=evaluate_schedule(host,candidate,schedule,plan)
        assert not cached and task_gap(result)['valid_complete']
        core.read_evidence(host,dict(reference=result['reference']))
        observed=host.store.artifact(result['raw_reference'])['samples']
        prediction=pred if label=='baseline' else raw['optimization']['best']['outputs']
        differences={key:float(np.max(abs(np.asarray(prediction[key])-np.asarray([r[sourcekey] for r in observed[30:]]))))
            for key,sourcekey in [('times_s','time_s'),('tip_positions_m','tip_m'),('tip_velocities_m_s','tip_velocity_m_s')]}
        assert max(differences.values())<1e-10
        replays[label]=dict(reference=result['reference'],raw_reference=result['raw_reference'],acceptance=result['acceptance'],
            gap=task_gap(result),prediction_difference=differences,wall_s=result['charged_numerical_s'])
        atomic_json(destination/'replays.json',replays)
        print(label,json.dumps(replays[label]),flush=True)
    brief=agent_decision_brief(host)
    assert '"integration_state":' not in json.dumps(brief) and '"tensions_n":' not in json.dumps(brief)
    citations=[*state(host)['analysis_results'],*state(host)['physical_replays']]
    core.dispatch(host,plan('stop',next_step='stop',supporting_evidence=citations),'stage-b-stop',origin='engineering')
    assert (dbpath.stat().st_size,dbpath.stat().st_mtime_ns)==before
    assert state(host)['pending'] is None and host.store.remaining()['used']['model_calls']==0
    summary=dict(baseline_commit='904f4932a',implementation=commit,candidate=candidate,optimization_reference=out['reference'],
        control_schedule_reference=value['control_schedule_reference'],source_execution=measured[0],source_store_unchanged=True,
        source_store_counts=counts,source_store_size_mtime=before,reproduction=reproduction,
        optimization_summary=analysis.decision_result(value,out['reference'])['native_analysis'],replays=replays,
        decision_view=view,reporter_delivery=delivery,receipt_reuse=reused['operation_reuse'],
        ledger=host.store.remaining(),numerical_s=state(host)['numerical_s'],
        mathematical_evaluations=state(host)['mathematical_evaluations'],elapsed_s=time.perf_counter()-started)
    evidence=ROOT/'evidence/mujoco_direct_stage_b'
    core.export(host,evidence/'study')
    atomic_json(evidence/'summary.json',summary)
    atomic_json(destination/'decision_brief.json',brief)
    print(json.dumps(dict(status='verified',reproduction=reproduction,cost=raw['cost'],passed=replays['optimized']['gap']['accepted'])))


if __name__=='__main__':main()
