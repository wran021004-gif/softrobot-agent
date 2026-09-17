"""Only candidate authorization, condition and topology boundaries; no solvers."""
import unittest
from copy import deepcopy
from examples.platform_tendon_family import example_design, design_space, session
from extensions.tendon_family.candidate import build
from extensions.tendon_family.contracts import BuildRequest, Design
from schemas.platform import SessionInput
from tools.platform_registry import registry
from tools.platform_tools import _candidate


class CandidateBoundaries(unittest.TestCase):
    def setUp(self):
        self.design=example_design(); self.space=design_space(self.design)

    def test_integer_and_choice_pass_public_candidate_without_task_change(self):
        inp=SessionInput.model_validate(session('family_mujoco',self.design,self.space))
        changed=_candidate(inp,{'components/near/cells':4,'components/near/interpolation':'linear'},registry())
        self.assertEqual(changed.task,inp.task)
        self.assertEqual(changed.robot.structure.data['components'][0]['cells'],4)
        self.assertIsInstance(changed.robot.structure.data['components'][0]['cells'],int)
        with self.assertRaisesRegex(ValueError,'INTEGER_REQUIRED'):
            _candidate(inp,{'components/near/cells':3.5},registry())
        with self.assertRaisesRegex(ValueError,'OPTION_NOT_AUTHORIZED'):
            _candidate(inp,{'components/near/interpolation':'arbitrary_code'},registry())

    def test_conditional_tube_and_invalid_physics_are_distinct(self):
        req=dict(baseline=self.design,space=self.space,changes={'template':'tube_distal',
            'components/far/sections/0/section/parameters/inner_radius_m':.005})
        valid=build(req); self.assertEqual(valid.status,'valid')
        bad=deepcopy(self.space.model_dump(mode='json'))
        bad['parameters']['components/far/sections/0/section/parameters/inner_radius_m']['bounds']=[.002,.01]
        invalid=build({**req,'space':bad,'changes':{**req['changes'],'components/far/sections/0/section/parameters/inner_radius_m':.009}})
        self.assertEqual(invalid.status,'physically_invalid')
        self.assertIn('TUBE_INNER',invalid.reason)

    def test_reserved_topology_never_compiles_or_becomes_a_performance_score(self):
        data=self.design.model_dump(mode='json')
        data['components'].append(dict(id='future_loop',kind='closed_chain',description='Requires closure constraint solver'))
        out=build(dict(baseline=Design.model_validate(data),space=self.space,changes={}))
        self.assertEqual(out.status,'backend_unsupported')
        self.assertIsNone(out.resolved_physics)


if __name__=='__main__': unittest.main()
