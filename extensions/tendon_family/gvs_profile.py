"""Versioned, fixed-scope control recipe and explicit historical numerical data.

Loading is solve-free. The imported plan is a guess; execution regenerates its
states from measurements and independently validates every delivered plan.
"""
import json
import time
from pathlib import Path
from typing import Literal
import numpy as np
from pydantic import Field, FiniteFloat
from schemas.common import Contract
from schemas.platform import EvidenceRef, Payload, SessionInput
from tools.platform_store import plain
from tools.state_io import digest
from .contracts import GVSTrajectoryParameters
from .gvs_basis import resolve_basis

PROFILE_ID = 'gvs_nmpc_free_reach_v1'
ASSET = 'extensions/tendon_family/profiles/gvs_nmpc_free_reach_v1.json'


class ProfileControl(Contract):
    profile_id: Literal['gvs_nmpc_free_reach_v1'] = PROFILE_ID


class SampledSettling(Contract):
    window_s: FiniteFloat = Field(default=.05,gt=0)
    position_limit_m: FiniteFloat = Field(default=.01,gt=0)
    speed_limit_m_s: FiniteFloat = Field(default=.02,gt=0)


class ReachControl(Contract):
    """Task owns target/initialization/timing; this payload owns only control."""
    recipe: GVSTrajectoryParameters
    settling: SampledSettling
    numerical_source: Literal['bundled_guess', 'initial_state_pretension'] = 'bundled_guess'


def reach_input(run_id, *, target_m=None, initial=None, timing=None, recipe=None, settling=None,
                numerical_source='bundled_guess'):
    """Public, solve-free v3 input. The fixed v2 asset remains unchanged."""
    value=profile_input(run_id)
    if target_m is not None:value['task']['goal']['data']['target_m']=list(target_m)
    if initial is not None:value['task']['initializer']['parameters']['data']=initial
    if timing is not None:value['task']['timing'].update(timing)
    parameters=dict(load_profile()['parameters'])
    if recipe is not None:parameters.update(recipe)
    control=ReachControl(recipe=parameters,settling=settling or SampledSettling(),numerical_source=numerical_source)
    value['policy']['controller']=dict(extension_id='controller.gvs_nmpc',version='3.0.0',
        parameters=dict(contract='family.gvs_reach_control',version='1.0.0',data=plain(control)))
    return SessionInput.model_validate(value).model_dump(mode='json')


def candidate_reach_input(run_id, *, robot=None, **kwargs):
    """Solve-free v4 length-design path; authorization belongs to the input space."""
    value=reach_input(run_id,**kwargs)
    value['policy']['controller']['version']='4.0.0'
    if robot is not None:value['robot']=plain(robot)
    checked_reach(SessionInput.model_validate(value))
    return value


