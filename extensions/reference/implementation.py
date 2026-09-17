"""Cheap reference model and registered task semantics; explicitly nonphysical."""
import math
import random
from schemas.platform import Payload, Signal, SignalSpec, BackendResult, EvaluationResult, Metric, ConstraintResult
from extensions.reference.contracts import (Empty, InitialState, ControlState, ControlOutput,
    ReferenceData, SearchState, MathNormResult)
from tools.state_io import digest


def initialize(parameters, seed):
    length = parameters.length_m + random.Random(seed).uniform(-parameters.jitter_m, parameters.jitter_m)
    return Payload(contract='reference.initial_state', data=InitialState(length_m=length, seed=seed).model_dump(mode='json'))


def initialize_legacy(parameters, seed):
    from extensions.reference.contracts import LegacyInitial
    return Payload(contract='legacy.initial_state', data=LegacyInitial(seed=seed).model_dump(mode='json'))


def reach_task(task, reg):
    from extensions.reference.contracts import ReachGoal, ReachEvaluation
    if type(reg.parse(task.goal)) is not ReachGoal or type(reg.parse(task.evaluator.parameters)) is not ReachEvaluation:
        raise ValueError('REACH_GOAL_OR_EVALUATOR_CONTRACT_MISMATCH')
    if task.evaluator.extension_id != 'evaluate.reach':
        raise ValueError('REACH_EVALUATOR_REQUIRED')
    required = [SignalSpec(name='tip_position', entity='tip', dimension=3, units='m', frame='world', phase=phase)
                for phase in ('post_step', 'sampled_state')]
    if not any(spec in task.observations for spec in required):
        raise ValueError('REQUIRED_SIGNAL: tip_position, tip, dimension=3, m, world, declared state phase')
    if task.environment.contract not in ('legacy.environment', 'experiment.assembly'):
        raise ValueError('REACH_ENVIRONMENT_ADAPTER_REQUIRED')
    expected_initializers = ('initialize.experiment', 'initialize.family') if task.environment.contract == 'experiment.assembly' else ('initialize.legacy_zero',)
    if task.initializer.extension_id not in expected_initializers:
        raise ValueError('REACH_INITIALIZER_ADAPTER_REQUIRED')
    if any(o.metric != 'position_error' or o.units != 'm' for o in task.objectives):
        raise ValueError('EVALUATOR_METRIC_OR_UNIT_UNAVAILABLE')
    return Empty()


def hold_task(task, reg):
    from extensions.reference.contracts import HoldGoal, HoldEvaluation
    if type(reg.parse(task.goal)) is not HoldGoal or type(reg.parse(task.evaluator.parameters)) is not HoldEvaluation:
        raise ValueError('HOLD_GOAL_OR_EVALUATOR_CONTRACT_MISMATCH')
    if task.evaluator.extension_id != 'evaluate.hold':
        raise ValueError('HOLD_EVALUATOR_REQUIRED')
    required = SignalSpec(name='tendon_length', entity='tendon_0', dimension=1, units='m', frame='actuator', phase='post_step')
    if required not in task.observations:
        raise ValueError('REQUIRED_SIGNAL: tendon_length, tendon_0, dimension=1, m, actuator, post_step')
    if task.environment.contract != 'reference.environment' or task.initializer.extension_id != 'initialize.length':
        raise ValueError('HOLD_ENVIRONMENT_OR_INITIALIZER_UNSUPPORTED')
    if any(o.metric not in ('rms_deviation', 'max_deviation') or o.units != 'm' for o in task.objectives):
        raise ValueError('EVALUATOR_METRIC_OR_UNIT_UNAVAILABLE')
    return Empty()


class LengthController:
    def __init__(self, parameters, period_s):
        self.parameters, self.period_s = parameters, period_s
        self.state = ControlState(steps=0, lifecycle='created')

    def reset(self):
        self.state = ControlState(steps=0, lifecycle='running')

    def restore(self, state):
        self.state = ControlState.model_validate(state)
        if self.state.lifecycle != 'running':
            raise ValueError('CONTROLLER_RESTORE_REQUIRES_RUNNING_CHECKPOINT')

    def command(self, time_s, observations):
        if self.state.lifecycle != 'running' or abs(time_s - self.state.steps * self.period_s) > 1e-8:
            raise ValueError('CONTROLLER_LIFECYCLE_OR_PERIOD_MISMATCH')
        self.state = ControlState(steps=self.state.steps + 1, lifecycle='running')
        return ControlOutput(channel='tendon_target_lengths_m', values_m=[self.parameters.command_m])

    def finish(self, interrupted=False):
        self.state = ControlState(steps=self.state.steps, lifecycle='aborted' if interrupted else 'finished')

    def checkpoint(self):
        return Payload(contract='reference.control_state', data=self.state.model_dump(mode='json'))


