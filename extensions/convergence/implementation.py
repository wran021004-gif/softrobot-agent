"""Offline plug-in exercise. No physical calibration and no model service."""
import json
import time
from schemas.platform import Payload, EvaluationResult, WorkerOutput, BackendResult, SignalSpec
from tools.platform_store import plain
from tools.platform_models import OfflineAdapter
from extensions.reference.implementation import ReferenceBackend
from extensions.convergence.contracts import Empty, StatefulState


class ObservingAdapter(OfflineAdapter):
    adapter_id = 'model.observing'

    def __init__(self, parameters):
        self.parameters = parameters

    def respond(self, payload, turn):
        # The only observation channel is the serialized request supplied here.
        context = json.loads(payload['messages'][-1]['content'])
        receipt = context['last_receipt']
        if receipt is None:
            tool, args = 'analysis.vector_norm', dict(values_m=self.parameters.values_m)
        elif receipt['tool_id'] == 'analysis.vector_norm':
            tool, args = 'evidence.read', dict(reference=receipt['output'], pointer='/norm_m')
        elif receipt['tool_id'] == 'evidence.read':
            norm = context['observation']['content']['content']
            command = 0.30 if norm <= 5 else 0.304
            changes = {'controller.command_m': command}
            if 'structure.response_fraction' in context['policy']['editable']:
                changes['structure.response_fraction'] = 0.6 if norm <= 5 else 0.8
            tool, args = 'simulation.run', dict(candidate_id='observed-' + str(norm), changes=changes)
        elif receipt['tool_id'] == 'simulation.run':
            tool, args = 'evaluation.run', dict(result=receipt['output'], execution_id=receipt['execution_id'])
        else:
            tool, args = 'session.control', dict(status='stopped', reason='saved evaluation received')
        return dict(request_id=f'model-{turn}-tool', tool_id=tool, tool_version=context['policy']['tool_bindings'][tool],
                    arguments=args, reason='Decision from delivered observation', evidence=[])


def apply_design(inp, parameters, changes):
    for key, value in changes.items():
        if key == 'structure.response_fraction':
            inp.robot.structure.data['response_fraction'] = value
        elif key == 'controller.command_m':
            inp.policy.controller.parameters.data['command_m'] = value
        else:
            raise ValueError('SYNTHETIC_PARAMETER_UNSUPPORTED')
    return inp


class LimitedBackend(ReferenceBackend):
    checks = []
    executions = []

    @staticmethod
    def check(inp, parameters, control):
        LimitedBackend.checks.append(plain(inp))
        if control.command_m > 0.305:
            raise ValueError('SYNTHETIC_COMMAND_LIMIT_0.305')
        ReferenceBackend.check(inp, parameters, control)

    def export(self):
        return super().export().model_copy(update=dict(backend_id='backend.limited_synthetic'))

    def compile(self, inp, reg):
        LimitedBackend.executions.append(plain(inp))
        super().compile(inp, reg)


def terminal_task(task, reg):
    reg.parse(task.goal)
    reg.parse(task.evaluator.parameters)
    expected = SignalSpec(name='tendon_length', entity='tendon_0', dimension=1, units='m', frame='actuator', phase='post_step')
    if expected not in task.observations or any(o.metric != 'terminal_error' or o.units != 'm' for o in task.objectives):
        raise ValueError('TERMINAL_SIGNAL_OR_OBJECTIVE_UNSUPPORTED')
    return Empty()


def terminal_evaluate(task, result, source, reg, identity):
    spec = task.observations[0]
    signal = next((s for s in result.signals if s.spec == spec), None)
    common = dict(source=source, evaluator=task.evaluator.extension_id, comparison_identity=identity, constraints=[])
    if result.solver_status != 'completed' or not signal or not signal.values or abs(signal.times_s[-1] - task.timing.duration_s) > 1e-8:
        return EvaluationResult(validity='incomplete', task_success=None, metrics=[], reason='MISSING_FINAL_SIGNAL', **common)
    error = abs(signal.values[-1][0] - reg.parse(task.goal).target_m)
    return EvaluationResult(validity='valid', task_success=error <= reg.parse(task.evaluator.parameters).tolerance_m,
        metrics=[dict(name='terminal_error', value=error, units='m')], **common)


class StatefulSearch:
    def __init__(self, parameters):
        self.parameters = parameters
        self.state = StatefulState(proposed=0, feedback=[], rng_state=[17])

    def propose(self):
        index = self.state.proposed
        self.state = self.state.model_copy(update=dict(proposed=index + 1, rng_state=[self.state.rng_state[0] * 3 + 1]))
        return {'controller.command_m': self.parameters.candidates[index]}

    def feedback(self, score):
        self.state = self.state.model_copy(update=dict(feedback=[*self.state.feedback, score]))

    def stopped(self):
        return self.state.proposed == len(self.parameters.candidates)

    def save(self):
        return Payload(contract='convergence.search_state', data=plain(self.state))

    def restore(self, state):
        self.state = StatefulState.model_validate(state)


def _output(order, client, started, contract, data, evidence=()):
    return WorkerOutput(work_id=order.work_id, base_candidate=order.base_candidate, source=order.input_snapshot,
        status='completed', result=Payload(contract=contract, data=data), evidence=list(evidence), usage=client.usage(),
        claim_key=contract, conclusion='checked_saved_data', started_at=started, ended_at=time.time())


def math_worker(order, parameters, raw, client):
    started = time.time()
    time.sleep(parameters.delay_s)
    if parameters.fail:
        raise ValueError('DEVELOPMENT_WORKER_FAILURE')
    # Reads the same fixed input and makes a real mathematical Host invocation.
    client.read(order.input_snapshot)
    receipt = client.invoke('analysis.vector_norm', dict(values_m=[3., 4.]), 'norm')
    return _output(order, client, started, 'convergence.math_report', dict(norm_m=client.result(receipt)['norm_m']), [receipt['output']])


def diagnostic_worker(order, parameters, raw, client):
    started = time.time()
    time.sleep(parameters.delay_s)
    client.read(order.input_snapshot)
    result = BackendResult.model_validate(raw)
    return _output(order, client, started, 'convergence.diagnostic_report', dict(signal_count=len(result.signals)))


def check_math(order, output, source, reg, evidence):
    report = reg.parse(output.result)
    if report.norm_m != 5 or len(evidence) != 1 or evidence[0].get('norm_m') != report.norm_m:
        raise ValueError('MATH_REPORT_MISMATCH')


def check_diagnostic(order, output, source, reg, evidence):
    report = reg.parse(output.result)
    if report.signal_count != len(BackendResult.model_validate(source).signals):
        raise ValueError('DIAGNOSTIC_SOURCE_MISMATCH')


def value_v1(ctx, args):
    return args


def value_v2(ctx, args):
    return args.model_copy(update=dict(value=args.value * 2))


class EvidenceStrategy:
    def decide(self, decoded, context):
        from schemas.platform import ToolRequest
        action = ToolRequest.model_validate(decoded)
        # Role-specific policy can evolve in this package. The Host still checks grants.
        if not action.reason.strip():
            raise ValueError('DECISION_REASON_REQUIRED')
        return action
