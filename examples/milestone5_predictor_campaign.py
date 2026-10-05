"""Bounded accuracy AND operational-cost campaign, linked to immutable predecessors."""
from copy import deepcopy
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from examples import milestone5_predictor_development as previous
from examples import milestone5_first_interval as first
from examples import milestone5_preparation as preparation
from tools.platform_store import Store,encode
from tools.platform_host import Host
from tools.platform_registry import registry
from tools.state_io import read,atomic_json,digest
from tools.runtime_identity import require_softagent_runtime
from tools.diagnostic_workflow import save
from tools.platform_models import tool_naming_policy,READABLE_TOOL_NAMING
from extensions.tendon_family.milestone5_campaign_reference import DEFINITION as REFERENCE
from extensions.tendon_family.milestone5_preparation import RESEARCH
from extensions.tendon_family.diagnostic_evidence import BoundReader,import_execution

RUN=ROOT/'runs/milestone5_predictor_campaign_20261005'
EVIDENCE=ROOT/'evidence/milestone5_predictor_campaign_20261005'
LIMITS=dict(model_calls=12,tool_calls=60,backend_solves=0,worker_calls=0,wall_s=6000.)
NUMERICAL=dict(reference_integrations=1,prediction_evaluations=16,local_solves=80,preview_attempts=2)
VALIDATION_LIMITS=dict(model_calls=4,tool_calls=16,backend_solves=2,worker_calls=0,wall_s=6000.)
AUTHORIZATION=dict(source='Direct user instruction, attachment c113be82-0dfe-4846-af91-d48f019021bf, 2026-10-05',
    destination='https://api.deepseek.com',model='deepseek-flash',development_limits=LIMITS,
    numerical_limits=NUMERICAL,conditional_validation_per_batch=VALIDATION_LIMITS,
    conditional_validation_batches=2,total_new_backend_attempts=4,backend_steps_during_development=0,
    data='Compact configurations, saved evidence, diagnostics, relevant implementation, instructions, schemas, budgets and corrections',
    credentials='Normal authentication via Join-Path $HOME .codex/.env only; never serialized',
    workers=0,subagents=0,commit=True,push_remote='origin',push_branch='feat/gvs-dynamics',force_push=False)
PROTECTED_FINAL_S=1265.


def snapshot():
    folders=[previous.RUN,previous.EVIDENCE,first.RUN,first.EVIDENCE,preparation.RUN,preparation.EVIDENCE,
             ROOT/'runs/milestone5_recovery_20261005',ROOT/'evidence/milestone5_recovery_20261005']
    return {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
        for folder in folders for p in folder.rglob('*') if p.is_file() and not p.name.endswith(('-wal','-shm'))}


def check_previous():
    assert snapshot()==read(RUN/'freeze.json')['predecessors'],'IMMUTABLE_PREDECESSOR_CHANGED'


def host(name, extension=None):
    r=registry()
    if extension is not None:r.add(extension)
    return Host(RUN,'m5campaign-'+name,reg=r)


def create_session(name,extension=None,reserve_s=1200.):
    h=host(name,extension)
    with h.store.connect(True) as db:exists=db.execute('SELECT 1 FROM sessions WHERE run_id=?',(h.run_id,)).fetchone()
    if exists:
        if not h.compatibility()['compatible']:raise ValueError('EXPLICIT_IMPLEMENTATION_REVISION_REQUIRED')
        return h
    old=Store(previous.RUN)
    inp=deepcopy(old.session(previous.host('research').run_id)['snapshot']['input'])
    bindings={RESEARCH.extension_id:RESEARCH.version,'evidence.read':'1.0.0'}
    if extension is not None:bindings[extension.extension_id]=extension.version
    provider=deepcopy(read(previous.RUN/'freeze.json')['provider_configuration'])
    provider['protocol_recovery']=dict(max_total=4,max_consecutive=2)
    provider['tool_naming']=tool_naming_policy(bindings,READABLE_TOOL_NAMING)
    allowances={RESEARCH.extension_id:dict(timeout_s=10.,reserve_s=5.),'evidence.read':dict(timeout_s=10.,reserve_s=5.)}
    if extension is not None:allowances[extension.extension_id]=dict(timeout_s=reserve_s,reserve_s=reserve_s)
    inp['run_id']=h.run_id
    inp['policy'].update(budget=LIMITS,allowed_tools=[],tool_bindings=bindings,model=provider,
                         timeout_s=600.,operation_allowances=allowances)
    h.create(inp)
    return h


