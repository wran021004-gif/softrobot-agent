from tools.research.state import *
"""Reusable reach-and-hold research with immutable candidates and one shared ledger.

Numerical business services remain the established complete-execution and mixed
design services. Strands owns the conversation and session recovery.
"""
import argparse
import asyncio
from copy import deepcopy
import hashlib
import io
import json
import math
import os
from pathlib import Path
import subprocess
import tarfile
import time
from uuid import uuid4

from schemas.platform import ProjectConfig, SessionInput
from tools.research.contracts import Parameters, Search, Plan, ExperienceQuery, EvidenceQuery, RLRequest, AnalysisRequest
from tools.platform_host import Host
from tools.platform_store import plain, zero
from tools.state_io import atomic_json, read, digest

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SPEC = ROOT/'configs/research/study.json'
def read_evidence(host, query):
    q = EvidenceQuery.model_validate(query); s = state(host)
    value = host.store.artifact(q.reference)
    if protected(host) and plain(q.reference) not in readable_results(s,host):
        raise ValueError('PROTECTED_EVIDENCE_READ_REQUIRES_NEW_RESULT_OR_TRAINING_SUMMARY')
    for part in q.pointer.strip('/').split('/') if q.pointer else []:
        part = part.replace('~1', '/').replace('~0', '~')
        value = value[int(part)] if isinstance(value, list) else value[part]
    if plain(q.reference) in [*s.get('results', []),*s.get('rl_evaluations', []), *s.get('rl_training_summaries', [])]:
        if q.pointer in ('','/acceptance','/episodes'):
            update(host,evaluation_reads=[*s.get('evaluation_reads',[]),plain(q.reference)])
        update(host, rl_evidence_reads=[*s.get('rl_evidence_reads', []), plain(q.reference)])
    return value














def prepare(spec_path=DEFAULT_SPEC, directory=None):
    from tools.research.config import resolve
    spec = resolve(spec_path); run_id = spec['study_id']
    directory = Path(directory or ROOT/'runs/research'/run_id)
    h = Host(directory, run_id, actor='unified-research')
    if h.store.db.exists() and h.store.connect(True).execute('SELECT COUNT(*) FROM sessions WHERE run_id=?',(run_id,)).fetchone()[0]:
        if state(h)['spec'] != spec: raise ValueError('STUDY_SPEC_CHANGED_USE_EXPLICIT_MIGRATION')
        if not state(h).get('reference_candidate'):
            started=time.perf_counter()
            candidate=construct(h,spec['reference_parameters'],dict(origin='initialization_recovery_no_scientific_dispatch'))
            update(h,reference_candidate=candidate,numerical_s=state(h)['numerical_s']+time.perf_counter()-started)
            if enabled(spec,'rl'):
                update(h,rl_task=save(h,h.store.artifact(candidate)['configuration']['task'],'rl_frozen_task'),rl_runs={},rl_evaluations=[],rl_evidence_reads=[])
        return h
    start = time.perf_counter()
    cfg=deepcopy(spec['configuration']); nominal=dict(configuration=deepcopy(cfg),provenance=spec['source_provenance'])
    # Recovery-enabled source is complete immutable execution evidence.
    cfg['policy']['controller']['parameters']['data']['recipe'].update({k:v for k,v in spec['reference_parameters'].items() if k in ('holding_tip_speed_weight','terminal_tip_speed_weight')})
    if spec.get('nominal_source'):
        from extensions.tendon_family.contracts import current_nmpc_recipe
        cfg['policy']['controller']['parameters']['data']['recipe']=current_nmpc_recipe(
            cfg['policy']['controller']['parameters']['data']['recipe'],spec.get('controller_recipe'))
    model = deepcopy(spec['runtime']['provider'])
    cfg['policy'].update(model=model, budget=limits(spec), allowed_tools=['evidence.read'],
        tool_bindings={'evidence.read':'1.0.0'}, operation_allowances={'evidence.read':dict(timeout_s=30.,reserve_s=30.)})
    if not h.store.db.exists():
        h.store.create(ProjectConfig(project_id=run_id, grant_id=run_id+'-authorized',
            authorization_source=spec['authorization'], budget=limits(spec),
            exclusive_resources={'provider_request':1,'backend.family_mujoco':1}))
    h.create(cfg); h.resume()
    from extensions.tendon_family.contracts import GVSTrajectoryParameters
    recipe = plain(GVSTrajectoryParameters.model_validate(cfg['policy']['controller']['parameters']['data']['recipe']))
    profile = dict(adapter='unified_recovery_profile_v1',version=spec['evaluation_version'],
        configuration=full_science(cfg), recipe=recipe, science_hashes=science_hashes(),
        recording=dict(complete_update_inputs=spec['complete_update_inputs'],update_ids=spec['record_update_ids']),
        acceptance='unchanged joint sampled reach/hold; inclusive .30-.35s; .01m/.02m/s',
        confirmation=spec['confirmation'])
    profile['execution_environment']=deepcopy(spec.get('numerical_environment',{}))
    profile['identity'] = digest(profile)
    update(h, spec=spec, base_configuration=cfg, profile=profile, profile_history=[profile],
        started_unix=time.time(), cutoff_unix=time.time()+spec['budgets']['activity_s']-spec['budgets']['delivery_reserve_s'],
        numerical_s=0., numerical_reserved_s=0., local_solves=0, local_solve_s=0.,
        results=[], candidates={}, plans=[], retrievals=[], searches={}, pending=None,
        offline_nlp=0, bdf_replays=0, mechanics_results=[], handoffs=[], historical_diagnostic_sources=[],
        research_status='ready', selected=None,
        pilot=dict(provider=model,live_model_requests=0,framework_session_id=run_id,
            request_deadline_unix=time.time()+spec['budgets']['activity_s']-spec['budgets']['delivery_reserve_s']))
    if spec.get('nominal_source'):
        update(h,nominal_configuration=nominal['configuration'],nominal_provenance=nominal['provenance'],mathematical_evaluations=0,analysis_results=[],analysis_costs=[],search_results=[],assignment_started_unix=time.time(),accounting_scope='Cumulative assignment includes engineering preflight; never reset at live start')
    update(h,scoped_context=[save(h,read(ROOT/path),'supplied_scoped_context') for path in spec.get('supplied_evidence',[])])
    candidate = construct(h, spec['reference_parameters'], dict(origin='initial_controller_reference', historical_result_ownership='sealed source activity'))
    update(h, reference_candidate=candidate, numerical_s=max(state(h)['numerical_s'],time.perf_counter()-start))
    if enabled(spec,'rl'):
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.scene import assemble
        inp=SessionInput.model_validate(h.store.artifact(candidate)['configuration'])
        if assemble(inp,physics_for(inp))['control']['tension_execution_mode']!='ideal_tension': raise ValueError('EXPLICIT_IDEAL_TENSION_REQUIRED')
        update(h,rl_task=save(h,plain(inp.task),'rl_frozen_task'),rl_runs={},rl_evaluations=[],rl_evidence_reads=[])
    atomic_json(directory/'resolved_configuration.json',spec)
    atomic_json(directory/'activity.json',spec)
    return h


