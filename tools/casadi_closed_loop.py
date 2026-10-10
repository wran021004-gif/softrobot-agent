"""Saved mathematical structure to receipt-backed exploratory feedback execution."""
from copy import deepcopy
import json
import tarfile
import time
import numpy as np
from schemas.casadi_feedback import ControlChoice
from schemas.design_optimization import DesignOptimizationProblem
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.state_io import read, digest
from tools.spec_tools import ROOT


def import_latest(store, db):
    directory=ROOT/'evidence/casadi_feedback_closeout_20261010'
    old=read(directory/'state.json');sources={};results=[];history={}
    with tarfile.open(directory/'immutable_artifacts.tar.gz','r:gz') as archive:
        imported={}
        def load(ref):
            aid=ref['artifact_id']
            if aid in imported:return imported[aid]
            extension='.json' if ref['media_type']=='application/json' else '.bin'
            body=archive.extractfile('artifacts/'+aid+extension).read()
            value=json.loads(body) if extension=='.json' else body
            new=store.put(db,value)
            if new.artifact_id!=aid:raise ValueError('IMPORTED_EVIDENCE_IDENTITY_CHANGED')
            imported[aid]=value
            return value
        for row in old['results']:
            if row['operation'] not in ('solve','replay','diagnose','speed','original_node_comparison','post_stop_correction'):continue
            value=load(row['reference'])
            results.append(dict(row,imported=True,source_activity=old['pilot']['activity_id'],new_numerical_s=0.))
            if row['operation']=='solve' and row.get('candidate'):
                candidate=load(row['candidate']);checkpoint=load(value['checkpoint_reference'])
                cfg=plain(store.put(db,checkpoint['configuration']))
                sources[row['candidate']['artifact_id']]=dict(configuration=cfg,checkpoint=value['checkpoint_reference'],
                    solve=row['reference'],source_activity=old['pilot']['activity_id'],selection=candidate['selection'])
        for p in old['plans']:load(p['reference'])
        history.update(plans=old['plans'],final_disposition=old['final_disposition'],
            original_node_comparisons=old['original_node_comparison_reference'],post_stop_correction=old['post_stop_correction_reference'])
        # Established mechanics and precision/AD studies remain read-only imports.
        for name,ref in old['historical'].items():
            if name=='selected_corrected_A':continue
            load(ref);history[name]=ref
    summary=read(directory/'result_summary.json');history['result_summary']=plain(store.put(db,summary))
    return history,results,sources


