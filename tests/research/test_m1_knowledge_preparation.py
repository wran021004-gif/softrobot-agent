"""Offline admission for the proposed M1 Study; no inference or integration."""
from copy import deepcopy
import hashlib
import unittest
from unittest.mock import patch
from uuid import uuid4

from tools.research import core
from tools.research.config import ROOT, resolve
from tools.research.conditions import condition_candidate
from tools.research.contracts import AnalysisRequest, Plan
from tools.research.design import full_science
from tools.research.experience import retrieve
from tools.research.scientific_intent import compile_question
from tools.research.state import require_authorization, save, state, update
from tools.research_tasks import task_adapter
from tools.state_io import atomic_json, digest
from tests.research.test_cross_task_integration import fixture_directory, plan


SPEC = ROOT / 'configs/research/study_m1_knowledge_assisted_v4.json'


class M1KnowledgePreparationTests(unittest.TestCase):
    def test_restart_preserves_science_and_carries_assignment_cost(self):
        original = resolve(SPEC)
        restart = resolve(ROOT / 'configs/research/study_m1_knowledge_assisted_v4_restart.json')
        self.assertNotEqual(restart['study_id'], original['study_id'])
        self.assertEqual(full_science(restart['configuration']), full_science(original['configuration']))
        for key in ('task_conditions', 'family_space', 'analysis_protocol', 'knowledge',
                    'knowledge_manifest', 'native_control_limits', 'research_decisions'):
            self.assertEqual(restart[key], original[key], key)
        self.assertEqual(restart['budgets']['provider_requests'] + 1, original['budgets']['provider_requests'])
        self.assertEqual(restart['budgets']['public_operations'] + 1, original['budgets']['public_operations'])
        for key in ('mathematical_evaluations', 'physical_launches', 'protected_provider_requests',
                    'protected_public_operations', 'provider_reserve_policy'):
            self.assertEqual(restart['budgets'][key], original['budgets'][key])
        self.assertTrue(restart['authorization'].startswith('PENDING_EXPLICIT_APPROVAL:'))
        self.assertFalse(restart['supplied_evidence'])

    def test_original_science_and_unapproved_fresh_store(self):
        proposed = resolve(SPEC)
        original = resolve(ROOT / 'configs/research/study_r0_m1_v4_draft.json')
        self.assertEqual(full_science(proposed['configuration']), full_science(original['configuration']))
        for key in ('task_conditions', 'family_space', 'analysis_protocol', 'topology_scope',
                    'confirmation', 'nmpc_limits', 'rl_limits', 'family_sensitivity_variables'):
            self.assertEqual(proposed[key], original[key], key)
        self.assertFalse(proposed['supplied_evidence'])
        for key in ('history', 'mathematics', 'control_seeds', 'background'):
            self.assertFalse(proposed['research_decisions'][key])
        self.assertTrue(proposed['authorization'].startswith('PENDING_EXPLICIT_APPROVAL:'))
        self.assertNotEqual(proposed['study_id'], original['study_id'])
        self.assertNotEqual(proposed['resolved_identity'], original['resolved_identity'])
        self.assertEqual(proposed['native_control_limits'], dict(evaluation_requests=800, iterations=100, knots_s=4))
        self.assertEqual({r['entry_id'] for r in proposed['knowledge_manifest']['entries']},
                         {'research-bounded-continuation', 'research-witness-and-cost'})
        fixture = deepcopy(proposed)
        fixture['study_id'] = 'm1-unapproved-fixture-' + uuid4().hex[:8]
        fixture['configuration']['run_id'] = fixture['study_id']
        fixture.pop('resolved_identity')
        fixture['resolved_identity'] = digest(fixture)
        with fixture_directory() as folder, patch('tools.research.config.resolve', return_value=fixture):
            h = core.prepare(directory=folder)
            self.assertFalse(state(h)['candidates'])
            with self.assertRaisesRegex(ValueError, 'INDEPENDENT_FORMAL_STUDY_APPROVAL'):
                require_authorization(h)
            self.assertFalse([e for e in h.store.events(h.run_id) if e['kind'] == 'formal_study_authorization'])

    def test_each_condition_compiles_and_knowledge_stays_scoped(self):
        fixture = deepcopy(resolve(SPEC))
        fixture['study_id'] = 'm1-offline-admission-fixture-' + uuid4().hex[:8]
        fixture['configuration']['run_id'] = fixture['study_id']
        fixture.pop('resolved_identity')
        fixture['resolved_identity'] = digest(fixture)
        with fixture_directory() as folder, patch('tools.research.config.resolve', return_value=fixture), \
                patch('tools.research.core.guard'), patch('tools.research.state.guard'), \
                patch('tools.service_execution._run_contained', side_effect=AssertionError('NO_WORKER')), \
                patch('mujoco.mj_step', side_effect=AssertionError('NO_PHYSICS')):
            h = core.prepare(directory=folder)
            scope = dict(study_id=h.run_id, resolved_identity=fixture['resolved_identity'],
                         execution_scopes=['registered mathematics'])
            save(h, dict(user_approval='FABRICATED OFFLINE FIXTURE ONLY', scope=scope,
                         scope_identity=digest(scope)), 'formal_study_authorization')
            update(h, freeze='fabricated-offline-fixture')
            generation = dict(version='serial_family_generation_v2',
                              family_space_identity=fixture['family_space_identity'], segment_count=2, tendon_count=6)
            root = core.dispatch(h, plan('generate', generation=generation), 'fixture-generate')['result']['candidate']
            rows = []
            for condition in fixture['task_conditions']:
                cid = condition['condition_id']
                c = condition_candidate(h, root, cid)
                cfg = h.store.artifact(c)['configuration']
                self.assertEqual(cfg['robot'], h.store.artifact(root)['configuration']['robot'])
                fit = task_adapter(cfg).check_compatibility()
                self.assertEqual(fit['technical_compatibility']['status'], 'supported')
                seed = core.dispatch(h, plan('initialize_control', root,
                    control_seed=dict(candidate=root, condition_id=cid, method='baseline')), 'seed-' + cid)['result']
                core.dispatch(h, plan('diagnose', c, next_research_action='control_feasibility'), 'diagnose-' + cid)
                question = dict(version='scientific_question_v4', domain='control', control=dict(
                    question_type='control_feasibility', effect_semantics='reoptimized_task_capability',
                    control_scope=dict(mode='full_task'), control_search_effort=dict(
                        method='response', knot_count=4, iterations=1, evaluation_requests=26)))
                compiled = compile_question(h, question, tool_use_id='compile-' + cid)
                self.assertEqual(compiled['status'], 'ready', compiled)
                request = AnalysisRequest.model_validate(compiled['request'])
                self.assertEqual(request.operation, 'mujoco_nonlinear_task_capability_v1')
                self.assertEqual(request.control_optimization.settings.evaluation_requests, 26)
                self.assertEqual(compiled['request']['candidate'], c)
                Plan.model_validate(plan('physical_replay', c, physical_replay=dict(candidate=c, source=seed['source'])))
                rows.append(dict(condition_id=cid, compatibility=fit, baseline_initialized=True,
                                 t1_compiled=True, replay_plan_validated=True))
            for row in fixture['knowledge_manifest']['entries']:
                receipt = retrieve(h, dict(operation='read', entry_id=row['entry_id'], revision=row['revision']),
                                   reader='offline_preparation_fixture')
                self.assertEqual(receipt['results'][0]['content_sha256'],
                                 hashlib.sha256((ROOT / row['path']).read_bytes()).hexdigest())
            self.assertFalse(retrieve(h, dict(operation='search', entry_id='model-physics-comparison'))['results'])
            with self.assertRaisesRegex(ValueError, 'EXACT_EXPERIENCE_READ_REQUIRES_ONE_ENTRY'):
                retrieve(h, dict(operation='read', entry_id='m1-research', revision='1'))
            self.assertEqual(state(h)['mathematical_evaluations'], 0)
            self.assertFalse(state(h)['physical_replays'])
            self.assertEqual(h.store.remaining()['used']['backend_solves'], 0)
            atomic_json(ROOT / 'runs/m1-preparation/condition_admission.json', dict(
                scope='Fabricated offline fixture only; no Provider, numerical worker or integration',
                conditions=rows, actual_provider_requests=0, mathematical_evaluations=0,
                physical_launches=0, main_knowledge_reads_in_formal_study=0))
