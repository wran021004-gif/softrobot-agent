"""Explicit finite engineering experiment; no LLM, NMPC solve or PPO training."""
import argparse
from copy import deepcopy
import hashlib
import io
import json
import tarfile
from tools.research import core
from tools.research.config import ROOT
from tools.research.state import state
from tools.research.rl import measured_nmpc_trajectory
from tools.research.physical_replay import binding, schedule_identity
from tools.research.feedback import task_gap
from tools.platform_store import encode
from tools.state_io import atomic_json, digest, read
from tests.research.test_s127_working_set import historical_host
from tests.research.s7_study import engineering_plan

SPEC=ROOT/'configs/research/study_s127_control_handoff.json'
OUT=ROOT/'evidence/s127_control_handoff'


def prepare():
    original=historical_host();before=digest(state(original));ledger=original.store.remaining();rows=[];values={}
    for ref in state(original)['results']:
        tr,provenance=measured_nmpc_trajectory(original,ref)
        result=original.store.artifact(ref);candidate=result['candidate'];old=original.store.artifact(candidate)
        source=dict(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured',trajectory=tr,
            provenance=dict(provenance,source_kind='measured_nmpc_execution_v1',original_study=original.run_id,inherited_acceptance=False))
        body=encode(source).encode();source_ref=dict(artifact_id=hashlib.sha256(body).hexdigest(),media_type='application/json')
        values[candidate['artifact_id']]=encode(old).encode();values[source_ref['artifact_id']]=body
        rows.append(dict(execution=ref,candidate=candidate,source=source_ref,intervals=len(tr['tensions_n']),
            channels=len(tr['tendon_order']),sequence_identity=digest(tr['tensions_n']),original_gap=task_gap(result),
            units='N',conversion_preflight='passed',independent_physics=0,inherited_acceptance=False))
    folder=ROOT/'runs/s127_measured_control_import';folder.mkdir(parents=True,exist_ok=True);members=[]
    with tarfile.open(folder/'immutable_artifacts.tar.gz','w:gz') as archive:
        for identity,body in values.items():
            name='artifacts/'+identity+'.json';member=tarfile.TarInfo(name);member.size=len(body);archive.addfile(member,io.BytesIO(body))
            members.append(dict(name=name,sha256=identity))
    atomic_json(folder/'archive_manifest.json',dict(members=members,archive_sha256=hashlib.sha256((folder/'immutable_artifacts.tar.gz').read_bytes()).hexdigest()))
    raw=read(ROOT/'configs/research/study_s125_cold.json')
    raw.update(study_id='s127-measured-control-engineering-20261021',mode='engineering_numerical',
        evidence_destination='runs/s127_control_engineering_export',authorization='Current S12.7.2 task: independent numerical engineering only, at most 6 new physics launches, zero external Provider requests, zero NMPC and PPO launches.',
        execution_instructions='Engineering-only numerical tool validation. No application model calls.',tool_readiness=None)
    raw['budgets'].update(provider_requests=1,protected_provider_requests=0,physical_launches=6,mathematical_evaluations=0,offline_nlp=0,bdf_replays=0)
    raw['nmpc_limits']['executions']=0
    raw['capabilities']=['physical_replay','control_correction','control_search']
    raw['allowed_plan_actions']=['generate','initialize_control','physical_replay','control_search','select','stop']
    raw['rl_limits'].update(training_stages=0,training_actions=1,actions_per_trial=1,evaluation_episodes=0)
    chosen=rows[-1]
    raw['research_decisions']['control_seeds']=[dict(folder=str(folder.relative_to(ROOT)).replace('\\','/'),candidate=chosen['candidate'],source=chosen['source'])]
    raw['research_decisions']['history']=[];raw['research_decisions']['mathematics']=[]
    atomic_json(SPEC,raw)
    assert before==digest(state(original)) and ledger==original.store.remaining()
    atomic_json(OUT/'preflight.json',dict(source_study=original.run_id,source_state_identity=before,rows=rows,
        historical_state_and_ledger_unchanged=True,new_physical_launches=0,new_nmpc_launches=0,
        frozen_new_physics_ceiling=6,planned='One six-tendon open-loop baseline, then one-coefficient response search, at most three callbacks including reusable baseline.',
        settings=dict(version='local_control_search_v2',method='response',knots_s=[0.,3.5],active_coefficients=[6],iterations=1,evaluation_requests=3,
            initial_radius_n=.02,coefficient_limit_n=.05)))
    return rows