def resolve_candidate(store, candidate_reference, source, control, run_id, policy):
    """Materialize once, before simulation; no schedule or predicted state applied."""
    from tools.design_optimization import resolved_input
    from extensions.tendon_family import generated_serial as family
    from extensions.tendon_family.gvs_codesign import expression
    from extensions.tendon_family.gvs_nmpc import workspace_key
    from extensions.tendon_family.gvs_projection import description
    from extensions.tendon_family.gvs_basis import resolve_basis
    from extensions.tendon_family.gvs_trajectory import GVSTrajectoryParameters
    candidate=store.artifact(candidate_reference)
    original=SessionInput.model_validate(store.artifact(source['configuration']))
    problem=DesignOptimizationProblem.model_validate(read(ROOT/'examples/casadi_codesign/case_A.json')['physical_source'])
    original_task=plain(original.task);frozen_task=plain(problem.task)
    original_task.pop('initializer');frozen_task.pop('initializer')
    family.validate_initializer(original,original)
    if original_task!=frozen_task or original.seed!=problem.execution.seed:
        raise ValueError('CANDIDATE_SOURCE_FROZEN_TASK_MISMATCH')
    problem=problem.model_copy(update={'task':original.task})
    old_recipe=original.robot.structure.data['metadata']['recipe']
    frozen=dict(segment_count=2,proximal_tendons=3,distal_tendons=3,lengths_m=[.16,.11],
        material='baseline',section_scale=1.,routing_scale=1.,pretension_n=.2)
    if plain(family.Recipe.model_validate(old_recipe))!=plain(family.Recipe.model_validate(frozen)):
        raise ValueError('CANDIDATE_SOURCE_STRUCTURAL_DOMAIN_MISMATCH')
    d=candidate['d'];lengths=[.16+.0055*d,.11-.0055*d]
    if not np.isfinite(d) or not -1<=d<=1 or not np.allclose(lengths,candidate['lengths_m'],rtol=0,atol=1e-12):
        raise ValueError('CANDIDATE_EXACT_DESIGN_VALUES_INVALID')
    choice=ControlChoice.model_validate(control)
    values=dict(old_recipe,lengths_m=list(candidate['lengths_m']),
        holding_tip_speed_weight=choice.holding_tip_speed_weight,terminal_tip_speed_weight=choice.terminal_tip_speed_weight)
    cfg=resolved_input(problem,values,run_id,policy);inp=SessionInput.model_validate(cfg)
    dims=family.dimensions(inp);expr=expression(cfg)
    if candidate['coordinate_order']!=dims['coordinate_order'] or candidate['tendon_order']!=dims['tendon_input_order']:
        raise ValueError('CANDIDATE_NAMED_COORDINATE_OR_TENDON_ORDER_MISMATCH')
    if list(expr.coordinate_order)!=dims['coordinate_order'] or list(expr.tendon_order)!=dims['tendon_input_order']:
        raise ValueError('PREDICTION_AND_SIMULATION_MAPPING_MISMATCH')
    if np.asarray(candidate['states']).shape[1:]!=(dims['dimensions']['reduced_state'],):
        raise ValueError('CANDIDATE_REDUCED_STATE_DIMENSION_MISMATCH')
    units=dims['numerical_initialization']['units']
    if units!=dict(q='rad/m',qdot='rad/(m*s)',tension='N'):
        raise ValueError('CANDIDATE_UNITS_MISMATCH')
    expected=plain(problem.execution.recipe);actual=cfg['policy']['controller']['parameters']['data']['recipe']
    for k in ('holding_tip_speed_weight','terminal_tip_speed_weight'):expected[k]=getattr(choice,k)
    if actual!=expected:raise ValueError('UNDECLARED_NMPC_RECIPE_CHANGE')
    physics=family.check_robot(inp.robot.structure.data,inp.policy.discretization.data)
    basis=resolve_basis(inp.robot.structure.data,problem.execution.recipe.basis)
    report=dict(candidate=plain(candidate_reference),source=source,resolved_values=values,
        dimensions=dims,physics_identity=physics['identity'],prediction_model_identity=digest(plain(expr)),
        prediction_design_identity=digest(plain(expr.design)),robot_design_identity=digest(inp.robot.structure.data),
        workspace_identity=workspace_key(inp.task,inp.robot,GVSTrajectoryParameters.model_validate(actual)),
        projection=description(physics,basis),controller_binding=cfg['policy']['controller'],
        backend_binding=cfg['policy']['backend'],model_binding=cfg['policy']['dynamics_model'],
        units=dict(**units,length='m',time='s'),
        candidate_unit_source='Saved Workspace.decode physical scaling (q 10 rad/m, qdot 1000 rad/(m*s), tension 8 N); checked against generated numerical contract',
        changes={},offline_schedule_used=False,
        numerical_initialization='initial_state_pretension: 0.2 N guesses; not equilibrium or physical initial tensions',
        eligibility=dict(eligible=True,scope='exploratory structure under feedback control',
            historical_open_loop_acceptance_unchanged=True,replay_gate_required=False))
    if report['prediction_design_identity']!=report['robot_design_identity']:
        raise ValueError('PREDICTION_PHYSICAL_CONFIGURATION_MISMATCH')
    return cfg,report


def validate_control(store, state, choice, action):
    choice=ControlChoice.model_validate(choice)
    source=state.get('candidate_sources',{}).get(choice.candidate.artifact_id)
    if source is None:raise ValueError('IMMUTABLE_CANDIDATE_SOURCE_PROVENANCE_REQUIRED')
    preceding=None;changes={};factors=['structure/controller evaluation']
    if choice.preceding_execution:
        rows=[r for r in state['results'] if r['operation']=='closed_loop' and r['reference']==plain(choice.preceding_execution) and not r.get('imported')]
        if not rows:raise ValueError('PRECEDING_CURRENT_ACTIVITY_EXECUTION_REQUIRED')
        preceding=store.artifact(choice.preceding_execution)
        for k in ('holding_tip_speed_weight','terminal_tip_speed_weight'):
            old=preceding['control'][k];new=getattr(choice,k)
            if old!=new:changes[k]=dict(before=old,after=new)
        same=preceding['candidate']==plain(choice.candidate)
        if action=='control_revision' and (not same or not changes):raise ValueError('CONTROL_ONLY_REVISION_REQUIRES_SAME_CANDIDATE_AND_CHANGED_WEIGHTS')
        factors=(['control'] if same else ['structure'])+(['control'] if changes and not same else [])
    return source,dict(preceding_execution=plain(choice.preceding_execution),exact_weight_changes=changes,
        changed_factors=factors,attribution='No unique causal attribution; changed structure and control are jointly reported.')