from tools.research.design import configuration_for, construct, verify_candidate, full_science












def bind(host, reason=None, specification=None):
    from tools.platform_tasks import compile_input
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('COMMIT_BEFORE_BIND_OR_MIGRATION')
    s=state(host)
    if s['pending']: raise ValueError('PENDING_OUTCOME_BLOCKS_MIGRATION')
    with host.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:
            raise ValueError('UNSEALED_RESERVATION_BLOCKS_BIND')
    if specification is not None and specification!=s['spec']:
        if not reason:raise ValueError('SPECIFICATION_MIGRATION_REASON_REQUIRED')
        immutable=('study_id','started_unix','baseline_archive','baseline_execution_id','baseline_offline_execution_id')
        if any(specification.get(k)!=s['spec'].get(k) for k in immutable):raise ValueError('MIGRATION_CANNOT_RESET_STUDY_OR_SOURCE_IDENTITY')
        ceilings=('activity_s','numerical_s','provider_requests','protected_provider_requests','local_solves','local_solve_s','offline_nlp','bdf_replays','physical_launches','public_operations','mathematical_evaluations')
        if any(specification['budgets'].get(k)!=s['spec']['budgets'].get(k) for k in ceilings):raise ValueError('MIGRATION_CANNOT_CHANGE_AUTHORIZED_CEILINGS')
        if specification['budgets']['delivery_reserve_s']!=s['spec']['budgets']['delivery_reserve_s']:raise ValueError('MIGRATION_CANNOT_RESET_DELIVERY_CUTOFF')
        relation=save(host,dict(previous=s['spec'],selected=specification,reason=reason,
            clocks_and_counters_preserved=True),'specification_migration')
        update(host,spec=specification,base_configuration=deepcopy(specification['configuration']),
            nominal_configuration=deepcopy(specification['configuration']),
            specification_migrations=[*s.get('specification_migrations',[]),relation])
        s=state(host)
    old=host.store.session(host.run_id)['snapshot']; input_configuration=deepcopy(old['input']);input_configuration['policy']['model']=deepcopy(s['spec']['runtime']['provider']);snapshot=compile_input(input_configuration,host.reg)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    profile=deepcopy(s['profile'])
    science_prefixes=('backend.','candidate.','controller.','evaluate.','initialize.','model.','solver.','task.')
    changed_dependencies=[name for name,value in snapshot['dependencies'].items()
        if name.startswith(science_prefixes) and old['dependencies'].get(name)!=value]
    selected_environment=s['spec'].get('numerical_environment',{})
    changed=science_hashes()!=profile['science_hashes'] or bool(changed_dependencies) or profile.get('execution_environment',{})!=selected_environment
    if 'freeze' in s and not reason: raise ValueError('MIGRATION_REASON_REQUIRED')
    if changed:
        profile.pop('identity'); profile['version']+=1; profile['science_hashes']=science_hashes()
        profile['execution_environment']=deepcopy(selected_environment)
        profile['identity']=digest(profile)
    snapshot.update(project_commit=commit,worktree_dirty=False)
    with host.store.transaction() as db:
        ref=host.store.put(db,snapshot)
        db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(ref.artifact_id,host.run_id))
        current=host.store.session(host.run_id,db)['state']
        current.update(freeze=commit,profile=profile,core_hashes=core_hashes(),
            scientific_dependencies={k:v for k,v in snapshot['dependencies'].items() if k.startswith(science_prefixes)})
        if changed: current['profile_history'].append(profile)
        if reason:
            current.setdefault('core_repairs',[]).append(dict(reason=reason,previous_commit=s.get('freeze'),commit=commit,
                evaluation_version=profile['version'],material_behavior_change=changed,
                changed_scientific_dependencies=changed_dependencies,
                old_results_and_costs_retained=True,improvement_requires_new_comparable_reference=changed))
        host.store.update_state(db,host.run_id,current)
        host.store.event(db,host.run_id,'implementation_binding','committed',outputs=[ref])
    if changed:
        ref=construct(host,s['spec']['reference_parameters'],dict(origin='new_version_reference_required'))
        update(host,reference_candidate=ref,selected=None)
    atomic_json(host.store.root/'implementation_freeze.json',dict(commit=commit,profile=profile))
    atomic_json(host.store.root/'resolved_configuration.json',state(host)['spec'])


