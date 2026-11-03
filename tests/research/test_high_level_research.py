"""High-level intent boundaries; synthetic fixtures, no Provider or Worker."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator

from tools.platform_store import plain
from tools.research import core
from tools.research.config import ROOT
from tools.research.contracts import REGISTERED_MATHEMATICS_SCOPE
from tools.research.scientific_intent import control_settings,compile_question,selected_question_schema
from tools.research.structure_intent import compile_generation
from tools.research.state import state
from tools.research.physical_replay import seed_control
from tools.research.contracts import ControlSeedRequest
from tests.research import test_m1_native_search_scope as fixtures
from tests.research.test_p63a_math_interface import generate
from tests.research.test_p63g3_action_handoff import diagnosis
from tests.research.test_research_authorization_preflight import approve


class HighLevelTests(unittest.TestCase):
    def setUp(self):
        self.patch=patch.object(fixtures,'SPEC',ROOT/'configs/research/study_m1_low_tendon_speed004_v1.json')
        self.patch.start();self.addCleanup(self.patch.stop)
        self.cm=fixtures.scoped_fixture();self.h=self.cm.__enter__()
        self.addCleanup(self.cm.__exit__,None,None,None)
        approve(self.h,[REGISTERED_MATHEMATICS_SCOPE]);self.c=generate(self.h)

    def test_scientific_effort_controls_real_freedom_and_full_physical_range(self):
        spec=state(self.h)['spec'];base=dict(exploration='broad',evaluation_requests=16)
        coarse=control_settings(spec,dict(base,resolution='coarse'),channels=2,physical_limit_n=6.)
        fine=control_settings(spec,dict(base,resolution='fine'),channels=2,physical_limit_n=6.)
        local=control_settings(spec,dict(base,resolution='coarse',exploration='local_refinement'),channels=2,physical_limit_n=6.)
        self.assertEqual((len(coarse.knots_s),len(fine.knots_s)),(3,9))
        self.assertEqual(coarse.coefficient_limit_n,6.)
        self.assertAlmostEqual(local.coefficient_limit_n,.6)
        self.assertEqual(coarse.initial_radius_n,1.5)
        self.assertTrue(all(abs(t/spec['analysis_protocol']['period_s']-round(t/spec['analysis_protocol']['period_s']))<1e-10 for t in fine.knots_s))
        window=control_settings(spec,dict(base,resolution='coarse'),channels=2,window=[.1,.5],physical_limit_n=6.)
        self.assertEqual(window.active_coefficients,[2,3])
        with self.assertRaisesRegex(ValueError,'CANNOT_MIX'):
            control_settings(spec,dict(base,resolution='fine',knot_count=3),channels=2)

    def test_provider_schema_and_compiler_bind_only_high_level_control_fields(self):
        source=seed_control(self.h,ControlSeedRequest(candidate=self.c))['source']
        with patch.object(core,'guard'):core.dispatch(self.h,diagnosis(self.c,'control_feasibility'),'high-level-diagnose')
        schema=selected_question_schema(self.h)
        effort=schema['$defs']['ScientificControlEffort']
        self.assertEqual(set(effort['properties']),{'resolution','exploration','evaluation_requests'})
        self.assertEqual(effort['properties']['evaluation_requests']['maximum'],state(self.h)['spec']['native_control_limits']['evaluation_requests'])
        payload=dict(version='scientific_question_v4',domain='control',control=dict(
            control_scope=dict(mode='full_task'),control_search_effort=dict(resolution='coarse',exploration='broad',evaluation_requests=4),
            source_selection=dict(control_source=source,additional_control_sources=[source])))
        Draft202012Validator(schema).validate(payload)
        before=deepcopy(self.h.store.remaining())
        out=compile_question(self.h,payload,tool_use_id='high-level-control')
        self.assertEqual(out['status'],'ready',out)
        cfg=out['request']['control_optimization']['settings']
        self.assertEqual(len(cfg['knots_s']),3)
        self.assertEqual(cfg['coefficient_limit_n'],8.)
        self.assertEqual(out['request']['control_optimization']['additional_sources'],[source])
        self.assertEqual(self.h.store.remaining(),before)
        self.assertFalse(state(self.h)['analysis_results'])
        payload['control']['control_scope']=dict(mode='holding_phase')
        stage=compile_question(self.h,payload,tool_use_id='high-level-holding')
        self.assertEqual(stage['status'],'ready',stage)
        cfg=stage['request']['control_optimization']['settings']
        self.assertGreater(cfg['knots_s'][0],0.)
        channels=len(self.h.store.artifact(self.c)['configuration']['robot']['structure']['data']['tendons'])
        self.assertEqual(cfg['active_coefficients'],list(range(channels,2*channels)))
        with self.assertRaisesRegex(ValueError,'requested=8192; maximum=8000'):
            control_settings(state(self.h)['spec'],dict(resolution='fine',exploration='broad',evaluation_requests=8192),channels=2)

    def test_physical_edit_preserves_every_other_resolved_parent_parameter(self):
        from extensions.tendon_family.family_space import resolved_request
        from tools.research.design import set_parameter
        candidate=self.h.store.artifact(self.c);space=state(self.h)['spec']['family_space']
        original=resolved_request(space,candidate['parameters']);expected=deepcopy(original)
        from tools.research.design import parameter_value
        value=parameter_value(original,'segments.0.length_m')*1.01
        set_parameter(expected,'segments.0.length_m',value)
        payload=dict(action='generate',decision=dict(selected_candidate=self.c),generation=dict(changes={'segments.0.length_m':value}))
        self.assertEqual(compile_generation(self.h,payload)['generation'],expected)
        payload['generation']['changes']={'segments.0.length_m':10.}
        with self.assertRaisesRegex(ValueError,'OUTSIDE_FROZEN_DOMAIN'):compile_generation(self.h,payload)
        self.assertFalse(state(self.h)['analysis_results'])

    def test_actual_sdk_generation_binds_legacy_identity_only_after_physical_edit_compilation(self):
        from tools.research.state import update
        from tests.research.test_cross_task_integration import plan
        from tests.research.test_recent_round_tools import run_fixture
        from tools.research.design import verify_candidate
        original=self.h.store.artifact(self.c)
        update(self.h,profile={**state(self.h)['profile'],'identity':'synthetic-new-profile'})
        p=plan('generate',generation=dict(changes={}));p['decision']['selected_candidate']=self.c
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')):
            wires=run_fixture(self.h,[('research_route',dict(tool='research_plan',action='generate')),
                ('research_plan',p),None])
        self.assertEqual(len(wires),3)
        fresh=list(state(self.h)['candidates'].values())[-1]
        self.assertNotEqual(fresh,self.c)
        self.assertEqual(verify_candidate(self.h,fresh)['configuration'],original['configuration'])
        plans=state(self.h)['plans'];self.assertTrue(plans)
        self.assertEqual(self.h.store.artifact(plans[-1])['original_plan']['generation']['family_space_identity'],
            state(self.h)['spec']['family_space_identity'])
        uses=[self.h.store.artifact(e['outputs'][0])['tool_use'] for e in self.h.store.events(self.h.run_id)
            if e['kind']=='model_original_tool_request']
        self.assertEqual(next(u for u in uses if u['name']=='research_plan')['input']['generation'],{'changes':{}})
        self.assertFalse(state(self.h)['analysis_results'])

    def test_real_plan_schema_exposes_physical_edits_and_scientific_search_effort(self):
        from tools.research.agent import plan_schema
        spec=state(self.h)['spec']
        schema=plan_schema(['generate'],decision_required=True,family_version='serial_family_space_v2',study=spec)
        from tests.research.test_cross_task_integration import plan
        p=plan('generate',generation=dict(changes={'segments.0.length_m':.15}))
        p['decision']['selected_candidate']=self.c
        Draft202012Validator(schema).validate(p)
        schema=plan_schema(['search'],decision_required=True,family_version='serial_family_space_v2',study=spec)
        props=schema['$defs']['ScientificControlEffort']['properties']
        self.assertEqual(set(props),{'resolution','exploration','evaluation_requests'})

    def test_t2_missing_prerequisites_return_scoped_physical_changes_without_requests(self):
        from tools.research.nonlinear_capability import preparation_view
        before=self.h.store.remaining();view=preparation_view(self.h,self.c,paths=['segments.0.length_m'],step_fraction=.02)
        row=view['parameters'][0]
        self.assertFalse(row['executable_T2']);self.assertFalse(row['baseline_T1_available'])
        self.assertIn('completed_current_implementation_baseline_T1',row['missing'])
        self.assertGreater(row['legal_perturbation']['actual_step'],0)
        self.assertEqual(row['next_actions'][0]['action'],'generate')
        wire=json.dumps(view)
        for field in ('ready_requests','family_domain','AnalysisRequest','t1_results','knots_s'):
            self.assertNotIn('"'+field+'"',wire)
        self.assertEqual(self.h.store.remaining(),before)
        self.assertEqual(len(preparation_view(self.h,self.c,detailed=True)['parameters']),len(view['parameter_choices']) or len(preparation_view(self.h,self.c)['parameter_choices']))

    def test_profile_migration_keeps_history_readable_and_requires_explicit_reconstruction(self):
        from tools.research.state import update
        from tools.research.task_constraints import mathematical_method_view
        from tools.research.nonlinear_capability import preparation_view
        from tools.research.research_context import mechanism_direction_view
        from tools.research.design import verify_candidate
        from tests.research.test_cross_task_integration import plan
        old=self.h.store.artifact(self.c)
        update(self.h,profile={**state(self.h)['profile'],'identity':'synthetic-new-profile'})
        with self.assertRaisesRegex(ValueError,'OLD_EVALUATION_PROFILE'):verify_candidate(self.h,self.c)
        before=self.h.store.remaining()
        with self.h.store.read_snapshot():
            view=mathematical_method_view(self.h,self.c)
            mechanism=mechanism_direction_view(self.h,self.c,view)
            preparation=preparation_view(self.h,self.c)
        self.assertEqual(mechanism['status'],'requires_current_profile_candidate')
        self.assertFalse(preparation['baseline_T1_available'])
        self.assertEqual(self.h.store.remaining(),before)
        p=plan('generate',generation=dict(changes={}));p['decision']['selected_candidate']=self.c
        with patch.object(core,'guard'),patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')):
            fresh=core.dispatch(self.h,p,'explicit-profile-reconstruction')['result']['candidate']
        new=verify_candidate(self.h,fresh)
        self.assertNotEqual(fresh,self.c)
        self.assertEqual(new['configuration'],old['configuration'])
        from extensions.tendon_family.family_space import resolved_request
        space=state(self.h)['spec']['family_space']
        self.assertEqual(resolved_request(space,new['parameters']),resolved_request(space,old['parameters']))
        self.assertFalse(preparation_view(self.h,fresh)['baseline_T1_available'])
        self.assertFalse(state(self.h)['analysis_results'])


if __name__=='__main__':unittest.main()
