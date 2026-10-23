"""Owned NMPC dispatch, completion and immutable evidence packaging."""
from copy import deepcopy
from pathlib import Path
import json, os, subprocess, sys, time
from uuid import uuid4
from tools.platform_host import Host
from tools.platform_store import plain, zero
from tools.state_io import atomic_json, read, digest
from tools.research.state import (ROOT, state, update, save, guard, charge_start,
    capacity, nmpc_timing)
from tools.research.design import verify_candidate, full_science


def record_orphan_exit(host, inventory_reference):
    """Trusted operator SDK recovery, never an Agent tool or a new execution.

    The original supervisor inventory must bind the actual worker PID to this
    request. Entering complete-simulation proves the worker installed its
    kill-on-close job before science. All observed worker processes must have
    exited; missing identity or inaccessible/live PIDs retain the pending call.
    """
    from tools.service_execution import process_exit_observation
    p=state(host)['pending']
    if not p or not p.get('launch_intent'):raise ValueError('LAUNCHED_PENDING_EXECUTION_REQUIRED')
    folder=host.store.root/'executions'/p['owner']
    if (folder/'boundary.json').exists():raise ValueError('USE_ORIGINAL_EXECUTION_BOUNDARY')
    recovered=folder/'recovery_boundary.json'
    if recovered.exists():return read(recovered)
    inventory=host.store.artifact(inventory_reference)
    request=str(folder/'request.json').replace('\\','/').casefold()
    workers=[r for r in inventory['processes'] if '-m tools.research.execution_worker ' in r['CommandLine']
        and r['CommandLine'].replace('\\','/').casefold().endswith(request)]
    if not workers or not p['started_unix']<=inventory['captured_unix']<=time.time():
        raise ValueError('ORIGINAL_WORKER_IDENTITY_REQUIRED')
    simulation=host.store.lookup(p['owner'],'complete-simulation')
    if not simulation or simulation['receipt']:raise ValueError('UNSEALED_STARTED_SIMULATION_REQUIRED')
    observations=[process_exit_observation(r['ProcessId']) for r in inventory['processes']]
    observed=time.time()
    proof=dict(owner=p['owner'],original_inventory=plain(inventory_reference),observed_unix=observed,
        process_observations=observations,containment='execution_worker installs kill-on-close job before complete-simulation',
        classification='Supervisor-confirmed orphan exit; original exit code/time unknown; no checkpoint continuation')
    ref=save(host,proof,'verified_orphan_exit')
    boundary=dict(termination_confirmed=True,timed_out=False,returncode=None,
        elapsed_s=observed-p['started_unix'],elapsed_semantics='conservative upper bound through verified exit observation',
        recovery_source=ref,original_boundary_missing=True)
    atomic_json(recovered,boundary)
    return boundary


