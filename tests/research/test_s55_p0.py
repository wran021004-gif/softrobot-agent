"""Read-only regression of the archived S5 scientific repetition and PPO evidence."""
from copy import deepcopy
from pathlib import Path
import unittest

from tools.platform_host import Host
from tools.research.feedback import (compare_experiments, experiment_identity,
    experiment_preflight)
from tools.rl.run import read_json


ROOT=Path(__file__).resolve().parents[2]
STUDY='sorosim-s5-agent-feedback-20261016'
CANDIDATE={'artifact_id':'47cb1f9ece26104d21d836c8068bdc4852b764cb186e5b53b7ea53f7f2793b3d',
    'media_type':'application/json'}
SOURCE={'artifact_id':'45815dc9cbf9266b3406a91657d1f9d7a163ac96557a5a4dce750d41f16780f9',
    'media_type':'application/json'}


class ScientificIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.host=Host(ROOT/'runs/research'/STUDY,STUDY)
        cls.candidate=cls.host.store.artifact(CANDIDATE)
        cls.source=cls.host.store.artifact(SOURCE)

    def test_archived_agent_repetitions_are_detected_before_reservation(self):
        for route,source,prior in [('nmpc',None,'sorosim_s5b'),
                                   ('fixed_tension',SOURCE,'sorosim_s5a')]:
            with self.subTest(route=route):
                result=experiment_preflight(self.host,CANDIDATE,route,source_ref=source)
                self.assertFalse(result['admitted'])
                match=next(m for m in result['matches'] if m['study']==prior)
                self.assertEqual(match['relation'],'equivalent_repeat')
                self.assertEqual(match['different_fields'],[])
                self.assertEqual(match['outcome'],'valid_failure')
                repeated=experiment_preflight(self.host,CANDIDATE,route,source_ref=source,repeat=True)
                self.assertTrue(repeated['admitted'])
                self.assertTrue(repeated['authorized_as_repeat'])

    def test_changed_tension_robot_seed_and_controller_are_distinct(self):
        base=experiment_identity(self.candidate,'fixed_tension',source=self.source)
        changed=deepcopy(self.source)
        changed['trajectory']['tensions_n'][0][0]+=.01
        other=experiment_identity(self.candidate,'fixed_tension',source=changed)
        self.assertEqual(compare_experiments(base,other)['relation'],'same_robot_different_control')
        robot=deepcopy(self.candidate)
        robot['scientific_configuration']['robot']['structure']['data']['components'][0]['length_m']+=.001
        other=experiment_identity(robot,'fixed_tension',source=self.source)
        self.assertEqual(compare_experiments(base,other)['relation'],'same_controller_different_robot')
        seed=deepcopy(self.candidate)
        seed['scientific_configuration']['seed']+=1
        other=experiment_identity(seed,'fixed_tension',source=self.source)
        self.assertEqual(compare_experiments(base,other)['relation'],'different_seed')
        controller=experiment_identity(self.candidate,'nmpc',environment={'OMP_NUM_THREADS':'1'})
        changed=deepcopy(controller)
        changed['controller']['parameters']['parameters']['data']['recipe']['horizon'] = 999
        self.assertEqual(compare_experiments(controller,changed)['relation'],'same_robot_different_control')

    def test_saved_ppo_diagnosis_matches_original_counts(self):
        report=read_json(ROOT/'evidence/sorosim_s55/p0_ppo_diagnosis.json')
        direct=report['routes']['direct']
        residual=report['routes']['residual']
        self.assertEqual(direct['diagnosis']['recorded_failures'],260)
        self.assertEqual(direct['consumed']['failed_episodes'],260)
        self.assertEqual(sum(direct['diagnosis']['episode_actions'].values()),260)
        self.assertEqual(residual['diagnosis']['recorded_failures'],0)
        self.assertEqual(residual['consumed']['failed_episodes'],0)

    def test_rl_checkpoint_and_mode_identity(self):
        study='sorosim-s5rl-design-b-20261016'
        host=Host(ROOT/'runs/research'/study,study)
        summary=read_json(ROOT/'evidence/sorosim_s5rl/summary.json')
        direct=next(row for row in summary['routes'] if row['mode']=='direct')
        residual=next(row for row in summary['routes'] if row['mode']=='residual')
        config=read_json(ROOT/'runs/research'/study/'rl'/direct['run_id']/'config.json')
        policy=direct['evaluation_facts']['policy_sha256']
        result=experiment_preflight(host,summary['candidate'],'rl',
            rl_configuration=config,policy_sha=policy)
        self.assertFalse(result['admitted'])
        self.assertTrue(any(m['study']=='sorosim_s5rl' for m in result['matches']))
        candidate=host.store.artifact(summary['candidate'])
        original=experiment_identity(candidate,'rl',rl_configuration=config,policy_sha=policy)
        changed=experiment_identity(candidate,'rl',rl_configuration=config,policy_sha='different-policy')
        self.assertEqual(compare_experiments(original,changed)['relation'],'same_robot_different_control')
        residual_config=read_json(ROOT/'runs/research'/study/'rl'/residual['run_id']/'config.json')
        changed=experiment_identity(candidate,'rl',rl_configuration=residual_config,
            policy_sha=residual['evaluation_facts']['policy_sha256'])
        self.assertEqual(compare_experiments(original,changed)['relation'],'same_robot_different_control')


if __name__=='__main__':
    unittest.main()
