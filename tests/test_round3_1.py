"""Round 3.1 observability and file-scoped authorization regression."""
import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import mujoco
import numpy as np
from pydantic import ValidationError

from controllers.open_loop_length import OpenLoopLength
from schemas.debug_artifact import DebugTrajectory
from tools.artifact_tools import file_hash
from tools.debug_tools import DebugObservability, PassiveObserver
from tools.design_compiler import build_robot_ir
from tools.evidence import EvidenceStore
from tools.experiment_policy_tools import validate_experiment_policy
from tools.experiment_tools import _candidate_stream, optimize_design
from tools.harness import run_reach
from tools.mujoco_tools import compile_mujoco, run_task
from tools.spec_tools import ROOT, load_task_package, load_yaml
from tests.test_architecture import design, BASELINE
from tests.test_round3 import SyntheticModel, read
from examples.validate_round3 import audit, numerical

POLICY = ROOT / 'configs/experiments/round3_1_reach_free.yaml'


class DisturbingViewer:
    """Inject GUI writes and exceptions; no desktop or alternate simulation."""
    def __init__(self, model, data, **kwargs):
        self.model, self.data = model, data
        self.calls = 0
        self.disturb()

    def disturb(self):
        self.data.qpos[:] = 9
        self.data.qvel[:] = 8
        self.data.ctrl[:] = 7
        self.data.qacc_warmstart[:] = 6
        self.data.qfrc_applied[:] = 5
        self.data.xfrc_applied[:] = 4
        self.data.time = 100
        self.model.opt.timestep = .9
        self.model.opt.gravity[:] = 0
        self.model.opt.iterations = 1
        self.model.body_mass[:] = 1

    def is_running(self):
        return True

    def sync(self, *, state_only):
        assert state_only is True
        self.calls += 1
        self.disturb()
        if self.calls == 2:
            raise RuntimeError('synthetic viewer interruption')

    def close(self):
        self.disturb()


class DebugTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='round3_1 Windows paths ', dir=ROOT/'runs')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.task, self.environment = load_task_package()
        self.xml = self.root/'robot with spaces.xml'
        compile_mujoco(design(), self.task, self.xml)

    def execute(self, observer=None):
        return run_task(self.xml, self.task, OpenLoopLength(BASELINE['tendon_target_lengths_m']),
                        observability=observer)

    def test_disabled_exact_regression_and_headless(self):
        with patch('mujoco.viewer.launch_passive', side_effect=AssertionError('desktop forbidden')):
            result = self.execute()
        self.assertEqual(result.metrics['position_error_m'], .17116166894090315)
        self.assertEqual(result.failure_code, 'TASK_FAILED')
        self.assertFalse((self.root/'debug').exists())

    def test_trajectory_schema_and_observational_values(self):
        baseline = self.execute()
        observer = DebugObservability(self.root/'debug', debug=True)
        observed = []
        original_step = mujoco.mj_step
        def record_step(m, d):
            original_step(m, d)
            observed.append((d.ten_length.tolist(), d.actuator_force.tolist()))
        with patch('mujoco.mj_step', side_effect=record_step) as step:
            result = self.execute(observer)
        self.assertEqual(step.call_count, 1000)
        self.assertEqual(result.model_dump(), baseline.model_dump())
        observer.finish()
        trajectory = DebugTrajectory.model_validate(read(self.root/'debug/trajectory.json'))
        self.assertEqual(len(trajectory.samples), 1000)
        self.assertEqual(trajectory.labels, ('DEBUG_ONLY','NON_CANONICAL'))
        final = trajectory.samples[-1]
        self.assertEqual(list(final.qpos), result.artifacts['final_state']['qpos'])
        self.assertEqual(list(final.qvel), result.artifacts['final_state']['qvel'])
        # Canonical final metrics follow the legacy final mj_forward; debug samples
        # retain each mj_step's original work arrays without an extra forward call.
        for row, (lengths, forces) in zip(trajectory.samples, observed):
            self.assertEqual(list(row.tendon_actual_lengths_m), lengths)
            self.assertEqual(list(row.actuator_force_n), forces)
        self.assertEqual(list(final.tendon_target_lengths_m), BASELINE['tendon_target_lengths_m'])
        m = mujoco.MjModel.from_xml_path(str(self.xml)); d = mujoco.MjData(m)
        for row in trajectory.samples[::113]:
            d.qpos[:] = row.qpos
            mujoco.mj_kinematics(m, d)
            np.testing.assert_array_equal(d.site('tip_site').xpos, row.tip_position_m)
            self.assertEqual(row.position_error_m, __import__('math').dist(row.tip_position_m, self.task.target_m))
        self.assertEqual(read(self.root/'debug/status.json')['errors'], [])
        for name in ('tip_error','tip_xyz','tendon_tracking','actuator_force','qpos_qvel'):
            data = (self.root/'debug'/f'{name}.png').read_bytes()
            self.assertTrue(data.startswith(b'\x89PNG'))
            self.assertIn(b'DEBUG_ONLY / NON_CANONICAL', data)
        value = trajectory.model_dump(mode='json')
        for change in ({'labels':['CANONICAL','NON_CANONICAL']}, {'nq':0}):
            with self.assertRaises(ValidationError):
                DebugTrajectory.model_validate({**value, **change})
        value['samples'][0]['time_s'] = float('nan')
        with self.assertRaises(ValidationError):
            DebugTrajectory.model_validate(value)

    def test_viewer_same_objects_and_full_execution_state_protected(self):
        launched = []
        def launcher(m, d, **kwargs):
            handle = DisturbingViewer(m, d, **kwargs)
            launched.append((m, d, handle))
            return handle
        observer = DebugObservability(self.root/'debug', visualize=True, viewer_launcher=launcher)
        baseline = self.execute()
        with patch('tools.debug_tools.time.sleep'), patch('mujoco.mj_step', wraps=mujoco.mj_step) as step:
            actual = self.execute(observer)
        self.assertEqual(step.call_count, 1000)
        self.assertEqual(actual.model_dump(), baseline.model_dump())
        self.assertIs(observer.viewer.model, launched[0][0])
        self.assertIs(observer.viewer.data, launched[0][1])
        before = copy.copy(observer.viewer.data)
        observer.finish()
        np.testing.assert_array_equal(observer.viewer.data.qacc_warmstart, before.qacc_warmstart)
        self.assertEqual(observer.viewer.data.time, before.time)
        self.assertTrue(any(e['operation']=='viewer_sync' for e in observer.errors))

    def test_debug_failures_and_plot_failures_do_not_change_toolresult_or_gate(self):
        first = run_reach(run_root=self.root, matlab_factory=SyntheticModel)
        with patch('tools.debug_tools.DebugObservability._sample', side_effect=RuntimeError('sampling failed')):
            second = run_reach(run_root=self.root, matlab_factory=SyntheticModel, debug=True)
        self.assertEqual(first.record.final_status, second.record.final_status)
        for name in ('model_result.json','mujoco_result.json','gate_summary.json','diagnostic_summary.json'):
            if name == 'gate_summary.json':
                self.assertEqual(read(first.path/name)['canonical_result'], read(second.path/name)['canonical_result'])
            else:
                # Diagnostic refs include run identity; compare numerical ToolResults separately.
                if name != 'diagnostic_summary.json':
                    self.assertEqual(numerical(read(first.path/name)), numerical(read(second.path/name)))
        errors = read(second.path/'debug/status.json')['errors']
        self.assertTrue(any(e['operation']=='matlab_plot' for e in errors))
        self.assertTrue(any(e['operation']=='trajectory_sample' for e in errors))
        # Existing diagnostics legitimately mention qpos peaks; no per-step events
        # or debug records may be added to the high-level trace.
        traces = [[json.loads(line) for line in (r.path/'trace.jsonl').read_text().splitlines()]
                  for r in (first,second)]
        self.assertEqual([e['operation'] for e in traces[0]], [e['operation'] for e in traces[1]])
        audit(second.path)

    def test_artifact_hashes_and_debug_evidence_admission_denied(self):
        run = run_reach(run_root=self.root, matlab_factory=SyntheticModel, debug=True)
        audit(run.path)
        self.assertIn('debug/trajectory.json', run.record.artifact_hashes)
        with self.assertRaisesRegex(ValueError, 'DEBUG_ONLY'):
            EvidenceStore(self.root).reference(run.record.run_id, 'debug/trajectory.json')
        path = run.path/'debug/trajectory.json'
        path.write_text('{}', encoding='utf-8')
        self.assertNotEqual(file_hash(path), run.record.artifact_hashes['debug/trajectory.json'])
        self.assertEqual(read(run.path/'gate_summary.json')['canonical_result'], 'FAIL')


