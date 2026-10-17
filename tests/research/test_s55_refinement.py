"""Frozen-grid and incomplete-root boundaries for S5.5 fixed-input refinement."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch

from tools.platform_host import Host
from tools.research.contracts import Plan
from extensions.tendon_family.sorosim_codesign import refine_fixed_sequence


ROOT=Path(__file__).resolve().parents[2]
STUDY='sorosim-s5-agent-feedback-20261016'
CANDIDATE={'artifact_id':'47cb1f9ece26104d21d836c8068bdc4852b764cb186e5b53b7ea53f7f2793b3d',
    'media_type':'application/json'}
SOURCE={'artifact_id':'45815dc9cbf9266b3406a91657d1f9d7a163ac96557a5a4dce750d41f16780f9',
    'media_type':'application/json'}


class RefinementBoundaries(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        host=Host(ROOT/'runs/research'/STUDY,STUDY)
        cls.configuration=host.store.artifact(CANDIDATE)['configuration']
        cls.source=host.store.artifact(SOURCE)

    def test_typed_substeps_and_frozen_grid(self):
        plan=dict(action='refine',refinement=dict(candidate=CANDIDATE,source=SOURCE,substeps=4),
            hypothesis='frozen-grid fixture',expected_observation='root output',
            weakening_observation='root failure',fixed_conditions='same 35 inputs',
            stopping_condition='one bounded attempt',interpretation='test only')
        self.assertEqual(Plan.model_validate(plan).refinement.substeps,4)
        plan['refinement']['substeps']=3
        with self.assertRaises(ValueError):Plan.model_validate(plan)
        self.assertEqual(len(self.source['trajectory']['tensions_n']),35)
        self.assertEqual(len(self.source['trajectory']['times_s']),36)
        changed=deepcopy(self.source)
        changed['trajectory']['times_s'][20]+=.0001
        with self.assertRaisesRegex(ValueError,'REFINEMENT_GRID_OR_INITIAL_STATE_MISMATCH'):
            refine_fixed_sequence(self.configuration,CANDIDATE,changed,4)

    def test_failed_root_is_not_task_success(self):
        source=self.source
        class Session:
            environment={}
            dependency={}
            timings={}
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def construct(self,spec):pass
            def evaluate(self,operation,request):
                assert operation=='diagnose' and request['kind']=='fixed_sequence'
                assert request['substeps']==2 and len(request['tensions_n'])==35
                assert len(request['times_s'])==36
                return dict(status='root_failed',complete=False,initial_state=request['x'],
                    states=[request['x']],failed_root=dict(interval=1,substep=1,residual_inf=.1))
        with patch('extensions.tendon_family.sorosim_codesign.SorosimSession',Session):
            result=refine_fixed_sequence(self.configuration,CANDIDATE,source,2)
        self.assertFalse(result['complete'])
        self.assertFalse(result['original_task_satisfied'])
        self.assertEqual(result['raw']['failed_root']['interval'],1)


if __name__=='__main__':unittest.main()
