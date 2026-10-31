"""Small synthetic protocol fixtures; no live Provider or scientific Worker."""
from copy import deepcopy
import json,unittest
from unittest.mock import patch
from tools.research.state import state,save,update
from tools.research.feedback import search_feedback,scientific_result_delivery
from tools.research.evidence_policy import registered_references,citation_role
from tools.research.design import verify_candidate
from tools.research.agent import decision_packet
from tests.research.test_p63g3_action_handoff import g3_host
from tests.research.test_p63a_math_interface import generate
from tests.research.test_recent_round_tools import run_fixture
from tests.research.test_information_flow import packet


def fixture(h,c,J,status='computed'):
    # Fabricated values test projection/ranking only, never scientific evidence.
    constraints=[dict(constraint_id=k,radius=v,signal=dict(units=u)) for k,v,u in
        [('terminal_error_m',.01,'m'),('holding_max_error_m',.01,'m'),('holding_max_speed_m_s',.02,'m/s')]]
    source=save(h,dict(fixture=True,control_for=c,J=J))
    best=dict(measure=dict(terminal_position_error_m=.009,holding_max_position_error_m=.0095,
        holding_max_speed_m_s=.019,signed_maximum_excess=J),task_gap=dict(valid_complete=status=='computed'))
    analysis=save(h,dict(candidate=c,status=status,operation='mujoco_nonlinear_task_capability_v1',
        control_schedule_reference=source,task_analysis=dict(constraints=constraints),
        binding=dict(canonical_task_identity='offline-task'),native_dynamics=dict(optimization=dict(best=best),cost=dict(rollouts=3)),
        requested_operation=dict(model_source='mujoco',control_optimization=dict(settings=dict(method='response',iterations=2))),
        protocol=dict(protocol_id='offline-protocol'),charged_numerical_s=1.,limitations=['Synthetic protocol fixture only']))
    condition=dict(analysis=analysis,candidate=c,control_source=source,status=status,J=J)
    row=dict(evidence=dict(candidate=c,conditions=dict(primary=condition)),computation_status=status,
        proxy_values=dict(task_violation=J),lineage=dict(search_method='bounded_mixed_coordinate_v1'),mathematical_numerical_s=1.)
    checkpoint=save(h,dict(problem=dict(query=dict(groups=['routing'],max_proposals=1,max_evaluations=1))))
    ref=save(h,dict(result=dict(status='fixture_bounded_search',best_native_candidate=row,
        requesting_plan=save(h,dict(fixture_hypothesis='Synthetic bounded comparison')),
        comparison_summary=[dict(candidate=c,conditions=dict(primary=condition))],evaluated=[row],
        resource_use=dict(proposed_designs=1,actual_mathematical_evaluations=1,elapsed_s=1.),
        termination_reason='proposal_budget_exhausted',search_state=checkpoint,score_semantics='finite fixture J')))
    s=state(h);update(h,analysis_results=[*s.get('analysis_results',[]),analysis],search_results=[*s.get('search_results',[]),ref])
    return ref,analysis,source


class ScientificResultDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.h=g3_host();self.c=generate(self.h)
        p=patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER_ALLOWED'))
        p.start();self.addCleanup(p.stop)

    def test_search_has_exact_metrics_thresholds_sources_counts_and_cost(self):
        search,analysis,source=fixture(self.h,self.c,-.05)
        value=search_feedback(self.h,search);fixed=value['fixed_result'];fact=fixed['best_mathematical'][0]
        self.assertEqual((fact['candidate'],fact['reference'],fact['control_source'],fact['J']),(self.c,analysis,source,-.05))
        self.assertEqual([x['limit'] for x in fact['metrics']],[.01,.01,.02])
        self.assertTrue(all(x['signed_excess']<0 for x in fact['metrics']))
        self.assertEqual(fixed['status_counts']['computed'],1);self.assertFalse(fixed['scientific_citation_eligible'])
        self.assertEqual(fixed['results_query']['pointer'],'/result/comparison_summary')
        self.assertEqual(fact['cost']['native']['rollouts'],3)
        self.assertFalse(fact['independent_evaluation_executed']);self.assertFalse(fact['formal_acceptance_read_credit'])

    def test_latest_worse_and_last_incomplete_keep_first_best(self):
        first,a,_=fixture(self.h,self.c,-.05);second,_,_=fixture(self.h,self.c,-.02)
        third,_,_=fixture(self.h,self.c,-1.,status='execution_incomplete')
        value=scientific_result_delivery(self.h)
        self.assertEqual(value['latest_search']['reference'],third)
        self.assertEqual(value['study_best_mathematical'][0]['search_reference'],first)
        self.assertEqual(value['study_best_mathematical'][0]['fact']['reference'],a)
        self.assertEqual(value['latest_search']['fixed_result']['status_counts']['execution_incomplete'],1)
        failure=value['critical_failures'][-1]
        self.assertEqual(failure['status'],'execution_incomplete')
        self.assertEqual(failure['search_reference'],third)
        self.assertEqual(failure['source_query']['pointer'],'/result/comparison_summary/0/conditions/primary')

    def test_native_discovery_reads_metadata_once_before_variable_loop(self):
        from tools.research.optimal_capability import candidate_methods
        _,analysis,_=fixture(self.h,self.c,-.05)
        original=self.h.store.artifact;reads=[]
        def metadata_only(ref,**kwargs):
            if ref==analysis:
                self.assertIsNotNone(kwargs.get('paths'),'Native rollouts must not be decoded for every parameter')
                reads.append(ref)
            return original(ref,**kwargs)
        with patch.object(self.h.store,'artifact',side_effect=metadata_only):
            result=candidate_methods(self.h,self.c)
        self.assertTrue(result['variables'])
        self.assertEqual(len(reads),1)

    def test_incomparable_profiles_are_not_ranked_together(self):
        fixture(self.h,self.c,-.05)
        c=deepcopy(self.h.store.artifact(self.c));c['profile_identity']='different-profile'
        other=save(self.h,c);fixture(self.h,other,-.08)
        self.assertEqual(len(scientific_result_delivery(self.h)['study_best_mathematical']),2)

    def test_old_profile_observable_but_cannot_execute_and_recipe_is_legal(self):
        ref,analysis,_=fixture(self.h,self.c,-.05);s=state(self.h)
        profile=deepcopy(s['profile']);profile['identity']='offline-new-profile';update(self.h,profile=profile)
        value=search_feedback(self.h,ref);fact=value['fixed_result']['best_mathematical'][0]
        self.assertTrue(fact['scientific_observation_available']);self.assertFalse(fact['executable_under_current_profile'])
        self.assertTrue(fact['current_profile_requires_new_construction'])
        with self.assertRaisesRegex(ValueError,'OLD_EVALUATION_PROFILE'):verify_candidate(self.h,self.c)
        recipe=value['final_materialization'];self.assertEqual(recipe['action'],'generate')
        self.assertIn(analysis,recipe['supporting_evidence'])
        self.assertEqual(recipe['source_search'],ref)
        self.assertNotIn(ref,recipe['supporting_evidence'])
        self.assertTrue(all(r in registered_references(self.h) for r in recipe['supporting_evidence']))
        from tools.research.contracts import Plan
        from tools.research.evidence_policy import admit_decision
        from tests.research.test_p63g2_structure_intent import search_plan
        plan=search_plan();plan.pop('search');plan.update(action='generate',generation=recipe['generation'],
            supporting_evidence=recipe['supporting_evidence'])
        # The historical candidate is evidence, not an executable new selection.
        plan['decision'].update(selected_candidate=None,research_intent='DESIGN_MODIFICATION',selected_method='generate')
        self.assertEqual(admit_decision(self.h,Plan.model_validate(plan))['claimed_inference'],'empirical_search')

    def test_view_does_not_register_search_or_change_state(self):
        ref,_,_=fixture(self.h,self.c,-.05);before=deepcopy(state(self.h));known=registered_references(self.h)
        scientific_result_delivery(self.h)
        self.assertEqual(state(self.h),before);self.assertEqual(registered_references(self.h),known)
        self.assertNotIn(ref,known);self.assertNotEqual(citation_role(self.h,ref),'independent_evaluation')

    def test_hash_checked_sparse_read_preserves_types_and_missing_fields(self):
        ref=save(self.h,dict(a=dict(b=[1,True,None]),false=False,number=1.5,unused=[0]*10000))
        self.assertEqual(self.h.store.artifact(ref,paths=('a.b','false','number','missing')),
            dict(a=dict(b=[1,True,None]),false=False,number=1.5))
        with self.assertRaises(ValueError):self.h.store.artifact(ref,raw=True,paths=('a',))

    def test_actual_sdk_mock_wire_keeps_fact_card_and_existing_fields(self):
        fixture(self.h,self.c,-.05);facts=scientific_result_delivery(self.h)
        for status in ('available','unavailable','skipped'):
            with self.subTest(reporter=status):
                h=g3_host();generate(h);original=decision_packet(h)
                projected=deepcopy(original);projected['research']['scientific_results']=facts
                projected['research']['latest_reports']=[dict(report_reference=save(h,dict(offline_report=status)),
                    reporter_status=status,result_references=[],findings=[],interpretations=[],unresolved=[])]
                with patch('tools.research.agent.decision_packet',return_value=projected):
                    wire=run_fixture(h,[None])[0]
                delivered=packet(wire)
                self.assertEqual(delivered['scientific_results'],facts)
                self.assertEqual(delivered['reporter_findings'][0]['status'],status)
                for key in ('research_trace','tool_continuation','knowledge','budget','capabilities','research_focus','evidence_access'):
                    self.assertIn(key,delivered)
                self.assertLess(len(json.dumps(wire).encode()),1048576)
                self.assertEqual(state(h)['physical_replays'],[])

    def test_compiled_search_scope_and_registered_math_are_direct_facts(self):
        ref,analysis,_=fixture(self.h,self.c,-.05)
        query=dict(variable_groups=['lengths','routing'],segment_counts=[2],tendon_counts=[6],
            span_strategies=['whole_chain'],section_types=['ellipse','rectangle'],bounds={},
            initial_tension_n=0.,previous_candidate_ref=None,max_proposals=64,max_evaluations=64,method='bounded_mixed_coordinate_v1')
        value=deepcopy(self.h.store.artifact(ref))
        domains={'length_m':[.08,.2],'routing.radius_m':[.014,.023]}
        value['result']['search_state']=save(self.h,dict(problem=dict(query=query,domains=domains)))
        actual=search_feedback(self.h,save(self.h,value))['fixed_result']
        for key in ('variable_groups','segment_counts','tendon_counts','span_strategies','section_types','bounds','initial_tension_n','previous_candidate_ref'):
            self.assertEqual(actual['search_scope'][key],query[key])
        self.assertEqual(actual['search_scope']['resolved_domains'],domains)
        fact=actual['best_mathematical'][0]
        self.assertTrue(fact['citation']['registered'])
        self.assertEqual(fact['citation']['role'],'scientific_result')
        self.assertIn(analysis,registered_references(self.h))
        self.assertFalse(actual['scientific_citation_eligible'])