def run():
    frozen=read(OUT/'preflight.json');original=historical_host();prior=digest(state(original));ledger=original.store.remaining()
    h=core.prepare(SPEC)
    if state(h)['research_status']=='stopped':raise ValueError('SEALED_ENGINEERING_STUDY_NO_RELAUNCH')
    if 'freeze' not in state(h):core.bind(h)
    elif (OUT/'settings_repair.json').exists():core.bind(h,reason='Prelaunch search knot correction to original 0.35-second task horizon; existing baseline and all costs preserved')
    seed=state(h)['control_initializations'][0];candidate=seed['candidate'];source=seed['source']
    cfg=h.store.artifact(candidate)['configuration'];tr=h.store.artifact(source)['trajectory'];binding(cfg,tr)
    chosen=frozen['rows'][-1];measured,_=measured_nmpc_trajectory(original,chosen['execution'])
    assert tr['tensions_n']==measured['tensions_n']
    old_cfg=original.store.artifact(chosen['candidate'])['configuration']
    assert schedule_identity(cfg,tr)==schedule_identity(old_cfg,tr)
    def act(action,intent,key,**payload):return core.dispatch(h,engineering_plan(action,intent,candidate,**payload),key,origin='engineering')['result']
    baseline=act('physical_replay','PHYSICAL_VALIDATION','s127-open-loop-baseline',physical_replay=dict(candidate=candidate,source=source))
    result=h.store.artifact(baseline['reference']);search=None
    if task_gap(result)['valid_complete'] and not task_gap(result)['accepted']:
        settings=read(OUT/'settings_repair.json')['settings'] if (OUT/'settings_repair.json').exists() else frozen['settings']
        proposal=engineering_plan('control_search','CONTROL_SEARCH',candidate,control_search=dict(candidate=candidate,source=source,settings=settings))
        proposal['decision']['requested_budget']=3
        search=core.dispatch(h,proposal,'s127-one-coefficient-response-signed-zero-reuse',origin='engineering')['result']
    s=state(h)
    for ref in s['physical_replays']:core.read_evidence(h,dict(reference=ref,pointer='/acceptance'))
    if s.get('success_gate'):act('select','SELECT','s127-select',selected_execution=s['success_gate']['evidence'],supporting_evidence=s['physical_replays'])
    act('stop','STOP','s127-stop',supporting_evidence=s['physical_replays'])
    rows=[]
    for ref in state(h)['physical_replays']:
        value=h.store.artifact(ref);applied=h.store.artifact(value['source_reference'])['trajectory']['tensions_n']
        import numpy as np
        rows.append(dict(reference=ref,candidate=value['candidate'],source=value['source_reference'],task_gap=task_gap(value),
            metrics=value['acceptance']['metrics'],constraints=value['acceptance']['components'],charged_numerical_s=value['charged_numerical_s'],
            max_tension_change_from_measured_n=float(np.max(np.abs(np.asarray(applied)-measured['tensions_n'])))))
    assert prior==digest(state(original)) and ledger==original.store.remaining()
    summary=dict(engineering_only=True,study_id=h.run_id,freeze=s['freeze'],historical=chosen,
        open_loop_baseline=baseline['reference'],new_results=rows,search=search,budget=h.store.remaining(),
        historical_state_and_ledger_unchanged=True,new_provider_requests=0,new_nmpc_launches=0,new_ppo_stages=0,
        scope='Measured historical closed-loop inputs, fresh open-loop physics and local response search. No inherited acceptance, autonomous cold-start result, global controllability or method superiority claim.')
    atomic_json(OUT/'experiment.json',summary)
    print(json.dumps(dict(study=h.run_id,new_physics=len(rows),gaps=[r['task_gap']['normalized_gap'] for r in rows])))


S1274_SPEC=ROOT/'configs/research/study_s127_4_control.json'
S1274_OUT=ROOT/'evidence/s127_4_control'


