"""Candidate-owned control preparation and execution scope; no historical defaults."""
import time
import numpy as np
from typing import Literal
from pydantic import Field,FiniteFloat
from schemas.common import Contract
from schemas.platform import Payload,SessionInput
from tools.platform_store import plain
from tools.state_io import digest
from .contracts import GVSTrajectoryParameters
from .gvs_basis import resolve_basis
class SampledSettling(Contract):
    window_s: FiniteFloat = Field(default=.05,gt=0)
    position_limit_m: FiniteFloat = Field(default=.01,gt=0)
    speed_limit_m_s: FiniteFloat = Field(default=.02,gt=0)

class ReachControl(Contract):
    """Task owns target/initialization/timing; this payload owns only control."""
    recipe: GVSTrajectoryParameters
    settling: SampledSettling
    numerical_source: Literal['bundled_guess', 'initial_state_pretension'] = 'bundled_guess'

def candidate_numerical(inp,control,baseline=None):
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
    old=baseline['numerical'] if baseline is not None else None
    seed=old['warm_guess'] if old else None
    compatible=bool(old) and (old['tendon_order']==tendon_order and old['units']['tension']=='N'
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

def execution_scope(value):
    """Facts that bound performance evidence; run IDs and budgets are excluded."""
    inp = SessionInput.model_validate(value)
    return dict(robot=dict(family=inp.robot.family,identity=digest(plain(inp.robot))),
        task=dict(family=inp.task.family,identity=digest(plain(inp.task)),
            environment=digest(plain(inp.task.environment)),goal=digest(plain(inp.task.goal)),
            timing=plain(inp.task.timing),initializer=digest(plain(inp.task.initializer))),backend=plain(inp.policy.backend),
        execution_model=plain(inp.policy.dynamics_model), discretization=plain(inp.policy.discretization),
        controller=plain(inp.policy.controller), seed=inp.seed)

class ProfileOutput(Contract):
    detail: dict


def checked_reach(inp):
    from .generated_serial import checked_reach as check
    return check(inp)


def checked_control(inp):
    return checked_reach(inp)


def settling_for(inp):
    return checked_reach(inp).settling


def reach_numerical(inp):
    return candidate_numerical(inp,checked_reach(inp))


def reach_assessment(inp):
    inp=SessionInput.model_validate(inp)
    checked_reach(inp)
    return dict(technical_compatibility=dict(status='supported',reason=f'Explicit frozen source with candidate-owned dimensions and pretension; two segments, {len(inp.robot.structure.data["tendons"])} ideal tensions'),
        historical_evidence=dict(status='not_transferred',exact_execution_scope_match=False,reason='Only fresh evaluation measures this candidate'),
        execution_preparation=dict(status='pending_execution_hook',source='initial_state_pretension'))


def prepare_execution(ctx,controller,inp):
    started=time.perf_counter();numerical=reach_numerical(inp)
    ref=ctx.save_artifact(numerical,'control_numerical_guess')
    controller.profile=dict(numerical=numerical)
    controller.preparation=dict(status='completed',wall_s=time.perf_counter()-started,source=plain(ref),
        **numerical['provenance'],coordinate_order=numerical['coordinate_order'],tendon_order=numerical['tendon_order'],
        units=numerical['units'],force_limits_n=numerical['force_limits_n'],warm_guess_is_execution_evidence=False,
        execution_scope=execution_scope(inp),cost_accounting='Included in complete-execution reservation/charge')
    ctx.save_artifact(controller.preparation,'control_preparation')

class ProfileReportRequest(Contract):
    simulation_request_id: str
    evaluation_request_id: str