def checked_reach(inp):
    """Compatibility, not performance validation. No graph construction/solve."""
    inp=SessionInput.model_validate(inp)
    control=ReachControl.model_validate(inp.policy.controller.parameters.data)
    baseline=load_profile();old=SessionInput.model_validate(baseline['session_input'])
    # Keep numerical source integrity/order/bounds checks from the fixed path.
    checked_profile(old)
    candidate_robot=plain(inp.robot)
    if inp.policy.controller.version=='4.0.0':
        # Support length changes only. Topology, sections, materials, damping,
        # attachments and actuator/tendon declarations keep their proven meaning.
        # The public builder enforces the experiment's separately declared bounds.
        historical={c['id']:c for c in old.robot.structure.data['components']}
        for component in candidate_robot['structure']['data']['components']:
            source=historical.get(component['id'])
            if source and component['kind']==source['kind']=='flexible_segment':
                length=component['length_m']
                if not np.isfinite(length) or length<=0:raise ValueError('GVS_REACH_INVALID_LENGTH')
                component['length_m']=source['length_m']
    if inp.policy.controller.version in ('6.0.0','7.0.0','8.0.0'):
        from .design_decisions import normalize_supported
        normalize_supported(candidate_robot['structure']['data'], plain(old.robot)['structure']['data'])
    fixed=(candidate_robot==plain(old.robot) and plain(inp.task.environment)==plain(old.task.environment)
        and all(plain(getattr(inp.policy,k))==plain(getattr(old.policy,k))
                for k in ('backend','dynamics_model','discretization')))
    task_before,task_after=plain(old.task),plain(inp.task)
    if (inp.policy.controller.version=='7.0.0' and inp.seed in (17,18)
            and task_after['sampling']['seeds']==[inp.seed]):
        # The frozen reach/hold study predeclares fresh repetitions 17 and 18.
        # Seed labels affect instance provenance, not target, physical timing,
        # acceptance, initialization mapping or stable-v7 solver behavior.
        task_before['sampling']['seeds']=list(task_after['sampling']['seeds'])
    for task in (task_before,task_after):
        for key in ('goal','initializer','timing'):task.pop(key)
    if not fixed or task_before!=task_after:
        raise ValueError('GVS_REACH_UNSUPPORTED_PHYSICS_OR_TASK: supported robot envelope, free-reach evaluator and physical scene required')
    if inp.task.goal.contract!=old.task.goal.contract or inp.task.goal.version!=old.task.goal.version:
        raise ValueError('GVS_REACH_GOAL_CONTRACT')
    if (inp.task.initializer.extension_id!=old.task.initializer.extension_id or
        inp.task.initializer.version!=old.task.initializer.version or
        inp.task.initializer.parameters.contract!=old.task.initializer.parameters.contract):
        raise ValueError('GVS_REACH_INITIALIZER_CONTRACT')
    from .contracts import Initial
    from .backends import physics_for
    initial=Initial.model_validate(inp.task.initializer.parameters.data)
    physics=physics_for(inp)
    for values,limit in ((initial.qpos_rad,.05),(initial.qvel_rad_s,.5)):
        if set(values)-set(physics['dofs']) or any(not np.isfinite(v) or abs(v)>limit for v in values.values()):
            raise ValueError('GVS_REACH_SMALL_NAMED_INITIAL_STATE_REQUIRED: |q|<=0.05 rad, |v|<=0.5 rad/s')
    p=control.recipe
    if plain(p.basis)!=plain(GVSTrajectoryParameters.model_validate(baseline['parameters']).basis):
        raise ValueError('GVS_REACH_BASIS_UNSUPPORTED')
    if not p.regenerate_warm_states:raise ValueError('GVS_REACH_MEASURED_WARM_REGENERATION_REQUIRED')
    t=inp.task.timing
    if (t.sample_period_s!=t.control_period_s or control.settling.window_s>t.duration_s or
        any(abs(v-round(v))>1e-8 for v in (t.duration_s/t.control_period_s,
            t.control_period_s/t.timestep_s,control.settling.window_s/t.sample_period_s))):
        raise ValueError('GVS_REACH_TIMING_AND_SETTLING_GRID_REQUIRED')
    return control


def reach_assessment(inp):
    control=checked_reach(inp)
    from .model_applicability import assess_model_uses
    from .contracts import GVSModelParameters
    from schemas.platform import Binding
    model=Binding(extension_id='model.gvs',parameters=Payload(contract='family.gvs_model',
        data=plain(GVSModelParameters(basis=control.recipe.basis))))
    assessment=assess_model_uses(inp.robot,inp.task,model,['reduced_dynamics','local_model_control'])
    old=SessionInput.model_validate(load_profile()['session_input'])
    return dict(technical_compatibility=dict(status='supported',reason='Length, uniform section scaling, material density/elasticity/declared viscosity; unchanged topology and routing' if inp.policy.controller.version in ('6.0.0','7.0.0','8.0.0') else 'Length-only candidate envelope' if inp.policy.controller.version=='4.0.0' else 'Same fixed robot/free-space execution; task-owned target, small named initial state and timing',
            model_use_assessment=plain(assessment)),
        historical_evidence=dict(status='unvalidated_configuration',exact_execution_scope_match=False,
            historical_task_match=plain(inp.task)==plain(old.task),
            historical_robot_match=plain(inp.robot)==plain(old.robot),
            reason='Fixed v2 success does not validate changed designs, targets, timing, initial states, recipes or acceptance conditions',
            sources=load_profile()['historical_evidence']),
        execution_preparation=dict(status='pending_execution_hook',source=control.numerical_source,
            next_step='simulation.run imports/generates and seals numerical guesses under its reserved wall/one-backend budget; actual-state regeneration and validation occur in each update'))


