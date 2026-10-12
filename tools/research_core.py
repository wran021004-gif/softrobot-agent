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
from schemas.research_core import Parameters, Search, Plan, ExperienceQuery, EvidenceQuery
from tools.platform_host import Host
from tools.platform_store import plain, zero
from tools.state_io import atomic_json, read, digest

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = ROOT/'examples/research_core/specification.json'
PYTHON = Path('D:/softrobot-agent/.mainline5-env/Scripts/python.exe')
SCIENCE_FILES = ['extensions/tendon_family/gvs_nmpc.py', 'extensions/tendon_family/gvs_trajectory.py',
    'extensions/tendon_family/gvs_projection.py','extensions/tendon_family/contracts.py',
    'extensions/optimization/contracts.py','schemas/casadi_feedback.py',
    'extensions/tendon_family/backends.py',
    'extensions/optimization/ipopt.py', 'extensions/tendon_family/generated_serial.py',
    'extensions/tendon_family/gvs_profile.py', 'tools/design_optimization.py',
    'tools/execution_completion.py', 'tools/research_tasks.py',
    'extensions/tendon_family/gvs_codesign.py', 'extensions/tendon_family/gvs_casadi.py',
    'extensions/tendon_family/gvs.py', 'extensions/tendon_family/gvs_basis.py',
    'tools/casadi_feedback_worker.py', 'tools/casadi_codesign_worker.py',
    'tools/research_core_mechanics.py', 'tools/research_core_mechanics_worker.py']
CORE_FILES = ['tools/research_core.py','tools/research_core_diagnostic.py','schemas/research_core.py',
              'tools/research_core_feedback.py','tools/research_core_demo.py','tools/research_core_numerics.py','tools/numerical_repair.py']


def save(host, value, kind='core_evidence'):
    with host.store.transaction() as db:
        ref = host.store.put(db, value)
        host.store.event(db, host.run_id, kind, 'saved', outputs=[ref])
        return plain(ref)


def state(host):
    return host.store.session(host.run_id)['state']


def update(host, **values):
    with host.store.transaction() as db:
        s = host.store.session(host.run_id, db)['state']; s.update(values)
        host.store.update_state(db, host.run_id, s)


def science_hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in SCIENCE_FILES}


def core_hashes():
    return {name: hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in CORE_FILES}


def full_science(cfg):
    return dict(robot=deepcopy(cfg['robot']), task=deepcopy(cfg['task']), seed=cfg['seed'],
        policy={k:deepcopy(cfg['policy'][k]) for k in ('controller','backend','dynamics_model','discretization','candidate_builder')})


def limits(spec):
    b = spec['budgets']
    return dict(model_calls=b['provider_requests'], tool_calls=b['public_operations'],
        backend_solves=b['physical_launches'], worker_calls=0, wall_s=b['activity_s'])


def prepare(spec_path=DEFAULT_SPEC, directory=None):
    spec = read(spec_path); run_id = spec['study_id']
    if spec.get('mode') == 'engineering_numerical' and (spec['budgets']['provider_requests'] != 0 or spec['budgets']['protected_provider_requests'] != 0):
        raise ValueError('NUMERICAL_MODE_REQUIRES_ZERO_MODEL_REQUESTS')
    directory = Path(directory or ROOT/'runs'/run_id)
    h = Host(directory, run_id, actor='unified-research')
    if h.store.db.exists():
        if state(h)['spec'] != spec: raise ValueError('STUDY_SPEC_CHANGED_USE_EXPLICIT_MIGRATION')
        return h
    start = time.perf_counter()
    from tools.nmpc_settling import baseline_configuration
    from tools.research_v2 import native_configuration
    cfg = baseline_configuration(); cfg['run_id'] = run_id
    # Recovery-enabled source is complete immutable execution evidence.
    cfg['policy']['controller']['parameters']['data']['recipe'].update({k:v for k,v in spec['reference_parameters'].items() if k != 'd'})
    cfg['policy']['controller']['parameters']['data']['recipe'].update(spec.get('controller_recipe',{}))
    model = native_configuration(run_id)['policy']['model']
    cfg['policy'].update(model=model, budget=limits(spec), allowed_tools=['evidence.read'],
        tool_bindings={'evidence.read':'1.0.0'}, operation_allowances={'evidence.read':dict(timeout_s=30.,reserve_s=30.)})
    h.store.create(ProjectConfig(project_id=run_id, grant_id=run_id+'-authorized',
        authorization_source=spec['authorization'], budget=limits(spec),
        exclusive_resources={'provider_request':1,'backend.family_mujoco':1}))
    h.create(cfg); h.resume()
    recipe = deepcopy(cfg['policy']['controller']['parameters']['data']['recipe'])
    profile = dict(adapter='unified_recovery_profile_v1',version=spec['evaluation_version'],
        configuration=full_science(cfg), recipe=recipe, science_hashes=science_hashes(),
        recording=dict(complete_update_inputs=spec['complete_update_inputs'],update_ids=spec['record_update_ids']),
        acceptance='unchanged joint sampled reach/hold; inclusive .30-.35s; .01m/.02m/s',
        confirmation=spec['confirmation'])
    profile['identity'] = digest(profile)
    update(h, spec=spec, base_configuration=cfg, profile=profile, profile_history=[profile],
        started_unix=spec['started_unix'], cutoff_unix=spec['started_unix']+spec['budgets']['activity_s']-spec['budgets']['delivery_reserve_s'],
        numerical_s=0., numerical_reserved_s=0., local_solves=0, local_solve_s=0.,
        results=[], candidates={}, plans=[], retrievals=[], searches={}, pending=None,
        offline_nlp=0, bdf_replays=0, mechanics_results=[], handoffs=[], historical_diagnostic_sources=[],
        research_status='ready', selected=None,
        pilot=dict(provider=model,live_model_requests=0,framework_session_id=run_id,
            request_deadline_unix=spec['started_unix']+spec['budgets']['activity_s']-spec['budgets']['delivery_reserve_s']))
    # Compact supplied history is explicitly different from retrieval.
    history = read(ROOT/'evidence/nmpc_settling_20261011/scientific_summary.json')
    ref = save(h, history, 'supplied_historical_context')
    update(h, historical_context=ref)
    latest=read(ROOT/'evidence/research_core_20261011/scientific_summary.json')
    update(h, supplied_core_history=save(h,latest,'supplied_sealed_core_history'))
    candidate = construct(h, spec['reference_parameters'], dict(origin='initial_controller_reference', historical_result_ownership='sealed source activity'))
    update(h, reference_candidate=candidate, numerical_s=time.perf_counter()-start)
    atomic_json(directory/'activity.json',spec)
    return h


