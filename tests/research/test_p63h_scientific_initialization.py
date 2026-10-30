"""Compiler-only fixtures; no Provider, worker, numerical solve or physics."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from tools.research.contracts import AnalysisRequest, ScientificQuestion
from tools.research.scientific_intent import compile_question
from tools.research.optimal_capability import CONIC
from tools.research.nonlinear_capability import T1_OPERATION
from tools.research.state import state, update
from tests.research.test_p63c2_scientific_intent import question_host, control_question
from tests.research.test_p63a_math_interface import generate, diagnose, t1_request


class ScientificInitializationTests(unittest.TestCase):
    def setUp(self):
        for name in ('tools.service_execution._run_contained',
                     'extensions.math_analysis.conic_capability.conic_capability',
                     'extensions.tendon_family.mujoco_analysis.NativeModel',
                     'tools.research.provider.load_credential'):
            p=patch(name,side_effect=AssertionError('NO_REAL_EXECUTION'))
            p.start();self.addCleanup(p.stop)
        self.h=question_host();spec=deepcopy(state(self.h)['spec'])
        spec['mathematical_methods'][CONIC]='Synthetic compiler fixture only'
        update(self.h,spec=spec)
        self.c=generate(self.h);diagnose(self.h,self.c,'scientific_question')

    def compile(self, **fields):
        return compile_question(self.h,dict(question_type='bounded_control_initialization',**fields),tool_use_id='p63h-fixture')

    def test_compiles_original_conic_without_control_source_or_execution(self):
        before=deepcopy(state(self.h));out=self.compile()
        self.assertEqual(out['status'],'ready');self.assertEqual(out['method'],CONIC)
        q=AnalysisRequest.model_validate(out['request'])
        self.assertEqual(q.operation,'task_capability');self.assertEqual(q.capability_method,CONIC)
        self.assertEqual(q.model_source,'gvs');self.assertEqual(q.operating_point,'standardized_initial_pretension')
        self.assertEqual(out['request']['protocol'],before['spec']['analysis_protocol'])
        self.assertIsNone(q.control_optimization)
        self.assertEqual(state(self.h)['mathematical_evaluations'],before['mathematical_evaluations'])
        self.assertEqual(state(self.h).get('control_initializations'),before.get('control_initializations'))
        self.assertFalse(out['scientific_execution_started'])
        from tools.research.agent import plan_schema
        schema=plan_schema(['initialize_control'],study=state(self.h)['spec'])
        self.assertIn('capability_sequence',schema['$defs']['ControlSeedRequest']['properties']['method']['description'])

    def test_rejects_native_budget_source_and_structural_semantic_substitution(self):
        for fields in [dict(requested_budget=2),dict(search_strategy='response'),dict(control_scope=dict(mode='full_task')),
                dict(parameter_paths=['segments.0.length_m']),dict(effect_semantics='reoptimized_task_capability'),
                dict(source_selection=dict(control_source=self.c)),dict(source_selection=dict(t1_results=[self.c])),
                dict(fixed_input='frozen_initial_tensions'),dict(tensions_n=[1.]*4),dict(response_horizon_s=.01)]:
            with self.subTest(fields=fields):
                self.assertEqual(self.compile(**fields)['status'],'unsupported')

    def test_missing_grant_and_dependency_remain_original_blocks(self):
        spec=deepcopy(state(self.h)['spec']);spec['mathematical_methods'].pop(CONIC);update(self.h,spec=spec)
        self.assertEqual(self.compile()['status'],'blocked')
        spec['mathematical_methods'][CONIC]='Synthetic fixture';update(self.h,spec=spec)
        with patch('tools.research.optimal_capability.dependencies',return_value=dict(available=False,reason='fixture missing dependency')):
            self.assertEqual(self.compile()['status'],'unsupported')

    def test_control_feasibility_stays_native_and_never_uses_conic_implicitly(self):
        t1_request(self.h,self.c);diagnose(self.h,self.c,'scientific_question')
        out=compile_question(self.h,control_question(),tool_use_id='p63h-native-fixture')
        self.assertEqual(out['status'],'ready');self.assertEqual(out['request']['operation'],T1_OPERATION)
        self.assertNotIn('capability_method',out['request'])
        schema=ScientificQuestion.model_json_schema()
        self.assertIn('bounded_control_initialization',schema['properties']['question_type']['enum'])

    def test_mock_main_wire_requests_conic_without_solver_fields_or_automatic_native(self):
        from pathlib import Path
        from types import SimpleNamespace
        from tools.state_io import read,atomic_json
        from tests.research.test_recent_round_tools import run_fixture
        question=dict(question_type='bounded_control_initialization')
        def contained(command,log,timeout,**kwargs):
            path=Path(command[-1]);request=read(path);q=request['query']
            self.assertEqual(q['operation'],'task_capability');self.assertEqual(q['capability_method'],CONIC)
            self.assertEqual(q['model_source'],'gvs');self.assertIsNone(q.get('control_optimization'))
            atomic_json(path.with_name('result.json'),dict(status='unavailable',
                reason='SYNTHETIC_STUB_NO_NUMERICAL_COMPUTATION',task_acceptance='unmeasured'))
            return SimpleNamespace(returncode=0)
        with patch('tools.service_execution._run_contained',side_effect=contained), \
                patch('tools.research.reporter.scientific_feedback',return_value=None):
            wires=run_fixture(self.h,[('research_analysis',question),None])
        schema=next(t['function']['parameters'] for t in wires[0]['tools'] if t['function']['name']=='research_analysis')
        self.assertIn('bounded_control_initialization',schema['properties']['question_type']['enum'])
        self.assertNotIn('capability_method',schema['properties'])
        bindings=[self.h.store.artifact(e['outputs'][0]) for e in self.h.store.events(self.h.run_id)
            if e['kind']=='analysis_request_binding']
        self.assertEqual(bindings[-1]['raw_main_input'],question)
        self.assertEqual(state(self.h)['mathematical_evaluations'],2)
        self.assertFalse(state(self.h).get('control_initializations'))
        self.assertEqual(len(state(self.h)['analysis_results']),1)


if __name__=='__main__':unittest.main()
