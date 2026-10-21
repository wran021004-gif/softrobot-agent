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
    raw['rl_limits'].update(training_stages=0,training_actions=0,evaluation_episodes=0)
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
        proposal=engineering_plan('control_search','CONTROL_SEARCH',candidate,control_search=dict(candidate=candidate,source=source,settings=frozen['settings']))
        proposal['decision']['requested_budget']=3
        search=core.dispatch(h,proposal,'s127-one-coefficient-response',origin='engineering')['result']
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


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--prepare',action='store_true');args=parser.parse_args()
    if args.prepare:print(json.dumps(prepare()))
    else:run()
