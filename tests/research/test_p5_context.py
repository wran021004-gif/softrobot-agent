"""Compact delivery retains scientific contracts; no live model or Worker."""
from copy import deepcopy
import json
import unittest
from types import SimpleNamespace
from jsonschema import Draft202012Validator, ValidationError
from tools.research.agent import plan_schema, load_selected_tool_schema
from tools.research.research_context import compact_tool_delivery
from tools.research.state import state, save, update
from tests.research.test_p5_budget import provision, plan


class P5ContextTests(unittest.TestCase):
    def test_closeout_keeps_stop_when_previous_plan_action_is_no_longer_available(self):
        h=provision();s=state(h)
        route=save(h,dict(tool='research_plan',action='initialize_control'),'offline_route_fixture')
        update(h,pilot={**s['pilot'],'tool_route':route})
        registry={name:SimpleNamespace(tool_spec=dict(name=name,inputSchema={'json':{}}))
            for name in ('research_plan','research_route')}
        loaded=load_selected_tool_schema(h,registry,[dict(tool='research_plan',actions=['stop','select'])])
        self.assertIn('research_plan',registry)
        self.assertEqual(loaded['plan_action'],'stop')
        self.assertEqual(registry['research_plan'].tool_spec['inputSchema']['json']['properties']['action']['enum'],['stop'])

    def test_generate_schema_keeps_research_fields_and_binds_frozen_domain(self):
        h=provision();spec=state(h)['spec']
        old=plan_schema(['generate'],decision_required=True,family_version=spec['family_space']['version'],focused=True)
        new=plan_schema(['generate'],decision_required=True,family_version=spec['family_space']['version'],focused=True,study=spec)
        Draft202012Validator.check_schema(new)
        validator=Draft202012Validator(new);value=plan(h,'generate');validator.validate(value)
        missing_version=deepcopy(value);missing_version['generation'].pop('version')
        with self.assertRaises(ValidationError):validator.validate(missing_version)
        self.assertLess(len(json.dumps(new)),len(json.dumps(old)))
        for key in ('hypothesis','expected_observation','weakening_observation','fixed_conditions','stopping_condition','interpretation','decision'):
            broken=deepcopy(value);broken.pop(key)
            with self.subTest(key=key),self.assertRaises(ValidationError):validator.validate(broken)
        for key,value in (('family_space_identity','wrong-identity'),('segment_count',3),('tendon_count',5)):
            broken=plan(h,'generate');broken['generation'][key]=value
            with self.subTest(key=key),self.assertRaises(ValidationError):validator.validate(broken)

    def test_deduplication_retains_exact_feedback_unfinished_intent_and_navigation(self):
        pending=dict(items=[dict(tool_id='read-1',tool='evidence_read',result=dict(status='success',content=[dict(text='Exact source bytes.')]))])
        hypothesis=dict(hypothesis='Unfinished fixture question.',weakening_observation='A contradictory measurement.')
        brief=dict(action_menu=[dict(action='generate',status='available',reason='Original admission applies.')],
            tool_directory=[dict(tool='research_plan',actions=['generate'])],loaded_tool=dict(tool='evidence_read',action=None,plan_action='generate'),
            tool_continuation=dict(plan_action='generate',plan_selection=dict(status='selected_not_submitted'),recent=[dict(tool_use_id='read-1')]),
            research_state=dict(pending_feedback=pending,task=dict(frozen=True),candidate_status=dict(generated_valid=0)),
            current_intent=dict(agent_hypothesis=hypothesis),history_trace=dict(total=1,recent=[dict(agent_hypothesis=deepcopy(hypothesis),outcome=dict(status='pending'))]),
            generation_contract=dict(version='serial_family_generation_v2',family_space_identity='fixture',domain_query=dict(pointer='',view='full')))
        result=compact_tool_delivery(deepcopy(brief))
        self.assertEqual(result['research_state'],brief['research_state'])
        self.assertEqual(result['current_intent'],brief['current_intent'])
        self.assertEqual(result['tool_directory'][0]['actions'],brief['action_menu'])
        self.assertEqual(result['tool_continuation']['plan_selection']['status'],'selected_not_submitted')
        self.assertFalse(result['tool_continuation']['recent'])
        self.assertEqual(result['history_trace']['recent'][0]['intent_at'],'current_intent')
        self.assertEqual(result['generation_contract']['domain_query'],brief['generation_contract']['domain_query'])
        self.assertNotIn('loaded_tool',result);self.assertNotIn('action_menu',result)


if __name__=='__main__':unittest.main()
