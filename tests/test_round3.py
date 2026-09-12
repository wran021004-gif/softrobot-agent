"""Round 3 contract/algorithm tests; synthetic ranges never enter formal tasks."""
import copy
import json
import math
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import yaml

from pydantic import ValidationError
from schemas.experiment_policy import ExperimentPolicy, FeedbackParameters
from schemas.candidate_evaluation import CandidateEvaluation
from schemas.feedback import FeedbackUpdate
from schemas.tool_result import ToolResult
from tests.test_architecture import design, BASELINE
from tests.test_gate_semantics import NegativeClearanceMatlab
from tools.spec_tools import ROOT, load_yaml
from tools.artifact_tools import file_hash
from tools.experiment_policy_tools import validate_experiment_policy, ApprovalRequired
from tools.experiment_tools import evaluate_candidate, optimize_design, run_parameter_sensitivity, run_repair_loop
from tools.pcc_math import tip_and_jacobian, pcc_sensitivity
from tools.trace_tools import read_trace, validate_trace
from tools.harness import run_reach
from tools.design_compiler import build_robot_ir
from controllers.pcc_tip_feedback import synthesize_feedback

FIXTURE = ROOT / 'tests/fixtures/round3'
PROPOSAL = ROOT / 'proposals/engineer/round3_experiment_policy.yaml'


class SyntheticModel(NegativeClearanceMatlab):
    """Fixed-bend geometric test double; not MATLAB planning/scientific evidence."""
    def plan_pcc_reach(self, ir, task, environment):
        theta, phi = BASELINE['theta_rad'], BASELINE['phi_rad']
        tip, _ = tip_and_jacobian(ir.total_length_m, [theta*math.cos(phi), theta*math.sin(phi)])
        lengths = [ir.total_length_m-ir.tendon_routing_radius_m*theta*math.cos(r.angle_rad-phi) for r in ir.tendon_routes]
        error = math.dist(tip, task.target_m)
        return ToolResult(tool='plan_pcc_reach', status='pass', metrics={
            'theta_rad': theta, 'phi_rad': phi, 'predicted_tip_m': tip,
            'target_position_m': list(task.target_m), 'predicted_position_error_m': error,
            'model_task_success': error <= task.position_error_max_m,
            'tendon_target_lengths_m': lengths})


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