def reach_numerical(inp):
    """Target-independent guesses only, not a claimed new equilibrium solution."""
    control=checked_reach(inp);p=control.recipe;baseline=load_profile()
    if inp.policy.controller.version in ('4.0.0','6.0.0','7.0.0','8.0.0'):
        return candidate_numerical(inp,control,baseline)
    from copy import deepcopy
    numerical=deepcopy(baseline['numerical']);n=len(numerical['coordinate_order'])
    if control.numerical_source=='bundled_guess':
        seed=numerical['warm_guess'];old_period=baseline['session_input']['task']['timing']['control_period_s']
        old_substeps=baseline['parameters']['substeps'];period=inp.task.timing.control_period_s
        old_x=np.asarray(seed['states']);old_u=np.asarray(seed['tensions'])
        # Resample only the guess; physical state trajectories are regenerated.
        old_times=np.arange(len(old_x))*old_period/old_substeps
        times=np.arange(p.horizon*p.substeps+1)*period/p.substeps
        numerical['warm_guess']=dict(states=np.column_stack([np.interp(times,old_times,old_x[:,j]) for j in range(2*n)]).tolist(),
            tensions=old_u[np.minimum((np.arange(p.horizon)*period/old_period+1e-9).astype(int),len(old_u)-1)].tolist())
        provenance=dict(historical_source=baseline['numerical_reference'],source_kind='compatible_historical_guess',reused=True,
            nominal_target_world_m=baseline['session_input']['task']['goal']['data']['target_m'],
            nominal_is_current_target_solution=False)
    else:
        from .backends import physics_for
        from .gvs_projection import project
        physics=physics_for(inp);initial=inp.task.initializer.parameters.data
        state=project(physics,resolve_basis(inp.robot.structure.data,p.basis),
            [initial.get('qpos_rad',{}).get(j,0.) for j in physics['dofs']],
            [initial.get('qvel_rad_s',{}).get(j,0.) for j in physics['dofs']])
        x=state['q_gvs']+state['qdot_gvs']
        u=[min(t['force_limit_n'],max(0.,t['pretension_n'])) for t in inp.robot.structure.data['tendons']]
        numerical['nominal']=dict(q0=x[:n],u0=u,source='initial_state_pretension_guess_not_equilibrium')
        numerical['warm_guess']=dict(states=[x]*(p.horizon*p.substeps+1),tensions=[u]*p.horizon)
        provenance=dict(source_kind='project_initial_state_and_bounded_pretension',reused=False,nominal_is_current_target_solution=False)
    numerical['provenance']=dict(**provenance,current_scope=execution_scope(inp),
        actual_initial_state_source='Task initializer then measured backend state at every update',
        validity='compatible finite bounded numerical guess; no dynamic feasibility or task success asserted')
    return numerical


def candidate_numerical(inp,control,baseline):
    """Candidate-owned dimensions/initial metadata; historical inputs are guesses only.

    No dynamics solves here: the execution-local workspace regenerates all states
    with this candidate's dynamics and the current measurement before optimization.
    """
    from .backends import physics_for
    from .gvs_projection import project
    p=control.recipe;physics=physics_for(inp)
    basis=resolve_basis(inp.robot.structure.data,p.basis)
    initial=inp.task.initializer.parameters.data
    state=project(physics,basis,
        [initial.get('qpos_rad',{}).get(j,0.) for j in physics['dofs']],
        [initial.get('qvel_rad_s',{}).get(j,0.) for j in physics['dofs']])
    x=state['q_gvs']+state['qdot_gvs'];n=len(basis.coordinate_order)
    tendon_order=[t['entity'] for t in physics['tendons']]
    limits=np.array([t['force_limit_n'] for t in physics['tendons']])
    previous=np.clip([t['pretension_n'] for t in physics['tendons']],0,limits)
    old=baseline['numerical'];seed=old['warm_guess']
    compatible=(old['tendon_order']==tendon_order and old['units']['tension']=='N'
        and np.asarray(seed['tensions']).shape[1:]==(len(tendon_order),))
    reused=control.numerical_source=='bundled_guess' and compatible
    if reused:
        old_period=baseline['session_input']['task']['timing']['control_period_s']
        indices=np.minimum((np.arange(p.horizon)*inp.task.timing.control_period_s/old_period+1e-9).astype(int),len(seed['tensions'])-1)
        tensions=np.clip(np.asarray(seed['tensions'])[indices],0,limits)
        # Preserve the recipe's declared initial applied input, without treating
        # the historical nominal state as an equilibrium for the new robot.
        previous=np.clip(old['nominal']['u0'],0,limits)
    else:tensions=np.tile(previous,(p.horizon,1))
    provenance=dict(source_kind='compatible_historical_tensions_only' if reused else 'project_initial_state_and_bounded_pretension',
        reused=reused,nominal_is_current_target_solution=False,
        historical_states_reused=False,current_scope=execution_scope(inp),
        physics_identity=physics['identity'],resolved_basis_identity=digest(plain(basis)),
        actual_initial_state_source='Candidate Task initializer then measured backend state at every update',
        previous_input_source='compatible bounded historical initial input' if reused else 'candidate bounded pretension',
        validity='Tensions are numerical guesses; placeholder states must be regenerated using candidate dynamics before use')
    if reused:provenance['historical_source']=baseline['numerical_reference']
    return dict(coordinate_order=list(basis.coordinate_order),tendon_order=tendon_order,
        units=dict(q='rad/m',qdot='rad/(m*s)',tension='N'),force_limits_n=limits.tolist(),
        measured_initial_state=x,
        nominal=dict(q0=x[:n],u0=previous.tolist(),source='candidate_initial_projection_not_equilibrium'),
        warm_guess=dict(states=[x]*(p.horizon*p.substeps+1),tensions=tensions.tolist()),provenance=provenance)


