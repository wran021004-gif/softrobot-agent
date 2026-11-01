"""M1 draft admission and real SDK/Mock HTTP handoff; no numerical execution."""
from copy import deepcopy
import json
import re
import unittest
from unittest.mock import patch
from uuid import uuid4

from jsonschema import Draft202012Validator

from tools.research import core
from tools.research.config import ROOT, resolve
from tools.research.conditions import condition_candidate
from tools.research.contracts import AnalysisRequest
from tools.research.scientific_intent import compile_question
from tools.research.state import state, update, save, require_authorization
from tools.research_tasks import task_adapter
from tools.state_io import atomic_json, digest
from tests.research.test_cross_task_integration import fixture_directory, plan
from tests.research.test_recent_round_tools import run_fixture


class M1PreparationTests(unittest.TestCase):
    def test_frozen_draft_and_mock_sdk_handoffs(self):
        spec = resolve(ROOT / 'configs/research/study_r0_m1_v4_draft.json')
        self.assertEqual([c['condition_id'] for c in spec['task_conditions']],
                         ['positive_high', 'negative_low', 'central_high'])
        self.assertEqual(spec['knowledge_manifest'], dict(entries=[]))
        self.assertEqual(spec['budgets']['provider_requests'], 0)
        self.assertFalse(spec['supplied_evidence'])
        with fixture_directory() as folder:
            draft_fixture = deepcopy(spec)
            draft_fixture['study_id'] += '-fixture-' + uuid4().hex[:8]
            draft_fixture['configuration']['run_id'] = draft_fixture['study_id']
            with patch('tools.research.config.resolve', return_value=draft_fixture):
                draft = core.prepare(directory=folder / 'draft')
            self.assertFalse(state(draft)['candidates'])
            with self.assertRaisesRegex(ValueError, 'INDEPENDENT_FORMAL_STUDY_APPROVAL'):
                require_authorization(draft)

            # A separate fabricated SDK session, never an approval of the draft.
            fixture = deepcopy(spec)
            fixture['study_id'] = 'r0-m1-mock-sdk-fixture-' + uuid4().hex[:8]
            fixture['configuration']['run_id'] = fixture['study_id']
            fixture['authorization'] = 'Fabricated offline SDK fixture only'
            fixture['budgets'].update(provider_requests=16, protected_provider_requests=0)
            fixture['configuration']['policy']['budget']['model_calls'] = 16
            with patch('tools.research.config.resolve', return_value=fixture):
                h = core.prepare(directory=folder / 'sdk')
            pilot = deepcopy(state(h)['pilot'])
            pilot.update(session_handoff_live_admitted=True, session_handoff_boundary='request_feedback')
            update(h, freeze='fabricated-sdk-fixture', pilot=pilot)
            scope = dict(study_id=h.run_id, resolved_identity=fixture['resolved_identity'],
                         execution_scopes=['registered mathematics'])
            save(h, dict(user_approval='OFFLINE FIXTURE ONLY', scope=scope,
                         scope_identity=digest(scope)), 'formal_study_authorization')
            request = dict(version='serial_family_generation_v2',
                           family_space_identity=fixture['family_space_identity'],
                           segment_count=2, tendon_count=6)
            with patch('tools.service_execution._run_contained', side_effect=AssertionError('NO_WORKER')), \
                 patch('mujoco.mj_step', side_effect=AssertionError('NO_PHYSICS')), \
                 patch('tools.research.agent.credential', return_value='offline-fixture'), \
                 patch('tools.research.reporter._wire', side_effect=ValueError('OFFLINE_REPORTER')):
                wires = run_fixture(h, [
                    ('research_route', dict(tool='research_plan', action='generate')),
                    ('research_plan', plan('generate', generation=request)), None])
                self.assertEqual(len(state(h)['candidates']), 1)
                root = next(iter(state(h)['candidates'].values()))
                conditions = []
                for condition in fixture['task_conditions']:
                    c = condition_candidate(h, root, condition['condition_id'])
                    cfg = h.store.artifact(c)['configuration']
                    self.assertEqual(cfg['robot'], h.store.artifact(root)['configuration']['robot'])
                    compatibility = task_adapter(cfg).check_compatibility()
                    self.assertEqual(compatibility['technical_compatibility']['status'], 'supported')
                    conditions.append(dict(condition=condition['condition_id'], compatibility=compatibility))
                diagnosis = plan('diagnose', root, next_research_action='mechanism_research')
                wires += run_fixture(h, [
                    ('research_route', dict(tool='research_plan', action='diagnose')),
                    ('research_plan', diagnosis), None], id_offset=10)
                schema = next(t['function']['parameters'] for t in wires[-1]['tools']
                              if t['function']['name'] == 'research_analysis')
                question = dict(version='scientific_question_v4', domain='structure', structure=dict(
                    operation='inspect', effect_semantics='mechanism_effect',
                    target=dict(quantity='tip_jacobian', reduction='norm'),
                    operating_point='frozen_task_initial_state', control_treatment='fixed_absolute_tensions',
                    requested_budget=1))
                Draft202012Validator(schema).validate(question)
                compiled = compile_question(h, question, tool_use_id='r0-compile-only')
                self.assertEqual(compiled['status'], 'ready', compiled)
                self.assertFalse(compiled['scientific_execution_started'])
                Draft202012Validator(AnalysisRequest.model_json_schema()).validate(compiled['request'])

                control_candidate = condition_candidate(h, root, 'negative_low')
                wires += run_fixture(h, [
                    ('research_route', dict(tool='research_plan', action='initialize_control')),
                    ('research_plan', plan('initialize_control', control_candidate,
                                          control_seed=dict(candidate=control_candidate, method='baseline'))),
                    None], id_offset=20)
                wires += run_fixture(h, [
                    ('research_route', dict(tool='research_plan', action='diagnose')),
                    ('research_plan', plan('diagnose', control_candidate,
                                           next_research_action='control_feasibility')), None], id_offset=30)
                control_schema = next(t['function']['parameters'] for t in wires[-1]['tools']
                                      if t['function']['name'] == 'research_analysis')
                self.assertEqual(control_schema['properties']['domain']['const'], 'control')
                control_question = dict(version='scientific_question_v4', domain='control', control=dict(
                    question_type='control_feasibility', effect_semantics='reoptimized_task_capability',
                    control_scope=dict(mode='full_task'), control_search_effort=dict(
                        method='response', knot_count=4, iterations=1, evaluation_requests=4)))
                Draft202012Validator(control_schema).validate(control_question)
                control = compile_question(h, control_question, tool_use_id='r0-native-compile-only')
                self.assertEqual(control['status'], 'ready', control)
                self.assertEqual(control['request']['candidate'], control_candidate)
                Draft202012Validator(AnalysisRequest.model_json_schema()).validate(control['request'])
            for wire in wires:
                wire_text = json.dumps(wire)
                self.assertNotIn('artifact_id', wire_text)
                self.assertIsNone(re.search(r'(?<![0-9a-f])[0-9a-f]{40,64}(?![0-9a-f])', wire_text, re.I))
            self.assertEqual(state(h)['mathematical_evaluations'], 0)
            self.assertFalse(state(h)['physical_replays'])
            self.assertEqual(h.store.remaining()['used']['backend_solves'], 0)
            atomic_json(ROOT / 'runs/r0-preparation/mock_sdk.json', dict(
                scope='Fabricated SDK/Mock HTTP fixture; no Provider, worker or integration',
                http_requests=len(wires), draft_authorization_blocked=True,
                condition_admission=conditions, structure_compile_status=compiled['status'],
                native_control_compile_status=control['status'],
                control_schema_domain='control', no_private_ids_on_wire=True,
                mathematical_evaluations=0, physical_launches=0,
                actual_provider_requests=0))