def run_closed_loop(host, choice, plan_reference, action):
    from tools.platform_host import Host
    from tools.execution_completion import complete_execution, EXECUTION_ALLOWANCES
    from tools.research_tasks import assemble_acceptance
    from tools.casadi_feedback_service import ACTIVITY, CEILINGS, budget
    started=time.perf_counter();state=host.store.session(ACTIVITY)['state']
    if state.get('pending') or state.get('engineering_pause'):raise ValueError('INSPECT_PENDING_EXECUTION_BEFORE_DISPATCH')
    source,revision=validate_control(host.store,state,choice,action)
    choice=ControlChoice.model_validate(choice)
    owner=ACTIVITY+'-cl-'+plan_reference['artifact_id'][:12]
    policy=deepcopy(host.store.session(ACTIVITY)['snapshot']['input']['policy'])
    policy.update(budget={**policy['budget'],'model_calls':0},allowed_tools=[],
        tool_bindings={n:'1.0.0' for n in ('simulation.run','evaluation.run','control.profile_report')},
        operation_allowances=deepcopy(EXECUTION_ALLOWANCES))
    policy['operation_allowances']['simulation.run']=dict(timeout_s=1800.,reserve_s=1800.)
    cfg,wiring=resolve_candidate(host.store,choice.candidate,source,choice,owner,policy)
    construction=time.perf_counter()-started
    with host.store.transaction() as db:
        cfg_ref=host.store.put(db,cfg);wiring_ref=host.store.put(db,dict(wiring,resolved_configuration=plain(cfg_ref),plan_reference=plan_reference,revision=revision))
        state=host.store.session(ACTIVITY,db)['state']
        if state['numerical_s']+construction+1890>CEILINGS['total_numerical_s'] or time.time()+1890>=state['cutoff_unix']:
            raise ValueError('CLOSED_LOOP_CANNOT_FIT_SCIENTIFIC_ALLOWANCE')
        if host.store.remaining()['remaining']['backend_solves']<=0:raise ValueError('TWO_CLOSED_LOOP_LAUNCH_CEILING')
        state['pending']=dict(operation='closed_loop',owner_run_id=owner,configuration=plain(cfg_ref),
            wiring=plain(wiring_ref),candidate=plain(choice.candidate),control=plain(choice),plan_reference=plan_reference,
            revision=revision,construction_s=construction,started_unix=time.time())
        host.store.update_state(db,ACTIVITY,state)
        host.store.event(db,ACTIVITY,'closed_loop_eligibility','exploratory',outputs=[wiring_ref,cfg_ref])
    child=Host(host.store.root,owner,actor=host.actor)
    child.create(cfg,parent_run_id=ACTIVITY)
    return finish_closed_loop(host,child,started)


