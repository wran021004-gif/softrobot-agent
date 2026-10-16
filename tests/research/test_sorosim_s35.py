"""Recheck saved numerical interventions without starting engines or optimizers."""
from copy import deepcopy
from pathlib import Path
import unittest

import numpy as np
from tools.state_io import read
from extensions.tendon_family.contracts import ResolvedGVSBasis
from extensions.tendon_family.gvs_projection import project
from sorosim_s35_probe import ROOT, RAW, norm

BATCH=ROOT/'evidence/sorosim_s35/attempt02'


def verify_alignment(physical):
    updates=read(RAW/'nmpc_updates.json')
    for i,p in enumerate(physical['probes']):
        assert norm(p['x'],updates[i]['measured_initial_state'])<1e-10
        assert norm(p['u'],updates[i]['one_step_prediction']['applied_tension_n'])<1e-12
        assert norm(p['u'],p['original']['actual_tension'])<1e-12
        assert norm(p['u'],p['actual_next']['actual_tension'])<1e-12
        assert abs(p['actual_next']['time_s']-(updates[i]['time_s']+.01))<1e-12
        assert p['original']['contacts']==p['reconstructed']['contacts']==p['actual_next']['contacts']==0
        if p['reconstructed_next'] and i:
            replay=p['reconstructed_next']
            assert np.max(np.abs(np.array(replay['all_applied_tension_n'])-p['u']))<1e-12
            assert max(replay['warnings'])==0


class S35Tests(unittest.TestCase):
    def test_current_diagnostic_source_freeze(self):
        import subprocess
        from tools.state_io import digest
        frozen=read(ROOT/'evidence/sorosim_s35/source_freeze.json');identity=frozen.pop('identity')
        self.assertEqual(digest(frozen),identity)
        for source,blob in frozen['git_blobs'].items():
            actual=subprocess.check_output(['git','hash-object',source],cwd=ROOT,text=True,stderr=subprocess.DEVNULL).strip()
            self.assertEqual(actual,blob,source)

    def test_matched_input_and_observation_contract(self):
        verify_alignment(read(BATCH/'physical.json'))

    def test_mismatched_applied_force_rejected(self):
        bad=deepcopy(read(BATCH/'physical.json'));bad['probes'][2]['u'][0]+=.1
        with self.assertRaises(AssertionError):verify_alignment(bad)

    def test_represented_state_roundtrip_and_energy(self):
        physical=read(BATCH/'physical.json');spec=read(RAW/'control_spec.json')['specification']
        physics=read(RAW/'resolved_physics.json');basis=ResolvedGVSBasis.model_validate(spec['resolved_basis'])
        for p in physical['probes']:
            reconstructed=p['reconstructed']
            again=project(physics,basis,reconstructed['qpos'],reconstructed['qvel'])
            self.assertLess(norm(again['q_gvs']+again['qdot_gvs'],p['x']),1e-9)
            self.assertTrue(np.isfinite(reconstructed['energy_j']).all())
        self.assertIsNone(physical['probes'][1]['projection_intervention'])
        self.assertEqual(physical['replays']+physical['prior_failed_batch_replays'],3)

    def test_callback_equivalence_and_independent_derivatives(self):
        for i in range(3):
            c=read(BATCH/f'callbacks_{i}.json');s=c['stats']
            self.assertEqual(c['equivalence'],0)
            self.assertTrue(np.all(np.array(c['directional_relative'])<2e-4))
            self.assertEqual(s['hits']+s['misses'],s['objective_requests']+s['constraint_requests']+s['inspect_requests'])
            self.assertEqual((s['misses'],s['unique_vectors']),(3,2))
            self.assertEqual(len(s['evaluation_times_s']),s['misses'])
            k=read(BATCH/f'kernels_{i}.json')
            counts={r['name']:r['calls'] for r in k['profiler']}
            self.assertEqual(counts['sr_routing'],25)
            self.assertEqual(counts['SorosimLinkage.FwdKinematics'],25)
            self.assertEqual(counts['SorosimLinkage.Jacobian'],25)
            self.assertEqual(counts['SorosimLinkage.DAEJacobians'],1)

    def test_integrator_residuals_and_archived_plan(self):
        updates=read(RAW/'nmpc_updates.json')
        reference=read(BATCH/'casadi.json')
        for i in range(3):
            rows=read(BATCH/f'integration_{i}.json')['refinements']
            for r in rows:
                self.assertLess(float(np.max(np.atleast_2d(r['roots'])[:,0])),1e-9)
                self.assertTrue(np.isfinite(r['x']).all())
            pred=updates[i]['one_step_prediction']
            self.assertLess(norm(rows[0]['position'],pred['tip_position_m']),1e-10)
            self.assertLess(norm(rows[0]['velocity'],pred['tip_velocity_m_s']),1e-10)
            self.assertLess(reference['probes'][i]['scaled_root_residual'],1e-9)
        for p in read(BATCH/'refinement.json')['probes']:
            for r in p['refinements']:
                self.assertLess(float(np.max(np.atleast_2d(r['roots'])[:,0])),1e-9)

    def test_independent_forward_dynamic_balance(self):
        for i in range(3):
            k=read(BATCH/f'kernels_{i}.json')['base'];forward=read(BATCH/f'forward_{i}.json')
            M=np.array(k['mass_matrix'])
            # Shift the complete residual to the returned acceleration with
            # its exact affine mass term, independently of the gateway output.
            residual=M@(np.array(forward['qdd'])-np.linspace(-10,20,12))+k['residual']
            self.assertLess(float(np.max(np.abs(residual))),1e-10)
            self.assertGreater(np.linalg.eigvalsh(M).min(),0)

    def test_full_update_status_and_counters(self):
        out=read(BATCH/'update.json')['result'];s=out['callback_profile']
        self.assertTrue(out['accepted'])
        self.assertLess(out['constraint_violation'],1e-5)
        self.assertEqual(out['optimization_converged'],out['exitflag']>0)
        self.assertEqual(s['hits']+s['misses'],s['objective_requests']+s['constraint_requests']+s['inspect_requests'])
        self.assertLessEqual(s['unique_vectors'],s['misses'])
        self.assertEqual(len(s['evaluation_times_s']),s['misses'])
        self.assertTrue(np.all(np.array(out['tensions'])>=0))
        self.assertTrue(np.all(np.array(out['tensions'])<=8))


if __name__=='__main__':
    unittest.main()