def configuration_for(host, parameters, owner):
    from tools.design_optimization import resolved_input
    from schemas.design_optimization import DesignOptimizationProblem
    s = state(host); p = Parameters.model_validate(parameters); base = s['base_configuration']
    problem = DesignOptimizationProblem.model_validate(read(ROOT/'examples/casadi_codesign/case_A.json')['physical_source'])
    data = plain(problem); data['task'] = deepcopy(base['task'])
    data['execution']['recipe'] = deepcopy(s['profile']['recipe'])
    data['execution']['settling'] = deepcopy(base['policy']['controller']['parameters']['data']['settling'])
    problem = DesignOptimizationProblem.model_validate(data)
    fixed = deepcopy(base['robot']['structure']['data']['metadata']['recipe'])
    fixed.update(lengths_m=[.16+.0055*p.d,.11-.0055*p.d],
        holding_tip_speed_weight=p.holding_tip_speed_weight,terminal_tip_speed_weight=p.terminal_tip_speed_weight)
    cfg = resolved_input(problem, fixed, owner, deepcopy(base['policy']))
    # Freeze every binding not regenerated by the declared length coordinate.
    for k in ('backend','dynamics_model'): cfg['policy'][k] = deepcopy(base['policy'][k])
    return cfg, fixed


def construct(host, parameters, provenance):
    s = state(host); p = plain(Parameters.model_validate(parameters))
    cfg, resolved = configuration_for(host,p,host.run_id)
    scientific = full_science(cfg)
    identity = digest(dict(parameters=resolved, configuration=scientific, evaluation_profile=s['profile']))
    old = s['candidates'].get(identity)
    if old:
        save(host,dict(candidate=old,provenance=provenance,immutable_candidate_reused=True,
            additional_scientific_executions=0),'candidate_construction_relation')
        return old
    candidate = dict(candidate_id='core-'+identity,identity=identity, parameters=p,
        resolved_parameters=resolved, configuration=cfg, scientific_configuration=scientific,
        profile_identity=s['profile']['identity'], evaluation_version=s['profile']['version'],
        provenance=provenance,offline_trajectory=None)
    ref = save(host,candidate,'candidate_constructed')
    candidates = state(host)['candidates']; candidates[identity] = ref; update(host,candidates=candidates)
    return ref


def verify_candidate(host, reference):
    s = state(host); c = host.store.artifact(reference)
    if s['candidates'].get(c.get('identity')) != plain(reference): raise ValueError('OWNED_RESOLVED_CANDIDATE_REQUIRED')
    if c['profile_identity'] != s['profile']['identity']: raise ValueError('OLD_EVALUATION_PROFILE_CANDIDATE_REQUIRES_NEW_CONSTRUCTION')
    cfg, values = configuration_for(host,c['parameters'],host.run_id)
    if values != c['resolved_parameters'] or full_science(cfg) != c['scientific_configuration']:
        raise ValueError('FULL_FIXED_AND_SEARCH_PARAMETER_IDENTITY_MISMATCH')
    expected = digest(dict(parameters=values,configuration=full_science(cfg),evaluation_profile=s['profile']))
    if expected != c['identity']: raise ValueError('CANDIDATE_IDENTITY_MISMATCH')
    return c


def allowance(s):
    return sum(s['spec']['execution_allowances'].values())


def repetition_reserve(s):
    return s['spec'].get('diagnostic_protocol', {}).get('repetition_launch_reserve', 1) if s['spec'].get('mode') == 'engineering_numerical' else 2