def finish_closed_loop(host, child=None, started=None):
    """Recovery continues sealed receipts; never replaces or relaunches a simulation."""
    from tools.platform_host import Host
    from tools.execution_completion import complete_execution
    from tools.research_tasks import assemble_acceptance
    from tools.casadi_feedback_service import ACTIVITY
    state=host.store.session(ACTIVITY)['state'];pending=state['pending']
    owner=pending['owner_run_id'];cfg=host.store.artifact(pending['configuration'])
    child=child or Host(host.store.root,owner,actor=host.actor)
    if started is None:
        if child.store.lookup(owner,'complete-simulation') is None:
            raise ValueError('RECOVERY_REQUIRES_EXISTING_LAUNCH_INSPECT_BEFORE_REPEAT')
        started=time.perf_counter()
    result=complete_execution(child,cfg,owner)
    receipts=result.get('receipts',{});profile=None;motion=[];acceptance=None
    if result['status']=='evaluated':
        profile=host.store.artifact(result['profile_report']['reference'])['detail']
        motion=host.store.artifact(profile['motion'])
        acceptance=assemble_acceptance(cfg,result['evaluation_data'],profile,
            evaluation_reference=receipts['evaluation']['output'],profile_reference=receipts['profile']['output'],motion=motion)
    partial=None;partial_s=0.
    if profile is None:
        inspection=time.perf_counter()
        partial=saved_partial_feedback(host.store,receipts)
        partial_s=time.perf_counter()-inspection
    costs={k:r['charged']['wall_s'] for k,r in receipts.items()}
    if partial_s:costs['saved_state_feedback']=partial_s
    costs.update(construction=pending['construction_s'],total=pending['construction_s']+sum(costs.values()))
    failures=[]
    if result['status']=='execution_unresolved':failures.append('missing_evidence_unknown_execution')
    elif result['status']=='execution_incomplete':failures.append('engineering_failure')
    if profile:
        reason=profile.get('execution_failure_reason') or ''
        if profile['solver_error_count'] or profile['unusable_plans'] or 'NUMERICAL' in reason:
            failures.append('numerical_failure')
        if acceptance and acceptance['status']=='valid_failure':failures.append('scientific_failure')
        if not profile['complete'] or acceptance.get('missing'):failures.append('missing_evidence')
    detail=dict(status=result['status'],candidate=pending['candidate'],control=pending['control'],
        plan_reference=pending['plan_reference'],revision=pending['revision'],resolved_configuration=pending['configuration'],
        wiring_reference=pending['wiring'],execution=result,acceptance=acceptance,profile=profile,
        holding_motion=[r for r in motion if .30-1e-9<=r['time_s']<=.35+1e-9],
        sampling=dict(closed_loop_s=.01,holding_endpoint_included=True,historical_bdf_s=.0005,continuous_time_guarantee=False),
        costs_s=costs,unknowns=[] if profile else ['Acceptance and complete control/model feedback unavailable; inspect retained receipts/artifacts'],
        failure_categories=failures,
        execution_references=dict(owner_run_id=owner,receipts=receipts,execution_id=result.get('execution_id'),executed_configuration=result.get('configuration')),
        partial_feedback=partial,
        actual_duration_s=(partial or {}).get('actual_duration_s') if profile is None else profile['last_valid_time_s'],
        completed_control_updates=(partial or {}).get('applied_control_updates') if profile is None else profile.get('applied_control_updates',profile['updates']),
        nmpc_internal_solves=(partial or {}).get('attempted_control_plans') if profile is None else profile['updates'],offline_nlp_slots_charged=0)
    with host.store.transaction() as db:
        ref=host.store.put(db,detail);state=host.store.session(ACTIVITY,db)['state']
        # Charge stages once even if reporting is recovered from existing receipts.
        accounted=state.setdefault('closed_loop_accounted',{})
        previous=accounted.get(owner,0.);state['numerical_s']+=max(0.,costs['total']-previous);accounted[owner]=costs['total']
        if result['status']=='execution_unresolved':state['pending']['retained_result']=plain(ref)
        else:
            state.pop('pending',None)
            state['results'].append(dict(operation='closed_loop',reference=plain(ref),candidate=pending['candidate'],owner_run_id=owner,status=result['status']))
        if result['status']=='execution_incomplete':state['engineering_pause']=dict(reference=plain(ref),reason='Execution chain incomplete; inspect partial evidence before repair')
        host.store.update_state(db,ACTIVITY,state)
        host.store.event(db,ACTIVITY,'closed_loop_feedback',result['status'],outputs=[ref])
    return dict(detail=detail,evidence_reference=plain(ref))


def saved_partial_feedback(store, receipts):
    """Inspect sealed exports after a failed stage; never replace the execution."""
    from extensions.tendon_family.control_evidence import ControlEvidence
    from extensions.tendon_family.gvs_reporting import reconstruct_motion,summarize
    from extensions.tendon_family.gvs_profile import settling_for
    sim=receipts.get('simulation',{})
    if not sim.get('output') or sim.get('execution_status')=='unknown':
        return dict(available=False,missing=['No confirmed simulation output'],termination_reason=sim.get('error'))
    try:
        reader=ControlEvidence(store);source=reader.resolve(sim['execution_id'])
        rows=reader.read_file(source,'trajectory.json.gz',[]);observations=reader.read_file(source,'controller_observations.json',[])
        files={name:store.artifact(ref,raw=True) for name,ref in source['files'].items()}
        task=SessionInput.model_validate(source['configuration']).task
        motion,physics=reconstruct_motion(files,rows,task.goal.data['target_m'])
        evaluation=store.artifact(receipts['evaluation']['output']) if receipts.get('evaluation',{}).get('output') else None
        report=summarize(task,store.artifact(sim['output']),evaluation,rows,observations,motion,
            [t['force_limit_n'] for t in physics['tendons']],settling_for(SessionInput.model_validate(source['configuration'])))
        return dict(available=True,source_execution=sim['execution_id'],manifest=source['manifest'],
            scope='Partial saved-state inspection; no completed profile receipt or changed acceptance',profile=report,
            actual_duration_s=report['last_valid_time_s'],attempted_control_plans=len(observations),
            applied_control_updates=sum(o.get('actual_tension_n') is not None for o in observations),
            termination_reason=report['execution_failure_reason'] or sim.get('error'),
            holding_motion=[m for m in motion if .30-1e-9<=m['time_s']<=.35+1e-9],
            missing=['Authoritative completed profile and acceptance remain unavailable'])
    except (ValueError,KeyError) as exc:
        return dict(available=False,missing=[str(exc)],termination_reason=sim.get('error'))