def execute(host, candidate_ref, operation_key, *, role='development', selected=None):
    guard(host,expensive=role!='confirmation'); s=state(host); c=verify_candidate(host,candidate_ref)
    if c['profile_identity']!=s['profile']['identity']:
        raise ValueError('FRESH_EXECUTION_REQUIRES_CURRENT_PROFILE; HISTORICAL_CANDIDATE_IS_READ_ANALYSIS_ONLY')
    expected_environment=s['spec'].get('numerical_environment',{})
    if any(os.environ.get(key)!=value for key,value in expected_environment.items()):
        raise ValueError('EXECUTION_REQUIRES_CALIBRATED_NUMERICAL_ENVIRONMENT_BEFORE_INTERPRETER_START')
    if s['spec'].get('require_configuration_cost_estimate'):
        estimate=s.get('execution_cost_estimate') or {}
        if estimate.get('recipe_identity')!=digest(s['profile']['recipe']):
            raise ValueError('CURRENT_CONFIGURATION_COST_REESTIMATE_REQUIRED')
        if estimate.get('science_hashes')!=s['profile']['science_hashes']:
            raise ValueError('CURRENT_IMPLEMENTATION_COST_REESTIMATE_REQUIRED')
        if estimate.get('numerical_environment',{})!=expected_environment:
            raise ValueError('CURRENT_RUNTIME_COST_REESTIMATE_REQUIRED')
    if s['spec'].get('nmpc_execution_cap_s'):
        timing=nmpc_timing(host,candidate_ref)
        if not timing['available']: raise ValueError(timing['reason'])
    confirmation=role=='confirmation'
    repetition=role in ('diagnostic_repetition','engineering_repetition')
    if repetition:
        if s['spec'].get('mode') != 'engineering_numerical' or plain(selected) not in s['results']:
            raise ValueError('OWNED_DIAGNOSTIC_REPETITION_REQUIRED')
        old=host.store.artifact(selected)
        if role=='engineering_repetition' and (not (old.get('acceptance') or {}).get('accepted') or old['role'] not in ('fixed_validation','length_validation')):
            raise ValueError('ENGINEERING_REPETITION_REQUIRES_SELECTED_VALIDATION_PASS')
        if old['candidate'] != plain(candidate_ref) or old['profile_identity'] != s['profile']['identity']:
            raise ValueError('REPETITION_REQUIRES_IDENTICAL_CONFIGURATION')
    if confirmation:
        old=host.store.artifact(selected)
        if old['candidate']!=plain(candidate_ref) or old['profile_identity']!=s['profile']['identity'] or old['scientific_configuration']!=c['scientific_configuration']:
            raise ValueError('CONFIRMATION_REQUIRES_SELECTED_COMPLETE_PARAMETERS_AND_EVALUATION_CONFIGURATION')
        if not old.get('acceptance',{}).get('accepted'): raise ValueError('SELECTED_PASSING_EXECUTION_REQUIRED')
        from tools.research.feedback import eligibility
        choice=eligibility(host,selected)
        if not choice['eligible']: raise ValueError('; '.join(choice['reasons']))
    admission=capacity(host,1,confirmation or repetition,candidate=candidate_ref)
    if admission['admitted']<1: raise ValueError('EXECUTION_AND_CONFIRMATION_RESERVE_CANNOT_FIT')
    # A unique execution owner is persisted before starting any backend.
    owner=host.run_id+'-exec-'+uuid4().hex[:16]
    cfg=deepcopy(c['configuration']); cfg['run_id']=owner
    from tools.execution_completion import EXECUTION_ALLOWANCES
    cfg['policy'].update(budget={**cfg['policy']['budget'],'model_calls':0},allowed_tools=[],
        tool_bindings={n:'1.0.0' for n in ('simulation.run','evaluation.run','control.profile_report')},
        operation_allowances=deepcopy(EXECUTION_ALLOWANCES))
    simulation_allowance=s.get('execution_cost_estimate',{}).get('simulation_watchdog_s',s['spec']['execution_allowances']['simulation_s'])
    cfg['policy']['operation_allowances']['simulation.run']=dict(timeout_s=simulation_allowance,reserve_s=simulation_allowance)
    if full_science(cfg)!=c['scientific_configuration']: raise ValueError('EXECUTION_CHANGED_FROZEN_SCIENCE')
    pending=dict(owner=owner,candidate=plain(candidate_ref),configuration=cfg,role=role,
        selected_execution=plain(selected),operation_key=operation_key,started_unix=time.time(),
        profile_identity=s['profile']['identity'],admission=admission,reserved_s=admission['per_execution_s'])
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state'];charge_start(current)
        current.update(pending=pending,numerical_reserved_s=current['numerical_reserved_s']+pending['reserved_s'],nmpc_launches=current.get('nmpc_launches',0)+1)
        host.store.update_state(db,host.run_id,current)
    return finish_execution(host)


