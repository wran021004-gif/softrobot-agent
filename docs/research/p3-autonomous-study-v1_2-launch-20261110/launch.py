"""Authorized lifecycle composition around the existing research CLI and Store.

The ignored launch leaf freezes the actual committed HEAD without a self-referential
Git commit hash. It changes only base_commit from the reviewed versioned source.
No research question, candidate, tool call or Plan is authored here.
"""
import os
for name in ('OMP_NUM_THREADS','MKL_NUM_THREADS','OPENBLAS_NUM_THREADS'):os.environ[name]='1'
import asyncio,json,subprocess,sys,time
from pathlib import Path
from tools.state_io import read,atomic_json,digest
from tools.research import core
from tools.research.state import state,save,guard
from tools.platform_host import Host
from tools.platform_store import Store

ROOT=Path(__file__).resolve().parents[3]
DOC=Path(__file__).resolve().parent
NAME='p3-passive-progressive-stiffness-autonomous-20261110-v1_2'
OLD='p3-passive-progressive-stiffness-autonomous-20261109-01'
SOURCE=ROOT/'configs/research/study_p3_passive_progressive_stiffness_autonomous_v1_2.json'
LEAF=SOURCE.with_name('.p3_autonomous_v1_2_launch.json')


def host():return Host(ROOT/'runs/research'/NAME,NAME,actor='user-authorized-v1_2-launch')


def prepare():
    if (ROOT/'runs/research'/NAME).exists():raise ValueError('EXISTING_STUDY_NEVER_RESET_OR_RECREATE')
    preflight=read(DOC/'preflight.json');assert preflight['ready']
    assert digest(Store(ROOT/'runs/research'/OLD).session(OLD)['state'])==preflight['old_state_identity']
    assert not subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip()
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    leaf=read(SOURCE);leaf['base_commit']=commit;atomic_json(LEAF,leaf)
    h=core.prepare(LEAF);s=state(h)
    assert s['spec']['base_commit']==commit and s['spec']['study_id']==NAME
    assert all(not s[k] for k in ('candidates','plans','results','physical_replays','analysis_results','search_results'))
    assert h.store.remaining()['used']['model_calls']==0
    core.bind(h)
    from tools.research.session_handoff import assess_live_admission,admit_formal_study
    evidence=assess_live_admission(h,ROOT.parent/'stage2-research-workflow-20261106/runs/research/phs2d-topology-successor-20261106','phs2d-topology-successor-20261106')
    evidence_ref=save(h,evidence,'handoff_transport_evidence')
    s=state(h)
    scope=dict(study_id=NAME,resolved_identity=s['spec']['resolved_identity'],implementation_freeze=s['freeze'],capabilities=s['spec']['capabilities'],
        execution_scopes=['registered mathematics','physical replay','request-feedback session handoff'],
        session_handoff=dict(boundary='request_feedback',evidence=evidence_ref),provider_requests=80,protected_provider_requests=0,provider_extension_authorized=False)
    authorization=save(h,dict(user_approval='User attachment 2026-11-10 expressly authorizes direct creation and launch of independent P3 v1.2 formal autonomous research: two-cell acceptance and independent Replay, shared 80 actual sends for Main and Reporter, unlimited cumulative passive science. No historical candidates, prior budget, or historical scientific evidence imported. No push.',scope=scope,scope_identity=digest(scope)),'formal_study_authorization')
    admit_formal_study(h,authorization);guard(h)
    receipt=dict(study_id=NAME,task_id=s['spec']['canonical_task']['task_id'],implementation=s['freeze'],base_commit=s['spec']['base_commit'],
        reviewed_source=str(SOURCE),frozen_launch_source=str(LEAF),launch_source_delta={'base_commit':commit},
        task_identity=s['spec']['canonical_task_identity'],family_space_identity=s['spec']['family_space_identity'],knowledge_manifest_identity=digest(s['spec']['knowledge_manifest']),
        resolved_identity=s['spec']['resolved_identity'],authorization=authorization,provider_budget=80,provider_used_before_start=0,
        candidates_before_start=0,plans_before_start=0,mathematical_evaluations_before_start=0,physical_cases_before_start=0,
        independent_store=str(h.store.db),timestamp_unix=time.time())
    atomic_json(DOC/'launch-receipt.json',receipt)
    status()


def status():
    h=host();s=state(h);events=h.store.events(NAME)
    from tools.research.reporter import provider_usage
    plans=[dict(reference=r,plan=h.store.artifact(r)['original_plan']) for r in s.get('plans',[])]
    analyses=[h.store.artifact(r,paths=('status','resource_use','internal_calculations','structure_research.cost')) for r in s.get('analysis_results',[])]
    observed={}
    for value in analyses:
        costs=value.get('internal_calculations') or [value.get('structure_research',{}).get('cost',{})]
        for cost in costs:
            for key,number in cost.items():
                if type(number) in (int,float):observed[key]=observed.get(key,0)+number
    for ref in s.get('physical_replays',[]):
        value=h.store.artifact(ref,paths=('actual_resource_consumption',))
        for key,number in (value.get('actual_resource_consumption') or {}).items():
            if type(number) in (int,float):observed[key]=observed.get(key,0)+number
    with h.store.connect(True) as db:unsettled=db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]
    preflight=read(DOC/'preflight.json');old=Store(ROOT/'runs/research'/OLD)
    assert digest(old.session(OLD)['state'])==preflight['old_state_identity'] and old.remaining()==preflight['old_ledger']
    value=dict(study_id=NAME,task_id=s['spec']['canonical_task']['task_id'],implementation=s.get('freeze'),base_commit=s['spec']['base_commit'],
        store=str(h.store.db),created=True,main_started=bool(s.get('live_started_unix')),main_plan_submitted=bool(plans),
        worker_started=bool(s.get('pending') or s.get('analysis_results') or s.get('search_results') or s.get('physical_replays')),
        task_acceptance=bool(s.get('success_gate')),selected=bool(s.get('selected')),research_status=s['research_status'],pending=s.get('pending'),
        unsettled_calls=unsettled,ledger=h.store.remaining(),provider_usage=provider_usage(h),
        provider_request_events=sum(e['kind']=='r3_request' for e in events),candidates=len(s['candidates']),plans=len(plans),
        first_main_plan=plans[0] if plans else None,mathematical_evaluations=s.get('mathematical_evaluations',0),analysis_results=len(analyses),
        physical_replay_results=len(s.get('physical_replays',[])),physical_replay_cases=s.get('physical_replay_launches',0),
        numerical_s=s['numerical_s'],observed_worker_costs=observed,old_study_unchanged=True,
        last_supervisor_pause=next((e['outputs'] for e in reversed(events) if e['kind']=='supervisor_pause'),None),timestamp_unix=time.time())
    atomic_json(DOC/'live-status.json',value)
    if plans:atomic_json(DOC/'first-main-plan.json',plans[0])
    print(json.dumps({k:v for k,v in value.items() if k not in ('first_main_plan','provider_usage','pending')},ensure_ascii=True))
    return value


def run():
    h=host();guard(h)
    remaining=h.store.remaining()['remaining']['model_calls']
    if remaining<1:raise ValueError('INITIAL_PROVIDER_ALLOCATION_EXHAUSTED_REQUIRES_USER_EXTENSION')
    from tools.research.agent import converse
    try:asyncio.run(converse(h,session_handoff=True,max_new_provider_requests=remaining))
    finally:status()


if __name__=='__main__':globals()[sys.argv[1]]()
