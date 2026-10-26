"""Fixed-program boundaries with fabricated motion fixtures; zero integration."""
from copy import deepcopy
from pathlib import Path
from contextlib import contextmanager
from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4
import shutil
import unittest

import mujoco
import numpy as np

from examples import b2_fixed_search as b2
from tools.state_io import atomic_json, read, digest


@contextmanager
def fixture_directory():
    parent = (b2.ROOT/'runs').resolve()
    folder = parent/('b2-fixture-'+uuid4().hex)
    folder.mkdir()
    try:
        yield folder
    finally:
        if folder.resolve().parent != parent:
            raise ValueError('WORKSPACE_FIXTURE_REQUIRED')
        shutil.rmtree(folder)


class FixedB2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.value = b2.plan()
        _, cls.configs = b2.configurations(cls.value, .018)

    def test_frozen_tasks_preserve_draft_physics_and_pair_structure(self):
        from tools.research.config import patch as compose
        draft = read(b2.ROOT/'tasks/b2_load_hold_zero_v1.json')
        force = read(b2.ROOT/'tasks/b2_load_hold_v1.json'); force.pop('extends')
        for old, (_, cfg) in zip([draft, compose(draft, force)], self.configs):
            current = deepcopy(cfg['task']); previous = deepcopy(old['task'])
            for task in (current, previous):
                for key in ('task_id','name','source','initializer'):
                    task.pop(key)
            self.assertEqual(current, previous)
            self.assertEqual(cfg['policy']['controller']['parameters']['data']['settling'], old['settling'])
        self.assertEqual(self.configs[0][1]['robot']['structure'], self.configs[1][1]['robot']['structure'])

    def test_frozen_input_tamper_is_rejected(self):
        wrong = deepcopy(self.value)
        wrong['frozen_files']['tasks/b2_load_hold_zero_frozen_v1.json'] = '0'*64
        with patch.object(b2, 'read', return_value=wrong):
            with self.assertRaisesRegex(ValueError, 'FROZEN_INPUT_CHANGED'):
                b2.plan()

    def test_new_approval_binds_exact_plan_mode_and_finite_steps(self):
        valid = dict(approved=True, user_approval='Fabricated test fixture, not authorization',
            experiment='B2-fixed-search-v1', mode='neutral', plan_identity=digest(self.value), physics_step_attempts=85400)
        valid['implementation'] = b2.subprocess.check_output(['git','rev-parse','HEAD'], cwd=b2.ROOT, text=True).strip()
        for field, change in [('approved',False),('user_approval','PENDING'),('mode','contrast'),
                ('plan_identity','wrong'),('physics_step_attempts',85401),('physics_step_attempts',True)]:
            with patch.object(b2, 'read', return_value={**valid, field:change}):
                with self.assertRaisesRegex(ValueError, 'SCIENTIFIC_APPROVAL_REQUIRED'):
                    b2.approved(Path('fixture'), self.value, 'neutral')
        with patch.object(b2, 'read', return_value=valid):
            self.assertEqual(b2.approved(Path('fixture'), self.value, 'neutral'), valid)

    def execute_fixture(self, folder, failing_zero=False, budget_failure=False):
        # The existing native search/evaluator run on fabricated arrays. mj_step
        # is blocked; raw.physics_steps below describes fixture completeness only.
        target = self.configs[0][1]['task']['goal']['data']['target_m']
        times = np.arange(36)*.01
        def outputs(native, start, grid, tensions, **kwargs):
            return dict(times_s=times.tolist(), tip_positions_m=[target]*36,
                tip_velocities_m_s=[[0.,0.,0.]]*36, actual_tensions_n=tensions)
        calls = []
        def playback(inp, physics, scene, commands, out):
            calls.append(bool(scene['forces']))
            if budget_failure:
                # Count attempted API steps without calling the engine.
                for _ in range(3):
                    b2.MujocoFailureSnapshot.call(SimpleNamespace(), None, mujoco.mj_step, 'fixture')
            point = [0.,0.,0.] if failing_zero and not scene['forces'] else target
            return dict(status='completed', physics_steps=700, tendon_order=[t['entity'] for t in physics['tendons']],
                samples=[dict(time_s=float(t), tip_m=point, tip_velocity_m_s=[0.,0.,0.],
                    speed_m_s=0., actual_tension_n=[.2]*4) for t in times])
        approval = dict(physics_step_attempts=2 if budget_failure else 85400, user_approval='test fixture',
            _path=str(folder/'fixture-approval.json'))
        with patch.object(b2, 'ROOT', folder), patch.object(b2, 'configurations', return_value=({}, self.configs)), \
                patch.object(b2.NativeModel, 'rollout_sequence', outputs), \
                patch.object(b2, 'playback_tensions', playback), \
                patch.object(b2.MujocoFailureSnapshot, 'call', return_value=None) if budget_failure else patch.object(
                    mujoco, 'mj_step', side_effect=AssertionError('No scientific integration in tests')):
            result = b2.run(self.value, folder/'result', approval, 'feasibility')
        return result, calls

    def test_real_search_and_evaluator_first_paired_pass_stops(self):
        with fixture_directory() as directory:
            folder = Path(directory)
            result, calls = self.execute_fixture(folder)
            self.assertEqual(result['status'], 'first_complete_witness')
            self.assertEqual(calls, [False, True])
            self.assertEqual(read(folder/'result/cost.json')['physics_step_attempts'], 0)
            self.assertTrue(all(c['status']=='accepted' for c in result['results'][0]['conditions'].values()))

    def test_one_condition_pass_does_not_make_a_witness(self):
        with fixture_directory() as directory:
            result, calls = self.execute_fixture(Path(directory), failing_zero=True)
            self.assertEqual(result['status'], 'bounded_search_unresolved')
            self.assertFalse(result['complete_witness'])
            self.assertEqual(len(calls), 6)

    def test_cap_attempts_retained_on_failure(self):
        with fixture_directory() as directory:
            folder = Path(directory)
            with self.assertRaisesRegex(ValueError, 'CAP_EXHAUSTED'):
                self.execute_fixture(folder, budget_failure=True)
            self.assertEqual(read(folder/'result/cost.json')['physics_step_attempts'], 2)
            self.assertEqual(read(folder/'result/summary.json')['status'], 'stopped_with_error')


if __name__ == '__main__':
    unittest.main()
