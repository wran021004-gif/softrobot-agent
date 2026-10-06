"""Bounded scheduling risks, using labelled synthetic outcomes and zero live work."""
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import MagicMock, patch
from tools.research_spec import load_spec, LEGACY_SPEC_PATH, ResearchSpecification
from tools.fixed_research import baseline_plan, run_study, prepare_candidate, select_candidate


class RevisionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.spec=load_spec()

    def test_frozen_parent_physics_cases_and_observed_development_failure(self):
        old=load_spec(LEGACY_SPEC_PATH);new=self.spec
        for key in ('starting_configuration','execution_template','cases','repetitions','acceptance','parameter_grants','formal_budget_per_group'):
            self.assertEqual(old[key],new[key],key)
        self.assertFalse(new['revision']['preserved_smoke']['unseen'])
        self.assertEqual(new['revision']['preserved_smoke']['status'],'observed_development_valid_failure')
        bad=deepcopy(new);bad['fixed_baseline']['allocation']['search_adaptation']=9
        with self.assertRaisesRegex(ValueError,'MATCHED_VALIDATION_ALLOCATION_CHANGED'):
            ResearchSpecification.model_validate(bad)

    def test_declared_family_and_control_allocation_and_shared_preparation(self):
        plan=baseline_plan(self.spec)
        self.assertEqual(len(plan['search_schedule']),8)
        self.assertEqual([s['family'] for s in self.spec['fixed_baseline']['structure_slots']],['unchanged','length','section','material'])
        self.assertEqual(len(plan['planned_coverage']['changed_variables']),5)
        self.assertEqual(len(plan['planned_coverage']['unvisited_variables']),3)
        with patch('tools.platform_search.parameter_search',wraps=__import__('tools.platform_search',fromlist=['parameter_search']).parameter_search) as shared, \
                patch('extensions.tendon_family.backends.MujocoBackend.run',side_effect=AssertionError('OFFLINE')), \
                patch('tools.model_transports.deepseek.request_completion',side_effect=AssertionError('OFFLINE')):
            for n,slot in enumerate(plan['search_schedule']):
                inp,_=prepare_candidate(self.spec,candidate_id=f'offline-{n}',changes=slot['changes'],case_id='nominal',seed=17)
                self.assertEqual(inp['policy']['controller']['version'],'7.0.0')
            self.assertEqual(shared.call_count,7)

    def execute_fixture(self, *, eligible=True, incomplete=False, available=28, anchor_failure=False):
        """Bookkeeping fixture only; fake rows cannot be cited as robot evidence."""
        store=MagicMock();store.root=Path('runs/offline-scheduling-fixture')
        budget=dict(backend_solves=available,tool_calls=100,wall_s=30000.,model_calls=0,worker_calls=0)
        used={k:0 for k in budget};calls=[]
        store.remaining.side_effect=lambda:dict(remaining=deepcopy(budget),used=deepcopy(used))
        def evaluate(_store,_spec,**args):
            calls.append(deepcopy(args))
            for key,cost in dict(backend_solves=1,tool_calls=3,wall_s=100.).items():budget[key]-=cost;used[key]+=cost
            execution='synthetic-'+args['candidate_id']
            accepted=eligible or not args['changes']
            if anchor_failure and args['purpose']=='matched_validation_unchanged_incumbent':accepted=False
            acc=dict(contract='research.task_acceptance',protocol_id='offline_reach_hold_v1',task_family='task.reach',
                task_identity='synthetic-task',status='accepted' if accepted else 'valid_failure',accepted=accepted,execution_id=execution,
                metrics=dict(terminal_error_m=.003,holding_max_error_m=.004,holding_max_speed_m_s=.01 if accepted else .04))
            if incomplete and args['purpose'].startswith('matched_validation'):
                acc.update(status='incomplete',accepted=None)
            return dict(**args,status='completed',configuration={'artifact_id':'a'*64,'media_type':'application/json'},acceptance=acc,
                receipt=dict(execution_id=execution,original_execution_id=execution,tool_id='simulation.run',cache_hit=False,charged=dict(backend_solves=1)))
        with patch('tools.fixed_research._project',return_value=store),patch('tools.fixed_research.atomic_json'), \
                patch('tools.fixed_research.evaluate_candidate',side_effect=evaluate), \
                patch('extensions.tendon_family.backends.MujocoBackend.run',side_effect=AssertionError('OFFLINE')), \
                patch('tools.model_transports.deepseek.request_completion',side_effect=AssertionError('OFFLINE')):
            delivery=run_study(store.root,self.spec)
        return delivery,calls

    def test_matched_validation_unchanged_anchor_and_one_frozen_candidate(self):
        d,calls=self.execute_fixture()
        self.assertEqual(len(calls),28);self.assertEqual(d['search_attempts'],8)
        self.assertEqual(len(d['robustness']),2)
        self.assertEqual(d['robustness'][0]['acceptance']['schedule_identity'],d['robustness'][1]['acceptance']['schedule_identity'])
        for incumbent,candidate in zip(calls[8::2],calls[9::2]):
            self.assertEqual(incumbent['changes'],{})
            self.assertEqual(candidate['changes'],d['selected_candidate']['changes'])
            for k in ('case_id','seed','repetition'):self.assertEqual(incumbent[k],candidate[k])
        self.assertFalse(d['candidate_promoted']) # Equivalent complete comparison retains incumbent.
        self.assertEqual(len(d['actual_search_coverage']['changed_variables']),5)

    def test_no_candidate_leaves_ten_slots_unused_and_no_improvement(self):
        d,calls=self.execute_fixture(eligible=False)
        self.assertEqual(len(calls),18)
        self.assertEqual(d['selection_outcome'],'no_eligible_new_candidate')
        self.assertEqual(d['validation_plan']['unused_candidate_allocation'],10)
        self.assertEqual(d['budget']['remaining']['backend_solves'],10)
        self.assertFalse(d['improvement_claim_supported'])
        self.assertIsNone(d['selected_candidate'])

    def test_validation_reservation_limits_search_and_incomplete_blocks_claims(self):
        d,calls=self.execute_fixture(available=20)
        self.assertEqual(d['search_attempts'],0);self.assertEqual(len(calls),10)
        d,_=self.execute_fixture(incomplete=True)
        self.assertEqual(d['matched_comparison']['relation'],'unavailable')
        self.assertFalse(d['candidate_promoted']);self.assertFalse(d['stop']['success_claim_supported'])

    def test_cached_or_misbound_nominal_result_is_not_eligible(self):
        d,_=self.execute_fixture()
        rows=deepcopy(d['results'][:8])
        for r in rows:r['receipt']['cache_hit']=True
        self.assertIsNone(select_candidate(rows))
        for r in rows:r['receipt'].update(cache_hit=False,execution_id='mismatched')
        self.assertIsNone(select_candidate(rows))

    def test_promotion_and_success_use_only_complete_matched_results(self):
        d,_=self.execute_fixture(anchor_failure=True)
        self.assertTrue(d['candidate_promoted']);self.assertTrue(d['improvement_claim_supported'])
        self.assertEqual(d['stop']['acceptance_result'],d['robustness'][1]['acceptance'])
        self.assertTrue(d['stop']['success_claim_supported'])


if __name__=='__main__':unittest.main()
