"""R2-derived protocol fixtures and scripted SDK requests; no science or network."""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
from jsonschema import Draft202012Validator
from tools.research import agent
from tools.research.config import ROOT
from tools.research.session_handoff import selected_evidence_facts
from tools.research.state import state, update
from tests.research.test_recent_round_tools import provision, run_fixture


def v2_host():
    h=provision();spec=deepcopy(state(h)['spec'])
    spec['research_decisions']['tool_schema_policy']={'version':'on_demand_tools_v2'}
    update(h,spec=spec)
    return h


class HarnessV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r2=json.loads((ROOT/'tests/research/fixtures/r2_harness_boundary.json').read_text(encoding='utf8'))

    def test_original_navigation_keeps_executable_queries(self):
        original=self.r2['navigation']
        parsed=json.loads(original['result']['content'][0]['text'])
        facts=selected_evidence_facts(parsed,original['tool_use']['input'],3000)
        self.assertTrue(facts['entries'])
        self.assertEqual(facts['entries'][0]['query'],parsed['entries'][0]['query'])
        self.assertIn('No full-read credit',facts['scope'])
        self.assertLessEqual(len(json.dumps(facts).encode()),3000)

    def test_loaded_generate_survives_retrieval_and_submits_once(self):
        h=v2_host();spec=state(h)['spec']
        plan=dict(action='generate',generation=dict(version='serial_family_generation_v2',
            family_space_identity=spec['family_space_identity'],segment_count=2,tendon_count=4),
            hypothesis='Synthetic protocol fixture, not a scientific claim.',
            expected_observation='A structurally valid candidate.',weakening_observation='Generation rejected.',
            fixed_conditions='Frozen fixture domain.',stopping_condition='No numerical computation.',
            interpretation='Task acceptance remains unmeasured.',
            decision=dict(hypothesis_id='offline-generation',research_intent='DESIGN_MODIFICATION',selected_method='generate'))
        Draft202012Validator(self.r2['generate_schema']).validate(plan)
        wires=run_fixture(h,[('research_route',dict(tool='research_plan',action='generate')),
            ('research_route',dict(tool='evidence_read')),
            ('evidence_read',dict(reference=state(h)['family_space_reference'],view='working_set',pointer='/candidate_index')),
            ('research_plan',plan),None])
        for wire in wires[:4]:
            schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']=='research_plan')
            self.assertIn('generate',schema['properties']['action']['enum'])
        packet=json.loads(wires[2]['messages'][-1]['content'].split('\n',1)[1])['research']
        self.assertEqual(packet['tool_continuation']['plan_action'],'generate')
        self.assertIn('No Plan submission',packet['tool_continuation']['scope'])
        final=json.loads(wires[4]['messages'][-1]['content'].split('\n',1)[1])['research']
        self.assertEqual(final['research_state']['pending_feedback']['items'][0]['tool'],'research_plan')
        self.assertEqual(len(state(h)['candidates']),1)
        self.assertEqual(len(state(h)['plans']),1)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        self.assertEqual(h.store.remaining()['used']['worker_calls'],0)
        self.assertFalse(state(h)['analysis_results'])
        self.assertFalse(state(h)['physical_replays'])
        before=h.store.remaining()
        with patch('tools.research.agent.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'):
            asyncio.run(agent.converse(h,restore_only=True))
        self.assertEqual(h.store.remaining()['used'],before['used'])

    def test_navigation_projection_reaches_next_wire(self):
        h=v2_host();original=self.r2['navigation'];value=json.loads(original['result']['content'][0]['text'])
        with patch('tools.research.agent.read_tool_evidence',return_value=value):
            wires=run_fixture(h,[('research_route',dict(tool='evidence_read')),
                ('evidence_read',dict(reference=state(h)['family_space_reference'],view='working_set')),None])
        packet=json.loads(wires[-1]['messages'][-1]['content'].split('\n',1)[1])['research']
        item=packet['research_state']['pending_feedback']['items'][0]
        self.assertTrue(item['facts']['entries'])
        self.assertEqual(item['facts']['entries'][0]['query'],value['entries'][0]['query'])

    def test_closeout_exposes_stop_without_choosing_it(self):
        h=v2_host();update(h,count_closeout=True)
        wires=run_fixture(h,[None])
        schema=next(t['function']['parameters'] for t in wires[0]['tools'] if t['function']['name']=='research_plan')
        self.assertEqual(schema['properties']['action']['enum'],['stop'])
        self.assertFalse(state(h)['plans'])


if __name__=='__main__':unittest.main()