def capacity(host, requested=1, confirmation=False, *, root_operation=False):
    """Admit all internal launches, with two full confirmation slots and time."""
    s=state(host); b=s['spec']['budgets']; a=allowance(s)
    remaining=host.store.remaining()['remaining']; protect=0 if confirmation else repetition_reserve(s)
    science=b['numerical_s']-s['numerical_s']-s['numerical_reserved_s']
    available_time=min(science, s['cutoff_unix']-time.time(), remaining['wall_s'])
    fit=max(0,min(requested,int(remaining['backend_solves'])-protect,math.floor(available_time/a)-protect,
        (int(remaining['tool_calls'])-4*protect-int(root_operation))//3))
    return dict(requested=requested, admitted=fit, internal_launches=fit, numerical_reservation_s=fit*a,
        confirmation_launch_reserve=protect, confirmation_time_reserve_s=protect*a,
        remaining_numerical_s=science, per_execution_s=a)


def guard(host, expensive=False):
    s=state(host)
    if s['research_status']=='stopped': raise ValueError('ACCEPTED_STOP_SEALED')
    if s['pending']: raise ValueError('PENDING_EXECUTION_RECOVER_WITHOUT_NEW_LAUNCH')
    if 'freeze' not in s: raise ValueError('COMMIT_AND_BIND_BEFORE_RESEARCH')
    if science_hashes()!=s['profile']['science_hashes'] or core_hashes()!=s.get('core_hashes') or not host.compatibility()['compatible']:
        raise ValueError('DEPENDENCIES_CHANGED_COMMIT_AND_MIGRATE_WITHOUT_RESETTING_COSTS')
    if time.time()>=s['cutoff_unix']: raise ValueError('PROTECTED_DELIVERY_WINDOW')
    if s['spec'].get('mode') == 'engineering_numerical':
        if host.store.remaining()['used']['model_calls'] or s['pilot']['live_model_requests']:
            raise ValueError('NUMERICAL_MODE_MODEL_REQUEST_VIOLATION')
    elif expensive and host.store.remaining()['remaining']['model_calls']<=s['spec']['budgets']['protected_provider_requests']:
        raise ValueError('LAST_FOUR_PROVIDER_REQUESTS_PROTECTED')


def bind(host, reason=None):
    from tools.platform_tasks import compile_input
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise ValueError('COMMIT_BEFORE_BIND_OR_MIGRATION')
    s=state(host)
    if s['pending']: raise ValueError('PENDING_OUTCOME_BLOCKS_MIGRATION')
    with host.store.connect(True) as db:
        if db.execute('SELECT COUNT(*) FROM calls WHERE receipt IS NULL').fetchone()[0]:
            raise ValueError('UNSEALED_RESERVATION_BLOCKS_BIND')
    old=host.store.session(host.run_id)['snapshot']; snapshot=compile_input(old['input'],host.reg)
    commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    profile=deepcopy(s['profile'])
    science_prefixes=('backend.','candidate.','controller.','evaluate.','initialize.','model.','solver.','task.')
    changed_dependencies=[name for name,value in snapshot['dependencies'].items()
        if name.startswith(science_prefixes) and old['dependencies'].get(name)!=value]
    changed=science_hashes()!=profile['science_hashes'] or bool(changed_dependencies)
    if 'freeze' in s and not reason: raise ValueError('MIGRATION_REASON_REQUIRED')
    if changed:
        profile.pop('identity'); profile['version']+=1; profile['science_hashes']=science_hashes()
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


def execute(host, candidate_ref, operation_key, *, role='development', selected=None):
    construction_started=time.perf_counter()
    guard(host,expensive=True); s=state(host); c=verify_candidate(host,candidate_ref)
    confirmation=role=='confirmation'
    repetition=role=='diagnostic_repetition'
    if repetition:
        if s['spec'].get('mode') != 'engineering_numerical' or plain(selected) not in s['results']:
            raise ValueError('OWNED_DIAGNOSTIC_REPETITION_REQUIRED')
        old=host.store.artifact(selected)
        if old['candidate'] != plain(candidate_ref) or old['profile_identity'] != s['profile']['identity']:
            raise ValueError('REPETITION_REQUIRES_IDENTICAL_CONFIGURATION')
    if confirmation:
        old=host.store.artifact(selected)
        if old['candidate']!=plain(candidate_ref) or old['profile_identity']!=s['profile']['identity'] or old['scientific_configuration']!=c['scientific_configuration']:
            raise ValueError('CONFIRMATION_REQUIRES_SELECTED_COMPLETE_PARAMETERS_AND_EVALUATION_CONFIGURATION')
        if not old.get('acceptance',{}).get('accepted'): raise ValueError('SELECTED_PASSING_EXECUTION_REQUIRED')
        if sum(host.store.artifact(r)['role']=='confirmation' and host.store.artifact(r).get('selected_execution')==plain(selected) for r in s['results'])>=2:
            raise ValueError('TWO_POST_SELECTION_CONFIRMATIONS_ALREADY_RECORDED')
    admission=capacity(host,1,confirmation or repetition)
    if admission['admitted']<1: raise ValueError('EXECUTION_AND_CONFIRMATION_RESERVE_CANNOT_FIT')
    # A unique execution owner is persisted before starting any backend.
    owner=host.run_id+'-exec-'+uuid4().hex[:16]
    cfg=deepcopy(c['configuration']); cfg['run_id']=owner
    from tools.execution_completion import EXECUTION_ALLOWANCES
    cfg['policy'].update(budget={**cfg['policy']['budget'],'model_calls':0},allowed_tools=[],
        tool_bindings={n:'1.0.0' for n in ('simulation.run','evaluation.run','control.profile_report')},
        operation_allowances=deepcopy(EXECUTION_ALLOWANCES))
    simulation_allowance=s['spec']['execution_allowances']['simulation_s']
    cfg['policy']['operation_allowances']['simulation.run']=dict(timeout_s=simulation_allowance,reserve_s=simulation_allowance)
    if full_science(cfg)!=c['scientific_configuration']: raise ValueError('EXECUTION_CHANGED_FROZEN_SCIENCE')
    pending=dict(owner=owner,candidate=plain(candidate_ref),configuration=cfg,role=role,
        selected_execution=plain(selected),operation_key=operation_key,started_unix=time.time(),
        profile_identity=s['profile']['identity'],admission=admission)
    update(host,pending=pending,numerical_reserved_s=allowance(s))
    child=Host(host.store.root,owner,actor=host.actor); child.create(cfg,parent_run_id=host.run_id)
    pending['construction_s']=time.perf_counter()-construction_started
    update(host,pending=pending)
    return finish_execution(host)


def finish_execution(host, recovery=False):
    """Only sealed receipts continue. Reporting failure cannot trigger simulation."""
    from tools.execution_completion import complete_execution
    from tools.research_tasks import assemble_acceptance
    from extensions.tendon_family.control_evidence import RECORD_UPDATE_IDS, COMPLETE_UPDATE_INPUTS
    s=state(host); p=s['pending']
    if not p: raise ValueError('NO_PENDING_EXECUTION')
    child=Host(host.store.root,p['owner'],actor=host.actor)
    if recovery and child.store.lookup(p['owner'],'complete-simulation') is None:
        raise ValueError('RECOVERY_HAS_NO_LAUNCH_RECEIPT_INSPECT_BEFORE_START')
    c=host.store.artifact(p['candidate']); started=time.perf_counter()
    prior_wall=sum(json.loads(row['receipt'])['charged']['wall_s'] for stage in ('simulation','evaluation','profile')
        if (row:=child.store.lookup(p['owner'],'complete-'+stage)) and row['receipt'])
    trace=RECORD_UPDATE_IDS.set(tuple(s['profile']['recording']['update_ids']))
    capture=COMPLETE_UPDATE_INPUTS.set(s['profile']['recording']['complete_update_inputs'])
    try: result=complete_execution(child,p['configuration'],c['candidate_id'])
    finally: RECORD_UPDATE_IDS.reset(trace); COMPLETE_UPDATE_INPUTS.reset(capture)
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
    stage_wall=sum(r['charged']['wall_s'] for r in receipts.values())
    actual=stage_wall+max(0.,time.perf_counter()-started-(stage_wall-prior_wall))+p.get('construction_s',0.)
    detail=dict(status=result['status'],role=p['role'],candidate=p['candidate'],candidate_id=c['candidate_id'],
        scientific_identity=c['identity'],scientific_configuration=c['scientific_configuration'],profile_identity=p['profile_identity'],
        evaluation_version=c['evaluation_version'],selected_execution=p['selected_execution'],
        acceptance=acceptance,profile=profile,execution=result,numerical_s=actual,
        execution_id=result.get('execution_id') or receipts.get('simulation',{}).get('execution_id'),
        owner_run_id=p['owner'],operation_key=p['operation_key'],
        owning_study=host.run_id, fresh_execution=True, cached_operation_receipt=False,
        candidate_artifact_reuse_does_not_reuse_execution=True,
        facts_classification='program-generated; principal interpretation remains in original plan',
        failure_categories=[] if acceptance and acceptance['accepted'] else
            ['scientific_task_failure'] if acceptance else ['engineering_or_missing_evidence'])
    from tools.research_core_feedback import mechanics_context
    detail['mechanics_context']=mechanics_context(host,p['candidate'])
    ref=save(host,detail,'experiment_result'); s=state(host)
    update(host,results=[*s['results'],ref],pending=None,numerical_reserved_s=0.,numerical_s=s['numerical_s']+actual)
    from tools.research_core_feedback import eligibility
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


def search_problem(host, search, admitted):
    from schemas.design_optimization import DesignOptimizationProblem
    s=state(host); base=s['base_configuration']; q=Search.model_validate(search)
    p=read(ROOT/'examples/casadi_codesign/case_A.json')['physical_source']
    p['study_id']=host.run_id; p['task']=deepcopy(base['task'])
    p['execution']['recipe']=deepcopy(s['profile']['recipe'])
    p['execution']['settling']=deepcopy(base['policy']['controller']['parameters']['data']['settling'])
    fixed=deepcopy(base['robot']['structure']['data']['metadata']['recipe'])
    fixed.pop('lengths_m'); fixed.pop('family',None); fixed.update({k:v for k,v in plain(q.fixed).items() if k!='d'})
    p['variables']={k:dict(kind='fixed',value=v) for k,v in fixed.items()}
    for k in q.variables:
        if k!='d': p['variables'][k]=dict(kind='continuous',bounds=list(q.bounds[k]),initial=getattr(q.fixed,k))
    free='d' in q.variables
    # The public +/-5% bound refers to the physical nominal design, not the
    # optimizer's chosen initial point. Use the closest nominal feasible point
    # for allocation validation; pass the requested initialization separately.
    baseline_d=min(max(0.,q.bounds['d'][0]),q.bounds['d'][1]) if free else q.fixed.d
    lengths=[.16+.0055*baseline_d,.11-.0055*baseline_d]
    bounds=[[.16+.0055*q.bounds['d'][0],.16+.0055*q.bounds['d'][1]],
        [.11-.0055*q.bounds['d'][1],.11-.0055*q.bounds['d'][0]]] if free else [[v,v] for v in lengths]
    p['lengths']=dict(free=free,total_flexible_length_m=.27,baseline_by_count={'2':lengths},bounds_by_count={'2':bounds})
    p['fixed_tendon_count']=6; p['fixed_actuator_count']=6
    p['budget']=dict(max_evaluations=admitted,wall_s=admitted*allowance(s))
    p['objective']=dict(ranking=q.ranking,accepted_resource_preference='none')
    p['method']=dict(name='hierarchical_coordinate_v1_1',step=q.step,initial_structures=[],stop_on_acceptance=False)
    return DesignOptimizationProblem.model_validate(p)


def run_search(host, query, key):
    from tools.design_optimization import solve, continuous_space, structures
    guard(host,True); q=Search.model_validate(query); admission=capacity(host,q.max_evaluations)
    if q.mechanics_source:
        from tools.research_core_mechanics import handoff
        if 'd' in q.variables: raise ValueError('MECHANICS_CONTROL_SEARCH_REQUIRES_FIXED_STRUCTURE')
        handoff(host,q.mechanics_source,plain(q.fixed),dict(operation_key=key,origin='control_search'))
    if not admission['admitted']: return dict(status='budget_limited',admission=admission,evaluated=[])
    problem=search_problem(host,q,admission['admitted']); s=state(host)
    if s['searches'].get(key):
        from schemas.design_optimization import DesignOptimizationProblem
        problem=DesignOptimizationProblem.model_validate(s['searches'][key]['problem'])
    def evaluator(problem,values,proposal_id):
        if capacity(host,1)['admitted']<1: return dict(status='shared_budget_exhausted',evidence={})
        params=dict(d=(values['lengths_m'][0]-.16)/.0055,**{k:values[k] for k in ('holding_tip_speed_weight','terminal_tip_speed_weight')})
        ref=construct(host,params,dict(origin='mathematical_search',plan_key=key,proposal_id=proposal_id))
        if q.mechanics_source:
            handoff(host,q.mechanics_source,params,dict(operation_key=key,proposal_id=proposal_id))
        c=verify_candidate(host,ref)
        completed=[host.store.artifact(r) for r in state(host)['results']]
        old=next((r for r in completed if r['operation_key']==key+':'+proposal_id),None)
        if old is None:
            feedback=execute(host,ref,key+':'+proposal_id,role='search')
            if feedback['status']!='evaluated': return dict(status=feedback['status'],evidence=feedback)
            old=host.store.artifact(feedback['reference'])
        execution_ref=next(r for r in state(host)['results'] if host.store.artifact(r)['operation_key']==key+':'+proposal_id)
        return dict(status=old['status'],acceptance=old['acceptance'],evidence=dict(result=execution_ref,execution_id=old['execution_id']),
            configuration=c['configuration'],candidate_id=c['candidate_id'],scientific_identity=c['identity'])
    def checkpoint(value):
        searches=state(host)['searches']; searches[key]=deepcopy(value); update(host,searches=searches)
        return save(host,value,'search_checkpoint')
    initial_latents=None
    if 'd' in q.variables:
        structure=structures(problem)[0];allocation,latent=continuous_space(problem,structure)
        latent.update(allocation.encode([.16+.0055*q.fixed.d,.11-.0055*q.fixed.d]))
        initial_latents={digest(structure):latent}
    result=plain(solve(problem,evaluator=evaluator,state=s['searches'].get(key),save_state=checkpoint,
        evaluation_profile=s['profile'],initial_latents=initial_latents))
    explored={k:sorted({r['resolved']['parameters'][k] for r in result['evaluated']}) for k in q.variables if k!='d'}
    if 'd' in q.variables: explored['d']=sorted({(r['resolved']['parameters']['lengths_m'][0]-.16)/.0055 for r in result['evaluated']})
    attempted=[dict(reference=r,parameters=host.store.artifact(host.store.artifact(r)['candidate'])['parameters'],
        **compact_result(host.store.artifact(r))) for r in state(host)['results']
        if host.store.artifact(r)['operation_key'].startswith(key+':')]
    return dict(result=result,admission=admission,actually_explored=explored,attempted_executions=attempted,
        failed_or_incomplete_executions=[r['reference'] for r in attempted if r['status']!='evaluated' or not (r['acceptance'] or {}).get('accepted')],
        requested_variables=q.variables, fixed_parameters=plain(q.fixed), mechanics_source=plain(q.mechanics_source),
        distinct_configurations=len({r['scientific_identity'] for r in result['evaluated']}),
        not_explored=[k for k,v in explored.items() if len(v)<2],
        batch_shrunk=admission['admitted']<q.max_evaluations)


def experience(host, query):
    q=ExperienceQuery.model_validate(query)
    paths={'case':'memory/nmpc_feasibility_case_draft.json','procedure':'docs/nmpc_feasibility_procedure.md'}
    metadata=dict(task='reach_and_hold',structure='two_segments_six_tendons',failure_type='numerical_feasibility',version='draft')
    matches=all(getattr(q,k) is None or getattr(q,k)==v for k,v in metadata.items())
    rows=[]
    for k,name in paths.items():
        if not matches or q.key is not None and k!=q.key: continue
        raw=(ROOT/name).read_text(encoding='utf8')
        original=read(ROOT/name) if name.endswith('.json') else raw
        refs=[]
        def walk(v):
            if isinstance(v,dict):
                if 'artifact_id' in v: refs.append(v)
                for child in v.values(): walk(child)
            elif isinstance(v,list):
                for child in v: walk(child)
        walk(original)
        rows.append(dict(key=k,path=name,**metadata,status='reference_backed_draft',
            applicability='recommendation only; historical controller/evaluation scope requires checking',
            metadata_origin='small curated index; source lacks uniform lifecycle metadata',
            original_evidence_references=refs,missing_metadata=['formal_skill_admission','uniform_evaluation_version'],
            **(dict(content=original) if q.operation=='read' else {})))
    record=dict(query=plain(q),results=rows,supplied_startup_context=False)
    ref=save(host,record,'actual_experience_retrieval'); update(host,retrievals=[*state(host)['retrievals'],ref])
    return dict(reference=ref,**record)


def diagnose(host, refs):
    from extensions.tendon_family.control_evidence import ControlEvidence
    s=state(host); reader=ControlEvidence(host.store); records=[]; numerical=[]; incomplete=[]
    for ref in refs:
        r=host.store.artifact(ref)
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
    from schemas.research_core import LocalDiagnostic
    from extensions.tendon_family.control_evidence import ControlEvidence
    q=LocalDiagnostic.model_validate(query); s=state(host); b=s['spec']['budgets']
    imported=plain(q.execution) in s.get('historical_diagnostic_sources',[])
    if imported:
        source=host.store.artifact(q.execution);record=source['record']
        if record['update_id']!=q.update_id: raise ValueError('IMPORTED_DIAGNOSTIC_UPDATE_MISMATCH')
    else:
        if plain(q.execution) not in s['results']: raise ValueError('OWNED_CURRENT_EXECUTION_REQUIRED')
        result=host.store.artifact(q.execution)
        if result['profile_identity']!=s['profile']['identity']: raise ValueError('DIAGNOSTIC_PROFILE_MISMATCH')
        reader=ControlEvidence(host.store); source=reader.resolve(result['execution_id'])
        observations=reader.read_file(source,'controller_observations.json',[])
        record=deepcopy(observations[q.update_id].get('complete_update_record'))
        if record and record.get('resolved_problem_reference'):
            definition=record['resolved_problem_reference'];body=host.store.artifact(source['files'][definition['filename']],raw=True)
            if hashlib.sha256(body).hexdigest()!=definition['sha256']:raise ValueError('RESOLVED_PROBLEM_DEFINITION_HASH_MISMATCH')
            record['resolved_problem']=json.loads(body)
            if digest(record['resolved_problem']['objective_function'])!=record['model_identity']:
                raise ValueError('RESOLVED_PROBLEM_EXPRESSION_IDENTITY_MISMATCH')
    if not record: raise ValueError('ACTUAL_COMPLETE_UPDATE_INPUT_REQUIRED')
    seconds=150.*(1+int(q.reuse_solver)); reserve=q.repetitions*seconds
    solves=q.repetitions*(1+int(q.reuse_solver)); protection=repetition_reserve(s)*allowance(s)
    if (s['local_solves']+solves>b['local_solves'] or s['local_solve_s']+reserve>b['local_solve_s'] or
        s['numerical_s']+s['numerical_reserved_s']+reserve+protection>b['numerical_s'] or
        time.time()+reserve+protection>=s['cutoff_unix']):
        raise ValueError('LOCAL_DIAGNOSTIC_AND_CONFIRMATION_RESERVE_CANNOT_FIT')
    rows=[]
    for index in range(q.repetitions):
        request_id=key+'-local-'+str(index)
        request=dict(configuration=source['configuration'],record=record,mode=q.mode,iteration_cap=q.iteration_cap,
            reuse_solver=q.reuse_solver,prepare_tail=q.prepare_tail)
        old=host.store.lookup(host.run_id,request_id)
        if old:
            if old['request_hash']!=digest(request): raise ValueError('DIAGNOSTIC_OPERATION_COLLISION')
            if not old['receipt']: raise ValueError('UNKNOWN_LOCAL_SOLVE_RECONCILE_OUTPUT_NO_REPEAT')
            rows.append(host.store.artifact(json.loads(old['receipt'])['output'])); continue
        def charge(db):
            current=host.store.session(host.run_id,db)['state']
            count=1+int(q.reuse_solver)
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
            process=subprocess.run([str(PYTHON),'-m','tools.research_core_diagnostic',str(inp),str(out)],cwd=ROOT,
                env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=seconds)
            value=read(out) if out.exists() else dict(status='diagnostic_no_output',returncode=process.returncode)
        except subprocess.TimeoutExpired:
            value=dict(status='known_killed_waited_diagnostic_timeout',timeout_s=seconds)
        elapsed=time.perf_counter()-start
        value.update(execution_id=row['execution_id'],charged_numerical_s=elapsed,source_execution=plain(q.execution),
            historical_input=imported,owning_study=host.run_id,
            source_update_id=q.update_id,origin='engineering' if s['spec'].get('mode')=='engineering_numerical' or key.startswith('engineering') else 'model',
            charged_solve_attempts=1+int(q.reuse_solver))
        with host.store.transaction() as db:
            current=host.store.session(host.run_id,db)['state']
            current['numerical_s']+=elapsed;current['local_solve_s']+=elapsed;current['numerical_reserved_s']-=seconds;current['pending']=None
            host.store.update_state(db,host.run_id,current)
            host.store.complete(row,dict(request_id=request_id,execution_id=row['execution_id'],caller=host.actor,
                tool_id='research.core_local_solve',tool_version='1.0.0',execution_status='completed',charged=zero()),value,elapsed=elapsed,db=db)
        rows.append(value)
    difference=max(abs(a-b) for a,b in zip(rows[0]['first_input_n'],rows[1]['first_input_n'])) if len(rows)==2 and all('first_input_n' in r for r in rows) else None
    detail=dict(rows=rows,maximum_first_input_difference_n=difference,mode=q.mode,
        interpretation='Identical recorded solve inputs; production and fixed-iteration modes are separate. Unique cause remains unassigned.')
    ref=save(host,detail,'local_diagnostic_comparison');update(host,diagnostics=[*state(host).get('diagnostics',[]),ref])
    return dict(reference=ref,**detail)


def claims(host):
    s=state(host); current=s['profile']['identity']; rows=[host.store.artifact(r) for r in s['results']]
    reference=host.store.artifact(s['reference_candidate'])['identity']
    comparable=[r for r in rows if r['profile_identity']==current and r['scientific_identity']==reference and r['status']=='evaluated']
    selected=host.store.artifact(s['selected']) if s.get('selected') else None
    confirmations=[r for r in rows if r['role']=='confirmation' and r['selected_execution']==s.get('selected')]
    repeat=bool(selected and selected['profile_identity']==current and selected['acceptance']['accepted'] and len(confirmations)==2 and
        all(r['acceptance'] and r['acceptance']['accepted'] and r['scientific_configuration']==selected['scientific_configuration'] and r['profile_identity']==current for r in confirmations))
    def score(r):
        m=r['acceptance']['metrics']
        ratios=[m['terminal_error_m']/.01,m['holding_max_error_m']/.01,m['holding_max_speed_m_s']/.02]
        return (max(ratios),sum(ratios))
    def parameters(r):return host.store.artifact(r['candidate'])['parameters']
    reference_d=host.store.artifact(s['reference_candidate'])['parameters']['d']
    same_structure=bool(selected and abs(parameters(selected)['d']-reference_d)<1e-10)
    def adapted(d):
        return {(parameters(r)['holding_tip_speed_weight'],parameters(r)['terminal_tip_speed_weight']) for r in rows
            if r['profile_identity']==current and r['status']=='evaluated' and r['role']!='confirmation' and abs(parameters(r)['d']-d)<1e-10}
    comparable_adaptation=bool(selected and (same_structure or (len(adapted(reference_d))>=2 and adapted(reference_d)==adapted(parameters(selected)['d']))))
    reference_structure=[r for r in rows if r['profile_identity']==current and r['status']=='evaluated' and abs(parameters(r)['d']-reference_d)<1e-10]
    improvement=bool(selected and reference_structure and score(selected)<min(score(r) for r in reference_structure))
    return dict(current_version_comparable_reference_count=len(comparable),selected=s.get('selected'),
        independent_confirmation_count=len(confirmations),confirmation_failures=sum(not (r['acceptance'] or {}).get('accepted',False) for r in confirmations),
        limited_repeat_supported_acceptance=repeat,
        observed_fixed_metric_ranking_improved=improvement,
        comparable_control_adaptation_for_structure_comparison=comparable_adaptation,
        parameter_improvement_attribution_permitted=bool(repeat and improvement and comparable_adaptation and selected['scientific_identity']!=reference),
        qualification='Task performance only without current-version comparable reference; two confirmations support limited tested acceptance, not general robustness. Fixed task metrics, never raw weighted NMPC objective.')


def packet(host):
    s=state(host)
    from tools.research_core_feedback import facts, eligibility, mechanics_context, compact_local
    from tools.research_core_numerics import compact_numerics
    return dict(specification=s['spec'],evaluation_profile=dict(identity=s['profile']['identity'],version=s['profile']['version'],
        recipe=s['profile']['recipe'],recording=s['profile']['recording'],acceptance=s['profile']['acceptance']),
        reference_candidate=s['reference_candidate'],candidates=[r for r in s['candidates'].values() if host.store.artifact(r)['profile_identity']==s['profile']['identity']],
        results=[dict(reference=r,**compact_result(host.store.artifact(r)),confirmation=eligibility(host,r)) for r in s['results']],
        decision_facts=facts(host),
        mechanics_results=[dict(reference=r,**{k:host.store.artifact(r).get(k) for k in
            ('operation','status','trajectory_reference','relaxed_nlp_feasible','original_task_feasible','trajectory_metrics',
             'hard_max_normalized_violation','original_task_gaps','charged_numerical_s','replay','physical_validation')},
             numerical_diagnostics=compact_numerics(host.store.artifact(r))) for r in s.get('mechanics_results',[])],
        handoffs=[dict(reference=r,**host.store.artifact(r),current_validation=mechanics_context(host,host.store.artifact(r)['candidate'])) for r in s.get('handoffs',[])],
        historical_context=dict(reference=s['historical_context'],
            facts=dict(development=dict(terminal_error_mm=2.912,holding_speed_m_s=.008583,accepted=True),
                independent_confirmation=dict(holding_speed_m_s=.058648,accepted=False),
                first_action_divergence=dict(update=8,time_s=.08,inputs_matched=True,unique_cause='unresolved; full earlier warm vectors unavailable'),
                mathematical_search='already executed; declared free control weights stayed fixed in archived search',
                generated_structures='already beyond four templates; optimized candidates already enter NMPC/MuJoCo',
                offline_schedule='not used as current feedback initialization/reference',
                synchronous_simulator='wall overrun did not skip simulated-time commands'),
            historical_costs='sealed source activity; not transferred or reset',supplied_context=True,autonomous_retrieval=False),
        resource_use=dict(shared_ledger=host.store.remaining(),numerical_s=s['numerical_s'],numerical_reserved_s=s['numerical_reserved_s'],
            local_solves=s['local_solves'],local_solve_s=s['local_solve_s'],admissible_batch=capacity(host,8,root_operation=True)),
        mechanics_resource_use=dict(offline_nlp=s.get('offline_nlp',0),bdf_replays=s.get('bdf_replays',0),
            independent_forward_integrations=s.get('bdf_replays',0) if s['spec'].get('mode')=='engineering_numerical' else None,
            refinement_validation_reservation=s.get('validation_reservation')),
        engineering_numerical_diagnosis=s.get('numerical_findings'),
        supplied_core_history=dict(reference=s.get('supplied_core_history'),original_study='unified-research-20261011',
            ownership='sealed historical evidence; not a fresh current-study execution',additional_numerical_s=0.,
            facts='All210 inputs complete; actual search only d0/~.05 at .10/.10 and both failed speed; current-version reference2 passes/1 failure; zero confirmations; first divergence update1 despite equal input vectors; unique cause unresolved; previous model identity/cost interpretations were unsupported.'),
        claims=claims(host),actual_retrievals=s['retrievals'],plans=s['plans'],status=s['research_status'],
        diagnostic_facts=s.get('diagnostic_facts',[]),local_diagnostic_evidence=s.get('diagnostics',[]),
        local_diagnostic_facts=[dict(reference=r,rows=[compact_local(v)
            for v in host.store.artifact(r).get('rows',[])]) for r in s.get('diagnostics',[])],
        incomplete_execution_evidence=s.get('incomplete_execution_evidence',[]))


def dispatch(host, value, request_id, origin='model'):
    """Native plan acceptance and internal batch use the same project Store."""
    if state(host)['spec'].get('mode') == 'engineering_numerical':origin='engineering'
    plan=Plan.model_validate(value); old=host.store.lookup(host.run_id,request_id)
    if old:
        if old['request_hash']!=digest(plain(plan)): raise ValueError('OPERATION_ID_COLLISION')
        if old['receipt']:
            from tools.research_core_feedback import cached
            return cached(host.store.artifact(json.loads(old['receipt'])['output']))
        raise ValueError('RECOVER_EXISTING_OPERATION_NO_NEW_EXECUTION')
    guard(host,plan.action in ('execute','search','confirm','mechanics','replay') or plan.diagnostic is not None)
    s=state(host)
    for r in plan.supporting_evidence: host.store.artifact(r)
    retrieved={r['artifact_id'] for r in s['retrievals']}
    if set(plan.experience_disposition)-retrieved: raise ValueError('DISPOSITION_REQUIRES_ACTUAL_RETRIEVAL')
    if plan.action=='stop' and any(r not in [plain(v) for v in plan.supporting_evidence] for r in [*s['results'],*s.get('mechanics_results',[])]):
        raise ValueError('STOP_MUST_CITE_ALL_NEW_EXPERIMENT_RESULTS')
    admission=capacity(host,plan.search.max_evaluations if plan.search else 1,plan.action=='confirm',root_operation=True)
    if plan.action=='execute' and admission['admitted']<1: raise ValueError('CANDIDATE_PLUS_TWO_CONFIRMATIONS_CANNOT_FIT')
    row,_=host.store.reserve(host.run_id,request_id,digest(plain(plan)),host.actor,{**zero(),'tool_calls':1})
    ref=save(host,dict(origin=origin,request_id=request_id,original_plan=plain(plan),admission=admission),'original_research_plan')
    update(host,plans=[*state(host)['plans'],ref])
    try:
        if plan.action=='propose':
            if plan.mechanics_source:
                from tools.research_core_mechanics import handoff
                relation=handoff(host,plan.mechanics_source,plain(plan.parameters),dict(origin=origin,plan=ref))
                result=dict(candidate=relation['candidate'],handoff=relation)
            else: result=dict(candidate=construct(host,plan.parameters,dict(origin=origin,plan=ref)))
        elif plan.action=='execute': result=execute(host,plain(plan.candidate),request_id)
        elif plan.action=='search': result=run_search(host,plan.search,request_id)
        elif plan.action in ('mechanics','replay'):
            from tools.research_core_mechanics import dispatch as mechanics_dispatch
            result=mechanics_dispatch(host,'solve' if plan.action=='mechanics' else 'replay',
                plan.mechanics if plan.action=='mechanics' else plan.mechanics_source,request_id)
        elif plan.action=='diagnose':
            result=diagnose(host,[plain(r) for r in plan.supporting_evidence])
            if plan.diagnostic: result['local_comparison']=local_diagnostic(host,plan.diagnostic,request_id)
        elif plan.action=='confirm':
            if plain(plan.selected_execution) not in s['results']: raise ValueError('OWNED_EXECUTION_SELECTION_REQUIRED')
            selected=host.store.artifact(plan.selected_execution)
            if s.get('selected') and s['selected']!=plain(plan.selected_execution):
                raise ValueError('POST_SELECTION_CONFIRMATIONS_CANNOT_CHANGE_SELECTION')
            candidate=verify_candidate(host,selected['candidate'])
            if selected['profile_identity']!=s['profile']['identity'] or selected['scientific_configuration']!=candidate['scientific_configuration']:
                raise ValueError('CONFIRMATION_REQUIRES_SELECTED_COMPLETE_PARAMETERS_AND_EVALUATION_CONFIGURATION')
            if not (selected.get('acceptance') or {}).get('accepted'):
                raise ValueError('SELECTED_PASSING_EXECUTION_REQUIRED')
            if admission['admitted']<1: raise ValueError('EXECUTION_AND_CONFIRMATION_RESERVE_CANNOT_FIT')
            update(host,selected=plain(plan.selected_execution))
            result=execute(host,selected['candidate'],request_id,role='confirmation',selected=plain(plan.selected_execution))
        else:
            update(host,research_status='stopped',final_disposition=ref)
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


INSTRUCTIONS = '''You are the sole research principal for the existing reach-and-hold task.
Choose freely among propose, execute, mathematical search, read-only diagnosis,
fresh post-selection confirmation, experience retrieval, evidence read and STOP.
Mechanics optimizes existing d, full states and tensions offline, with separate
offline objective weights and relaxed task slacks; replay independently integrates
its returned schedule with BDF. BDF is not physical validation. A handoff retains
trajectory and failure flags; goal-based runtime NMPC holds structure and weights
fixed. Search adapts selected weights at fixed structure (cite mechanics_source
for that handoff), or optionally the existing structural coordinate when justified.
Engineering-selected integration actions are supplied evidence, not your choices.
No mandatory traversal. Direct proposals construct parameters without offline NLP.
Diagnosis may optionally perform bounded identical-recorded-input standalone solves;
production mode retains elapsed stopping, fixed_iteration is only a diagnostic mode.
Search fixes unselected variables and uses the same evaluator; several numerical
proposals may run internally. Inspect actual explored coordinates. Give hypothesis,
evidence, expected and weakening observations, fixed conditions and stopping rule.
The program supplies facts; retain your interpretations separately. Experience
drafts are recommendations, not validated skills; record adoption/rejection.
Freeze all other task, physics, controller, solver and initialization settings.
Candidate identity includes all resolved fixed/search parameters and evaluation
profile; each independent execution has its own identity. Confirmations must cite
the exact result EvidenceRef in confirmation_options, not candidate/hash/receipt.
Identical candidate artifacts legitimately yield fresh positive-cost executions
owned by this study. Cached operation receipts incur zero additional execution
cost; previous result costs remain visible. Imported history is not owned passing
execution evidence. Failed submissions return usable facts without choosing for you.
Run confirmations twice with identical full science.
Numerical feasibility, early stopping, selection/recovery, prediction disagreement,
input limits, task acceptance and missing data are distinct. No weight direction
is prescribed. Compare fixed task metrics, never objectives with different weights.
Historical development .10/.10 passed but same-configuration confirmation failed;
unique cause unresolved. Earlier complete warm plans were not saved. Wall overruns
did not skip synchronous simulated-time commands. Archived free weight declarations
did not demonstrate exploration. Old offline schedule is not the feedback reference.
A material repair versions the evaluation profile and retains all costs/results.
Without a new comparable reference under the current profile report performance
only, withhold parameter improvement attribution. Reserve two confirmations before
every development/search and obey the shared ledger including all internal launches.
Last four provider requests are for results/STOP only. You may stop on scientific
failure or sufficient evidence; do not force success or fill quotas. STOP must cite
every new experiment result. Accepted STOP ends sends, with no narrative polish.
No robustness, global optimum, continuous-time, hardware, generalization or LLM
superiority claims. Current facts refresh at model boundaries; Strands owns history.'''


async def converse(host):
    if state(host)['spec'].get('mode') == 'engineering_numerical':
        raise ValueError('NUMERICAL_MODE_FORBIDS_APPLICATION_MODEL_ENDPOINTS')
    from strands.tools.tools import PythonAgentTool
    from strands.tools.executors import SequentialToolExecutor
    from strands.hooks.events import BeforeModelCallEvent, BeforeToolCallEvent, AfterToolCallEvent
    from tools.strands_pilot import build_harness
    from tools.strands_pilot_r3 import LiveBoundary, live_model_class, record, pending
    from examples.gvs_nmpc_route_experiment import load_credential
    def feedback_context_references():
        refs=[]
        for event in host.store.events(host.run_id):
            if event['kind']!='model_original_tool_feedback': continue
            value=host.store.artifact(event['outputs'][0]);use=value['tool_use']
            if use['name']!='research_plan' or use['input'].get('action') in ('stop',None): continue
            if value['result']['status']!='success': continue
            refs.extend(use['toolUseId']+'_'+str(i) for i,_ in enumerate(value['result'].get('content',[])))
        return refs
    guard(host)
    if pending(host): raise ValueError('UNKNOWN_PROVIDER_OUTCOME_RECOVER_BEFORE_SEND')
    load_credential(Path.home()/'.codex'/'.env')
    class Boundary(LiveBoundary):
        async def handle_async_request(self,request):
            s=state(host)
            if s['research_status']=='stopped' or s['pending']: raise ValueError('SEALED_STOP_OR_PENDING_WORK_BLOCKS_SEND')
            if not s['pilot'].get('unconsumed_response'):
                wire=json.loads(request.content)
                if host.store.remaining()['remaining']['model_calls']<=4:
                    definitions={t['function']['name']:t['function'] for t in wire.get('tools',[])}
                    action=definitions.get('research_plan',{}).get('parameters',{}).get('properties',{}).get('action',{})
                    if action.get('const')!='stop' or set(definitions)-{'research_plan','evidence_read','retrieve_context'}:
                        raise ValueError('PROTECTED_SEND_REQUIRES_STOP_ONLY_NATIVE_SCHEMA')
                    retrieval=definitions.get('retrieve_context')
                    if retrieval:
                        advertised=retrieval.get('parameters',{}).get('properties',{}).get('reference',{}).get('enum')
                        if advertised is None or not set(advertised)<=set(feedback_context_references()):
                            raise ValueError('PROTECTED_CONTEXT_RETRIEVAL_REQUIRES_EXISTING_FEEDBACK')
            return await super().handle_async_request(request)
    boundary=Boundary(host,allow_truncated_response=True)
    def handler(kind):
        def run(use,**kwargs):
            try:
                if kind=='plan': value=dispatch(host,use['input'],'native-'+use['toolUseId'])
                else:
                    key='native-'+use['toolUseId']
                    row,fresh=host.store.reserve(host.run_id,key,digest(use['input']),host.actor,{**zero(),'tool_calls':1})
                    if not fresh and row['receipt']: value=host.store.artifact(json.loads(row['receipt'])['output'])
                    else:
                        if kind=='experience': value=experience(host,use['input'])
                        else:
                            q=EvidenceQuery.model_validate(use['input']); value=host.store.artifact(q.reference)
                            current_state=state(host)
                            if host.store.remaining()['remaining']['model_calls']<=4 and plain(q.reference) not in [*current_state['results'],*current_state.get('mechanics_results',[])]:
                                raise ValueError('PROTECTED_EVIDENCE_READ_REQUIRES_NEW_RESULT')
                            for part in q.pointer.strip('/').split('/') if q.pointer else []:
                                part=part.replace('~1','/').replace('~0','~')
                                value=value[int(part)] if isinstance(value,list) else value[part]
                        host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
                            tool_id='research.core_'+kind,tool_version='1.0.0',execution_status='completed',charged=zero()),value)
                return dict(toolUseId=use['toolUseId'],status='success',content=[dict(text=json.dumps(value))])
            except Exception as exc:
                from tools.research_core_feedback import facts
                return dict(toolUseId=use['toolUseId'],status='error',content=[dict(text=json.dumps(dict(
                    error=type(exc).__name__,message=str(exc),decision_facts=facts(host))))])
        return run
    native=[PythonAgentTool(name,dict(name=name,description=description,inputSchema={'json':schema.model_json_schema()}),handler(kind))
        for name,description,schema,kind in [('research_plan','Propose, execute, mechanics, BDF replay, search, diagnose, confirm or STOP',Plan,'plan'),
            ('experience_retrieve','Read-only case/procedure draft search/read with provenance',ExperienceQuery,'experience'),
            ('evidence_read','Read exact immutable evidence and JSON pointer',EvidenceQuery,'evidence')]]
    agent=build_harness(host,transport=boundary,api_key=os.environ['DEEPSEEK_API_KEY'],instructions=INSTRUCTIONS,
        model_class=live_model_class(boundary),tool_executor=SequentialToolExecutor(),research_tools=native,
        configuration_path=host.store.root/'framework_configuration.json',session_directory=host.store.root/'framework_sessions')
    def before_model(event):
        s=state(host)
        if s['research_status']=='stopped': event.cancel='Accepted native STOP; no additional request'; return
        if s['pilot'].get('unconsumed_response'):
            saved=s['pilot']['unconsumed_response']; ev=next(e for e in host.store.events(host.run_id) if e['kind']=='r3_request' and e['request_id']==saved)
            original=host.store.artifact(host.store.artifact(ev['outputs'][0])['request'])
            agent.system_prompt=next(m['content'] for m in original['messages'] if m['role']=='system'); return
        guard(host); current=packet(host); record(host,'model_decision_packet',current)
        agent.system_prompt=INSTRUCTIONS+'\nCURRENT_RESEARCH_PACKET\n'+json.dumps(current)
        if host.store.remaining()['remaining']['model_calls']<=4:
            schema=Plan.model_json_schema(); schema['properties']['action']={'const':'stop','type':'string'}
            native[0].tool_spec={**native[0].tool_spec,'inputSchema':{'json':schema}}
            agent.tool_registry.registry.pop('experience_retrieve',None)
            schema=EvidenceQuery.model_json_schema()
            schema['$defs']['EvidenceRef']['properties']['artifact_id']['enum']=[r['artifact_id'] for r in [*s['results'],*s.get('mechanics_results',[])]]
            native[2].tool_spec={**native[2].tool_spec,'inputSchema':{'json':schema}}
            retrieval=agent.tool_registry.registry.get('retrieve_context')
            if retrieval:
                from strands.tools.tools import normalize_tool_spec
                spec=deepcopy(normalize_tool_spec(retrieval.tool_spec))
                spec['inputSchema']['json']['properties']['reference']['enum']=feedback_context_references()
                retrieval.tool_spec=spec
            agent.system_prompt+='\nPROTECTED CLOSEOUT: consume supplied results and STOP only.'
    def before_tool(event):
        record(host,'model_original_tool_request',dict(tool_use=event.tool_use))
        if state(host)['research_status']=='stopped': event.cancel_tool='Accepted STOP seals further workflow work.'
        if host.store.remaining()['remaining']['model_calls']<=4 and event.tool_use['name']=='retrieve_context' and event.tool_use['input'].get('reference') not in feedback_context_references():
            event.cancel_tool='Protected closeout permits existing execution feedback only.'
    def after_tool(event):
        record(host,'model_original_tool_feedback',dict(tool_use=event.tool_use,result=event.result))
        key='native-'+event.tool_use['toolUseId']
        if host.store.lookup(host.run_id,key) is None:
            row,_=host.store.reserve(host.run_id,key,digest(event.tool_use),host.actor,{**zero(),'tool_calls':1})
            host.store.complete(row,dict(request_id=key,execution_id=row['execution_id'],caller=host.actor,
                tool_id=event.tool_use['name'],tool_version='1.0.0',execution_status='completed',charged=zero()),event.result)
    agent.hooks.add_callback(BeforeModelCallEvent,before_model)
    agent.hooks.add_callback(BeforeToolCallEvent,before_tool); agent.hooks.add_callback(AfterToolCallEvent,after_tool)
    try:
        while state(host)['research_status']!='stopped':
            result=await agent.invoke_async('Use actual saved evidence, choose your next research action or STOP, then consume feedback and decide freely.')
            record(host,'model_original_turn',dict(result=str(result)))
            if state(host)['pending'] or pending(host): raise ValueError('PENDING_OUTCOME_REQUIRES_LOCAL_RECOVERY')
    finally: await boundary.aclose()