def finish_execution(host, recovery=False):
    """Only sealed receipts continue. Reporting failure cannot trigger simulation."""
    s=state(host);p=s['pending']
    if recovery and p and not p.get('launch_intent'):
        # Launch intent is durably committed before any subprocess send. Its
        # absence proves that this failed dispatch never started a worker.
        from datetime import datetime
        failures=[e for e in host.store.events(host.run_id) if e['kind']=='pending_operation_failure'
            and host.store.artifact(e['outputs'][0]).get('pending',{}).get('owner')==p['owner']]
        if not failures:raise ValueError('PRELAUNCH_RECOVERY_REQUIRES_RECORDED_FAILURE')
        last=failures[-1];folder=host.store.root/'executions'/p['owner'];folder.mkdir(parents=True,exist_ok=True)
        atomic_json(folder/'boundary.json',dict(termination_confirmed=True,timed_out=False,
            worker_started=False,prelaunch_failure=last['outputs'][0],
            elapsed_s=max(0.,datetime.fromisoformat(last['timestamp']).timestamp()-p['started_unix'])))
    from tools.execution_completion import complete_execution, STAGES
    from tools.service_execution import _run_contained
    from tools.research_tasks import assemble_acceptance
    s=state(host); p=s['pending']
    if not p: raise ValueError('NO_PENDING_EXECUTION')
    child=Host(host.store.root,p['owner'],actor=host.actor)
    c=host.store.artifact(p['candidate']); started=time.perf_counter()
    folder=host.store.root/'executions'/p['owner']; folder.mkdir(parents=True,exist_ok=True)
    outcome=folder/'boundary.json'; output=folder/'result.json'
    if not recovery:
        if p.get('launch_intent'): raise ValueError('LAUNCH_ALREADY_REQUESTED_RECOVERY_ONLY_NO_RELAUNCH')
        request=folder/'request.json'
        atomic_json(request,dict(root=str(host.store.root),study=host.run_id,owner=p['owner'],actor=host.actor,
            configuration=p['configuration'],candidate_id=c['candidate_id'],recording=s['profile']['recording']))
        # Persist launch intent first. A crash thereafter is uncertain, never replayable.
        update(host,pending=dict(p,launch_intent=True))
        try:
            with (folder/'worker.log').open('w',encoding='utf8') as log:
                done=_run_contained([str(s['spec']['runtime']['research_python']),'-m','tools.research.execution_worker',str(request)],log,
                    min(p['reserved_s'],max(.001,execution_deadline(host)-time.time())))
            boundary=dict(termination_confirmed=True,timed_out=False,returncode=done.returncode)
        except subprocess.TimeoutExpired as exc:
            boundary=dict(termination_confirmed=getattr(exc,'termination_confirmed',False),timed_out=True)
        except Exception as exc:
            boundary=dict(termination_confirmed=False,timed_out=False,error=str(exc))
        boundary['elapsed_s']=time.perf_counter()-started
        atomic_json(outcome,boundary)
    elif not outcome.exists():
        raise ValueError('UNKNOWN_WORKER_TERMINATION_RETAINS_PENDING_RESERVATION; NO_RELAUNCH')
    boundary=read(outcome)
    if not boundary['termination_confirmed']:
        return dict(status='execution_unresolved',reason='Worker tree termination uncertain; reservation retained; no replay',pending=p)
    receipts={}; unfinished=None
    for stage,tool in STAGES:
        row=child.store.lookup(p['owner'],'complete-'+stage)
        if row and row['receipt']: receipts[stage]=json.loads(row['receipt'])
        elif row:
            unfinished=(stage,tool,row);break
    if unfinished:
        stage,tool,row=unfinished
        # Use the existing settlement API: failed receipt, exact prior costs retained.
        elapsed=max(0.,boundary['elapsed_s']-sum(r['charged']['wall_s'] for r in receipts.values()))
        receipts[stage]=child.store.complete(row,dict(request_id=row['request_id'],execution_id=row['execution_id'],
            caller=row['caller'],tool_id=tool,tool_version='1.0.0',execution_status='failed',charged=zero(),
            error='TIMEOUT' if boundary['timed_out'] else 'WORKER_EXIT_WITH_UNFINISHED_STAGE'),
            dict(status='execution_incomplete',task_performance='unmeasured',boundary=boundary),elapsed=elapsed)
    if boundary['timed_out'] or unfinished:
        result=dict(status='execution_incomplete',timed_out=boundary['timed_out'],receipts=receipts,
            stage=unfinished[0] if unfinished else 'execution',failure_reason='timeout' if boundary['timed_out'] else 'worker exit',
            task_performance='unmeasured',boundary=boundary,retained_evidence=[r for e in host.store.events(p['owner']) for r in e['outputs']])
    elif output.exists(): result=read(output)
    else:
        # Package only when every stage already has a sealed receipt. No missing-stage launch.
        if len(receipts)==len(STAGES): result=complete_execution(child,p['configuration'],c['candidate_id'])
        else: result=dict(status='execution_incomplete',receipts=receipts,failure_reason='worker returned without result',task_performance='unmeasured')
    if boundary.get('worker_started') is False:
        result.update(failure_reason='prelaunch engineering failure; no numerical worker started',boundary=boundary,
            task_performance='unmeasured')
    if result['status']=='execution_unresolved':
        save(host,dict(pending=p,partial_result=result),'unresolved_execution'); return result
    acceptance=None; profile=None
    if result['status']=='evaluated':
        profile=host.store.artifact(result['profile_report']['reference'])['detail']
        acceptance=assemble_acceptance(p['configuration'],result['evaluation_data'],profile,
            evaluation_reference=result['receipts']['evaluation']['output'],profile_reference=result['receipts']['profile']['output'],
            motion=host.store.artifact(profile['motion']))
    receipts=result.get('receipts',{})
    # Sealed stage costs plus construction/analysis; never charge enclosing
    # simulation and its internal updates twice, including on recovery.
    actual=max(boundary['elapsed_s'],sum(r['charged']['wall_s'] for r in receipts.values()))+(time.perf_counter()-started if recovery else 0.)
    detail=dict(status=result['status'],role=p['role'],candidate=p['candidate'],candidate_id=c['candidate_id'],
        implementation=s['freeze'],science_hashes=s['profile']['science_hashes'],
        numerical_environment={key:os.environ.get(key) for key in s['spec'].get('numerical_environment',{})},
        scientific_identity=c['identity'],scientific_configuration=c['scientific_configuration'],profile_identity=p['profile_identity'],
        evaluation_version=c['evaluation_version'],selected_execution=p['selected_execution'],
        acceptance=acceptance,profile=profile,execution=result,numerical_s=actual,
        execution_id=result.get('execution_id') or receipts.get('simulation',{}).get('execution_id'),
        owner_run_id=p['owner'],operation_key=p['operation_key'],
        owning_study=host.run_id, fresh_execution=True, cached_operation_receipt=False,
        candidate_artifact_reuse_does_not_reuse_execution=True,
        facts_classification='program-generated; principal interpretation remains in original plan',
        runtime_observation='complete' if result['status']=='evaluated' else 'censored or incomplete; no complete episode timing',
        failure_categories=[] if acceptance and acceptance['accepted'] else
            ['scientific_task_failure'] if acceptance else ['engineering_or_missing_evidence'])
    from tools.research.feedback import mechanics_context
    detail['mechanics_context']=mechanics_context(host,p['candidate'])
    ref=save(host,detail,'experiment_result'); s=state(host)
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        if not current.get('pending') or current['pending']['owner']!=p['owner']: raise ValueError('EXECUTION_ALREADY_SETTLED')
        current.update(results=[*current['results'],ref],pending=None,
            numerical_reserved_s=current['numerical_reserved_s']-p['reserved_s'],numerical_s=current['numerical_s']+actual)
        host.store.update_state(db,host.run_id,current)
    from tools.research.feedback import eligibility
    return dict(reference=ref,**compact_result(detail),confirmation=eligibility(host,ref),
        operation_cost=dict(additional_numerical_s=actual,additional_scientific_executions=1,cached_operation_receipt=False))


def compact_result(r):
    profile=r.get('profile') or {}
    result={k:r.get(k) for k in ('status','role','candidate','candidate_id','scientific_identity','profile_identity','evaluation_version',
        'selected_execution','acceptance','execution_id','owner_run_id','owning_study','fresh_execution',
        'cached_operation_receipt','numerical_s','failure_categories','mechanics_context')} | dict(
        controller_facts={k:profile[k] for k in ('updates','applied_control_updates','initialization_selected','accepted_noninitialization_plans',
            'solver_error_count','unusable_plans','deadline_misses','one_step_prediction_summary') if k in profile})
    if not result['execution_id']:
        result['execution_id']=r.get('execution',{}).get('receipts',{}).get('simulation',{}).get('execution_id')
        result['execution_identity_source']='sealed failed simulation receipt; no completed acceptance implied'
    return result


def search_problem(host,query,count):
    from tools.research.search import search_problem as build
    return build(host,query,count)


def run_search(host,query,key):
    from tools.research.search import run_search as search
    return search(host,query,key,guard=guard,execute=execute,capacity=capacity)


def experience(host, query):
    from tools.research.experience import retrieve
    return retrieve(host,query)


