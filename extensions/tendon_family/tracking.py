"""Frozen world/SI time references and independently sampled tracking acceptance."""
from typing import Literal
import numpy as np
from pydantic import Field, FiniteFloat, model_validator
from schemas.common import Contract
from schemas.platform import EvaluationResult, Metric, ConstraintResult, SessionInput
from tools.platform_store import plain
from .contracts import GVSTrajectoryParameters


class CartesianReference(Contract):
    frame: Literal['world'] = 'world'
    units: Literal['SI'] = 'SI'
    interpolation: Literal['constant', 'quintic']
    start_s: FiniteFloat = Field(ge=0)
    end_s: FiniteFloat = Field(gt=0)
    start_m: tuple[FiniteFloat, FiniteFloat, FiniteFloat]
    end_m: tuple[FiniteFloat, FiniteFloat, FiniteFloat]
    outside: Literal['clamp_position_zero_velocity'] = 'clamp_position_zero_velocity'
    provenance: str = Field(min_length=1)

    @model_validator(mode='after')
    def interval(self):
        if self.end_s <= self.start_s:
            raise ValueError('REFERENCE_INTERVAL_REQUIRED')
        if self.interpolation == 'constant' and self.start_m != self.end_m:
            raise ValueError('CONSTANT_REFERENCE_ENDPOINTS_MUST_MATCH')
        return self


def reference_at(reference, times):
    r = CartesianReference.model_validate(reference)
    times = np.asarray(times, dtype=float)
    if not np.isfinite(times).all():
        raise ValueError('FINITE_REFERENCE_TIMES_REQUIRED')
    s = np.clip((times-r.start_s)/(r.end_s-r.start_s), 0., 1.)
    delta = np.asarray(r.end_m)-r.start_m
    blend = 10*s**3-15*s**4+6*s**5
    rate = 30*s**2*(1-s)**2/(r.end_s-r.start_s)
    return np.asarray(r.start_m)+blend[..., None]*delta, rate[..., None]*delta


class TrackingEvaluation(Contract):
    max_position_error_m: FiniteFloat = Field(default=.01, gt=0)
    tension_limits_n: dict[str, FiniteFloat] = Field(min_length=1)
    sampling: Literal['uniform_samples_inclusive_arithmetic_rms'] = 'uniform_samples_inclusive_arithmetic_rms'


class TrackingControl(Contract):
    recipe: GVSTrajectoryParameters
    numerical_source: Literal['bundled_guess', 'initial_state_pretension'] = 'initial_state_pretension'


def tracking_task(task, reg):
    from schemas.platform import SignalSpec
    from extensions.reference.contracts import Empty
    if not isinstance(reg.parse(task.goal), CartesianReference) or task.evaluator.extension_id != 'evaluate.tracking':
        raise ValueError('TRACKING_REFERENCE_AND_EVALUATOR_REQUIRED')
    if not isinstance(reg.parse(task.evaluator.parameters), TrackingEvaluation):
        raise ValueError('TRACKING_EVALUATION_CONTRACT_REQUIRED')
    spec = SignalSpec(name='tip_position', entity='tip', dimension=3, units='m', frame='world', phase='post_step')
    if spec not in task.observations:
        raise ValueError('TRACKING_SAMPLED_WORLD_TIP_REQUIRED')
    grid = task.timing.sample_period_s
    if task.sampling.window_s[0] < grid-1e-9:
        raise ValueError('TRACKING_POST_STEP_SCORING_STARTS_AT_FIRST_SAMPLE')
    if any(abs(t/grid-round(t/grid)) > 1e-8 for t in (*task.sampling.window_s, task.timing.duration_s)):
        raise ValueError('TRACKING_SCORING_BOUNDARIES_MUST_BE_SAMPLED')
    if any(o.metric != 'max_position_error' or o.units != 'm' for o in task.objectives):
        raise ValueError('TRACKING_OBJECTIVE_REQUIRED')
    return Empty()


