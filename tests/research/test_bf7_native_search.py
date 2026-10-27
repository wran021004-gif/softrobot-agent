"""Offline interface fixtures only; no scientific integration."""
from copy import deepcopy
import unittest
from tools.research.design import final_fidelity_matches
from tools.state_io import digest


class FrozenConditionFidelityTests(unittest.TestCase):
    def test_each_frozen_condition_retains_exact_mesh_and_backend(self):
        policy=dict(final_evaluation=dict(cells_per_segment=12))
        cfg=dict(policy=dict(backend={'fixture':1},discretization=dict(data=dict(cells={'a':12,'b':12}))))
        task={'fixture':'second'}
        spec=dict(fidelity_policy=policy,final_evaluation_identity='fixture',configuration=cfg,
            canonical_task_identity='root',task_conditions=[dict(condition_id='second',task=task)])
        c=dict(configuration=deepcopy(cfg),fidelity_policy_identity=digest(policy),final_evaluation_identity='fixture',task_identity='root')
        self.assertTrue(final_fidelity_matches(spec,c))
        c.update(condition_id='second',task_identity=digest(task))
        self.assertTrue(final_fidelity_matches(spec,c))
        c['task_identity']='root'
        self.assertFalse(final_fidelity_matches(spec,c))
        c['task_identity']=digest(task);c['configuration']['policy']['discretization']['data']['cells']['b']=6
        self.assertFalse(final_fidelity_matches(spec,c))
        c['configuration']=deepcopy(cfg);c['condition_id']='unfrozen'
        self.assertFalse(final_fidelity_matches(spec,c))


if __name__=='__main__':unittest.main()