def diagnose(host, refs):
    from extensions.tendon_family.control_evidence import ControlEvidence
    s=state(host); reader=ControlEvidence(host.store); records=[]; numerical=[]; incomplete=[]
    for ref in refs:
        r=host.store.artifact(ref)
        if plain(ref) not in s['results'] and r.get('status')=='evaluated':
            from tools.research.feedback import result_view
            numerical.append(dict(reference=plain(ref),historical=True,**result_view(host,ref)))
            continue
        if plain(ref) in s.get('mechanics_results',[]):
            numerical.append(dict(reference=plain(ref),physical_validation=False,**{k:r.get(k) for k in
                ('operation','status','execution_id','trajectory_metrics','relaxed_nlp_feasible','original_task_feasible','replay','charged_numerical_s')}))
            continue
        if plain(ref) in s['results'] and r.get('status')!='evaluated':
            incomplete.append(dict(reference=plain(ref),**compact_result(r),acceptance_available=False,
                archived_partial_evidence=s.get('incomplete_execution_evidence',[])))
            continue
        if not r.get('execution_id') or r.get('status')!='evaluated': continue
        source=reader.resolve(r['execution_id']); obs=reader.read_file(source,'controller_observations.json',[])
        records.append(dict(execution_id=r['execution_id'],observations=obs,source=source,
            scientific_configuration=r.get('scientific_configuration'),profile_identity=r.get('profile_identity')))
    comparison=[]
    if len(records)>=2:
        a,b=records[-2:]; left=a['observations']; right=b['observations']
        for index,(x,y) in enumerate(zip(left,right)):
            if x['actual_tension_n']!=y['actual_tension_n']:
                rx=x.get('complete_update_record',{}); ry=y.get('complete_update_record',{})
                comparison.append(dict(update_id=index,time_s=x['time_s'],
                    scientific_configuration_equal=a['scientific_configuration']==b['scientific_configuration'],
                    evaluation_profile_equal=a['profile_identity']==b['profile_identity'],
                    maximum_action_difference_n=max(abs(i-j) for i,j in zip(x['actual_tension_n'],y['actual_tension_n'])),
                    measured_state_equal=x['measured_initial_state']==y['measured_initial_state'],
                    previous_input_equal=rx.get('previous_applied_input_n')==ry.get('previous_applied_input_n'),
                    warm_source_equal=rx.get('warm')==ry.get('warm'),
                    initialized_vector_equal=rx.get('initialization',{}).get('initialized_vector')==ry.get('initialization',{}).get('initialized_vector'),
                    selection=[rx.get('selection'),ry.get('selection')],iterations=[x.get('optimization_selected_iteration'),y.get('optimization_selected_iteration')]))
    value=dict(status='read_only_diagnosis',sources=refs,
        numerical_evidence=numerical,incomplete_executions=incomplete,
        execution_evidence=[dict(execution_id=r['execution_id'],source=r['source'],updates=len(r['observations']),
            complete_records=sum('complete_update_record' in o for o in r['observations']),
            capture_s=sum(o.get('complete_record_capture_s',0.)+o.get('complete_update_record',{}).get('record_capture_s',0.)+o.get('snapshot_capture_wall_s',0.) for o in r['observations'])) for r in records],
        first_action_divergence=comparison[0] if comparison else None,action_divergences=comparison,
        unique_cause='unresolved; equality and differences are recorded, no causal rule imposed')
    ref=save(host,value,'diagnosis')
    update(host,diagnostic_facts=[*state(host).get('diagnostic_facts',[]),dict(reference=ref,
        status=value['status'],first_action_divergence=value['first_action_divergence'],
        numerical_evidence=numerical,incomplete_executions=incomplete,
        unique_cause=value['unique_cause'],execution_evidence=[{k:r[k] for k in ('execution_id','updates','complete_records','capture_s')} for r in value['execution_evidence']])])
    return dict(reference=ref,**value)


def local_diagnostic(host, query, key):
    guard(host,True)
    from tools.research.contracts import LocalDiagnostic
    from tools.research.numerics import execution_update
    q=LocalDiagnostic.model_validate(query); s=state(host); b=s['spec']['budgets']
    source=execution_update(host,q.execution,q.update_id);record=source['record']
    imported=source.get('imported_historical_evidence',False)
    if not record: raise ValueError('ACTUAL_COMPLETE_UPDATE_INPUT_REQUIRED')
    seconds=s['spec'].get('standalone_watchdog_s',300.); reserve=q.repetitions*seconds
    solves=q.repetitions; protection=repetition_reserve(s)*allowance(s)
    downstream=s['spec'].get('downstream_reserve',{})
    if downstream:
        protection=max(protection,downstream['passing_executions']*allowance(s))
        protection+=max(0,downstream['fixed_verifications']-s.get('fixed_validation_jobs',0))*s['spec']['mechanics_allowances']['replay_s']
        protection+=b.get('delivery_numerical_s',0.)
    if (s['local_solves']+solves>b['local_solves'] or s['local_solve_s']+reserve>b['local_solve_s'] or
        s['numerical_s']+s['numerical_reserved_s']+reserve+protection>b['numerical_s'] or
        time.time()+reserve+protection>=s['cutoff_unix']):
        raise ValueError('LOCAL_DIAGNOSTIC_AND_CONFIRMATION_RESERVE_CANNOT_FIT')
    rows=[]
    for index in range(q.repetitions):
        request_id=key+'-local-'+str(index)
        request=dict(configuration=source['configuration'],record=record,mode=q.mode,
            current_recipe=s['profile']['recipe'],external_timeout_s=seconds,
            numerical_environment=dict(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1'))
        old=host.store.lookup(host.run_id,request_id)
        if old:
            if old['request_hash']!=digest(request): raise ValueError('DIAGNOSTIC_OPERATION_COLLISION')
            if not old['receipt']: raise ValueError('UNKNOWN_LOCAL_SOLVE_RECONCILE_OUTPUT_NO_REPEAT')
            rows.append(host.store.artifact(json.loads(old['receipt'])['output'])); continue
        def charge(db):
            current=host.store.session(host.run_id,db)['state']
            count=1
            if current['local_solves']+count>b['local_solves']: raise ValueError('LOCAL_SOLVE_CEILING')
            current['local_solves']+=count;current['numerical_reserved_s']+=seconds
            host.store.update_state(db,host.run_id,current)
        row,_=host.store.reserve(host.run_id,request_id,digest(request),host.actor,{**zero(),'wall_s':seconds},kind='local_diagnostic',guard=charge)
        folder=host.store.root/'local_diagnostics'/row['execution_id'];folder.mkdir(parents=True,exist_ok=True)
        inp,out=folder/'input.json',folder/'output.json';atomic_json(inp,request)
        update(host,pending=dict(kind='local_diagnostic',worker_request_id=request_id,input=str(inp),output=str(out),
            reserved_s=seconds,source_execution=plain(q.execution),source_update_id=q.update_id,historical_input=imported,
            started_unix=time.time(),origin='engineering' if s['spec'].get('mode')=='engineering_numerical' or key.startswith('engineering') else 'model'))
        start=time.perf_counter();env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
        try:
            process=subprocess.run([str(s['spec']['runtime']['research_python']),'-m','tools.research.diagnostic',str(inp),str(out)],cwd=ROOT,
                env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=seconds)
            value=read(out) if out.exists() else dict(status='diagnostic_no_output',returncode=process.returncode)
        except subprocess.TimeoutExpired:
            value=dict(status='known_killed_waited_diagnostic_timeout',timeout_s=seconds)
        elapsed=time.perf_counter()-start
        value.update(execution_id=row['execution_id'],charged_numerical_s=elapsed,source_execution=plain(q.execution),
            implementation=s['freeze'],science_hashes=s['profile']['science_hashes'],
            original_request=save(host,request,'local_diagnostic_request'),
            historical_input=imported,owning_study=host.run_id,
            source_update_id=q.update_id,origin='engineering' if s['spec'].get('mode')=='engineering_numerical' or key.startswith('engineering') else 'model',
            charged_solve_attempts=1)
        with host.store.transaction() as db:
            current=host.store.session(host.run_id,db)['state']
            current['numerical_s']+=elapsed;current['local_solve_s']+=elapsed;current['numerical_reserved_s']-=seconds;current['pending']=None
            host.store.update_state(db,host.run_id,current)
            host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
                tool_id='research.core_local_solve',tool_version='1.0.0',execution_status='completed',charged=zero()),value,elapsed=elapsed,db=db)
        rows.append(value)
    difference=max(abs(a-b) for a,b in zip(rows[0]['first_input_n'],rows[1]['first_input_n'])) if len(rows)==2 and all('first_input_n' in r for r in rows) else None
    detail=dict(rows=rows,maximum_first_input_difference_n=difference,mode=q.mode,
        interpretation='Exact saved problem under declared iteration/convergence policy; local agreement does not establish episode repeatability or unique cause.')
    ref=save(host,detail,'local_diagnostic_comparison');update(host,diagnostics=[*state(host).get('diagnostics',[]),ref])
    return dict(reference=ref,**detail)


