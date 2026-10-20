"""S12 engineering checks and read-only audit entry; never choose research actions."""
import json,subprocess
from tools.research.config import ROOT,resolve
from tools.research.state import state
from tools.research.research_context import context,decision_brief
from tools.research.contracts import RLRequest
from tools.research.rl import prepare_input
from tools.research.budget import nmpc_timing
from tools.research.analysis import admission
from tools.state_io import atomic_json
from tools.platform_host import Host


def preflight():
    h=Host(ROOT/'runs/research/s12-engineering-verified-20261020','s12-engineering-verified-20261020',actor='unified-research')
    s=state(h);candidate=s['research_history'][-1]['candidate']
    cfg,task=prepare_input(h,RLRequest(operation='start',candidate=candidate,mode='direct',rationale='S12 environment construction only, no training or rollout'))
    atomic_json(h.store.root/'rl_environment_input.json',cfg)
    code="import json,sys; from tools.rl.env import TensionEnv; c=json.load(open(sys.argv[1],encoding='utf8')); e=TensionEnv(c); print(json.dumps(dict(status='constructed',mode=e.mode,dofs=e.model.nv,actions=list(e.action_space.shape),observations=list(e.observation_space.shape),command_intervals=c['task']['command_intervals'],lower=e.lower.tolist(),upper=e.upper.tolist()))); e.close()"
    p=subprocess.run([s['spec']['runtime']['rl_python'],'-c',code,str(h.store.root/'rl_environment_input.json')],cwd=ROOT,capture_output=True,text=True)
    if p.returncode:raise ValueError(p.stderr)
    formal=resolve(ROOT/'configs/research/study_s12_mirror.json')
    report=dict(scientific_evidence=False,provider_requests=0,new_physics=0,training_executed=False,
        engineering_study=h.run_id,implementation=s['freeze'],canonical_task_identity=formal['canonical_task_identity'],
        family_space_identity=formal['family_space_identity'],matlab=formal['tool_readiness']['sorosim_matlab']['status'],
        mathematics_admission=admission(h),nmpc_admission=nmpc_timing(h,candidate),direct_rl_environment=json.loads(p.stdout),
        residual_rl='Requires original complete compatible published reference; no acceptance transfer',
        history=s['research_history'],mathematics=s['research_mathematics'],current_context=decision_brief(context(h)),
        limits=dict(budgets=formal['budgets'],nmpc=formal['nmpc_limits'],rl=formal['rl_limits']),ledger=h.store.remaining(),
        limitations=['Readiness does not establish NMPC, training or task acceptance','Historical mathematics is not current verified input sensitivity'])
    assert report['ledger']['used']['backend_solves']==report['ledger']['used']['model_calls']==0
    atomic_json(ROOT/'evidence/s12_mirror/preflight.json',report)
    return dict(matlab=report['matlab'],direct_rl=report['direct_rl_environment'],new_physics=0,provider_requests=0)


def cold_preflight():
    """S12.5 disposable engineering candidate; never imported by the formal Study."""
    from tests.research.test_s125_contract import cold_host
    from tools.research.research_context import import_history
    from tools.research.design import generate_candidate
    from tools.research.physical_replay import seed_control
    from tools.research.contracts import ControlSeedRequest, MechanicsRequest
    from tools.research.mechanics import warm_start
    from tools.research.core import read_evidence
    h=cold_host();import_history(h);s=state(h);initial=decision_brief(context(h))
    assert not any(s.get(k) for k in ('candidates','reference_candidate','research_history','research_mathematics','control_initializations'))
    from tests.research.s125_wire_audit import audit
    old_ref=audit()['errors'][0]['tool_use']['input']['reference']
    try:read_evidence(h,dict(reference=old_ref))
    except ValueError as exc:rejection=str(exc)
    else:raise AssertionError('OLD_STUDY_ACCESS')
    candidate=generate_candidate(h,dict(version='serial_family_generation_v2',
        family_space_identity=s['spec']['family_space_identity'],segment_count=2,tendon_count=4),
        dict(origin='s125_engineering_only_no_formal_import'))['candidate']
    seed=seed_control(h,ControlSeedRequest(candidate=candidate))
    assert warm_start(h,MechanicsRequest(candidate=candidate,initialization='constant_0_2')) is None
    cfg,task=prepare_input(h,RLRequest(operation='start',candidate=candidate,mode='direct',rationale='Environment construction only'))
    atomic_json(h.store.root/'rl_environment_input.json',cfg)
    code="import json,sys; from tools.rl.env import TensionEnv; c=json.load(open(sys.argv[1],encoding='utf8')); e=TensionEnv(c); print(json.dumps(dict(status='constructed',mode=e.mode,dofs=e.model.nv,actions=list(e.action_space.shape),observations=list(e.observation_space.shape),intervals=c['task']['command_intervals']))); e.close()"
    p=subprocess.run([s['spec']['runtime']['rl_python'],'-c',code,str(h.store.root/'rl_environment_input.json')],cwd=ROOT,capture_output=True,text=True)
    if p.returncode:raise ValueError(p.stderr)
    report=dict(scientific_evidence=False,engineering_store=str(h.store.root),initial_context=initial,
        old_reference_rejection=rejection,bootstrap=s['spec']['implementation_scaffold'],
        framework_session_id=s['pilot']['framework_session_id'],session_history_exists=(h.store.root/'framework_sessions').exists(),
        engineering_candidate=candidate,initialization=seed,cold_mathematics=True,
        mathematics_admission=admission(h),nmpc_admission=nmpc_timing(h,candidate),
        direct_rl_environment=json.loads(p.stdout),canonical_task_identity=s['spec']['canonical_task_identity'],
        family_space_identity=s['spec']['family_space_identity'],ledger=h.store.remaining(),
        scope='No Provider, simulation, training or numerical solve. Engineering candidate and seed are not formal study inputs.')
    assert report['ledger']['used']['model_calls']==report['ledger']['used']['backend_solves']==0
    atomic_json(ROOT/'evidence/s125_preflight/cold_start.json',report)
    return dict(status='passed',direct_rl=report['direct_rl_environment'],provider_requests=0,new_physics=0)