class Round3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=ROOT/'runs')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.policy_tmp = tempfile.TemporaryDirectory(dir=FIXTURE)
        self.addCleanup(self.policy_tmp.cleanup)
        self.policy = load_yaml(FIXTURE/'policy.yaml')
        self.path = Path(self.policy_tmp.name)/'policy.yaml'
        self.write()

    def write(self, **changes):
        self.policy.update(changes)
        self.path.write_text(yaml.safe_dump(self.policy), encoding='utf-8')
        return self.path

    def verify(self, run):
        self.assertEqual(run.record.final_status, 'PASS', list(run.path.glob('*summary.json')))
        for name, expected in run.record.artifact_hashes.items():
            self.assertEqual(file_hash(run.path/name), expected, name)
        validate_trace(read_trace(run.path/'trace.jsonl'), run.path)
        for path in run.path.glob('candidate_*_run_reference.json'):
            ref = read(path)
            child = self.root/ref['run_id']
            self.assertEqual(file_hash(child/'run.json'), ref['run_manifest_hash'])
            for name, expected in ref['artifact_hashes'].items():
                self.assertEqual(file_hash(child/name), expected)
            self.assertEqual(read(child/'experiment_context.json')['parent_experiment_id'], run.record.run_id)

    def test_schema_and_proposed_boundary(self):
        proposed = ExperimentPolicy.model_validate(load_yaml(PROPOSAL))
        self.assertEqual(proposed.approval_status, 'HUMAN_APPROVAL_REQUIRED')
        with self.assertRaises(ApprovalRequired):
            validate_experiment_policy(PROPOSAL)
        with patch('tools.experiment_tools.run_reach') as runner:
            run = optimize_design(PROPOSAL, run_root=self.root)
        runner.assert_not_called()
        self.assertEqual(run.record.final_status, 'BLOCKED_FOR_HUMAN_APPROVAL')
        self.assertEqual(file_hash(run.path/'optimization_policy.yaml'), file_hash(PROPOSAL))
        for change in ({'target_m':[1,2,3]}, {'seed':None}, {'evaluation_budget':True},
                       {'scientific_status':'HUMAN_APPROVED'}, {'mujoco_validation_budget':100},
                       {'feedback_parameters':None}, {'stop_conditions':[]}):
            with self.subTest(change=change), self.assertRaises(ValidationError):
                ExperimentPolicy.model_validate({**self.policy, **change})

    def test_variable_units_bounds_and_grammar_authority(self):
        base = copy.deepcopy(self.policy)
        for change in ({'name':'target_m'}, {'name':'joint_stiffness_nm_per_rad'}, {'unit':'mm'},
                       {'lower_bound':.34}, {'lower_bound':.5}, {'upper_bound':float('inf')},
                       {'constraints':[]}, {'name':'body_radius_m'}):
            self.policy = copy.deepcopy(base)
            self.policy['variables'][0].update(change)
            self.write()
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_experiment_policy(self.path)

    def test_unselected_field_and_task_mutations(self):
        validated = validate_experiment_policy(self.path)
        for candidate in (design(body_radius_m=.03), design(total_length_m=.46),
                          {**design().model_dump(), 'task':{'target_m':[0,0,0]}}):
            with self.assertRaises(ValueError):
                validated.validate_candidate(candidate)
        validated.validate_candidate(design(total_length_m=.35))
        self.write(seed=99)
        with self.assertRaisesRegex(ValueError, 'changed'):
            validated.validate_candidate(design())

    def test_fixture_cannot_execute_frozen_or_proposed_task(self):
        for task_id, source in (('reach_free_v1','tasks/reach_free/contract.yaml'),
                              ('reach_window_v1_proposal','proposals/benchmark/reach_window_v1/contract.yaml')):
            self.write(task_contract_id=task_id, task_contract_source=source)
            with self.assertRaises(ValueError):
                validate_experiment_policy(self.path)
        self.assertEqual(load_yaml(ROOT/'benchmarks/tendon_v1.yaml')['tasks'][0]['package'],'tasks/reach_free')

    def test_m0_m1_canonical_separation_and_candidate_provenance(self):
        protected = {p:file_hash(p) for p in [ROOT/'tasks/reach_free/task.yaml',ROOT/'tasks/reach_free/environment.yaml',FIXTURE/'contract.yaml']}
        for fidelity in ('M0','M1','MUJOCO'):
            result, run = evaluate_candidate(FIXTURE/'contract.yaml', design(), self.path, fidelity,
                                            run_root=self.root, matlab_factory=SyntheticModel)
            self.verify(run)
            self.assertEqual(result.scope,'TEST_ONLY')
            self.assertEqual(result.policy_hash,file_hash(self.path))
            self.assertEqual(result.design_hash,file_hash(run.path/'candidate_0000_design.yaml'))
            child = self.root/result.run_id
            self.assertEqual(result.robot_ir_hash,file_hash(child/'robot_ir.yaml'))
            if fidelity != 'MUJOCO':
                self.assertEqual(result.canonical_task_status,'NOT_RUN')
                self.assertEqual(result.canonical_metrics,{})
                self.assertEqual(read(child/'gate_summary.json')['termination'],'MODEL_ONLY')
                self.assertFalse((child/'robot.xml').exists())
                with self.assertRaises(ValidationError):
                    CandidateEvaluation.model_validate({**result.model_dump(),'canonical_metrics':{'task_success':True}})
            else:
                self.assertEqual(result.canonical_task_status,'TASK_FAILED')
        self.assertEqual(protected,{p:file_hash(p) for p in protected})

    def test_illegal_candidate_retained_without_execution(self):
        with patch('tools.experiment_tools.run_reach') as runner:
            result, run = evaluate_candidate(FIXTURE/'contract.yaml', design(body_radius_m=.03), self.path,'M1',run_root=self.root)
        runner.assert_not_called()
        self.verify(run)
        self.assertEqual(result.status,'REJECTED')
        self.assertIsNone(result.run_id)
        self.assertEqual(len((run.path/'optimization_history.jsonl').read_text().splitlines()),1)

    def test_deterministic_optimization_replay_and_budget(self):
        first = optimize_design(self.path,run_root=self.root,matlab_factory=SyntheticModel)
        second = optimize_design(self.path,run_root=self.root,matlab_factory=SyntheticModel)
        for run in (first,second):
            self.verify(run)
            summary = read(run.path/'experiment_summary.json')
            self.assertEqual(summary['evaluations'],6)
            self.assertEqual(summary['mujoco_attempts'],2)
            self.assertEqual(read(run.path/'optimization_summary.json')['scope'],'TEST_ONLY')
        for a in first.path.glob('candidate_*_design.yaml'):
            self.assertEqual(a.read_bytes(),(second.path/a.name).read_bytes())
        self.assertEqual(read(first.path/'optimization_summary.json'),read(second.path/'optimization_summary.json'))

    def test_runtime_failed_candidates_are_retained(self):
        class Broken(SyntheticModel):
            def plan_pcc_reach(self,*args):
                raise RuntimeError('synthetic failure')
        run = optimize_design(self.path,run_root=self.root,matlab_factory=Broken)
        self.verify(run)
        history = [json.loads(line) for line in (run.path/'optimization_history.jsonl').read_text().splitlines()]
        self.assertTrue(history)
        self.assertTrue(all(r['canonical_task_status']=='NOT_RUN' for r in history))
        self.assertTrue(all(r['run_id'] for r in history))
        self.assertIsNone(read(run.path/'optimization_summary.json')['best_canonical_candidate'])

    def test_sensitivity_records_exact_perturbations(self):
        run = run_parameter_sensitivity(self.path,run_root=self.root,matlab_factory=SyntheticModel)
        self.verify(run)
        rows = read(run.path/'sensitivity_evidence.json')['evidence'][0]
        self.assertEqual([r['value'] for r in rows['observations']],[.35,.4,.45])
        self.assertEqual(rows['causal_attribution'],'UNKNOWN')
        for path in run.path.glob('candidate_*_design.yaml'):
            candidate = load_yaml(path)
            candidate.pop('total_length_m')
            baseline = design().model_dump()
            baseline.pop('total_length_m')
            self.assertEqual(candidate,baseline)

    def test_pcc_jacobian_matches_finite_difference_and_straight_limit(self):
        for bend in ([0.,0.],[.4,-.7],[1e-7,-1e-7]):
            _, jac = tip_and_jacobian(.4,bend)
            for axis in range(2):
                plus, minus = list(bend),list(bend)
                plus[axis]+=1e-6
                minus[axis]-=1e-6
                a,_=tip_and_jacobian(.4,plus)
                b,_=tip_and_jacobian(.4,minus)
                for row in range(3):
                    self.assertAlmostEqual(jac[row][axis],(a[row]-b[row])/2e-6,places=8)
        result = pcc_sensitivity(build_robot_ir(design()),0,0)
        self.assertEqual(result.metrics['tip_jacobian_m_per_rad'],[[0.,0.],[.2,0.],[0.,.2]])
        self.assertEqual(result.metrics['causal_attribution'],'UNKNOWN')

    def feedback(self):
        experiment = validate_experiment_policy(self.path)
        ir = build_robot_ir(design())
        plan = SyntheticModel().plan_pcc_reach(ir,experiment.resolved.task,experiment.resolved.environment)
        return synthesize_feedback(ir,experiment.resolved.task,plan,experiment)

    def test_feedback_updates_timing_and_command_bounds(self):
        controller = self.feedback()
        previous = controller.target.tendon_target_lengths_m
        for step in range(61):
            command = controller.command(step*.002,{'step':step,'tip_position_m':[10.,-10.,10.]})
            self.assertTrue(all(.2<=x<=.6 for x in command.tendon_target_lengths_m))
            self.assertLessEqual(max(abs(a-b) for a,b in zip(command.tendon_target_lengths_m,previous)),.0001+1e-15)
            previous = command.tendon_target_lengths_m
        self.assertEqual([r['step'] for r in controller.updates],[0,20,40,60])
        self.assertTrue(all(FeedbackUpdate.model_validate(r) for r in controller.updates))
        with self.assertRaises(ValueError):
            controller.command(0,{'step':0,'tip_position_m':[0,0,0]})
        with self.assertRaises(ValidationError):
            FeedbackParameters.model_validate({**self.policy['feedback_parameters'],'max_command_update_m':0})

    def test_real_mujoco_feedback_observes_and_replays(self):
        results = []
        for _ in range(2):
            result, run = evaluate_candidate(FIXTURE/'contract.yaml',design(),self.path,'MUJOCO',controller_level='C2',
                run_root=self.root,matlab_factory=SyntheticModel)
            self.verify(run)
            self.assertNotEqual(result.canonical_task_status,'NOT_RUN',result.failure_message)
            child = self.root/result.run_id
            updates = read(child/'feedback_updates.json')
            self.assertEqual(len(updates),50)
            self.assertEqual(updates[0]['observed_tip_m'],[.39999999999999997,0.,0.])
            self.assertNotEqual(updates[0]['observed_tip_m'],updates[-1]['observed_tip_m'])
            self.assertEqual(read(child/'controller.json')['spec']['level'],'C2')
            comparison=read(child/'compare_model_sim.json')
            self.assertEqual(comparison['metrics']['evidence_status'],'unavailable')
            self.assertEqual(read(child/'diagnostic_summary.json')['failure_attribution'],'UNKNOWN')
            results.append((updates,read(child/'simulation_state.json')))
        self.assertEqual(results[0],results[1])

    def test_feedback_disabled_legacy_exact_baseline(self):
        from tests.test_trace import FixtureMatlab
        run = run_reach(run_root=self.root,matlab_factory=FixtureMatlab)
        self.assertEqual(run.record.final_status,'TASK_FAILED')
        self.assertEqual(read(run.path/'mujoco_result.json')['metrics']['position_error_m'],BASELINE['position_error_m'])
        self.assertEqual(read(run.path/'controller.json')['spec']['level'],'C1')
        self.assertFalse((run.path/'feedback_updates.json').exists())

    def test_repair_is_bounded_and_evidence_authorized(self):
        self.write(repair_actions=['synthesize_feedback']*3)
        run=run_repair_loop(self.path,run_root=self.root,matlab_factory=SyntheticModel)
        self.verify(run)
        summary=read(run.path/'repair_summary.json')
        self.assertEqual(summary['iterations'],1)
        self.assertEqual(summary['decisions'][0]['authority'],'optimization_policy.yaml#repair_actions/0')
        self.assertEqual(summary['causal_attribution'],'UNKNOWN')
        self.assertEqual(read(run.path/'experiment_summary.json')['evaluations'],2)
        self.assertTrue(any(e.event_type=='DECISION_RECORDED' for e in read_trace(run.path/'trace.jsonl')))

    def test_repair_zero_budget_and_missing_route(self):
        self.write(repair_iteration_budget=0)
        run=run_repair_loop(self.path,run_root=self.root,matlab_factory=SyntheticModel)
        self.verify(run)
        self.assertEqual(read(run.path/'repair_summary.json')['iterations'],0)
        self.write(allowed_controller_levels=['C1'],feedback_parameters=None)
        with self.assertRaises(ValueError):
            validate_experiment_policy(self.path)

    def test_sensitivity_and_repair_share_total_budget(self):
        self.write(evaluation_budget=2, mujoco_validation_budget=1,
                   repair_actions=['run_parameter_sensitivity']*2, repair_iteration_budget=2)
        run=run_repair_loop(self.path,run_root=self.root,matlab_factory=SyntheticModel)
        self.verify(run)
        self.assertEqual(read(run.path/'experiment_summary.json')['evaluations'],2)
        self.assertEqual(read(run.path/'experiment_summary.json')['mujoco_attempts'],1)
        self.assertEqual(read(run.path/'repair_summary.json')['iterations'],1)

    def test_abort_retains_completed_child_and_partial_budget(self):
        from tools.experiment_tools import ExperimentSession
        original = ExperimentSession.evaluate
        def interrupted(session,*args,**kwargs):
            result = original(session,*args,**kwargs)
            raise RuntimeError('synthetic interruption after completed candidate')
        with patch.object(ExperimentSession,'evaluate',interrupted):
            run=optimize_design(self.path,run_root=self.root,matlab_factory=SyntheticModel)
        self.assertEqual(run.record.final_status,'ERROR')
        self.assertTrue(read(run.path/'optimization_summary.json')['executed'])
        self.assertEqual(read(run.path/'experiment_summary.json')['evaluations'],1)
        self.assertTrue((run.path/'candidate_0000_run_reference.json').is_file())
        self.assertEqual(file_hash(run.path/'optimization_history.jsonl'),run.record.artifact_hashes['optimization_history.jsonl'])