def claims(host):
    if state(host)['spec'].get('capabilities'):
        from tools.research.feedback import confirmation_progress
        s=state(host);progress=confirmation_progress(host)
        changed=bool(s.get('selected') and host.store.artifact(host.store.artifact(s['selected'])['candidate'])['configuration']['robot']!=s.get('nominal_configuration',{}).get('robot'))
        search_rows=[host.store.artifact(r) for r in s.get('search_results',[])]
        return dict(selected=s.get('selected'),model_selected_structure_search_evaluations=len({row['evidence']['analysis']['artifact_id'] for search in search_rows for row in search['result']['evaluated'] if row['evidence'].get('analysis') and host.store.artifact(row['evidence']['candidate'])['configuration']['robot']!=s.get('nominal_configuration',{}).get('robot')}),selected_structurally_new=changed,new_design_and_control_confirmed=bool(changed and progress['confirmed']),independent_confirmation_count=progress['required_total']-progress['remaining'],
            required_confirmations=progress['required_total'],confirmation_failures=progress['failures'],
            confirmation_progress=progress,limited_repeat_supported_acceptance=progress['confirmed'],task_passed=bool(s.get('selected') and __import__('tools.research.feedback',fromlist=['result_view']).result_view(host,s['selected'])['passed']),required_extra_confirmations=progress['required_total'],executed_extra_confirmations=progress['current_study_confirmations'],confirmation_status='not_required' if progress['required_total']==0 else 'passed' if progress['confirmed'] else 'pending',reproducibility_assessed=progress['confirmed'],
            parameter_improvement_attribution_permitted=False,
            interface_evaluations=sum(bool(host.store.artifact(r).get('independent_evaluation_executed')) for r in s.get('rl_evaluations',[])))


def packet(host):
    s=state(host)
    if s['spec'].get('capabilities'):
        from tools.research.feedback import result_view, eligibility, facts
        from tools.research.rl import packet as rl_packet
        return dict(decision_facts=facts(host),specification=s['spec'],scoped_context=s.get('scoped_context',[]),frozen_task=plain(s['base_configuration']['task']),reference_candidate=s['reference_candidate'],
            candidates=[r for r in s['candidates'].values() if host.store.artifact(r)['profile_identity']==s['profile']['identity']],results=[dict(reference=r,**result_view(host,r),confirmation=eligibility(host,r)) for r in [*s['results'],*s.get('rl_evaluations',[])]],
            analysis_results=[dict(reference=r,**{k:host.store.artifact(r).get(k) for k in ('status','candidate','operation','proxy_values','origin','charged_numerical_s','local_model_constraints','internal_calculations','score_semantics')}) for r in s.get('analysis_results',[])],
            search_results=s.get('search_results',[]),
            mathematical_accounting=dict(evaluations=s.get('mathematical_evaluations',0),costs=s.get('analysis_costs',[]),engineering_preflight_s=sum(c['numerical_s'] for c in s.get('analysis_costs',[]) if c['origin']=='engineering_preflight'),cumulative_costs_preserved=True),
            mechanics_results=[dict(reference=r,**{k:host.store.artifact(r).get(k) for k in ('status','operation','trajectory_reference','objective_definition','original_task_feasible','relaxed_nlp_feasible','original_task_gaps','trajectory_metrics','charged_numerical_s','checkpoint_reference')}) for r in s.get('mechanics_results',[])],
            handoffs=[dict(reference=r,**host.store.artifact(r)) for r in s.get('handoffs',[])],
            rl=rl_packet(host) if enabled(s['spec'],'rl') else None,
            nmpc_admission=[dict(candidate=r,**nmpc_timing(host,r),remaining_phase_admission=capacity(host,1,candidate=r)) for r in s['candidates'].values() if host.store.artifact(r)['profile_identity']==s['profile']['identity']] if s['spec'].get('nmpc_execution_cap_s') else None,
            resource_use=dict(shared_ledger=host.store.remaining(),numerical_s=s['numerical_s'],numerical_reserved_s=s['numerical_reserved_s'],remaining_numerical_s=s['spec']['budgets']['numerical_s']-s['numerical_s']-s['numerical_reserved_s'],charged_starts=s.get('charged_starts',0),shared_start_limit=s['spec'].get('shared_start_limit'),elapsed_s=max(0,s.get('closed_unix',time.time())-s['started_unix'])),
            claims=claims(host),research_status=s['research_status'])


