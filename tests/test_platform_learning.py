"""Memory-only trainer and persistent contract fixtures; no training or engines."""
import hashlib
import gc
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Literal, get_args
import unittest
from unittest.mock import patch

from pydantic import Field, ValidationError
from examples.platform_fixtures import project, reference_input
from extensions.platform.manifest import Empty
from extensions.tendon_family.route import Combination
from schemas.common import Contract
from schemas.platform import Binding, EvidenceRef, Payload, SessionInput
from schemas.platform_diagnostics import DiagnosticAttribution, DiagnosticFact, DiagnosticReport, GateResult
from schemas.platform_learning import (PolicyArtifact, RewardDefinition, RLProblem, RLTrainingSpecification,
    TrainingBudget, TrainingJob, TrainingMetric, TrainingMetricName, TrainingResult, TrainingStatus)
from schemas.platform_protocols import RLTrainer
from tools.platform_registry import Extension, ExtensionKind, registry
from tools.platform_store import Store, encode, plain


class AlgorithmParameters(Contract):
    learning_rate: float = Field(default=.001, gt=0)
    batch_size: int = Field(default=8, gt=0)


class Normalization(Contract):
    mean: list[float]
    scale: list[float]


class Finiteness(Contract):
    name: TrainingMetricName
    step: int
    finite: bool


def payload(name, value):
    return Payload(contract=name, data=plain(value))


class TrainerStub:
    """Only produces fixtures in instance-local memory; never trains or launches."""
    def __init__(self, parameters):
        self.parameters = parameters
        self.artifacts = {}

    def remember(self, value):
        data = plain(value)
        ref = EvidenceRef(artifact_id=hashlib.sha256(encode(data).encode('utf8')).hexdigest())
        self.artifacts[ref.artifact_id] = data
        return ref

    def start(self, problem, specification):
        return TrainingJob(job_id='fixture-training', trainer=Binding(extension_id='trainer.test',
            parameters=payload('platform.empty', Empty())), status='queued',
            problem=self.remember(payload('platform.rl_problem', problem)),
            specification=self.remember(payload('platform.rl_training_specification', specification)))

    def status(self, job):
        return job.model_copy(update={'status': 'completed'}) if job.status in ('queued', 'running') else job

    def cancel(self, job):
        return job.model_copy(update={'status': 'cancelled'})

    def collect(self, job):
        if job.status != 'completed':
            raise ValueError('FIXTURE_NOT_COMPLETED')
        problem = RLProblem.model_validate(self.artifacts[job.problem.artifact_id]['data'])
        spec = RLTrainingSpecification.model_validate(self.artifacts[job.specification.artifact_id]['data'])
        source = self.remember(payload('platform.training_job', job))
        policies = []
        for label in ('best', 'final'):
            artifact = PolicyArtifact(checkpoint=self.remember({'fixture_checkpoint': label}),
                algorithm_id=spec.algorithm_id, observations=problem.observations, actions=problem.actions,
                preprocessing=payload('test.normalization', Normalization(mean=[.25], scale=[.5])),
                training_configuration=job.specification, source_job=source)
            policies.append(self.remember(payload('platform.policy_artifact', artifact)))
        return TrainingResult(job=source, status='completed', best_policy=policies[0], final_policy=policies[1],
            metrics=[TrainingMetric(name='train/return', step=8, value=100., seed=17)],
            gates=[GateResult(gate_id='checkpoint.available', status='passed', evidence=policies)],
            limitations=['Serialization fixture only; no training or formal evaluation'])


