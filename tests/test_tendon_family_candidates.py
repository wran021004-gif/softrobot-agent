"""Only candidate authorization, condition and topology boundaries; no solvers."""
import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from copy import deepcopy
from examples.platform_tendon_family import example_design, design_space, session, prepare, prepare_candidate, save_selection
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

    def test_final_template_values_obey_space_and_allow_explicit_override(self):
        path='components/near/length_m'
        baseline=self.design.model_dump(mode='json'); baseline['components'][0]['length_m']=.175
        space=self.space.model_dump(mode='json'); space['parameters'][path]['bounds']=[.17,.18]
        request=dict(baseline=baseline,space=space,changes={'template':'tube_distal'})
        invalid=build(request)
        self.assertEqual(invalid.status,'physically_invalid')
        self.assertIn('PARAMETER_OUT_OF_BOUNDS: '+path,invalid.reason)
        valid=build({**request,'changes':{'template':'tube_distal',path:.175}})
        self.assertEqual(valid.status,'valid')
        self.assertEqual(valid.candidate.components[0].length_m,.175)
        self.assertEqual(space['templates']['tube_distal']['components'][0]['length_m'],.16)

    def test_public_task_bounds_cover_template_and_baseline(self):
        path='components/near/length_m'
        inp=SessionInput.model_validate(session('family_mujoco',self.design,self.space))
        inp=inp.model_copy(update={'policy':inp.policy.model_copy(update={'editable':{path:(.17,.18)}})})
        inp.robot.structure.data['components'][0]['length_m']=.175
        with self.assertRaisesRegex(ValueError,'TASK_PARAMETER_OUT_OF_BOUNDS'):
            _candidate(inp,{'template':'tube_distal'},registry())
        allowed=_candidate(inp,{'template':'tube_distal',path:.175},registry())
        self.assertEqual(allowed.robot.structure.data['components'][0]['length_m'],.175)
        self.assertEqual(allowed.task,inp.task)
        inp.robot.structure.data['components'][0]['length_m']=.16
        with self.assertRaisesRegex(ValueError,'TASK_PARAMETER_OUT_OF_BOUNDS'):
            _candidate(inp,{},registry())

    def test_final_conditions_skip_inactive_but_require_active_parameter(self):
        self.assertEqual(build(dict(baseline=self.design,space=self.space,changes={})).status,'valid')
        space=self.space.model_dump(mode='json')
        path='components/far/sections/0/section/parameters/missing_dimension'
        space['parameters'][path]=dict(type='number',bounds=[0.,1.],when={'components/far/sections/0/section/kind':'tube'})
        out=build(dict(baseline=self.design,space=space,changes={'template':'tube_distal'}))
        self.assertEqual(out.status,'physically_invalid')
        self.assertIn('CONSTRAINED_PARAMETER_MISSING: '+path,out.reason)

    def test_build_and_run_preparation_share_sources_and_reject_stale_build(self):
        scratch=Path(__file__).resolve().parents[1]/'runs'
        with TemporaryDirectory(dir=scratch) as folder:
            root=Path(folder).resolve()
            assert root.parent==scratch.resolve()
            prepare(root)
            continuous=prepare_candidate(root,'continuous','matlab_spatial')
            structural=prepare_candidate(root,'structural','matlab_spatial')
            other=prepare_candidate(root,'structural','family_mujoco')
            self.assertEqual(continuous['built'].candidate.components[0].length_m,.17)
            self.assertEqual(structural['built'].candidate.components[0].length_m,.16)
            far=next(c for c in structural['built'].candidate.components if c.id=='far')
            self.assertEqual((far.sections[0].section.kind,far.cells),('tube',3))
            self.assertEqual(len(structural['built'].resolved_physics['dofs']),12)
            for key in ('request_identity','design_identity','physics_identity','scene_identity'):
                self.assertEqual(structural['selection'][key],other['selection'][key])
            save_selection(root,'structural','matlab_spatial',structural,rebuild=True)
            run_ready=prepare_candidate(root,'structural','matlab_spatial')
            self.assertEqual(run_ready['selection'],structural['selection'])
            save_selection(root,'structural','matlab_spatial',run_ready)
            artifact=root/'structural_candidate.json'
            stale=json.loads(artifact.read_text(encoding='utf8')); stale['candidate']['components'][0]['length_m']=.17
            artifact.write_text(json.dumps(stale),encoding='utf8')
            with self.assertRaisesRegex(ValueError,'CANDIDATE_BUILD_STALE'):
                save_selection(root,'structural','matlab_spatial',run_ready)
            save_selection(root,'structural','matlab_spatial',run_ready,rebuild=True)
            path=root/'inputs/structural_request.json'; request=json.loads(path.read_text(encoding='utf8'))
            request['changes']['components/near/length_m']=.175
            path.write_text(json.dumps(request),encoding='utf8')
            updated=prepare_candidate(root,'structural','matlab_spatial')
            self.assertEqual(updated['built'].candidate.components[0].length_m,.175)
            with self.assertRaisesRegex(ValueError,'CANDIDATE_BUILD_STALE'):
                save_selection(root,'structural','matlab_spatial',updated)
            # A standalone design edit is visible to both preparation paths,
            # even though it does not override a complete structural template.
            path=root/'inputs/design.json'; baseline=json.loads(path.read_text(encoding='utf8'))
            baseline['components'][0]['cells']=4; path.write_text(json.dumps(baseline),encoding='utf8')
            changed=prepare_candidate(root,'continuous','matlab_spatial')
            self.assertEqual(changed['built'].candidate.components[0].cells,4)


if __name__=='__main__': unittest.main()