@unittest.skipUnless(os.environ.get('SOFTROBOT_TEST_MATLAB')=='1','Real MATLAB integration opt-in')
class Round3RealMatlabTests(unittest.TestCase):
    def test_real_multifidelity_feedback_and_derivative(self):
        from tools.matlab_tools import MatlabTools
        matlab=MatlabTools()
        try:
            class Shared:
                def __getattr__(self,name):
                    return getattr(matlab,name)
                def close(self):
                    pass
            with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
                model,parent=evaluate_candidate(FIXTURE/'contract.yaml',design(),FIXTURE/'policy.yaml','M1',run_root=tmp,matlab_factory=Shared)
                self.assertEqual(parent.record.final_status,'PASS')
                self.assertEqual(model.canonical_task_status,'NOT_RUN')
                self.assertEqual(model.model_metrics['predicted_position_error_m'],BASELINE['predicted_position_error_m'])
                derivative=pcc_sensitivity(build_robot_ir(design()),model.model_metrics['theta_rad'],model.model_metrics['phi_rad'])
                for a,b in zip(derivative.metrics['tip_m'],model.model_metrics['predicted_tip_m']):
                    self.assertAlmostEqual(a,b,places=14)
                feedback,parent=evaluate_candidate(FIXTURE/'contract.yaml',design(),FIXTURE/'policy.yaml','MUJOCO',controller_level='C2',run_root=tmp,matlab_factory=Shared)
                self.assertEqual(parent.record.final_status,'PASS')
                self.assertNotEqual(feedback.canonical_task_status,'NOT_RUN',feedback.failure_message)
                self.assertEqual(len(read(Path(tmp)/feedback.run_id/'feedback_updates.json')),50)
        finally:
            matlab.close()