def final_checks():
    import hashlib,os,tarfile
    from pathlib import Path
    from tools.research.state import science_hashes,core_hashes
    from tools.research.agent import load_credential
    from tools.research.feedback import task_gap
    from tools.state_io import read,digest
    from tools.platform_store import plain
    from schemas.platform import SessionInput,BackendResult,Signal,Payload
    from extensions.reference.implementation import evaluate_reach
    from tools.platform_registry import registry
    from tools.research_tasks import task_adapter,assemble_acceptance
    h=Host(ROOT/'runs/research/s12-mirror-live-20261020','s12-mirror-live-20261020',actor='unified-research')
    s=state(h);out=ROOT/'evidence/s12_mirror';f=read(out/'frozen_protocol.json')
    assert s['research_status']=='stopped' and not s['pending'] and not s['pilot'].get('unconsumed_response')
    assert s['freeze']==f['implementation_commit'] and s['spec']['resolved_identity']==f['configuration_identity']
    assert science_hashes()==f['science_hashes'] and core_hashes()==f['core_hashes']
    with h.store.connect(True) as db:assert db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]==0
    events=h.store.events(h.run_id);requests=[e for e in events if e['kind']=='r3_request']
    responses={e['request_id']:h.store.artifact(e['outputs'][0]) for e in events if e['kind']=='r3_response'}
    assert len(requests)==len(responses)==s['pilot']['live_model_requests']==h.store.remaining()['used']['model_calls']
    feedback={}
    for e in events:
        if e['kind']=='model_original_tool_feedback':
            v=h.store.artifact(e['outputs'][0]);key=v['tool_use']['toolUseId'];assert key not in feedback;feedback[key]=v
    for e in requests:
        wire=h.store.artifact(h.store.artifact(e['outputs'][0])['request']);assert digest(wire)==h.store.lookup(h.run_id,e['request_id'])['request_hash']
        ids={t['id'] for m in wire['messages'] if m['role']=='assistant' for t in m.get('tool_calls',[])}
        assert all(m.get('tool_call_id') in ids for m in wire['messages'] if m['role']=='tool')
    for e in events:
        if e['kind']=='model_original_tool_request':
            t=h.store.artifact(e['outputs'][0])['tool_use'];assert feedback[t['toolUseId']]['tool_use']==t
    for r in responses.values():assert hashlib.sha256(h.store.artifact(r['body'],raw=True)).hexdigest()==r['body']['artifact_id']
    fresh=[r for k in ('results','mechanics_results','physical_replays','matched_state_results','rl_evaluations','analysis_results') for r in s.get(k,[])]
    disposition=h.store.artifact(s['final_disposition']);plan=disposition.get('original_plan',{})
    if plan.get('action')=='stop':assert all(r in plan['supporting_evidence'] for r in fresh)
    physical=[]
    for ref in s.get('physical_replays',[]):
        v=h.store.artifact(ref);assert v['owning_study']==h.run_id
        cfg=h.store.artifact(v['candidate'])['configuration'];inp=SessionInput.model_validate(cfg)
        raw=h.store.artifact(v['raw_reference']);samples=raw['samples'];source=h.store.artifact(v['source_reference'])['trajectory']
        if not task_gap(v)['valid_complete']:
            physical.append(dict(reference=ref,complete=False,independent_recompute='not_tested'));continue
        signal=next(x for x in inp.task.observations if x.name=='tip_position' and x.phase=='post_step')
        backend=BackendResult(solver_status='completed',backend_id='backend.family_mujoco',model_id='mujoco_serial_bending_v1',
            signals=[Signal(spec=signal,times_s=[x['time_s'] for x in samples[1:]],values=[x['tip_m'] for x in samples[1:]])],
            data=Payload(contract='family.backend_data',data=dict(physical_replay=True)),limitations=['Ideal direct tendon tension; nominal sampled task only'],
            initial_state=inp.task.initializer.parameters,seed=inp.seed)
        ev=evaluate_reach(inp.task,backend,v['raw_reference'],registry(),digest(dict(candidate=v['candidate'],source=v['source_reference'])))
        assert plain(ev)==h.store.artifact(v['evaluation_reference'])
        adapter=task_adapter(cfg);limits=adapter.ranking_limits();hold=[x for x in samples if x['time_s']>=adapter.holding_start_s()-1e-12]
        complete=raw['status']=='completed' and len(samples)==len(source['tensions_n'])+1
        complete=complete and raw['physics_steps']==round(inp.task.timing.duration_s/raw['physics_timestep_s'])
        error=max(x['position_error_m'] for x in hold);speed=max(x['speed_m_s'] for x in hold)
        bounds={t['id']:t['force_limit_n'] for t in cfg['robot']['structure']['data']['tendons']}
        force=max(max(0.,-u,u-bounds[name]) for x in samples[1:] for name,u in zip(raw['tendon_order'],x['actual_tension_n']))
        expected_hold=round(inp.policy.controller.parameters.data['settling']['window_s']/inp.task.timing.control_period_s)+1
        profile=dict(complete=complete,execution_id=v['profile']['execution_id'],simulation=v['raw_reference'],evaluation=v['evaluation_reference'],
            task=plain(inp.task),official_task_success=ev.task_success,solver_error_count=0 if complete else 1,force_bound_violation_n=force,
            sampled_settling=dict(window_s=inp.policy.controller.parameters.data['settling']['window_s'],position_limit_m=limits['holding_max_error_m'],
                speed_limit_m_s=limits['holding_max_speed_m_s'],available=len(hold)==expected_hold,max_error_m=error,max_speed_m_s=speed,
                passed=bool(len(hold)==expected_hold and error<=limits['holding_max_error_m'] and speed<=limits['holding_max_speed_m_s'])))
        acceptance=assemble_acceptance(cfg,ev,profile,evaluation_reference=v['evaluation_reference'],profile_reference=None,motion=[dict(time_s=x['time_s']) for x in samples])
        assert acceptance==v['acceptance'] and profile==v['profile']
        physical.append(dict(reference=ref,original_evaluator_and_full_acceptance_equal=True,accepted=acceptance['accepted'],task_gap=task_gap(v)))
    manifest=read(out/'study/archive_manifest.json');archive=out/'study/immutable_artifacts.tar.gz'
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==manifest['archive_sha256']
    load_credential(Path(s['spec']['runtime']['credentials_reference']).expanduser());secret=os.environ['DEEPSEEK_API_KEY'].encode()
    with tarfile.open(archive) as tar:
        for m in manifest['members']:
            b=tar.extractfile(m['name']).read();assert hashlib.sha256(b).hexdigest()==m['sha256'] and secret not in b
    unchanged=['extensions','matlab','schemas','tasks','evidence/s7_mirror','evidence/s8_mirror','evidence/s9_variant','evidence/s10_mirror','evidence/s11_mirror','configs/research/family_space_s7.json']
    assert not subprocess.check_output(['git','diff','25e1c889','--',*unchanged],text=True)
    checks=dict(study_id=h.run_id,freeze=s['freeze'],source_hashes_match_frozen=True,original_task_science_and_sealed_history_unchanged=True,
        provider_requests=len(requests),model_tool_pairs=len(feedback),original_request_response_tool_ids_verified=True,all_receipts_settled=True,
        pending=None,unconsumed_response=None,complete_stop_citations=len(fresh) if plan.get('action')=='stop' else None,
        native_action=plan.get('action'),disposition_origin=disposition.get('origin'),accepted=bool(s.get('selected')),
        fresh_physical_results=len(s.get('physical_replays',[])),fresh_mathematics=len(s.get('analysis_results',[]))+len(s.get('mechanics_results',[])),
        archive_members_verified=len(manifest['members']),configured_key_matches=0,ledger=h.store.remaining(),independent_acceptance=physical,new_scientific_executions_in_audit=0)
    atomic_json(out/'final_artifact_checks.json',checks)
    return checks


if __name__=='__main__':
    import sys
    print(json.dumps(final_checks() if '--final' in sys.argv else preflight()))