class LearningContracts(unittest.TestCase):
    def setUp(self):
        self.reg = registry()
        for name, schema in [('algorithm', AlgorithmParameters), ('normalization', Normalization), ('finiteness', Finiteness)]:
            self.reg.add_contract('test.' + name, '1.0.0', schema)
        self.reg.add(Extension('trainer.test', 'rl_trainer', '1.0.0', Empty, TrainingResult,
            'tests.test_platform_learning:TrainerStub', 'Memory-only lifecycle fixture',
            capabilities={'supported_algorithms': ['algorithm.test']}))
        self.binding = Binding(extension_id='trainer.test', parameters=payload('platform.empty', Empty()))
        definition, parameters = self.reg.bind(self.binding, 'rl_trainer')
        self.trainer: RLTrainer = definition.resolve()(parameters)
        self.inp = SessionInput.model_validate(reference_input())
        self.problem = RLProblem(task=self.trainer.remember(self.inp.task),
            experiment=self.trainer.remember(self.inp), observations=self.inp.task.observations,
            actions=[self.inp.task.observations[0].model_copy(update={'name': 'length_command', 'phase': 'interval_start'})],
            reward=RewardDefinition(terms=['distance'], implementation=payload('platform.empty', Empty())),
            termination=self.trainer.remember(self.inp.task.timing), reset=self.inp.task.initializer)
        self.spec = RLTrainingSpecification(algorithm_id='algorithm.test',
            parameters=payload('test.algorithm', AlgorithmParameters()),
            budget=TrainingBudget(environment_steps=8), seeds=[17])

    def persist_and_reopen(self, artifacts):
        # Exercise the real existing Store, isolating its authority anchor too.
        with TemporaryDirectory(dir='runs') as folder, patch('tools.platform_store.ROOT', Path(folder).resolve()):
            store = Store(Path(folder) / 'project')
            store.create(project())
            with store.transaction() as db:
                for identity, value in artifacts.items():
                    self.assertEqual(store.put(db, value).artifact_id, identity)
            reopened = Store(store.root)
            restored = {identity: reopened.artifact(EvidenceRef(artifact_id=identity)) for identity in artifacts}
            gc.collect()  # Release SQLite context-manager connections before Windows directory cleanup.
            return restored

    def test_problem_specification_and_authority_boundaries(self):
        for name, value in [('rl_problem', self.problem), ('reward_definition', self.problem.reward),
                            ('rl_training_specification', self.spec)]:
            self.assertEqual(self.reg.parse(payload('platform.' + name, value)), value)
        self.assertEqual(self.reg.parse(self.spec.parameters), AlgorithmParameters())
        with self.assertRaises(ValidationError):
            self.reg.parse(payload('test.algorithm', {'learning_rate': .01, 'task_success': True}))
        with self.assertRaises(ValidationError):
            RewardDefinition(terms=['distance'], implementation='lambda obs: 100')
        for override in ('task', 'evaluator', 'environment', 'design_space'):
            with self.subTest(override=override), self.assertRaises(ValidationError):
                RLTrainingSpecification.model_validate({**plain(self.spec), override: {}})
        self.assertNotIn('task_success', TrainingResult.model_fields)
        self.assertNotIn('evaluator', RewardDefinition.model_fields)
        self.assertEqual(self.trainer.artifacts[self.problem.task.artifact_id], plain(self.inp.task))

    def test_registry_lifecycle_and_persistent_policy_handoff(self):
        self.assertIn('rl_trainer', get_args(ExtensionKind))
        for kind in ('backend', 'solver', 'search', 'controller'):
            with self.assertRaisesRegex(ValueError, 'EXTENSION_KIND_MISMATCH'):
                self.reg.bind(self.binding, kind)
        queued = self.trainer.start(self.problem, self.spec)
        queued_ref = self.trainer.remember(payload('platform.training_job', queued))
        # Recreate the adapter and restore only saved inputs/artifacts, no chat or process handle.
        inputs = self.persist_and_reopen(self.trainer.artifacts)
        restored_job = self.reg.parse(Payload.model_validate(inputs[queued_ref.artifact_id]))
        definition, parameters = self.reg.bind(restored_job.trainer, 'rl_trainer')
        recovered = definition.resolve()(parameters)
        recovered.artifacts = inputs
        job = recovered.status(restored_job)
        result = recovered.collect(job)
        self.assertEqual(job.job_id, queued.job_id)
        self.assertEqual(job.status, 'completed')
        self.assertEqual(recovered.cancel(queued).status, 'cancelled')
        for status in get_args(TrainingStatus):
            value = job.model_copy(update={'status': status})
            self.assertEqual(self.reg.parse(payload('platform.training_job', value)), value)
        result_ref = recovered.remember(payload('platform.training_result', result))
        saved = self.persist_and_reopen(recovered.artifacts)
        restored = self.reg.parse(Payload.model_validate(saved[result_ref.artifact_id]))
        self.assertEqual(restored, result)
        self.assertNotEqual(restored.best_policy, restored.final_policy)
        policy = self.reg.parse(Payload.model_validate(saved[restored.best_policy.artifact_id]))
        self.assertEqual(policy.source_job, restored.job)
        self.assertEqual(policy.training_configuration, job.specification)
        self.assertEqual(self.reg.parse(policy.preprocessing), Normalization(mean=[.25], scale=[.5]))
        self.assertEqual(saved[policy.checkpoint.artifact_id], {'fixture_checkpoint': 'best'})
        # Existing Binding can carry a PolicyArtifact payload; no Controller runtime is added.
        controller = Binding(extension_id='controller.rl_policy', parameters=payload('platform.policy_artifact', policy))
        self.assertEqual(Binding.model_validate_json(controller.model_dump_json()), controller)
        self.assertEqual(set(Combination.model_fields), {'dynamics_model', 'backend', 'controller'})
        with self.assertRaises(ValidationError):
            PolicyArtifact.model_validate({key: value for key, value in plain(policy).items() if key != 'preprocessing'})
        with self.assertRaisesRegex(ValueError, 'COMPLETED_TRAINING_REQUIRES_POLICY'):
            TrainingResult(job=restored.job, status='completed')
        with self.assertRaises(ValidationError):
            TrainingResult.model_validate({**plain(result), 'task_success': True})

    def test_extensible_metrics_and_no_fabricated_nan_values(self):
        names = ['train/episode_length', 'train/return', 'eval/return', 'eval/success_rate',
            'train/loss/policy', 'train/loss/value', 'train/entropy', 'train/approx_kl', 'train/clip_fraction',
            'train/actor_loss', 'train/critic_loss', 'train/q_value', 'reward/distance/episodic_return', 'custom/new_metric']
        for name in names:
            metric = TrainingMetric(name=name, step=8, value=.5)
            self.assertEqual(self.reg.parse(payload('platform.training_metric', metric)), metric)
        with self.assertRaises(ValidationError):
            TrainingMetric(name='train/critic_loss', step=18320, value=float('nan'))

    def test_gates_and_diagnostic_report_persist_facts_separately(self):
        observation = payload('test.finiteness', Finiteness(name='train/critic_loss', step=18320, finite=False))
        evidence = self.trainer.remember(observation)
        failed = GateResult(gate_id='training.finite', status='failed', evidence=[evidence], observed=observation,
            reason='Nonfinite critic loss was observed at step 18320')
        missing = GateResult(gate_id='backend.finite', status='ungradable', reason='Backend log missing')
        self.assertIsNone(missing.observed)
        self.assertNotEqual(failed.status, missing.status)
        for gate in (failed, missing):
            self.assertEqual(self.reg.parse(payload('platform.gate_result', gate)), gate)
        report = DiagnosticReport(subject='training', source=evidence,
            facts=[DiagnosticFact(fact_id='critic.nonfinite', statement=failed.reason, evidence=[evidence], observed=observation)],
            attribution=[DiagnosticAttribution(cause='training_instability', status='supported',
                fact_ids=['critic.nonfinite'], reason='Recorded critic loss is nonfinite'),
                DiagnosticAttribution(cause='persistently_finite_critic', status='ruled_out',
                    fact_ids=['critic.nonfinite'], reason='Contradicted by recorded loss'),
                DiagnosticAttribution(cause='robot_design', status='insufficient_evidence', reason='No design evidence'),
                DiagnosticAttribution(cause='optimizer_configuration', status='possible',
                    fact_ids=['critic.nonfinite'], reason='Needs configuration evidence')],
            gates=[failed, missing], recommended_actions=['Inspect optimizer configuration and obtain backend log'],
            limitations=['Fixture facts; no formal task evaluation or LLM inference'])
        report_ref = self.trainer.remember(payload('platform.diagnostic_report', report))
        saved = self.persist_and_reopen(self.trainer.artifacts)
        restored = self.reg.parse(Payload.model_validate(saved[report_ref.artifact_id]))
        self.assertEqual(restored, report)
        self.assertEqual(restored.facts[0].evidence, [evidence])
        self.assertNotIn('attribution', DiagnosticFact.model_fields)
        self.assertEqual(self.reg.parse(Payload.model_validate(saved[evidence.artifact_id])).finite, False)
        with self.assertRaises(ValidationError):
            DiagnosticFact(fact_id='design.bad', statement='Bad robot design', evidence=[])
        with self.assertRaisesRegex(ValueError, 'FACT_NOT_DECLARED'):
            DiagnosticReport(subject='training', source=evidence, attribution=[DiagnosticAttribution(
                cause='training_instability', status='supported', fact_ids=['absent'], reason='Unsupported link')])


if __name__ == '__main__':
    unittest.main()
