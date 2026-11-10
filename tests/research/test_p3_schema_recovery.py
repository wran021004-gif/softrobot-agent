"""Offline regression for the P3 tools rejection; no science or live sends."""
import asyncio
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
import httpx
from jsonschema import Draft202012Validator,SchemaError
from tools.research.agent import plan_schema
from tools.research.config import resolve
from tools.research.provider import LiveBoundary,provider_schema,request_settings
from tools.research.scientific_intent import question_schema
from schemas.platform import TaskDefinition
from extensions.reference.passive_program import execution_scope

ROOT=Path(__file__).resolve().parents[2]


class P3SchemaRecovery(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec=resolve(ROOT/'configs/research/study_p3_passive_progressive_stiffness_autonomous_v1_2.json')

    def test_multiple_fidelities_full_and_focused_tools_are_valid(self):
        spec=self.spec
        for actions in [spec['allowed_plan_actions'],*[[a] for a in spec['allowed_plan_actions']]]:
            schema=plan_schema(actions,decision_required=True,focused=len(actions)==1,study=spec)
            Draft202012Validator.check_schema(schema)
            Draft202012Validator.check_schema(provider_schema(schema))
            if 'ScientificStructureSearch' in schema.get('$defs',{}):
                required=schema['$defs']['ScientificStructureSearch']['required']
                self.assertEqual(required.count('screening_fidelity'),1)
        legacy=resolve(ROOT/'configs/research/study_p3_passive_progressive_stiffness_architecture_v1_1.json')
        schema=plan_schema(legacy['allowed_plan_actions'],decision_required=True,study=legacy)
        self.assertNotIn('screening_fidelity',schema['$defs']['ScientificStructureSearch']['required'])

    def test_execution_choices_match_frozen_worker_admission(self):
        spec=self.spec
        schema=question_schema(spec)
        Draft202012Validator.check_schema(provider_schema(schema))
        profile=schema['$defs']['PassiveExecutionProfile'];validator=Draft202012Validator(profile)
        task=TaskDefinition.model_validate(spec['canonical_task'])
        final=dict(purpose='final_acceptance',fidelity='final_evaluation')
        self.assertTrue(validator.is_valid(final));self.assertEqual(execution_scope(task,final)['load_conditions'],['plus_x','minus_x'])
        wrong={**final,'recording':'sampled','load_conditions':['plus_x','minus_x']}
        self.assertFalse(validator.is_valid(wrong))
        self.assertFalse(validator.is_valid({**final,'fidelity':'diagnostic4'}))
        with self.assertRaisesRegex(ValueError,'FINAL_ACCEPTANCE'):execution_scope(task,wrong)
        for name in ('screening','screening1','refinement2','diagnostic4','diagnostic32'):
            exploration=dict(purpose='exploration',fidelity=name,load_conditions=['plus_x'],stage_prefix='low',requested_observables=['tendon_transitions'])
            self.assertTrue(validator.is_valid(exploration));self.assertEqual(execution_scope(task,exploration)['end_s'],{'plus_x':8.})
        self.assertFalse(validator.is_valid(dict(purpose='exploration',fidelity='two cells per segment')))
        self.assertFalse(validator.is_valid(dict(purpose='exploration',stage_prefix='invented_stage')))

    def test_invalid_wire_schema_rejected_before_send_or_debit(self):
        p=self.spec['runtime']['provider'];host=SimpleNamespace(run_id='fixture',store=Mock())
        host.store.session.return_value={'state':{'spec':self.spec}}
        malformed=dict(type='object',properties=dict(screening_fidelity=dict(type='string')),required=['screening_fidelity','screening_fidelity'])
        wire={**request_settings(p), 'messages':[dict(role='user',content='Synthetic schema fixture')],
            'tools':[dict(type='function',function=dict(name='research_plan',parameters=malformed))]}
        request=httpx.Request('POST',p['base_url'].rstrip('/')+'/chat/completions',json=wire)
        sends=[]
        transport=httpx.MockTransport(lambda request:sends.append(request))
        with patch('tools.research.provider.pilot',return_value={'provider':p}),patch('tools.research.provider.pending',return_value=[]):
            boundary=LiveBoundary(host,transport=transport)
            with self.assertRaises(SchemaError):asyncio.run(boundary.handle_async_request(request))
        self.assertFalse(sends);host.store.reserve.assert_not_called();host.store.transaction.assert_not_called()


if __name__=='__main__':unittest.main()
