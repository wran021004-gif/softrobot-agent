"""Resource-contract fixtures; no formal Study edits or scientific claims."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from tools.research import config,analysis
from tools.research.budget import decision_budget,science_fits,protected
from tools.research.state import state,update,require_research_authorization
from tools.research.scientific_intent import control_settings
from tools.research.contracts import ScientificControlEffort,FamilyMixedSearch
from tests.research.test_m1_native_search_scope import scoped_fixture,proposal,SPEC
from tests.research import test_bf7_native_search as native_fixture
from tools.research.structure_intent import compile_search
from tools.research import search


def unmetered(h):
    s=state(h);spec=deepcopy(s['spec']);spec['budgets']['mathematical_evaluations']=None
    spec['analysis_cap_s']=600
    spec['native_control_limits']=dict(evaluation_requests=8000,iterations=1000,knots_s=16)
    spec['family_search'].update(max_proposals=1024,max_evaluations=3072)
    update(h,spec=spec)
    return spec


class UnmeteredNativeResourcesTests(unittest.TestCase):
    def test_no_count_exhaustion_but_provider_and_exact_authorization_still_apply(self):
        with scoped_fixture() as h:
            unmetered(h);update(h,mathematical_evaluations=1000000)
            self.assertEqual(analysis.admission(h,5000)['admitted'],5000)
            self.assertEqual(analysis.admission(h)['timeout_s'],600)
            self.assertTrue(science_fits(h));self.assertFalse(protected(h))
            budget=decision_budget(h)
            self.assertIsNone(budget['science_budget']['remaining_mathematical'])
            self.assertTrue(budget['science_budget']['any_scientific_route_fits'])
            from tools.research.research_context import agent_decision_brief
            brief=agent_decision_brief(h)
            self.assertIsNone(brief['budget']['science_budget']['remaining_mathematical'])
            with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL'):require_research_authorization(h)
            with patch.object(h.store,'remaining',return_value=dict(remaining=dict(model_calls=12,tool_calls=500,backend_solves=18))):
                self.assertTrue(protected(h))

    def test_resolver_and_compiler_accept_explicit_large_finite_resources(self):
        original=config.read;raw=deepcopy(original(SPEC));raw['budgets']['mathematical_evaluations']=None
        raw['analysis_cap_s']=600;raw['native_control_limits']=dict(evaluation_requests=8000,iterations=1000,knots_s=16)
        raw['family_search'].update(max_proposals=1024,max_evaluations=3072)
        with patch.object(config,'read',side_effect=lambda p:raw if p==SPEC else original(p)):
            resolved=config.resolve(SPEC)
        self.assertIsNone(resolved['budgets']['mathematical_evaluations'])
        settings=control_settings(resolved,ScientificControlEffort(method='pattern',knot_count=16,iterations=1000,evaluation_requests=8000))
        self.assertEqual((len(settings.knots_s),settings.iterations,settings.evaluation_requests),(16,1000,8000))
        default=control_settings(resolved,ScientificControlEffort(method='pattern',knot_count=8,evaluation_requests=8000))
        self.assertEqual(default.iterations,1000)
        with scoped_fixture() as h:
            unmetered(h)
            p=compile_search(h,proposal(structure_search_effort=dict(max_proposals=1024,max_evaluations=3072),
                control_search_effort=dict(method='pattern',iterations=1000,knot_count=16,evaluation_requests=8000)),'large-finite')
            self.assertEqual(p['search']['max_evaluations'],3072)

    def test_engineering_watchdog_keeps_partial_cost_and_idempotent_result(self):
        import subprocess
        from pathlib import Path
        from tools.state_io import atomic_json
        from tests.research.test_r3_b_stage1 import integrated_host
        from tests.research.test_p63a_math_interface import t1_request
        h,c=integrated_host();s=state(h);spec=deepcopy(s['spec'])
        spec['budgets']['mathematical_evaluations']=None;spec['analysis_cap_s']=600
        update(h,spec=spec,mathematical_evaluations=1000000)
        q=t1_request(h,c)
        def timeout(command,log,limit,**kwargs):
            self.assertEqual(limit,600)
            atomic_json(Path(command[-1]).with_name('numerical_native_progress_0001.json'),
                dict(cost=dict(rollouts=1,physics_steps=400),fixture='Synthetic partial cost; no physics'))
            exc=subprocess.TimeoutExpired(command,limit);exc.termination_confirmed=True
            raise exc
        with patch('tools.service_execution._run_contained',side_effect=timeout):
            result=analysis.dispatch(h,q,'watchdog-fixture',guard=lambda *a:None,origin='engineering_preflight')
        raw=h.store.artifact(result['reference'])
        self.assertEqual(raw['status'],'incomplete');self.assertTrue(raw['boundary']['timed_out'])
        self.assertEqual(raw['native_progress']['cost']['physics_steps'],400)
        self.assertEqual(state(h)['mathematical_evaluations'],1000001)
        self.assertIsNone(state(h)['pending']);self.assertNotEqual(state(h)['research_status'],'stopped')
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_REPEAT_WORKER')):
            reused=analysis.dispatch(h,q,'watchdog-fixture',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(reused['reference'],result['reference'])

    def test_bigger_batch_interruption_resumes_existing_results_without_recharge(self):
        with scoped_fixture() as h:
            unmetered(h)
            p=compile_search(h,proposal(['lengths','materials','routing'],structure_search_effort=dict(max_proposals=10,max_evaluations=30)),'ten-structures')
            calls=[];score=native_fixture.NativeMixedSearchTests().scored
            def interrupt(*a,**k):
                out=score(*a,**k);calls.append(out)
                if len(calls)==2:raise RuntimeError('settled result then supervisor interruption')
                return out
            with patch.object(analysis,'dispatch',side_effect=interrupt),self.assertRaises(RuntimeError):
                search.run_search(h,p['search'],'ten-structures',guard=lambda *a:None,execute=None,capacity=None)
            self.assertEqual(state(h)['mathematical_evaluations'],2)
            with patch.object(analysis,'dispatch',side_effect=score):
                out=search.run_search(h,p['search'],'resumed-ten',guard=lambda *a:None,execute=None,capacity=None)
            self.assertGreater(out['result']['resource_use']['actual_mathematical_evaluations'],24)
            self.assertEqual(out['result']['evaluated'][0]['evidence']['conditions']['negative_low']['analysis'],calls[1]['reference'])
            count=state(h)['mathematical_evaluations']
            with patch.object(analysis,'dispatch',side_effect=AssertionError('NO_DUPLICATE_WORKER')):
                self.assertTrue(search.run_search(h,p['search'],'same-request-again',guard=lambda *a:None,execute=None,capacity=None)['reused'])
            self.assertEqual(state(h)['mathematical_evaluations'],count)

    def test_actual_optimizer_has_no_hidden_800_callback_or_100_iteration_cap(self):
        from tools.research.local_control_search import search as optimize
        from tests.research.test_local_control_search import start
        initial=start();initial['limits']=[1000000]*4
        calls=[]
        def evaluate(_start,_source,_meta):
            calls.append(1);gap=10000-len(calls)
            return dict(reference=dict(artifact_id=str(len(calls))),outputs={},measure=dict(signed_maximum_excess=gap),
                task_gap=dict(valid_complete=True,normalized_gap=gap,accepted=False),cost_s=0,independent_evaluation_executed=False)
        settings=dict(version='local_control_search_v2',method='pattern',correction_window_s=[0,.35],
            knots_s=[.35*i/15 for i in range(16)],iterations=1000,evaluation_requests=8000,
            active_coefficients=[0],coefficient_limit_n=1000000)
        out=optimize([initial],evaluate,settings,rank_key=lambda r:r['measure']['signed_maximum_excess'])
        self.assertEqual(out['iterations_started'],1000);self.assertEqual(len(calls),1001)
        calls.clear();settings['iterations']=10000
        out=optimize([initial],evaluate,settings,rank_key=lambda r:r['measure']['signed_maximum_excess'])
        self.assertEqual(len(calls),8000);self.assertEqual(out['stop_reason'],'evaluation_request_budget')


if __name__=='__main__':unittest.main()
