"""Independent physical invariants and deliberate corruption checks on evidence."""

import argparse
import copy
import json
from pathlib import Path
import unittest

import numpy as np

from compare import differences

HERE = Path(__file__).resolve().parent
EVIDENCE = HERE/'evidence/run_20261016_01'


class ValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cfg = json.loads((HERE/'cases.json').read_text(encoding='utf-8'))
        cls.data = {name: json.loads((EVIDENCE/f'{name}_one_segment.json').read_text(encoding='utf-8'))
                    for name in ('gvs','matlab')}

    def test_straight_pose_and_stiffness_from_closed_form(self):
        c = self.cfg; L = c['cases'][0]['lengths_m'][0]; radius = c['cases'][0]['radii_m'][0]
        T = np.eye(4); T[0,3] = L
        K = c['young_pa']*np.pi*radius**4/4*L*np.diag([1,1/3,1,1/3])
        for data in self.data.values():
            for level in data['levels']:
                t = level['probes'][0]['terms']
                np.testing.assert_allclose(t['pose'],T,atol=1e-13,rtol=0)
                np.testing.assert_allclose(t['stiffness'],K,atol=1e-15,rtol=1e-12)

    def test_straight_gravity_sign_and_length_scaling(self):
        c = self.cfg; L = c['cases'][0]['lengths_m'][0]; radius = c['cases'][0]['radii_m'][0]
        value = c['density_kg_m3']*np.pi*radius**2*9.81*L**3/6
        expected = np.array([value,-value/2,0,0])
        for data in self.data.values():
            for level in data['levels']:
                actual = np.ravel(level['probes'][0]['terms']['gravity_force'])
                # Midpoint pose integration of linear curvature has O(h^2)
                # error in the slope mode; do not demand exact quadrature of it.
                bound = value/level['setting']['gvs_steps']**2
                self.assertLess(abs(actual[1]-expected[1]),bound)
                np.testing.assert_allclose(actual[[0,2,3]],expected[[0,2,3]],atol=1e-12,rtol=0)

    def test_tensile_virtual_work_sign_and_zero_slope_mode(self):
        L = self.cfg['cases'][0]['lengths_m'][0]
        expected = np.array([[-L*d[2],0,L*d[1],0] for d in self.cfg['tendon_offsets_m']]).T
        for data in self.data.values():
            for level in data['levels']:
                np.testing.assert_allclose(level['probes'][0]['terms']['tendon_force_map'],
                                           expected,atol=1e-13,rtol=0)

    def test_comparison_detects_frame_force_and_scale_corruption(self):
        original = self.data['gvs']['levels'][-1]['probes'][-1]['terms']
        for field in ('pose','tip_jacobian','gravity_force','tendon_force','stiffness'):
            changed = copy.deepcopy(original)
            changed[field] = (-1000*np.asarray(changed[field])).tolist()
            self.assertGreater(max(differences(original,changed).values()),1e-4)

    def test_all_recorded_finest_gates_pass(self):
        for case in ('one_segment','two_segment'):
            result = json.loads((EVIDENCE/f'comparison_{case}.json').read_text(encoding='utf-8'))
            self.assertTrue(result['correspondence_pass'])
            self.assertTrue(result['derivatives_pass'])
            for level in result['levels']:
                self.assertLess(level['numpy_kernel_check']['pose_max_abs'],1e-10)
                self.assertLess(level['numpy_kernel_check']['residual_max_abs'],1e-8)
                self.assertLess(level['numpy_kernel_check']['tendon_jacobian_max_abs'],1e-8)

    def test_nonfinite_evidence_cannot_pass_a_tolerance_gate(self):
        original = self.data['gvs']['levels'][-1]['probes'][-1]['terms']
        changed = copy.deepcopy(original)
        changed['gravity_force'][0][0] = float('nan')
        with self.assertRaisesRegex(ValueError,'Nonfinite mathematical evidence'):
            differences(original,changed)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence',type=Path,default=EVIDENCE)
    args, extra = parser.parse_known_args()
    EVIDENCE = args.evidence
    unittest.main(argv=['test_validation.py',*extra])