def dispatch(host, value, request_id, origin='model'):
    """Native plan acceptance and internal batch use the same project Store."""
    if state(host)['spec'].get('mode') == 'engineering_numerical':origin='engineering'
    plan=Plan.model_validate(value)
    if state(host)['spec'].get('allowed_plan_actions') is not None and plan.action not in state(host)['spec']['allowed_plan_actions']:
        raise ValueError('Operation outside declared follow-up scope')
    capability={'execute':'nmpc','search':'search','mechanics':'mathematics','replay':'replay'}.get(plan.action)
    if capability and not enabled(state(host)['spec'],capability): raise ValueError('Undeclared capability: '+capability)
    old=host.store.lookup(host.run_id,request_id)
    if old:
        if old['request_hash']!=digest(plain(plan)): raise ValueError('OPERATION_ID_COLLISION')
        if old['receipt']:
            from tools.research.feedback import cached
            return cached(host.store.artifact(json.loads(old['receipt'])['output']))
        raise ValueError('RECOVER_EXISTING_OPERATION_NO_NEW_EXECUTION')
    admit_closeout(host,'research_plan',plain(plan))
    guard(host,plan.action in ('execute','search','mechanics','replay') or plan.diagnostic is not None)
    s=state(host)
    for r in plan.supporting_evidence: host.store.artifact(r)
    from tools.research.experience import disposition_bindings
    experience_bindings=disposition_bindings(host,plan.experience_disposition)
    if plan.action=='stop' and any(r not in [plain(v) for v in plan.supporting_evidence] for r in [*s['results'],*s.get('mechanics_results',[]),*s.get('rl_evaluations',[]),*s.get('analysis_results',[])]):
        raise ValueError('STOP_MUST_CITE_ALL_NEW_EXPERIMENT_RESULTS')
    if enabled(s['spec'],'rl') and plan.action=='stop' and s.get('rl_runs'):
        evaluations=s.get('rl_evaluations',[])
        if s['spec'].get('rl_evaluation_source') and not evaluations: raise ValueError('RL_STOP_REQUIRES_EVALUATION_AND_NEXT_STEP_DECISION')
        if not plan.next_step: raise ValueError('RL_STOP_REQUIRES_NEXT_STEP_DECISION')
        for entry in s['rl_runs'].values():
            summary_ref=entry.get('training_summary')
            if summary_ref not in s.get('rl_evidence_reads',[]) or summary_ref not in [plain(v) for v in plan.supporting_evidence]:
                raise ValueError('RL_STOP_REQUIRES_PUBLIC_TRAINING_SUMMARY_READ_AND_CITATION')
            summary=host.store.artifact(summary_ref)
            if summary.get('checkpoint') and summary['checkpoint']['policy_present'] and not any(host.store.artifact(r).get('run_id')==summary['run_id'] for r in evaluations):
                raise ValueError('RL_STOP_REQUIRES_USABLE_CHECKPOINT_EVALUATION')
        if any(r not in [plain(v) for v in plan.supporting_evidence] for r in evaluations): raise ValueError('RL_STOP_MUST_CITE_NEW_EVALUATION')
        if any(r not in s.get('rl_evidence_reads',[]) for r in evaluations): raise ValueError('RL_STOP_REQUIRES_PUBLIC_EXPLICIT_EVIDENCE_READ')
        if any(e.get('status',{}).get('worker_alive',True) for e in s['rl_runs'].values()): raise ValueError('RL_STOP_REQUIRES_TERMINAL_STATUS_QUERY')
    admission=dict(scope='selection without execution or numerical reservation') if plan.action=='select' else capacity(host,plan.search.max_evaluations if plan.search else 1,plan.action=='confirm',root_operation=True,candidate=plan.candidate)
    if plan.action=='execute' and s['spec'].get('nmpc_execution_cap_s'):
        timing=nmpc_timing(host,plan.candidate)
        if not timing['available']: raise ValueError(timing['reason'])
    if plan.action=='execute' and admission['admitted']<1: raise ValueError('CANDIDATE_PLUS_DECLARED_CONFIRMATIONS_CANNOT_FIT')
    row,_=host.store.reserve(host.run_id,request_id,digest(plain(plan)),host.actor,{**zero(),'tool_calls':1})
    ref=save(host,dict(origin=origin,request_id=request_id,original_plan=plain(plan),admission=admission,
        experience_read_bindings=experience_bindings),'original_research_plan')
    update(host,plans=[*state(host)['plans'],ref])
    try:
        if plan.action=='propose':
            if plan.mechanics_source:
                from tools.research.mechanics import handoff
                relation=handoff(host,plan.mechanics_source,plain(plan.parameters),dict(origin=origin,plan=ref))
                result=dict(candidate=relation['candidate'],handoff=relation)
            else: result=dict(candidate=construct(host,plan.parameters,dict(origin=origin,plan=ref)))
        elif plan.action=='execute': result=execute(host,plain(plan.candidate),request_id)
        elif plan.action=='search': result=run_search(host,plan.search,request_id)
        elif plan.action in ('mechanics','replay'):
            from tools.research.mechanics import dispatch as mechanics_dispatch
            result=mechanics_dispatch(host,'solve' if plan.action=='mechanics' else 'replay',
                plan.mechanics if plan.action=='mechanics' else plan.mechanics_source,request_id)
        elif plan.action=='diagnose':
            result=diagnose(host,[plain(r) for r in plan.supporting_evidence])
            if plan.diagnostic: result['local_comparison']=local_diagnostic(host,plan.diagnostic,request_id)
        elif plan.action in ('select','confirm'):
            from tools.research.feedback import eligibility, result_view, confirmation_progress
            choice=eligibility(host,plan.selected_execution,revise_selection=plan.revise_selection,selection=plan.action=='select')
            if not choice['eligible']: raise ValueError('; '.join(choice['reasons']))
            selected=result_view(host,plan.selected_execution)
            if plan.revise_selection:
                transition=dict(previous_selection=s['selected'],selected_execution=plain(plan.selected_execution),
                    previous_progress=confirmation_progress(host),solution_identity=selected['solution_identity'],
                    plan=ref,confirmation_reservation=choice['confirmation_reservation'])
                update(host,selection_history=[*s.get('selection_history',[]),transition],selected=plain(plan.selected_execution))
            else: update(host,selected=plain(plan.selected_execution))
            if plan.action=='select':
                update(host,selected_solution=save(host,dict(evaluation=plain(plan.selected_execution),solution_identity=selected['solution_identity'],candidate=selected['candidate'],configuration=host.store.artifact(selected['candidate'])['configuration']),'frozen_selected_solution'))
                result=dict(selected=True,task_passed=True,required_extra_confirmations=confirmation_count(s),executed_extra_confirmations=0,confirmation_status='not_required' if confirmation_count(s)==0 else 'pending',reproducibility_assessed=False)
                if confirmation_count(s)==0:
                    update(host,research_status='stopped',final_disposition=ref,closed_unix=time.time())
            elif selected['controller_route']=='rl':
                from tools.research.rl import confirm
                result=confirm(host,plan.selected_execution,request_id+'-rl-confirm')
            else:
                result=execute(host,selected['candidate'],request_id,role='confirmation',selected=plain(plan.selected_execution))
            if confirmation_progress(host)['confirmed']:
                update(host,research_status='stopped',final_disposition=ref,closed_unix=time.time())
        else:
            update(host,research_status='stopped',final_disposition=ref,closed_unix=time.time())
            result=dict(accepted_stop=True,claims=claims(host))
        output=dict(plan=ref,result=result,resource_use=packet(host)['resource_use'])
        host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_plan',tool_version='1.0.0',execution_status='completed',charged=zero()),output)
        return output
    except Exception as exc:
        failure=dict(error=type(exc).__name__,message=str(exc),pending=state(host)['pending'])
        if state(host)['pending']: save(host,failure,'pending_operation_failure')
        else:
            host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
                tool_id='research.core_plan',tool_version='1.0.0',execution_status='failed',error=str(exc),charged=zero()),failure)
        raise