def recover(host):
    if (state(host).get('pending') or {}).get('kind') == 'local_diagnostic':
        from tools.research_core_numerics import recover_local
        return recover_local(host)
    from tools.strands_pilot_r3 import pending as provider_pending, received, settle
    for row in provider_pending(host):
        response=received(host,row['request_id'])
        if response: settle(host,row,response)
        else: raise ValueError('UNKNOWN_PROVIDER_SEND_INSPECT_BEFORE_REPEAT')
    p=state(host)['pending']
    if p and p.get('kind')=='mechanics':
        from tools.research_core_mechanics import recover as mechanics_recover
        recovered=mechanics_recover(host)
    else: recovered=finish_execution(host,recovery=True) if p else None
    s=state(host); completed=[]
    for ref in s['plans']:
        original=host.store.artifact(ref);key=original['request_id'];row=host.store.lookup(host.run_id,key)
        if not row or row['receipt']: continue
        plan=Plan.model_validate(original['original_plan'])
        if plan.action=='search': result=run_search(host,plan.search,key)
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
    out=Path(destination or ROOT/state(host)['spec'].get('evidence_destination','evidence/research_core_20261011')); out.mkdir(parents=True,exist_ok=True)
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


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('command',choices=['prepare','bind','migrate','execute','diagnose','live','recover','status','export'])
    parser.add_argument('--spec',type=Path,default=DEFAULT_SPEC); parser.add_argument('--plan',type=Path)
    parser.add_argument('--request-id'); parser.add_argument('--reason'); args=parser.parse_args()
    spec=read(args.spec); h=prepare(args.spec) if args.command=='prepare' else Host(ROOT/'runs'/spec['study_id'],spec['study_id'],actor='unified-research')
    if args.command in ('bind','migrate'): bind(h,args.reason if args.command=='migrate' else None)
    elif args.command=='execute': print(json.dumps(dispatch(h,read(args.plan),args.request_id or 'manual-'+uuid4().hex,origin='engineering'))); return
    elif args.command=='diagnose': print(json.dumps(diagnose(h,state(h)['results']))); return
    elif args.command=='recover': print(json.dumps(recover(h))); return
    elif args.command=='live': asyncio.run(converse(h))
    elif args.command=='export': print(json.dumps(export(h))); return
    print(json.dumps(packet(h)))


if __name__=='__main__': main()