def prepare():
    require_softagent_runtime()
    if (RUN/'freeze.json').exists():check_previous();return
    store=Store(RUN)
    if not store.db.exists():store.create(dict(project_id='m5-predictor-campaign-20261005',
        grant_id='m5-predictor-campaign-20261005',budget=LIMITS,authorization_source=json.dumps(AUTHORIZATION)))
    else:assert store.config()['budget']==LIMITS
    h=create_session('reference',REFERENCE);create_session('research')
    with store.transaction() as db:db.execute("INSERT OR IGNORE INTO meta VALUES ('diagnostic_work',?)",
        (encode(dict(limits=NUMERICAL,used={k:0 for k in NUMERICAL})),))
    old=Store(previous.RUN);oldfreeze=read(previous.RUN/'freeze.json');bindings=[]
    for binding in oldfreeze['bindings']:
        r=BoundReader(old,binding);bindings.append(import_execution(r,r.binding['execution_id'],store,h.run_id))
    r=BoundReader(old,oldfreeze['source_binding'])
    source=import_execution(r,r.binding['execution_id'],store,'m5campaign-research')
    criteria=dict(position_reporting_m=1e-6,speed_reporting_m_s=1e-4,vector_reporting_m_s=1e-4,
        residual_limit=1e-5,reference_successive_comparisons=2,ranking_margin_m_s=1e-4,
        physical_position_limit_m=.01,physical_speed_limit_m_s=.02,
        local_accuracy='Report each distinct interval, require all vector/speed/position tolerances for quantitative local accuracy; direction cannot replace accuracy',
        discrimination='At least one resolved correct historical pair at unchanged 1e-4 margin; universal abstention fails',
        economics='ALL incremental operational setup, prediction and decision cost strictly below ONE complete evaluation actually avoided; abstention avoids zero',
        admission=['causal implementation','supported reference for claimed scope','one evidence-backed physical correction',
                   'one measured dominant-cost strategy','useful historical discrimination','known failures handled within explicitly frozen role',
                   'plausible positive net saving','specific independent hypothesis','accepted native research judgment','adequate reservation'],
        distinctions=['numerical self-consistency','physical prediction accuracy','candidate discrimination','operational economics','prospective validation','real-time control'])
    frozen=dict(authorization=AUTHORIZATION,predecessors=snapshot(),source_binding=source,bindings=bindings,
        incumbent=oldfreeze['incumbent'],accepted_selection=oldfreeze['accepted_selection'],
        accepted_predecessor_interpretation=read(previous.RUN/'interpretation_response.json'),
        criteria=criteria,distinct_local_intervals=[dict(case='shared_first',binding_indices=[0,1],interval_s=[0.,.01]),
            dict(case='early075',binding_indices=[0],interval_s=[.01,.02]),
            dict(case='holding075',binding_indices=[0],interval_s=[.30,.31]),
            dict(case='holding15',binding_indices=[1],interval_s=[.30,.31])],
        historical_complete_cases=['history075','history15'],historical_scope_s=[0.,.35],holding_scope_s=[.30,.35],
        development_limits=LIMITS,numerical_limits=NUMERICAL,protected_final_interpretation_export_s=PROTECTED_FINAL_S,
        reference=dict(step_s=.00000390625,substeps=2560,guard_s=800.,outer_reservation_s=1200.,attempts=1,reused_resolutions=8),
        conditional_validation=dict(ledgers=['milestone5_predictor_campaign_validation1_20261005','milestone5_predictor_campaign_validation2_20261005'],
            per_batch=VALIDATION_LIMITS,preview_attempts=2,preview_controller_attempts=70,production_updates=70,combined_controller_attempts=140,
            scenarios=['incumbent_checkpoint_20_new_clock','incumbent_checkpoint_30_new_clock'],
            grants='Materialize only after frozen development admission; linked predecessor usage never reset',
            continuation='Same method/candidates/metrics. Batch 2 only if Batch 1 complete and valid, no false-safe, resolved correct ranking, all declared numerical checks pass, positive counterfactual net saving, accepted research continuation. Otherwise stop.'),
        corrections=dict(total=4,consecutive=2),physical_correction='Select once after localization and freeze before its comparisons',
        cost_strategy='Select once from saved timing and freeze before its comparisons',
        unchanged=['controller.gvs_nmpc@7.0.0','physical parameters','actuator limits','task and physical acceptance','incumbent','historical pass/fail'])
    atomic_json(RUN/'authorization.json',AUTHORIZATION);atomic_json(RUN/'freeze.json',frozen)
    atomic_json(RUN/'freeze_seal.json',dict(identity=digest(frozen),frozen_before_new_results=True))
    atomic_json(RUN/'linked_ledgers.json',dict(predecessor=str(previous.RUN),predecessor_cumulative=read(previous.RUN/'accounting.json')['cumulative'],
        development=str(RUN),validation=[dict(name=n,limits=VALIDATION_LIMITS,grant_materialized=False,used={k:0 for k in LIMITS})
        for n in frozen['conditional_validation']['ledgers']]))
    print(json.dumps(dict(status='frozen',limits=LIMITS,distinct_intervals=4)))


def calculate(name,p,extension,reserve_s=1200.):
    prepare();h=create_session(name,extension,reserve_s);request='campaign-'+name
    prior=h.store.lookup(h.run_id,request)
    if prior:
        if not prior['receipt']:raise ValueError('UNRESOLVED_ATTEMPT_NO_REPLAY')
        receipt=json.loads(prior['receipt'])
        event=next(e for e in h.store.events(h.run_id) if e['request_id']==request and e['status']=='reserved')
        saved=h.store.artifact(h.store.artifact(event['inputs'][0])['arguments']['protocol'])
        if saved!=p:raise ValueError('REQUEST_BINDING_MISMATCH')
    else:
        if h.store.remaining()['remaining']['wall_s']<reserve_s+PROTECTED_FINAL_S:raise ValueError('PROTECTED_FINALIZATION')
        h.resume();receipt=h.invoke(dict(request_id=request,tool_id=extension.extension_id,tool_version=extension.version,
            arguments=dict(protocol=save(h.store,p)),reason='Authorized bounded accuracy and cost development; no backend steps',cache='new'))
    atomic_json(RUN/(name+'_receipt.json'),receipt)
    if receipt['execution_status']!='completed':raise ValueError(str(receipt.get('error')))
    result=h.store.artifact(receipt['output'])['detail'];atomic_json(RUN/(name+'.json'),result);check_previous()
    print(json.dumps(dict(phase=name,status='completed',charged=receipt['charged'])))
    return result


def reference():
    return calculate('reference',dict(specification=read(first.RUN/'specification.json'),
        completed_results=read(previous.RUN/'reference.json')['results']),REFERENCE)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--phase',required=True);args=parser.parse_args()
    if args.phase=='prepare':prepare()
    elif args.phase=='reference':reference()
    else:raise ValueError('Unsupported phase')