def checked_control(inp):
    if inp.policy.controller.version=='5.0.0':
        from .tracking import checked_tracking
        return checked_tracking(inp)
    if inp.policy.controller.version in ('3.0.0','4.0.0','6.0.0','7.0.0','8.0.0'):
        checked_reach(inp)
    else:checked_profile(inp)


def settling_for(inp):
    return checked_reach(inp).settling if inp.policy.controller.version in ('3.0.0','4.0.0','6.0.0','7.0.0','8.0.0') else SampledSettling()


class ProfileOutput(Contract):
    detail: dict


class ProfileReportRequest(Contract):
    simulation_request_id: str
    evaluation_request_id: str


class ProfileStrategyRequest(Contract):
    skill_ref: str


def load_profile():
    from tools.spec_tools import ROOT
    return json.loads((ROOT / ASSET).read_text(encoding='utf8'))


def execution_scope(value):
    """Facts that bound performance evidence; run IDs and budgets are excluded."""
    inp = SessionInput.model_validate(value)
    return dict(robot=dict(family=inp.robot.family,identity=digest(plain(inp.robot))),
        task=dict(family=inp.task.family,identity=digest(plain(inp.task)),
            environment=digest(plain(inp.task.environment)),goal=digest(plain(inp.task.goal)),
            timing=plain(inp.task.timing),initializer=digest(plain(inp.task.initializer))),backend=plain(inp.policy.backend),
        execution_model=plain(inp.policy.dynamics_model), discretization=plain(inp.policy.discretization),
        controller=plain(inp.policy.controller), seed=inp.seed)


def checked_profile(inp):
    profile = load_profile()
    if execution_scope(inp) != profile['scope']:
        raise ValueError('GVS_PROFILE_SCOPE_MISMATCH: fixed design, task, initialization, execution and timing required')
    numerical = profile['numerical']
    if digest(numerical) != profile['numerical_reference']['artifact_id']:
        raise ValueError('GVS_PROFILE_NUMERICAL_IDENTITY_MISMATCH')
    p = GVSTrajectoryParameters.model_validate(profile['parameters'])
    order = list(resolve_basis(inp.robot.structure.data, p.basis).coordinate_order)
    tendons = [t['id'] for t in inp.robot.structure.data['tendons']]
    if (numerical['coordinate_order'] != order or numerical['tendon_order'] != tendons
            or numerical['units'] != dict(q='rad/m', qdot='rad/(m*s)', tension='N')):
        raise ValueError('GVS_PROFILE_ORDER_OR_UNITS_MISMATCH')
    n, m = len(order), len(tendons)
    point, seed = numerical['nominal'], numerical['warm_guess']
    X, U = np.asarray(seed['states']), np.asarray(seed['tensions'])
    limits = np.array([t['force_limit_n'] for t in inp.robot.structure.data['tendons']])
    if (len(point['q0']) != n or len(point['u0']) != m
            or X.shape != (p.horizon*p.substeps+1, 2*n) or U.shape != (p.horizon, m)
            or not np.isfinite(X).all() or not np.isfinite(U).all()
            or np.any(U < -1e-6) or np.any(U > limits+1e-6)):
        raise ValueError('GVS_PROFILE_NUMERICAL_DIMENSIONS_OR_BOUNDS')
    return profile


def profile_input(run_id):
    """Public Python configuration entry point; no Store or process cache needed."""
    value = load_profile()['session_input']
    value['run_id'] = run_id
    return SessionInput.model_validate(value).model_dump(mode='json')


def summary(profile=None):
    p = profile or load_profile()
    return {k:p[k] for k in ('profile_id','predictor','execution','initialization_policy',
        'scope_description','limitations','historical_cost','historical_evidence','numerical_reference')}