def execute(host, candidate_ref, operation_key, *, role='development', selected=None):
    guard(host,expensive=role!='confirmation')
    s=state(host)
    c=verify_candidate(host,candidate_ref)
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
        if not timing['available']:
            raise ValueError(timing['reason'])
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
        if not old.get('acceptance',{}).get('accepted'):
            raise ValueError('SELECTED_PASSING_EXECUTION_REQUIRED')
        from tools.research.feedback import eligibility
        choice=eligibility(host,selected)
        if not choice['eligible']:
            raise ValueError('; '.join(choice['reasons']))
    from tools.research.feedback import experiment_preflight
    novelty=experiment_preflight(host,candidate_ref,'nmpc',repeat=confirmation or repetition)
    if not novelty['admitted']:
        raise ValueError('EQUIVALENT_SCIENTIFIC_EXPERIMENT_REQUIRES_EXPLICIT_REPLICATION_GRANT: '
            +json.dumps(novelty,sort_keys=True))
    admission=capacity(host,1,confirmation or repetition,candidate=candidate_ref)
    if admission['admitted']<1:
        raise ValueError('EXECUTION_AND_CONFIRMATION_RESERVE_CANNOT_FIT')
    if s['spec'].get('fidelity_policy'):
        if Path(s['spec']['runtime']['research_python']).resolve()!=Path(sys.executable).resolve():
            raise ValueError('CAPABILITY_REQUIRES_EXACT_EXECUTION_INTERPRETER')
        from tools.research.design import final_fidelity_matches
        if not final_fidelity_matches(s['spec'],c):
            return dict(status='final_fidelity_required',candidate=plain(candidate_ref),task_success=None,
                final_evaluation_identity=s['spec']['final_evaluation_identity'])
        from tools.research.runtime_capability import capability
        support=capability(host,plain(candidate_ref))
        if support['status']!='runtime_available':
            return dict(status=support['status'],candidate=plain(candidate_ref),task_success=None,capability=support)
    # A unique execution owner is persisted before starting any backend.
    owner=host.run_id+'-exec-'+uuid4().hex[:16]
    cfg=deepcopy(c['configuration'])
    cfg['run_id']=owner
    from tools.execution_completion import EXECUTION_ALLOWANCES
    cfg['policy'].update(budget={**cfg['policy']['budget'],'model_calls':0},allowed_tools=[],
        tool_bindings={n:'1.0.0' for n in ('simulation.run','evaluation.run','control.profile_report')},
        operation_allowances={name:dict(timeout_s=None,reserve_s=None) for name in EXECUTION_ALLOWANCES})
    simulation_allowance=s.get('execution_cost_estimate',{}).get('simulation_watchdog_s',s['spec']['execution_allowances']['simulation_s'])
    cfg['policy']['operation_allowances']['simulation.run']=dict(timeout_s=simulation_allowance,reserve_s=simulation_allowance)
    if full_science(cfg)!=c['scientific_configuration']:
        raise ValueError('EXECUTION_CHANGED_FROZEN_SCIENCE')
    pending=dict(owner=owner,candidate=plain(candidate_ref),configuration=cfg,role=role,
        selected_execution=plain(selected),operation_key=operation_key,started_unix=time.time(),
        profile_identity=s['profile']['identity'],admission=admission,reserved_s=admission['numerical_reservation_s'],timeout_s=admission['per_execution_s'])
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        from tools.research.budget import backend_capacity
        if backend_capacity(host,db)<1:raise ValueError('BACKEND_CAPACITY_PROTECTS_RESERVED_RL_EVALUATIONS')
        charge_start(current)
        current.update(pending=pending,numerical_reserved_s=current['numerical_reserved_s']+pending['reserved_s'],nmpc_launches=current.get('nmpc_launches',0)+1)
        host.store.update_state(db,host.run_id,current)
    return finish_execution(host)


