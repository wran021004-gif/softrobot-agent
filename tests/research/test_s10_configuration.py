"""Offline frozen-task and capability admission; no Provider or scientific starts."""
import unittest
from tools.research.config import ROOT,resolve
from tools.research.evidence_policy import comparable_task
from tools.research.numerics import archived


class S10Configuration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=resolve(ROOT/'configs/research/study_s10_mirror.json')

    def test_unchanged_mirror_task(self):
        old=resolve(ROOT/'configs/research/study_s8_mirror.json')
        self.assertEqual(self.spec['canonical_task'],old['canonical_task'])
        self.assertEqual(self.spec['canonical_task']['goal']['data']['target_m'],[.29,-.035,.19])
        self.assertNotEqual(self.spec['study_id'],old['study_id'])

    def test_counts_and_methods(self):
        s=self.spec
        self.assertEqual((s['budgets']['provider_requests'],s['budgets']['physical_launches']),(32,64))
        self.assertTrue({'analysis','mathematics','physical_replay','nmpc','rl','control_search'}<=set(s['capabilities']))
        self.assertEqual(s['rl_limits']['training_actions'],65536)
        self.assertEqual(s['control']['rl_defaults']['ppo']['n_steps'],256)
        self.assertEqual(s['confirmation']['fresh_independent_repetitions'],0)
        self.assertEqual(s['tool_readiness']['sorosim_matlab']['status'],'ready')

    def test_historical_scope(self):
        for entry in self.spec['research_decisions']['history']:
            v=archived(entry['folder'],entry['reference'])
            candidate=archived(entry['folder'],v['candidate'])
            self.assertEqual(comparable_task(self.spec,candidate['configuration']['task']),self.spec['canonical_task'])
            self.assertFalse(v['acceptance']['accepted'])
        for entry in self.spec['research_decisions']['mathematics']:
            self.assertEqual(archived(entry['folder'],entry['reference'])['operation'],'equilibrium')


if __name__=='__main__':unittest.main()
