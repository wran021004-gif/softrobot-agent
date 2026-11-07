"""Existing search/Store/worker path with explicitly synthetic model results."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from jsonschema import Draft202012Validator

from tools.platform_store import plain
from tools.research import core,search,reporter
from tools.research.state import state,update
from tools.research.research_context import compact_evidence
from tests.research.test_matched_interaction import compiled_fixture,BilinearNative
from tests.research.test_structure_mechanism_aplus import synthetic_worker


def fixture():
    h,c,request=compiled_fixture();spec=deepcopy(state(h)['spec'])
    spec['capabilities']=list(set(spec['capabilities'])|{'search'})
    spec['allowed_plan_actions']=list(set(spec.get('allowed_plan_actions',[]))|{'search','diagnose'})
    spec['family_search']=dict(method='bounded_mixed_coordinate_v1',coupled_block_enabled=True,
        variable_groups=['lengths'],segment_counts=[2],tendon_counts=[4],
        max_proposals=4,max_evaluations=4,evaluation_modes=['mathematical_proxy'])
    spec['research_decisions']['structure_search_interface']='scientific_structure_search_v1'
    update(h,spec=spec)
    question=dict(operation='interact',effect_semantics='mechanism_effect',
        parameter_paths=['segments.0.length_m','segments.1.length_m'],target=dict(quantity='mass_matrix',reduction='norm'),
        operating_point='frozen_task_initial_state',control_treatment='fixed_absolute_tensions')
    query=dict(version='family_mixed_search_v2',method='bounded_coupled_block_v1',
        family_space_identity=spec['family_space_identity'],previous_candidate_ref=c,analysis=question)
    plan=dict(action='search',search=query,hypothesis='SYNTHETIC coupling fixture; no physical claim',
        expected_observation='Four matched model observations',weakening_observation='Invalid or unmatched contrast',
        fixed_conditions='Frozen fixture task, model, initial state, control and other parameters',
        interpretation='Offline fixture only',stopping_condition='One finite matched block',
        decision=dict(hypothesis_id='fixture-block',research_intent='MATHEMATICAL_ANALYSIS',
            selected_candidate=c,selected_method='bounded_coupled_block_v1',selected_variables=question['parameter_paths'],requested_budget=4))
    return h,c,query,plan


class CoupledSearchTests(unittest.TestCase):
    def test_shared_four_point_worker_cost_reuse_and_reporter_handoff(self):
        h,c,q,plan=fixture();before=state(h);count=len(before['candidates'])
        # The native scientific search schema delegates these binding fields.
        for key in ('research_intent','selected_method','requested_budget'):plan['decision'].pop(key)
        from tools.research.agent import plan_schema
        Draft202012Validator(plan_schema(['search'],decision_required=True,focused=True,study=state(h)['spec'])).validate(plan)
        with patch.object(core,'guard'),synthetic_worker(h,c,model=BilinearNative):
            out=core.dispatch(h,plan,'synthetic-coupled-search')
        saved=h.store.artifact(out['result']['reference']) if 'result' in out and out['result'].get('reference') else h.store.artifact(out['reference'])
        # Core wraps the existing run_search response, just like coordinate mode.
        result=saved['result'];self.assertEqual(result['status'],'matched_block_completed')
        self.assertEqual(len(result['evaluated']),4)
        self.assertEqual(result['resource_use']['actual_mathematical_evaluations'],4)
        self.assertEqual(result['resource_use']['candidate_materializations'],0)
        self.assertEqual(len(state(h)['candidates']),count)
        self.assertEqual(state(h)['mathematical_evaluations']-before['mathematical_evaluations'],4)
        budget=h.store.remaining();reused=search.run_search(h,q,'another-key',guard=lambda *a:None,execute=None,capacity=None)
        self.assertTrue(reused['reused']);self.assertEqual(h.store.remaining(),budget)
        report=reporter.assemble(h,[reused['reference']])
        self.assertEqual(reporter.interpretation_priority(plain(report),[],decision_v3=True),'new_matched_interaction_result')
        wire=reporter._wire(h,reused['reference'],dict(report=plain(report),interpretation_status='deferred',
            interpretation_for=reused['reference'],request={},error=None))
        packet=json.loads(wire['messages'][1]['content'])
        self.assertTrue(any(s['reference']==result['mathematical_analysis'] for s in packet['source_catalog'].values()))
        summary=compact_evidence(saved,reused['reference'],facts_only=True)['summary']['coupled_block_search']
        self.assertEqual(summary['interaction']['interaction_effect'],result['interaction']['interaction_effect'])

    def test_incomplete_block_counts_failed_attempt_and_skips_without_effect(self):
        h,c,q,plan=fixture();baseline=h.store.artifact(c)['resolved_parameters']['segments'][0]['length_m']
        class InvalidFirstChange(BilinearNative):
            def mechanics(self,data,u):
                if self.lengths[0]!=baseline:raise ValueError('SYNTHETIC_INVALID_FIRST_CHANGED_MODEL')
                return super().mechanics(data,u)
        with patch.object(core,'guard'),synthetic_worker(h,c,model=InvalidFirstChange):
            core.dispatch(h,plan,'synthetic-incomplete-block')
        result=h.store.artifact(state(h)['search_results'][-1])['result'];cost=result['resource_use']
        self.assertEqual(result['status'],'matched_block_incomplete')
        self.assertIsNone(result['interaction']['interaction_effect'])
        self.assertEqual(cost['attempted_points'],2);self.assertEqual(cost['unrecorded_failed_attempts'],1)
        self.assertEqual(len(cost['skipped_moves']),2);self.assertEqual(cost['actual_mathematical_evaluations'],2)
        self.assertEqual(cost['charged_mathematical_evaluations'],4)

    def test_whole_block_admission_and_discrete_or_ungranted_parameters(self):
        h,c,q,plan=fixture()
        with self.assertRaisesRegex(ValueError,'ALL_FOUR'):search.search_problem(h,q,3)
        discrete=deepcopy(q);discrete['analysis']['parameter_paths'][0]='segment_count'
        with self.assertRaisesRegex(ValueError,'DISCRETE_PARAMETER'):search.search_problem(h,discrete,4)
        spec=deepcopy(state(h)['spec']);spec['family_search']['coupled_block_enabled']=False;update(h,spec=spec)
        with self.assertRaisesRegex(ValueError,'FROZEN_COUPLED'):search.search_problem(h,q,4)

    def test_worker_exit_without_cost_keeps_actual_attempts_unknown(self):
        h,c,q,plan=fixture()
        with patch.object(core,'guard'),patch('tools.service_execution._run_contained',return_value=SimpleNamespace(returncode=1)):
            core.dispatch(h,plan,'synthetic-worker-exit')
        result=h.store.artifact(state(h)['search_results'][-1])['result'];cost=result['resource_use']
        self.assertEqual(result['status'],'matched_block_incomplete')
        self.assertIsNone(result['interaction']);self.assertIsNone(cost['actual_mathematical_evaluations'])
        self.assertIsNone(cost['attempted_points']);self.assertIsNone(cost['skipped_moves'])
        self.assertEqual(cost['charged_mathematical_evaluations'],4)


if __name__=='__main__':unittest.main()