class ReferenceBackend:
    """One-dimensional discrete test plant. Does not simulate tendon mechanics."""
    @staticmethod
    def check(inp, parameters, control):
        if inp.task.timing.sample_period_s != inp.task.timing.timestep_s:
            raise ValueError('REFERENCE_SAMPLE_PERIOD_MUST_EQUAL_TIMESTEP')

    def __init__(self):
        self.cancelled = False
        self.closed = False

    def compile(self, inp, reg):
        self.inp, self.reg = inp, reg
        self.robot = reg.parse(inp.robot.structure)
        self.compiled = True

    def initialize(self, initial, controller):
        self.length = self.reg.parse(initial).length_m
        self.initial = initial
        self.controller = controller
        self.controller.reset()
        self.index, self.rows, self.times = 0, [], []
        self.command_value = self.length

    def step(self):
        if self.closed or self.cancelled:
            raise ValueError('BACKEND_CLOSED_OR_CANCELLED')
        timing = self.inp.task.timing
        stride = round(timing.control_period_s / timing.timestep_s)
        if self.index % stride == 0:
            self.command_value = self.controller.command(self.index * timing.timestep_s, {}).values_m[0]
        self.length += self.robot.response_fraction * (self.command_value - self.length)
        self.index += 1
        self.times.append(self.index * timing.timestep_s)
        self.rows.append([self.length])

    def observe(self):
        return [Signal(spec=SignalSpec(name='tendon_length', entity='tendon_0', dimension=1, units='m', frame='actuator', phase='post_step'), times_s=self.times, values=self.rows),
                Signal(spec=SignalSpec(name='contact_count', entity='contact', dimension=1, units='count', frame='world', phase='post_step'), times_s=self.times, values=[[0.] for _ in self.rows])]

    def run(self, *, folder=None, timeout_s=None, cancel=None):
        import time
        started = time.monotonic()
        for _ in range(round(self.inp.task.timing.duration_s / self.inp.task.timing.timestep_s)):
            if timeout_s is not None and time.monotonic() - started >= timeout_s:
                self.cancel()
                break
            if cancel and cancel():
                self.cancel()
                break
            self.step()
        self.controller.finish(self.cancelled)
        return self.export()

    def export(self):
        return BackendResult(solver_status='cancelled' if self.cancelled else 'completed', backend_id='backend.reference',
            model_id='discrete_length_response_fixture', signals=self.observe(),
            data=Payload(contract='reference.backend_data', data=ReferenceData(steps=self.index, controller_state=self.controller.checkpoint()).model_dump(mode='json')),
            limitations=['合成离散信号模型；无质量、重力、接触或绳索动力学，不代表真实机器人能力。'], initial_state=self.initial, seed=self.inp.seed)

    def cancel(self):
        self.cancelled = True

    def close(self):
        self.closed = True


def evaluate_signals(task, result, source, reg, comparison_identity, mode):
    if result.solver_status != 'completed':
        return EvaluationResult(validity='incomplete', task_success=None, metrics=[], constraints=[], source=source,
            evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity, reason='SOLVER_NOT_COMPLETE')
    signal_name = 'tip_position' if mode == 'reach' else 'tendon_length'
    spec = next(s for s in task.observations if s.name == signal_name)
    signal = next((s for s in result.signals if s.spec == spec), None)
    if signal is None or not signal.times_s or abs(signal.times_s[-1] - task.timing.duration_s) > 1e-8:
        return EvaluationResult(validity='incomplete', task_success=None, metrics=[], constraints=[], source=source,
            evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity, reason='MISSING_SIGNAL_OR_DURATION')
    first = 0 if signal.spec.phase == 'sampled_state' else 1
    if any(abs(t - (i + first) * task.timing.sample_period_s) > 1e-8 for i, t in enumerate(signal.times_s)):
        return EvaluationResult(validity='incomplete', task_success=None, metrics=[], constraints=[], source=source,
            evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity, reason='INCOMPLETE_SAMPLING')
    goal = reg.parse(task.goal)
    params = reg.parse(task.evaluator.parameters)
    if mode == 'reach':
        value = math.dist(signal.values[-1], goal.target_m)
        metrics, limit = [Metric(name='position_error', value=value, units='m')], params.tolerance_m
    else:
        errors = [abs(v[0] - goal.length_m) for t, v in zip(signal.times_s, signal.values)
                  if task.sampling.window_s[0] - 1e-9 <= t <= task.sampling.window_s[1] + 1e-9]
        if not errors:
            raise ValueError('EMPTY_EVALUATION_WINDOW')
        value, limit = max(errors), params.max_deviation_m
        metrics = [Metric(name='max_deviation', value=value, units='m'),
                   Metric(name='rms_deviation', value=math.sqrt(sum(e * e for e in errors) / len(errors)), units='m')]
    return EvaluationResult(validity='valid', task_success=value <= limit, metrics=metrics,
        constraints=[ConstraintResult(name='task_bound', satisfied=value <= limit, observed=value, limit=limit, units='m')],
        source=source, evaluator=task.evaluator.extension_id, comparison_identity=comparison_identity)


def evaluate_reach(task, result, source, reg, identity):
    return evaluate_signals(task, result, source, reg, identity, 'reach')


def evaluate_hold(task, result, source, reg, identity):
    return evaluate_signals(task, result, source, reg, identity, 'hold')


class ScalarSequenceSearch:
    def __init__(self, parameters):
        self.parameters = parameters
        self.state = SearchState(index=0, scores=[])

    def propose(self):
        return {self.parameters.parameter: self.parameters.candidates[self.state.index]}

    def feedback(self, score):
        self.state = SearchState(index=self.state.index + 1, scores=[*self.state.scores, score])

    def stopped(self):
        return self.state.index >= len(self.parameters.candidates)

    def save(self):
        return Payload(contract='reference.search_state', data=self.state.model_dump(mode='json'))

    def restore(self, state):
        self.state = SearchState.model_validate(state)
        if self.state.index != len(self.state.scores) or self.state.index > len(self.parameters.candidates):
            raise ValueError('SEARCH_STATE_INVALID')


def vector_norm(context, arguments):
    return MathNormResult(norm_m=math.sqrt(sum(v * v for v in arguments.values_m)))
