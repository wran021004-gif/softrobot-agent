"""Offline H2 action/parameter projections; no real Provider, Worker or physics."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import httpx
from jsonschema import Draft202012Validator
from tools.research import agent,analysis,core
from tools.research.contracts import Plan,ResearchDecision,PLAN_RESEARCH_INTENTS,AnalysisRequest
from tools.research.object_choices import main_tool_schema,reference_choices,expand_references,bind_plan_selection
from tools.research.provider import provider_schema
from tools.research.state import state,update
from tools.research.scientific_intent import parameter_catalog,compile_question
from tools.research.structure_research import parameters
from tests.research.test_passive_program_v2 import prepared_host_v2
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_p63c2_scientific_intent import question_host
from tests.research.test_p63a_math_interface import generate

def rationale(candidate):
    return dict(action='diagnose',hypothesis='OFFLINE H2: a registered stiffness change may reduce the measured violation.',
        expected_observation='A valid matched local numerical comparison decreases the violation.',
        weakening_observation='An inconsistent, nondecreasing, invalid or contact-gate result weakens this local hypothesis.',
        fixed_conditions='Original frozen task, evaluator, topology, physical model, initial state and protocol.',
        stopping_condition='Review the admitted numerical evidence before choosing another action.',
        interpretation='An offline interface fixture; no numerical evidence or structural conclusion is fabricated.',
        next_research_action='mechanism_research',
        decision=dict(hypothesis_id='OFFLINE-H2',selected_candidate=candidate,
            selected_variables=['segments.0.young_pa'],requested_budget=5))

class H2ActionInterfaceTests(unittest.TestCase):
    def setUp(self):
        for target in ('tools.service_execution._run_contained','mujoco.mj_step',
                'extensions.tendon_family.mujoco_analysis.NativeModel','tools.research.provider.load_credential'):
            p=patch(target,side_effect=AssertionError('NO_REAL_PROVIDER_WORKER_OR_PHYSICS'))
            p.start();self.addCleanup(p.stop)

    def host(self):return prepared_host_v2(mathematical_budget=8,physical_budget=16,mock_provider_budget=20)

    def schema(self,h,actions):
        spec=state(h)['spec']
        return provider_schema(main_tool_schema(agent.plan_schema(actions,decision_required=True,
            family_version=spec.get('family_space',{}).get('version'),study=spec),reference_choices(h,include_all=True)))

    def test_intent_is_host_bound_for_every_action_without_changing_canonical_plan(self):
        schema=main_tool_schema(agent.plan_schema(list(PLAN_RESEARCH_INTENTS),decision_required=True),{})
        self.assertNotIn('research_intent',schema['$defs']['ResearchDecision']['properties'])
        self.assertTrue(ResearchDecision.model_fields['research_intent'].is_required())
        ref=dict(artifact_id='a'*64,media_type='application/json')
        host=SimpleNamespace(store=SimpleNamespace(artifact=lambda r,**kw:dict(candidate=ref)))
        for action,intent in PLAN_RESEARCH_INTENTS.items():
            q=dict(action=action,decision={},candidate=ref,control_seed=dict(candidate=ref),
                control_search=dict(candidate=ref),selected_execution=ref,mechanics_source=ref)
            before=deepcopy(q);bound=bind_plan_selection(host,q)
            self.assertEqual(bound['decision']['research_intent'],intent)
            self.assertEqual(q,before)
        # Deliberate legacy inputs retain canonical validation, including errors.
        q=rationale(ref);q['decision']['research_intent']='STOP'
        self.assertEqual(bind_plan_selection(host,q)['decision']['research_intent'],'STOP')

    def test_read_only_diagnose_actual_sdk_preserves_scientific_fields(self):
        h,c=self.host();q=rationale(c)
        wires=run_fixture(h,[('research_plan',q),None])
        schema=next(t['function']['parameters'] for t in wires[0]['tools'] if t['function']['name']=='research_plan')
        self.assertNotIn('research_intent',schema['$defs']['ResearchDecision']['properties'])
        saved=h.store.artifact(state(h)['plans'][-1])['original_plan'];Plan.model_validate(saved)
        self.assertEqual(saved['decision']['research_intent'],'DIAGNOSE')
        self.assertEqual(saved['decision']['selected_candidate'],c)
        for field in ('hypothesis','weakening_observation','expected_observation','fixed_conditions','stopping_condition','interpretation'):
            self.assertEqual(saved[field],q[field])
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_ambiguous_candidates_require_explicit_owned_choice(self):
        h=question_host();first=generate(h);second=generate(h,lengths=(.17,.11));q=rationale(second)
        q.pop('next_research_action');schema=self.schema(h,['diagnose'])
        from tools.research.object_choices import main_projection
        offered=main_projection(h,q);Draft202012Validator(schema).validate(offered)
        expanded=bind_plan_selection(h,expand_references(offered,schema))
        self.assertEqual(expanded['decision']['selected_candidate'],second)
        del offered['decision']['selected_candidate']
        self.assertFalse(Draft202012Validator(schema).is_valid(offered))
        self.assertIsNone(bind_plan_selection(h,dict(action='diagnose',decision={}))['decision'].get('selected_candidate'))
        self.assertNotEqual(first,second)

    def test_catalog_separates_design_differentiation_authorization_and_domain(self):
        h,c=self.host();spec=state(h)['spec'];raw=h.store.artifact(c)
        rows={r['parameter_id']:r for r in parameter_catalog(spec,raw)}
        canonical={r['parameter_id']:r for r in parameters(spec,raw)}
        for path,authorized in (('segments.0.young_pa',True),('segments.0.sections.0.parameters.semi_z_m',False)):
            row=rows[path];source=canonical[path]
            self.assertTrue(row['design_supported'])
            self.assertEqual(row['study_authorized'],authorized)
            self.assertEqual(row['differentiation']['supported'],authorized)
            self.assertEqual(row['domain']['minimum'],source['minimum'])
            self.assertEqual(row['domain']['maximum'],source['maximum'])
            self.assertEqual(row['execution_admission'],'not_checked')
            page=core.read_tool_evidence(h,dict(subject=c,topic='structure_parameters',selection=[path]))
            self.assertEqual(page['facts'][0]['differentiation']['supported'],authorized)
            self.assertIn('domain',page['facts'][0])
        self.assertEqual(rows['segments.0.sections.0.parameters.semi_z_m']['differentiation']['reason'],
            'ORIGINAL_FROZEN_PARAMETER_AUTHORIZATION_REQUIRED')

    def test_authorized_v4_compile_and_original_admission_without_worker(self):
        h,c=self.host();q=rationale(c);q['decision']['research_intent']='DIAGNOSE'
        core.dispatch(h,q,'OFFLINE-H2-original-diagnose')
        question=dict(version='scientific_question_v4',domain='structure',structure=dict(operation='differentiate',
            effect_semantics='finite_time_task_response',parameter_paths=['segments.0.young_pa'],
            target='finite_time_task_violation',operating_point='frozen_task_initial_state',control_treatment='no_active_control',
            requested_budget=5,load_condition='all_frozen_conditions'))
        allowed=compile_question(h,question,tool_use_id='OFFLINE-H2-allowed')
        self.assertEqual(allowed['status'],'ready',allowed)
        AnalysisRequest.model_validate(allowed['request'])
        self.assertEqual(allowed['required_evaluations'],5)
        self.assertEqual(allowed['dynamic_cost_bound']['physics_steps'],2500)
        self.assertEqual(analysis.admission(h,requested=5)['admitted'],5)
        rejected=deepcopy(question);rejected['structure']['parameter_paths'].append('segments.0.sections.0.parameters.semi_z_m')
        denied=compile_question(h,rejected,tool_use_id='OFFLINE-H2-unapproved')
        self.assertEqual(denied['reason'],'ORIGINAL_FROZEN_PARAMETER_AUTHORIZATION_REQUIRED')
        self.assertFalse(denied['scientific_execution_started'])
        self.assertEqual(state(h)['mathematical_evaluations'],0)
        self.assertEqual(h.store.remaining()['used']['model_calls'],0)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)

    def test_old_plan_schema_restores_before_high_level_refresh(self):
        h,c=self.host()
        def legacy_projection(schema,choices):
            result=main_tool_schema(schema,choices)
            if 'ResearchDecision' in result.get('$defs',{}):
                decision=result['$defs']['ResearchDecision'];source=schema['$defs']['ResearchDecision']
                decision['properties']['research_intent']=deepcopy(source['properties']['research_intent'])
                if 'research_intent' not in decision['required']:decision['required'].append('research_intent')
            return result
        with patch('tools.research.object_choices.main_tool_schema',side_effect=legacy_projection):
            first=run_fixture(h,[None])[0]
        before=h.store.remaining()
        with patch('tools.research.agent.credential',return_value='OFFLINE'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(lambda r: self.fail('restore_only must not send'))):
            asyncio.run(agent.converse(h,restore_only=True))
        self.assertEqual(h.store.remaining(),before)
        second=run_fixture(h,[None],id_offset=20)[0]
        schema=lambda w:next(t['function']['parameters'] for t in w['tools'] if t['function']['name']=='research_plan')
        self.assertIn('research_intent',schema(first)['$defs']['ResearchDecision']['properties'])
        self.assertNotIn('research_intent',schema(second)['$defs']['ResearchDecision']['properties'])
        self.assertEqual(state(h)['mathematical_evaluations'],0)

if __name__=='__main__':unittest.main()