class AuthorizationTests(unittest.TestCase):
    def test_exact_human_authorization_and_no_general_grant(self):
        p = validate_experiment_policy(POLICY)
        self.assertEqual(p.policy.task_contract_id, 'reach_free_v1')
        self.assertEqual(p.policy.allowed_model_levels, ('M1',))
        self.assertEqual(p.policy.allowed_controller_levels, ('C1',))
        self.assertEqual((p.policy.evaluation_budget,p.policy.mujoco_validation_budget,p.policy.seed), (12,5,17))
        self.assertEqual((p.policy.repair_iteration_budget,p.policy.repair_actions,p.policy.feedback_parameters), (0,(),None))
        self.assertEqual(p.policy.objective_metric_refs, ('model.predicted_position_error_m','mujoco.position_error_m'))
        self.assertEqual([v.model_dump() for v in p.policy.variables], [dict(name='total_length_m',unit='m',lower_bound=.35,upper_bound=.45,constraints=('positive',))])
        self.assertEqual(p.baseline, design())
        from agents.contracts.optimization import validate_optimization_variables
        # Round 3 FINAL adds reusable length authority; the historical policy still
        # retains its exact narrower bounds and C1-only route.
        self.assertEqual(validate_optimization_variables(p.baseline.robot_family, ('total_length_m',))[0].lower_bound, .05)
        with tempfile.TemporaryDirectory(dir=POLICY.parent) as tmp:
            other = Path(tmp)/POLICY.name
            other.write_bytes(POLICY.read_bytes())
            self.assertEqual(validate_experiment_policy(other).policy.variables, p.policy.variables)

    def test_length_only_and_rejection_of_every_other_field(self):
        p = validate_experiment_policy(POLICY)
        for value in (.35,.4,.45):
            p.validate_candidate(design(total_length_m=value))
        for value in (.349,.451,float('inf'),float('nan'),0,-1):
            with self.assertRaises(ValueError):
                p.validate_candidate({**design().model_dump(),'total_length_m':value})
        mutations = dict(robot_family='other',sections=2,segments=9,body_radius_m=.021,tendon_count=5,tendon_routing_radius_m=.016)
        self.assertEqual(set(mutations), set(type(design()).model_fields)-{'total_length_m'})
        for key,value in mutations.items():
            with self.subTest(field=key), self.assertRaises(ValueError):
                p.validate_candidate({**design().model_dump(),key:value})

    def test_seeded_candidate_replay_within_exact_bounds(self):
        p = validate_experiment_policy(POLICY)
        streams = [_candidate_stream(p), _candidate_stream(p)]
        for _ in range(12):
            a,b = (p.validate_candidate(next(s)) for s in streams)
            self.assertEqual(a,b)

    def test_testonly_search_replay_provenance_and_boundary(self):
        # Software replay uses the existing TEST_ONLY policy, never spends formal budget.
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            runs = [optimize_design(ROOT/'tests/fixtures/round3/policy.yaml', run_root=tmp,
                                    matlab_factory=SyntheticModel) for _ in range(2)]
            for run in runs:
                audit(run.path)
                summary = read(run.path/'optimization_summary.json')
                self.assertEqual(summary['boundary_result'], 'BOUNDARY_OPTIMUM_OBSERVED')
                self.assertFalse(summary['bounds_expanded'])
                self.assertEqual(summary['canonical_boundary_variables'], ['total_length_m'])
                rows = read(run.path/'candidate_comparison.json')
                self.assertEqual([r['total_length_m'] for r in rows[:3]], [.4,.35,.45])
                for row in rows:
                    self.assertEqual(row['parent_experiment_id'], run.record.run_id)
                    child = Path(tmp)/row['model_run_id']
                    self.assertEqual(row['robot_ir_hash'], file_hash(child/'robot_ir.yaml'))
                    audit(child)
                    for v in row['mujoco_validations']:
                        actual = Path(tmp)/v['run_id']
                        audit(actual)
                        self.assertEqual(v['robot_ir_hash'], row['robot_ir_hash'])
                        self.assertEqual(read(actual/'experiment_context.json')['parent_experiment_id'], run.record.run_id)
            self.assertEqual(read(runs[0].path/'optimization_summary.json'),read(runs[1].path/'optimization_summary.json'))


@unittest.skipUnless(os.environ.get('SOFTROBOT_TEST_MATLAB')=='1', 'real MATLAB opt-in')
class RealMatlabDebugTests(unittest.TestCase):
    def test_saved_plotting_free_and_window_is_observational_and_headless(self):
        from tools.matlab_tools import MatlabTools
        matlab = MatlabTools()
        self.addCleanup(matlab.close)
        class Shared:
            def __getattr__(self, name):
                return getattr(matlab,name)
            def close(self):
                pass
        with tempfile.TemporaryDirectory(prefix='round3_1 Windows spaces ',dir=ROOT/'runs') as tmp:
            for package in (ROOT/'tasks/reach_free',ROOT/'tests/fixtures/reach_window_dev'):
                baseline = run_reach(task_package=package,run_root=tmp,matlab_factory=Shared)
                debug = run_reach(task_package=package,run_root=tmp,matlab_factory=Shared,debug=True)
                self.assertEqual(debug.record.final_status, 'TASK_FAILED')
                self.assertEqual(read(debug.path/'debug/status.json')['errors'], [])
                self.assertTrue((debug.path/'debug/matlab_pcc.png').is_file())
                if package.name == 'reach_window_dev':
                    self.assertTrue((debug.path/'debug/matlab_clearance.png').is_file())
                for name in ('metrics.json','model_result.json','mujoco_result.json'):
                    self.assertEqual(numerical(read(baseline.path/name)),numerical(read(debug.path/name)))
                saved = (debug.path/'model_result.json').read_bytes()
                matlab.plot_saved_results(debug.path,debug.path/'debug'/'中文 figures',visible=False)
                self.assertEqual((debug.path/'model_result.json').read_bytes(), saved)
                self.assertEqual(read(debug.path/'model_result.json')['metrics']['predicted_position_error_m'], .08714456960728613)
                self.assertEqual(read(debug.path/'mujoco_result.json')['metrics']['position_error_m'], .17116166894090315)


if __name__ == '__main__':
    unittest.main()