def prepare_s1274():
    from tools.platform_host import Host
    from tests.research.s127_4_control_audit import audit
    import numpy as np
    from tools.research.control_correction import corrected_tensions
    checked=audit();old=Host(ROOT/'runs/research'/checked['source_study'],checked['source_study'])
    before=(digest(state(old)),old.store.remaining(),digest(old.store.events(old.run_id)))
    folder=ROOT/'runs/s127_4_control_history';core.export(old,folder)
    raw=read(ROOT/'configs/research/study_s127_control_handoff.json')
    raw.update(study_id='s127-4-control-sensitivity-20261021',evidence_destination='runs/s127_4_control_export',
        authorization='Current S12.7.4C task: independent targeted engineering grant, at most 4 new physics starts; zero Provider, mathematics, NMPC or PPO; never reopen the STOP predecessor.')
    raw['budgets'].update(provider_requests=0,physical_launches=4)
    raw['research_decisions']['history']=[dict(folder=str(folder.relative_to(ROOT)).replace('\\','/'),reference=r) for r in state(old)['physical_replays']]
    base=old.store.artifact(state(old)['physical_replays'][0]);source=old.store.artifact(base['source_reference']);tr=source['trajectory']
    cfg=old.store.artifact(base['candidate'])['configuration']
    trials=[]
    for label,changes in [('half_positive_6',{6:.005}),('release_late_1',{7:-.01}),
            ('release_late_4',{10:-.01}),('paired_release',{7:-.01,10:-.01})]:
        x=np.zeros(12)
        for j,v in changes.items():x[j]=v
        moved=deepcopy(tr);moved['tensions_n']=corrected_tensions(tr['tensions_n'],tr['times_s'][:-1],[0.,.35],x,[8.]*6).tolist()
        assert schedule_identity(cfg,moved)!=schedule_identity(cfg,tr)
        trials.append(dict(label=label,coefficients_n=x.tolist(),applied_identity=schedule_identity(cfg,moved)))
    preflight=dict(stage='S12.7.4C',source_study=old.run_id,source_status='stopped',historical_results=state(old)['physical_replays'],
        historical_state_identity=before[0],baseline_source=base['source_reference'],task_identity=tr['task_identity'],
        study_id=raw['study_id'],new_physical_ceiling=4,provider_ceiling=0,nmpc_ceiling=0,ppo_ceiling=0,
        knots_s=[0.,.35],trials=trials,
        rationale='Half-positive coefficient 6 checks measured one-sided scale consistency. Negative late coefficients 7 and 10 release the two upper-bound tendons throughout the pre-hold/hold intervals with no clipping. The fourth combines those same two releases to test additive local response. Negative coefficient 6 is not a reverse of the measured input direction and is deferred.',
        no_new_baseline='Use exact historical failure with identity preserved, never spend a new rollout on an already measured sequence.',
        first_original_pass_stops=True,old_budget_reused=False)
    if S1274_SPEC.exists() and read(S1274_SPEC)!=raw:raise ValueError('FROZEN_C_SPEC_CHANGED')
    atomic_json(S1274_SPEC,raw);atomic_json(S1274_OUT/'preflight.json',preflight)
    assert before==(digest(state(old)),old.store.remaining(),digest(old.store.events(old.run_id)))
    return preflight