def recover(host):
    if (state(host).get('pending') or {}).get('kind')=='candidate_analysis':
        from tools.research.analysis import recover as recover_analysis
        recover_analysis(host)  # Seal only existing output, then reconcile the owning workflow below.
    if (state(host).get('pending') or {}).get('kind') == 'local_diagnostic':
        from tools.research.diagnostic import recover_local
        return recover_local(host)
    from tools.research.agent import pending as provider_pending, received, settle
    for row in provider_pending(host):
        response=received(host,row['request_id'])
        if response: settle(host,row,response)
        else: raise ValueError('UNKNOWN_PROVIDER_SEND_INSPECT_BEFORE_REPEAT')
    p=state(host)['pending']
    if p and p.get('kind')=='mechanics':
        from tools.research.mechanics import recover as mechanics_recover
        recovered=mechanics_recover(host)
    else: recovered=finish_execution(host,recovery=True) if p else None
    s=state(host); completed=[]
    for ref in s['plans']:
        original=host.store.artifact(ref);key=original['request_id'];row=host.store.lookup(host.run_id,key)
        if not row or row['receipt']: continue
        plan=Plan.model_validate(original['original_plan'])
        if plan.action=='search':
            result=dict(status='search_execution_incomplete',saved_checkpoint=s['searches'].get(key),
                attempted_executions=[r for r in s['results'] if host.store.artifact(r)['operation_key'].startswith(key+':')],
                reason='Recovery packages existing evidence only; further proposals require a new model-requested search')
        elif plan.action in ('execute','confirm'):
            matches=[r for r in state(host)['results'] if host.store.artifact(r)['operation_key']==key]
            if len(matches)!=1: raise ValueError('RECOVERY_REQUIRES_UNIQUE_SEALED_RESULT_NO_NEW_LAUNCH')
            result=dict(reference=matches[0],**compact_result(host.store.artifact(matches[0])))
        elif plan.action in ('mechanics','replay'):
            result=recovered
            if not result:
                worker=host.store.lookup(host.run_id,key+'-mechanics')
                if not worker or not worker['receipt']: raise ValueError('RECOVER_MECHANICS_NO_SECOND_SOLVE')
                receipt=json.loads(worker['receipt']);value=host.store.artifact(receipt['output'])
                ref=next(r for r in state(host)['mechanics_results'] if host.store.artifact(r)['execution_id']==worker['execution_id'])
                result=dict(reference=ref,status=value['status'],recovered_without_repeating_completed_outputs=True)
        else: raise ValueError('INSPECT_UNSEALED_NONEXECUTION_OPERATION')
        output=dict(plan=ref,result=result,resource_use=packet(host)['resource_use'],recovered_without_repeating_completed_outputs=True)
        host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
            tool_id='research.core_plan',tool_version='1.0.0',execution_status='completed',charged=zero()),output)
        completed.append(key)
    return dict(execution=recovered,sealed_workflows=completed,provider_outcomes='known')


def export(host, destination=None):
    out=Path(destination or ROOT/state(host)['spec']['evidence_destination']); out.mkdir(parents=True,exist_ok=True)
    members=[]
    with host.store.connect(True) as db, tarfile.open(out/'immutable_artifacts.tar.gz','w:gz') as archive:
        for row in db.execute('SELECT id,media,body FROM artifacts ORDER BY id'):
            name='artifacts/'+row['id']+('.json' if row['media']=='application/json' else '.bin')
            info=tarfile.TarInfo(name); info.size=len(row['body']); archive.addfile(info,io.BytesIO(row['body']))
            members.append(dict(name=name,sha256=row['id'],bytes=info.size,media=row['media']))
        calls=[dict(r) for r in db.execute('SELECT * FROM calls ORDER BY rowid')]
    current=packet(host)
    for name,value in [('state',state(host)),('events',host.store.events(host.run_id)),('calls',calls),('final_packet',current),('ledger',host.store.remaining())]:
        atomic_json(out/(name+'.json'),value)
    atomic_json(out/'archive_manifest.json',dict(members=members,archive_sha256=hashlib.sha256((out/'immutable_artifacts.tar.gz').read_bytes()).hexdigest()))
    return dict(destination=str(out),results=len(state(host)['results']),claims=claims(host),resources=current['resource_use'])