def evaluate_tracking(task, result, source, reg, identity):
    base = dict(source=source, evaluator=task.evaluator.extension_id, comparison_identity=identity)
    def invalid(reason):
        return EvaluationResult(**base, validity='incomplete', task_success=None, metrics=[], constraints=[], reason=reason)
    if result.solver_status != 'completed':
        return invalid('EXECUTION_NOT_COMPLETE')
    spec = next(s for s in task.observations if s.name == 'tip_position')
    signal = next((s for s in result.signals if s.spec == spec), None)
    times = np.arange(1,round(task.timing.duration_s/task.timing.sample_period_s)+1)*task.timing.sample_period_s
    if signal is None or len(signal.times_s) != len(times) or not np.allclose(signal.times_s, times, rtol=0, atol=1e-8):
        return invalid('MISSING_OR_INCOMPLETE_SAMPLES')
    actual = np.asarray(signal.values)
    if not np.isfinite(actual).all():
        return invalid('NONFINITE_MOTION')
    desired, _ = reference_at(task.goal.data, times)
    errors = np.linalg.norm(actual-desired, axis=1)
    lo, hi = task.sampling.window_s
    scored = errors[(times >= lo-1e-9) & (times <= hi+1e-9)]
    parameters = reg.parse(task.evaluator.parameters)
    limit = parameters.max_position_error_m
    force_constraints=[]
    for entity,bound in parameters.tension_limits_n.items():
        force=next((s for s in result.signals if s.spec.name=='tendon_tension' and s.spec.entity==entity
            and s.spec.units=='N' and s.spec.frame=='path' and s.spec.phase=='pre_step_solver'),None)
        if force is None or len(force.times_s)!=len(times) or not np.allclose(force.times_s,times-task.timing.sample_period_s,rtol=0,atol=1e-8):
            return invalid('MISSING_TENSION_SAMPLES')
        values=np.asarray(force.values)
        if not np.isfinite(values).all():return invalid('NONFINITE_TENSION')
        violation=float(max(0.,np.max(-values),np.max(values-bound)))
        force_constraints.append(ConstraintResult(name='tension_bound_'+entity,satisfied=violation<=1e-8,
            observed=violation,limit=1e-8,units='N'))
    maximum = float(max(scored))
    return EvaluationResult(**base, validity='valid', task_success=maximum <= limit and all(c.satisfied for c in force_constraints),
        metrics=[Metric(name=n, value=v, units='m') for n, v in (
            ('max_position_error', maximum), ('rms_position_error', float(np.sqrt(np.mean(scored**2)))),
            ('terminal_position_error', float(errors[-1])))],
        constraints=[ConstraintResult(name='sampled_tracking_bound', satisfied=maximum <= limit,
            observed=maximum, limit=limit, units='m'),*force_constraints])


def checked_tracking(inp):
    """Reuse the length-only physical envelope without weakening reaching checks."""
    from .gvs_profile import load_profile, checked_reach, ReachControl, SampledSettling
    from tools.platform_registry import registry
    inp = SessionInput.model_validate(inp)
    if inp.policy.controller.extension_id!='controller.gvs_nmpc' or inp.policy.controller.version!='5.0.0':
        raise ValueError('TRACKING_CONTROLLER_VERSION_REQUIRED')
    control = TrackingControl.model_validate(inp.policy.controller.parameters.data)
    tracking_task(inp.task, registry())
    if inp.task.evaluator.parameters.data['tension_limits_n']!={t['id']:t['force_limit_n'] for t in inp.robot.structure.data['tendons']}:
        raise ValueError('TRACKING_FROZEN_TENSION_LIMITS_MISMATCH')
    if control.recipe.holding_tip_speed_weight or control.recipe.holding_brake_lead_s:
        raise ValueError('TRACKING_HAS_NO_ABSOLUTE_SPEED_HOLDING_SCHEDULE')
    old = SessionInput.model_validate(load_profile()['session_input'])
    # Only the new task semantics differ. Keep physical scene, initialization,
    # channels, observations, robot envelope and model checks authoritative.
    task = plain(inp.task)
    for key in ('task_id','task_version','name','source','family','goal','evaluator','objectives','sampling'):
        task[key] = plain(old.task)[key]
    # checked_reach requires the archived nonphysical metadata exactly.
    task['sampling'] = plain(old.task.sampling)
    proxy = plain(inp)
    proxy['task'] = task
    proxy['policy']['controller'].update(version='4.0.0', parameters=dict(
        contract='family.gvs_reach_control', data=plain(ReachControl(recipe=control.recipe,
            settling=SampledSettling(window_s=inp.task.timing.sample_period_s), numerical_source=control.numerical_source))))
    checked_reach(SessionInput.model_validate(proxy))
    return control


def assessment(inp):
    checked_tracking(inp)
    return dict(technical_compatibility=dict(status='supported', reason='Length-only robot envelope; frozen world reference; ideal bounded tensions'),
        historical_evidence=dict(status='unvalidated_tracking', reason='Archived reaching is not tracking evidence'))
