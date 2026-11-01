"""General interface readiness only: Mock motion, no Provider/worker/integration."""
from copy import deepcopy
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator
from tools.research import core
from tools.research.config import ROOT, resolve
from tools.research.contracts import AnalysisRequest
from tools.research.nonlinear_capability import T1, T1_OPERATION, T2
from tools.research.scientific_intent import DIRECT, compile_question, question_schema, control_method_choices
from tools.research.state import state, update
from tools.research.task_constraints import mathematical_method_view
from tests.research.test_cross_task_integration import fixture_directory, fixture_host, plan


def v4_question(**changes):
    return dict(version='scientific_question_v4',domain='control',control=dict(
        question_type='control_feasibility',effect_semantics='reoptimized_task_capability',
        control_scope=dict(mode='full_task'),control_search_effort=dict(
            method='response',knot_count=4,iterations=1,evaluation_requests=1),**changes))


class GeneralTaskAdaptationTests(unittest.TestCase):
    def setUp(self):
        for name in ('tools.service_execution._run_contained','mujoco.mj_step',
                     'tools.research.provider.load_credential'):
            p=patch(name,side_effect=AssertionError('NO_REAL_PROVIDER_WORKER_OR_PHYSICS'))
            p.start();self.addCleanup(p.stop)

    def test_v4_candidate_catalog_routes_native_without_t1_impersonation(self):
        for leaf in ('study_tracking_public.json','study_bf5_public.json','study_bf6_public.json'):
            with self.subTest(leaf=leaf), fixture_directory() as folder:
                h=fixture_host(folder,leaf);spec=deepcopy(state(h)['spec'])
                spec['research_decisions']=resolve(ROOT/'configs/research/study_r0_m1_v4_draft.json')['research_decisions']
                spec.setdefault('mathematical_methods',{}).update({T1:'MOCK ONLY',T2:'MOCK ONLY'})
                spec['budgets']['mathematical_evaluations']=4
                update(h,spec=spec)
                with patch('tools.research.core.guard'),patch('tools.research.state.guard'):
                    request=dict(version='serial_family_generation_v2',family_space_identity=spec['family_space_identity'],
                        segment_count=2,tendon_count=6)
                    c=core.dispatch(h,plan('generate',generation=request),'generate')['result']['candidate']
                    seed=core.dispatch(h,plan('initialize_control',c,control_seed=dict(candidate=c)),'seed')['result']
                    diagnosis=plan('diagnose',c,next_research_action='control_feasibility')
                    diagnosis['decision'].pop('selected_method')
                    core.dispatch(h,diagnosis,'diagnose')
                view=mathematical_method_view(h,c)
                choices=control_method_choices(view)
                self.assertEqual([r['method'] for r in choices if r['selectable']],[DIRECT],choices)
                self.assertFalse(view['methods'][T1]['kernel_supported'])
                self.assertFalse(view['methods'][T2]['kernel_supported'])
                q=v4_question();schema=question_schema(spec,h.store.artifact(c),'control_feasibility')
                Draft202012Validator(schema).validate(q)
                compiled=compile_question(h,q,tool_use_id='mock-native-compile')
                self.assertEqual(compiled['status'],'ready',compiled)
                self.assertEqual(compiled['method'],DIRECT)
                full=compiled['request'];AnalysisRequest.model_validate(full)
                self.assertEqual(full['operation'],DIRECT)
                self.assertEqual(full['control_optimization']['source'],seed['source'])
                self.assertEqual(full['control_optimization']['settings']['evaluation_requests'],1)
                self.assertEqual(full['protocol'],spec['analysis_protocol'])
                rejected=compile_question(h,v4_question(numerical_method=T1),tool_use_id='mock-invalid-t1')
                self.assertEqual(rejected['status'],'unsupported')
                closed=deepcopy(spec);closed['budgets']['mathematical_evaluations']=0
                update(h,spec=closed)
                self.assertNotEqual(compile_question(h,q,tool_use_id='mock-no-budget')['status'],'ready')
                self.assertEqual(state(h)['mathematical_evaluations'],0)
                self.assertFalse(state(h)['physical_replays'])


if __name__=='__main__':unittest.main()
