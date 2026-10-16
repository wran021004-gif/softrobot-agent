"""Saved S3.6 mechanics, geometry and failure-persistence checks; no new solves."""
import gzip
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from tools.state_io import read
from sorosim_s36_probe import ROOT, RAW, BATCH
from sorosim_s35_probe import physical_probes

EVIDENCE=ROOT/'evidence/sorosim_s36/attempt02'


class S36Tests(unittest.TestCase):
    def test_matched_state_identity_and_frame_coverage(self):
        spec=read(RAW/'control_spec.json')['specification']
        provenance=read(EVIDENCE/'provenance.json')
        self.assertEqual(provenance['model_identity'],spec['identity'])
        self.assertEqual(provenance['budget']['new_mujoco_replays'],0)
        for i,p in enumerate(read(BATCH/'physical.json')['probes']):
            rod=read(EVIDENCE/f'rod_{i}.json');c=read(EVIDENCE/f'comparison_{i}.json')
            self.assertEqual(rod['input'],p)
            self.assertEqual(len(c['geometry']),50)
            self.assertEqual({g['sample']['kind'] for g in c['geometry']},
                             {'centerline','rigid_origin','start','guide','anchor','tip'})
            self.assertLess(c['checks']['compiled_site_error_m'],1e-12)
            self.assertLess(max(g['rod_gvs_position_m'] for g in c['geometry']),1e-7)
            self.assertLess(max(g['gvs_refinement_m'] for g in c['geometry']),2e-7)

    def test_force_signs_and_additive_mechanics(self):
        old=read(BATCH/'diagnosis.json')['raw_facts']['virtual_work_probes']
        for i in range(3):
            c=read(EVIDENCE/f'comparison_{i}.json');d=c['cell']
            for name,check in c['checks'].items():
                if name.endswith('decomposition'):self.assertLess(check['absolute_norm'],1e-14)
            residual=sum(np.array(d[k])*s for k,s in [('velocity_bias',1),('elastic_force',1),
                ('viscous_force',1),('gravity_force',-1),('tendon_force',-1)])
            np.testing.assert_allclose(residual,d['residual'],rtol=0,atol=1e-14)
            self.assertAlmostEqual(c['mechanics']['mass_matrix']['relative_norm'],old[i]['mass_relative_fro'],places=12)
            self.assertGreater(np.linalg.eigvalsh(d['mass_matrix']).min(),0)

    def test_geometric_mechanism_isolation(self):
        results=read(EVIDENCE/'isolation.json')['results']
        for r in results:self.assertLess(r['physical_reconstruction_error_m'],1e-12)
        for r in results[1:]:
            self.assertGreater(r['straight_to_arc_change']['absolute_norm'],.0005)
            self.assertLess(r['hinge_order_change']['absolute_norm'],r['straight_to_arc_change']['absolute_norm']/10)
            self.assertLess(r['arc_to_rod_remaining']['absolute_norm'],r['straight_to_arc_change']['absolute_norm']/10)

    def test_saved_replay_survives_later_failure_software_fixture(self):
        # No MuJoCo steps: a synthetic step function fails after the first replay.
        # The persisted artifact is temporary fixture data, never scientific evidence.
        import mujoco
        count=0
        def fake_step(*args):
            nonlocal count
            count+=1
            if count==21:raise RuntimeError('injected subsequent replay failure')
        with tempfile.TemporaryDirectory(dir=ROOT/'runs') as tmp:
            folder=Path(tmp)
            with patch.object(mujoco,'mj_step',side_effect=fake_step):
                with self.assertRaisesRegex(RuntimeError,'injected'):
                    physical_probes(read(RAW/'nmpc_updates.json'),
                        json.loads(gzip.decompress((RAW/'trajectory.json.gz').read_bytes())),
                        read(RAW/'control_spec.json')['specification'],folder=folder)
            self.assertTrue((folder/'replay_1_represented.json').is_file())
            self.assertFalse((folder/'replay_1_original.json').exists())
            self.assertFalse(list(folder.glob('*.tmp')))


if __name__=='__main__':unittest.main()