def run_s1274():
    import numpy as np
    from tools.platform_host import Host
    from tools.research.control_correction import corrected_tensions,task_outputs,task_measure,correction_basis
    from tools.research.physical_replay import evaluate_schedule
    from tests.research.s127_4_control_audit import options
    frozen=read(S1274_OUT/'preflight.json');old=Host(ROOT/'runs/research'/frozen['source_study'],frozen['source_study'])
    before=(digest(state(old)),old.store.remaining(),digest(old.store.events(old.run_id)))
    h=core.prepare(S1274_SPEC)
    if state(h)['research_status']=='stopped':raise ValueError('SEALED_NEW_STUDY_NO_RELAUNCH')
    if 'freeze' not in state(h):core.bind(h)
    seed=state(h)['control_initializations'][0];candidate=seed['candidate'];source=h.store.artifact(seed['source'])
    tr=source['trajectory'];cfg=h.store.artifact(candidate)['configuration'];opt=options(cfg)
    baseline=old.store.artifact(frozen['historical_results'][0]);prior_probe=old.store.artifact(frozen['historical_results'][1])
    raw_base=task_outputs(old.store.artifact(baseline['raw_reference']))
    old_delta={k:np.asarray(task_outputs(old.store.artifact(prior_probe['raw_reference']))[k])-raw_base[k]
        for k in ('tip_positions_m','tip_velocities_m_s')}
    rows=[]
    def factory(action,**kwargs):return engineering_plan(action,'PHYSICAL_VALIDATION',candidate,**kwargs)
    for trial in frozen['trials']:
        move=deepcopy(source);coeff=trial['coefficients_n']
        move['trajectory']['tensions_n']=corrected_tensions(tr['tensions_n'],tr['times_s'][:-1],frozen['knots_s'],coeff,[8.]*6).tolist()
        move['provenance']['s127_4_trial']=dict(label=trial['label'],coefficients_n=coeff,source_study=old.run_id,
            historical_baseline=frozen['historical_results'][0],inherited_acceptance=False)
        assert schedule_identity(cfg,move['trajectory'])==trial['applied_identity']
        prediction=None
        if trial['label']=='half_positive_6':
            predicted=dict(times_s=raw_base['times_s'],**{k:(np.asarray(raw_base[k])+.5*v).tolist() for k,v in old_delta.items()})
            prediction=task_measure(predicted,**opt)['normalized_gap']
        if trial['label']=='paired_release' and len(rows)==3:
            deltas=[task_outputs(h.store.artifact(h.store.artifact(r['reference'])['raw_reference'])) for r in rows[1:3]]
            predicted=dict(times_s=raw_base['times_s'],**{k:(np.asarray(deltas[0][k])+deltas[1][k]-np.asarray(raw_base[k])).tolist() for k in old_delta})
            prediction=task_measure(predicted,**opt)['normalized_gap']
        result,cached=evaluate_schedule(h,candidate,move,factory)
        # Independent returned-array recomputation checks every terminal/hold sample.
        outputs=task_outputs(h.store.artifact(result['raw_reference']));measure=task_measure(outputs,**opt)
        np.testing.assert_allclose(measure['normalized_gap'],task_gap(result)['normalized_gap'],rtol=0,atol=1e-12)
        actual=task_gap(baseline)['normalized_gap']-measure['normalized_gap']
        predicted_improvement=None if prediction is None else task_gap(baseline)['normalized_gap']-prediction
        rows.append(dict(label=trial['label'],coefficients_n=coeff,reference=result['reference'],source=result['source_reference'],
            raw_reference=result['raw_reference'],task_gap=task_gap(result),acceptance=result['acceptance'],
            independent_array_measure=measure,independent_array_recomputation_passed=True,
            input_inf_n=float(np.max(abs(np.asarray(move['trajectory']['tensions_n'])-tr['tensions_n']))),
            clipped_entries=int(np.sum(abs(np.asarray(move['trajectory']['tensions_n'])-tr['tensions_n']-
                (correction_basis(tr['times_s'][:-1],frozen['knots_s'],6)@coeff).reshape(-1,6))>1e-12)),
            actual_improvement=actual,predicted_improvement=predicted_improvement,
            direction_agrees=None if predicted_improvement is None or actual==0 else bool(actual*predicted_improvement>0),
            cost_s=0. if cached else result['charged_numerical_s'],cache_hit=cached))
        if result['acceptance']['accepted']:break
    for r in state(h)['physical_replays']:core.read_evidence(h,dict(reference=r,pointer='/acceptance'))
    if state(h).get('success_gate'):
        core.dispatch(h,engineering_plan('select','SELECT',selected_execution=state(h)['success_gate']['evidence'],supporting_evidence=state(h)['physical_replays']),'s127-4-select',origin='engineering')
    if state(h)['research_status']!='stopped':
        core.dispatch(h,engineering_plan('stop','STOP',supporting_evidence=state(h)['physical_replays']),'s127-4-stop',origin='engineering')
    assert before==(digest(state(old)),old.store.remaining(),digest(old.store.events(old.run_id)))
    result=dict(stage='S12.7.4C',study_id=h.run_id,freeze=state(h)['freeze'],status=state(h)['research_status'],
        historical_baseline=frozen['historical_results'][0],historical_baseline_gap=task_gap(baseline),trials=rows,
        ledger=h.store.remaining(),numerical_s=state(h)['numerical_s'],new_provider_requests=0,new_nmpc_launches=0,new_ppo_stages=0,
        historical_state_ledger_events_unchanged=True,baseline_physics_repeated=False,
        interpretation='Finite engineering observations around one measured six-tendon failure; no autonomous cold-start success, full Jacobian, structural infeasibility or general method superiority claim.')
    atomic_json(S1274_OUT/'experiment.json',result)
    print(json.dumps(dict(study=h.run_id,gaps=[r['task_gap']['normalized_gap'] for r in rows],ledger=h.store.remaining())))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');parser.add_argument('--prepare-s1274',action='store_true');parser.add_argument('--s1274',action='store_true');args=parser.parse_args()
    if args.prepare_s1274:print(json.dumps(prepare_s1274()))
    elif args.s1274:run_s1274()
    elif args.prepare:print(json.dumps(prepare()))
    else:run()