def finish_execution(host, recovery=False):
    """Only sealed receipts continue. Reporting failure cannot trigger simulation."""
    s=state(host)
    p=s['pending']
    if recovery and p and not p.get('launch_intent'):
        # Launch intent is durably committed before any subprocess send. Its
        # absence proves that this failed dispatch never started a worker.
        from datetime import datetime
        failures=[e for e in host.store.events(host.run_id) if e['kind']=='pending_operation_failure'
            and host.store.artifact(e['outputs'][0]).get('pending',{}).get('owner')==p['owner']]
        if not failures:
            raise ValueError('PRELAUNCH_RECOVERY_REQUIRES_RECORDED_FAILURE')
        last=failures[-1]
        folder=host.store.root/'executions'/p['owner']
        folder.mkdir(parents=True,exist_ok=True)
        atomic_json(folder/'boundary.json',dict(termination_confirmed=True,timed_out=False,
            worker_started=False,prelaunch_failure=last['outputs'][0],
            elapsed_s=max(0.,datetime.fromisoformat(last['timestamp']).timestamp()-p['started_unix'])))
    from tools.execution_completion import complete_execution, STAGES
    from tools.service_execution import _run_contained
    from tools.research_tasks import assemble_acceptance
    s=state(host)
    p=s['pending']
    if not p:
        raise ValueError('NO_PENDING_EXECUTION')
    child=Host(host.store.root,p['owner'],actor=host.actor)
    c=host.store.artifact(p['candidate'])
    started=time.perf_counter()
    folder=host.store.root/'executions'/p['owner']
    folder.mkdir(parents=True,exist_ok=True)
    outcome=folder/'boundary.json'
    output=folder/'result.json'
    if not recovery:
        if p.get('launch_intent'):
            raise ValueError('LAUNCH_ALREADY_REQUESTED_RECOVERY_ONLY_NO_RELAUNCH')
        request=folder/'request.json'
        atomic_json(request,dict(root=str(host.store.root),study=host.run_id,owner=p['owner'],actor=host.actor,
            configuration=p['configuration'],candidate_id=c['candidate_id'],recording=s['profile']['recording']))
        # Persist launch intent first. A crash thereafter is uncertain, never replayable.
        update(host,pending=dict(p,launch_intent=True))
        try:
            with (folder/'worker.log').open('w',encoding='utf8') as log:
                done=_run_contained([str(s['spec']['runtime']['research_python']),'-m','tools.research.execution_worker',str(request)],log,
                    p.get('timeout_s'),lifecycle_path=folder/'worker_lifecycle.json')
            boundary=dict(termination_confirmed=True,timed_out=False,returncode=done.returncode)
        except subprocess.TimeoutExpired as exc:
            boundary=dict(termination_confirmed=getattr(exc,'termination_confirmed',False),timed_out=True)
        except Exception as exc:
            boundary=dict(termination_confirmed=False,timed_out=False,error=str(exc))
        boundary['elapsed_s']=time.perf_counter()-started
        atomic_json(outcome,boundary)
    elif not outcome.exists():
        outcome=folder/'recovery_boundary.json'
        if not outcome.exists():
            raise ValueError('UNKNOWN_WORKER_TERMINATION_RETAINS_PENDING_RESERVATION; NO_RELAUNCH')
    boundary=read(outcome)
    if not boundary['termination_confirmed']:
        return dict(status='execution_unresolved',reason='Worker tree termination uncertain; reservation retained; no replay',pending=p)
    receipts={}
    unfinished=None
    for stage,tool in STAGES:
        row=child.store.lookup(p['owner'],'complete-'+stage)
        if row and row['receipt']:
            receipts[stage]=json.loads(row['receipt'])
        elif row:
            unfinished=(stage,tool,row)
            break
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
        if boundary.get('recovery_source'):
            result.update(failure_reason='supervisor-verified orphan exit; incomplete physical episode, no exact state checkpoint',
                termination_evidence=boundary['recovery_source'])
    elif output.exists():
        result=read(output)
    else:
        # Package only when every stage already has a sealed receipt. No missing-stage launch.
        if len(receipts)==len(STAGES):
            result=complete_execution(child,p['configuration'],c['candidate_id'])
        else:
            result=dict(status='execution_incomplete',receipts=receipts,failure_reason='worker returned without result',task_performance='unmeasured')
    if boundary.get('worker_started') is False:
        result.update(failure_reason='prelaunch engineering failure; no numerical worker started',boundary=boundary,
            task_performance='unmeasured')
    if result['status']=='execution_unresolved':
        save(host,dict(pending=p,partial_result=result),'unresolved_execution')
        return result
    acceptance=None
    profile=None
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
    ref=save(host,detail,'experiment_result')
    s=state(host)
    with host.store.transaction() as db:
        current=host.store.session(host.run_id,db)['state']
        if not current.get('pending') or current['pending']['owner']!=p['owner']:
            raise ValueError('EXECUTION_ALREADY_SETTLED')
        current.update(results=[*current['results'],ref],pending=None,
            numerical_reserved_s=current['numerical_reserved_s']-p['reserved_s'],numerical_s=current['numerical_s']+actual)
        host.store.update_state(db,host.run_id,current)
    from tools.research.budget import observe_pass
    from tools.research.tool_readiness import observe_failure
    observe_failure(host,detail,ref)
    observe_pass(host,ref)
    from tools.research.rl import compatible_references
    compatible_references(host)
    from tools.research.feedback import eligibility
    return dict(reference=ref,**compact_result(detail),confirmation=eligibility(host,ref),
        operation_cost=dict(additional_numerical_s=actual,additional_scientific_executions=0 if recovery else 1,cached_operation_receipt=False))


def compact_result(r):
    from tools.research.feedback import execution_evidence
    profile=r.get('profile') or {}
    result={k:r.get(k) for k in ('status','role','candidate','candidate_id','scientific_identity','profile_identity','evaluation_version',
        'selected_execution','acceptance','execution_id','owner_run_id','owning_study','fresh_execution',
        'cached_operation_receipt','numerical_s','failure_categories','mechanics_context')} | dict(
        controller_facts={k:profile[k] for k in ('updates','applied_control_updates','initialization_selected','accepted_noninitialization_plans',
            'solver_error_count','unusable_plans','deadline_misses','one_step_prediction_summary') if k in profile})
    if r.get('execution',{}).get('termination_evidence'):
        result['interruption']={k:r['execution'][k] for k in ('failure_reason','termination_evidence')}
    if not result['execution_id']:
        result['execution_id']=r.get('execution',{}).get('receipts',{}).get('simulation',{}).get('execution_id')
        result['execution_identity_source']='sealed failed simulation receipt; no completed acceptance implied'
    return dict(result,**execution_evidence(r))


