"""Exact following-command and discrepancy semantics for the S5-A probes."""
from pathlib import Path
import unittest

import numpy as np

from tools.platform_host import Host
from tools.research.contracts import Plan
from tools.research.matched_state import _vectors


ROOT=Path(__file__).resolve().parents[2]
REF=lambda value:dict(artifact_id=value,media_type='application/json')


class MatchedStateBoundaries(unittest.TestCase):
    def test_exact_checkpoint_scope(self):
        plan=dict(action='matched_state',matched_state=dict(candidate=REF('a'*64),
            source=REF('b'*64),physical_source=REF('c'*64),indices=[0,15,29],
            resolutions=[4,8]),hypothesis='test',expected_observation='test',
            weakening_observation='test',fixed_conditions='test',
            stopping_condition='test',interpretation='test')
        self.assertEqual(Plan.model_validate(plan).matched_state.indices,(0,15,29))
        plan['matched_state']['indices']=[0,15,28]
        with self.assertRaises(ValueError):Plan.model_validate(plan)

    def test_following_command_and_increment(self):
        name='sorosim-s5a-open-loop-20261016'
        host=Host(ROOT/'runs/research'/name,name)
        result=host.store.artifact(REF('e4d212379075da3f0be79f8aab3b5c32cee19dabe87e93ba8fdcc7f02c71d60e'))
        raw=host.store.artifact(result['raw_reference'])
        source=host.store.artifact(REF('45815dc9cbf9266b3406a91657d1f9d7a163ac96557a5a4dce750d41f16780f9'))
        following=source['trajectory']['tensions_n'][29]
        self.assertEqual(following,raw['samples'][30]['requested_tension_n'])
        self.assertNotEqual(following,raw['samples'][29]['requested_tension_n'])
        values=_vectors(dict(start=[1.,2.,3.],end=[2.,4.,6.]),
            dict(start=np.array([.5,1.,1.5]),end=np.array([1.,3.,4.])))
        self.assertEqual(values['e_projection'],[.5,1.,1.5])
        self.assertEqual(values['e_one_step'],[1.,1.,2.])
        self.assertEqual(values['e_increment'],[.5,0.,.5])


if __name__=='__main__':unittest.main()