def describe(ctx, args):
    if ctx.input.policy.controller.version=='5.0.0':
        from .tracking import assessment
        return ProfileOutput(detail=dict(controller=plain(ctx.input.policy.controller),execution_scope=execution_scope(ctx.input),**assessment(ctx.input)))
    if ctx.input.policy.controller.version in ('3.0.0','4.0.0','6.0.0','7.0.0','8.0.0'):
        return ProfileOutput(detail=dict(controller=plain(ctx.input.policy.controller),
            execution_scope=execution_scope(ctx.input),**reach_assessment(ctx.input),
            execution_authorization=dict(simulation_tool_granted='simulation.run' in ctx.input.policy.tool_bindings,
                session_budget=ctx.store.remaining(ctx.run_id),project_budget=ctx.store.remaining()),
            authority='Task goal/initializer/timing; controller recipe; separately frozen sampled settling',
            effective_settling=plain(settling_for(ctx.input)),
            invocation='reach_input(run_id, target_m=..., initial=..., recipe=..., settling=...); simulation.run, evaluation.run, control.profile_report'))
    profile = load_profile()
    numerical = ctx.save_artifact(profile['numerical'], 'historical_numerical_import')
    reference = ctx.save_artifact(profile, 'control_profile')
    return ProfileOutput(detail=dict(**{k:v for k,v in summary(profile).items() if k!='numerical_reference'},
        profile_reference=plain(reference), numerical_reference=plain(numerical),
        controller=profile['session_input']['policy']['controller'],
        applicability='matching' if execution_scope(ctx.input)==profile['scope'] else 'incompatible',
        invocation='Select the declared controller Binding and frozen profile configuration; simulation.run then evaluation.run. Python: profile_input(new_run_id).'))


def prepare_execution(ctx, controller, inp):
    """Budgeted public execution hook. Imports data, never injects a cache."""
    started = time.perf_counter()
    try:
        if inp.policy.controller.version in ('3.0.0','4.0.0','5.0.0','6.0.0','7.0.0','8.0.0'):
            numerical=candidate_numerical(inp,checked_control(inp),load_profile()) if inp.policy.controller.version=='5.0.0' else reach_numerical(inp)
            historical=numerical['provenance'].get('historical_source')
            if historical is not None:
                imported=ctx.save_artifact(load_profile()['numerical'],'historical_numerical_import')
                if plain(imported)!=historical:
                    raise ValueError('GVS_REACH_HISTORICAL_SOURCE_IDENTITY_MISMATCH')
            ref=ctx.save_artifact(numerical,'control_numerical_guess')
            controller.profile=dict(numerical=numerical)
            controller.preparation=dict(status='completed',wall_s=time.perf_counter()-started,
                source=plain(ref),**numerical['provenance'],coordinate_order=numerical['coordinate_order'],
                tendon_order=numerical['tendon_order'],units=numerical['units'],
                force_limits_n=numerical.get('force_limits_n'),
                warm_guess_is_execution_evidence=False,execution_scope=execution_scope(inp),
                cost_accounting='Included in simulation.run reserved/charged wall time; graph/solver construction and state regeneration are separate execution costs')
            ctx.save_artifact(controller.preparation,'control_preparation')
            return
        profile = checked_profile(inp)
        ref = ctx.save_artifact(profile['numerical'], 'historical_numerical_import')
        if plain(ref) != profile['numerical_reference']:
            raise ValueError('GVS_PROFILE_IMPORT_REFERENCE_MISMATCH')
        controller.preparation = dict(status='completed', wall_s=time.perf_counter()-started,
            source=plain(ref), source_kind='explicit_historical_numerical_import',
            warm_guess_is_execution_evidence=False,
            current_state='backend measurement at each control interval',
            previous_input='declared initial nominal tension, then last applied bounded command',
            regeneration='entire warm state trajectory; independently checked in each update')
        ctx.save_artifact(controller.preparation, 'control_preparation')
    except ValueError as exc:
        ctx.save_artifact(dict(status='failed', wall_s=time.perf_counter()-started, reason=str(exc)), 'control_preparation')
        raise


def declare_strategy(ctx, args):
    from tools.platform_skills import library
    from tools.skill_policy import strategy_hash
    skill = library(ctx.host).get(args.skill_ref)
    checked_control(ctx.input)
    if skill.applicability.execution_scope != execution_scope(ctx.input):
        raise ValueError('STRATEGY_SCOPE_MISMATCH')
    with ctx.store.transaction() as db:
        session = ctx.store.session(ctx.run_id, db)
        if session['state'].get('result_executions'):
            raise ValueError('STRATEGY_MUST_PRECEDE_EXECUTION')
        state = session['state']
        declaration = dict(skill_ref=skill.reference, strategy_sha256=strategy_hash(skill))
        state['control_profile_strategy'] = declaration
        ctx.store.update_state(db, ctx.run_id, state)
    return ProfileOutput(detail=declaration)
