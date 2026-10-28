"""Fixtures, not scientific evidence: inverse geometry and unilateral semantics."""
import copy
import unittest
import numpy as np
from tools.research.config import resolve
from tools.state_io import read
from tools.platform_store import plain
from extensions.tendon_family.family_space import parse_space
from extensions.tendon_family.generated_serial import generate_family
from extensions.tendon_family.inverse_routing import generation
from extensions.tendon_family.passive import PassiveModel
from extensions.tendon_family.passive_equilibrium import solve,consistency
from extensions.tendon_family.passive_inverse import modal_target,multicase_metrics
from extensions.tendon_family.route_validation import validate_routes,interval


class InverseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=resolve('configs/research/study_phs2d_round3_v1.json');cls.protocol=read('configs/research/phs2d_protocol_inverse_v1.json')

    def native(self,g):
        a,_,p=generate_family(dict(space=self.spec['family_space'],request=dict(version='serial_family_generation_v2',family_space_identity=self.spec['family_space_identity'],**g)))
        n=PassiveModel(p,self.protocol,p['reference_lengths_m'],'runs/round3-fixtures');n.design_components=a['components'];return n

    def test_old_space_identity_and_payload_opt_in(self):
        old=resolve('configs/research/study_phs2d_round2_v1.json')['family_space']
        self.assertNotIn('terminal_payload_anchor',plain(parse_space(old)))
        with self.assertRaisesRegex(ValueError,'ROUTE_ATTACHMENT_OUTSIDE_FAMILY'):
            generate_family(dict(space=old,request=dict(version='serial_family_generation_v2',family_space_identity=resolve('configs/research/study_phs2d_round2_v1.json')['family_space_identity'],**generation(lengths=(.14,.14),radii=(.02,.014)))))

    def test_actual_jacobian_and_zero_pose_solid_path(self):
        n=self.native(generation());v=consistency(n)
        self.assertLess(v['tendon_gradient_error'],1e-7)
        self.assertEqual(validate_routes(n,[np.zeros(n.model.nv)])['status'],'legal_at_checked_poses')
        g=generation()
        for route in g['route_overrides'].values():route[0]['attachment']['position_m'][2]*=-1
        bad=self.native(g)
        self.assertEqual(validate_routes(bad,[np.zeros(bad.model.nv)])['status'],'illegal')

    def test_modal_distinguishes_ideal_from_force_response(self):
        n=self.native(generation(cells=8));b=solve(n);self.assertEqual(b['status'],'qualified_local_minimum')
        result=modal_target(n,b['equilibrium'],[.3,.5,.7])
        self.assertEqual(len(result['A_ideal_tip_null_modes']),3)
        self.assertEqual(len(result['B_C_unilateral_force_response']['predictions']),6)
        self.assertTrue(all(x['tip_xy_m']<1e-10 for x in result['A_ideal_tip_null_modes']))
        self.assertLess(result['matching_all']['horizontal_row_residuals'][0],.01)

    def test_no_division_in_minimax_surrogate(self):
        b=dict(positions=np.zeros((22,3)).tolist());r=multicase_metrics(self.protocol,b,b,.3)
        self.assertTrue(np.isfinite(r['worst_violation']));self.assertEqual(r['violations']['point'],1.)


if __name__=='__main__':unittest.main()
