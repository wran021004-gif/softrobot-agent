"""C-F directed checks: fixture facts only, no Provider or physical integration."""
from copy import deepcopy
import unittest
from unittest.mock import patch
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.research import analysis
from tools.research.contracts import AnalysisRequest
from tools.research.native_analysis import applicability, assessment
from tools.research.budget import decision_budget
from tools.research.research_context import tool_feedback
from tests.research.test_task_analysis_contract import TaskAnalysisTests
from tests.research.test_research_reporting import offline_host


class PrerequisiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        TaskAnalysisTests.setUpClass()

    def setUp(self):
        self.f=TaskAnalysisTests();self.f.setUp()

    def query(self,start=0.):
        end=self.f.req.duration_s
        return AnalysisRequest(candidate=self.f.ref,operation='mujoco_direct_control_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=self.f.q.protocol,
            control_optimization=dict(source=self.f.ref,settings=dict(version='local_control_search_v2',
                correction_window_s=[start,end],knots_s=[start,end])))

    def test_standard_initialization_covers_full_task_without_worker(self):
        inp=SessionInput.model_validate(self.f.cfg)
        fit=applicability(self.f.req,self.query(),assessment(inp,self.f.req),dict(phase='interval_start_native'))
        self.assertEqual(fit['status'],'applicable')
        self.assertEqual(fit['horizon']['legal_correction_window_s'],[0.,self.f.req.duration_s])
        self.assertTrue(fit['horizon']['covers_required_samples'])

    def test_late_window_does_not_manufacture_late_state(self):
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',side_effect=AssertionError('NO_PHYSICS')):
            result=analysis.calculate(self.f.cfg,self.f.binding,self.query(self.f.req.duration_s*.8),dict(actual_time_s=0.))
        self.assertEqual(result['status'],'not_applicable')
        host,_=offline_host({})
        with patch('tools.research.research_context.save',return_value=self.f.ref),patch('tools.research.evidence_policy.registered_references',return_value=[]):
            feedback=tool_feedback(host,result)['execution_feedback']
        self.assertFalse(feedback['worker_started'])
        self.assertIn('selected state time 0.0',str(feedback['reasons']))
        self.assertEqual(feedback['horizon']['legal_correction_window_s'],[0.,self.f.req.duration_s])

    def budget(self,shared,replays_used):
        spec=deepcopy(self.f.spec);spec['mode']='engineering_numerical'
        spec['budgets'].update(physical_launches=19,mathematical_evaluations=9)
        spec.update(physical_replay_limit=13,native_control_limits=dict(evaluation_requests=73,iterations=3,knots_s=4))
        host,s=offline_host({},spec=spec,analysis_results=[],physical_replay_launches=replays_used,mathematical_evaluations=2)
        host.store.events.return_value=[]
        host.store.session.side_effect=lambda *args:dict(state=s)
        host.store.remaining.return_value=dict(remaining=dict(model_calls=40,tool_calls=100,backend_solves=shared))
        return host,s,decision_budget(host)['science_budget']

    def test_plan_and_native_callback_caps_have_distinct_units(self):
        host,s,budget=self.budget(7,3)
        self.assertEqual(budget['plan_control_search']['declared_callback_maximum'],20)
        self.assertEqual(budget['native']['per_request_control_limits']['evaluation_requests'],73)
        self.assertEqual(budget['remaining_mathematical'],7)
        self.assertIn('full physical replay',budget['plan_control_search']['callback_unit'])
        host.store.reserve.assert_not_called()

    def test_replay_sublimit_does_not_add_to_shared_allowance(self):
        _,_,budget=self.budget(2,3)
        self.assertEqual(budget['remaining_full_replays'],10)
        self.assertEqual(budget['remaining_physical'],2)
        self.assertEqual(budget['available_full_replays'],2)

    def test_failed_worker_preserves_cause_cost_and_start_observation(self):
        value=dict(status='execution_incomplete',operation='mujoco_direct_control_v1',candidate=plain(self.f.q.candidate),
            error='ValueError',reason='FIXTURE_NATIVE_PREFIX_MISMATCH',boundary=dict(worker_started=True),
            charged_analysis_evaluations=1,charged_numerical_s=.125,
            native_progress=dict(cost=dict(physics_steps=17,rollouts=1)))
        feedback=analysis.compact_result(value,self.f.ref)['execution_feedback']
        self.assertTrue(feedback['worker_started'])
        self.assertEqual(feedback['reason'],'FIXTURE_NATIVE_PREFIX_MISMATCH')
        self.assertEqual(feedback['charged_analysis_evaluations'],1)
        self.assertEqual(feedback['native_cost']['physics_steps'],17)
        del value['boundary'];del value['native_progress']
        feedback=analysis.compact_result(value,self.f.ref)['execution_feedback']
        self.assertIsNone(feedback['worker_started'])
        self.assertIsNone(feedback['native_cost'])

    def test_generic_template_query_uses_only_shared_fields(self):
        from tests.research.test_c1_method_context import C1Archive
        from tools.research.task_constraints import mathematical_method_view,mathematical_catalog
        from tools.research.research_context import compact_scientific_delivery
        archive=C1Archive()
        try:
            host,s=archive.host();view=mathematical_method_view(host,s['reference_candidate'])
            brief=compact_scientific_delivery(dict(mathematical_capabilities=mathematical_catalog(view)),decision_only=True)
            catalog=brief['mathematical_capabilities'];fields=catalog['request_template_query_format']['fields']
            for key,row in view['methods'].items():
                self.assertTrue(set(fields)<=set(row),key)
            self.assertNotIn('action_prerequisites',fields)
            self.assertIn('action_prerequisites',catalog['methods']['mujoco_direct_control_v1']['request_template_query']['fields'])
            host.store.reserve.assert_not_called();host.store.transaction.assert_not_called()
        finally:archive.archive.close()

    def test_native_exact_queries_and_evidence_only_prerequisites(self):
        from tests.research.test_c1_method_context import C1Archive
        from tools.research.task_constraints import mathematical_method_view,mathematical_catalog
        from tools.research.research_context import compact_scientific_delivery
        from tools.research.nonlinear_capability import T1,T2
        archive=C1Archive()
        try:
            host,s=archive.host();s['spec']['mathematical_methods']={T1:'offline fixture',T2:'offline fixture'}
            view=mathematical_method_view(host,s['reference_candidate'])
            brief=compact_scientific_delivery(dict(mathematical_capabilities=mathematical_catalog(view)),decision_only=True)
            for key in ('mujoco_direct_control_v1',T1,T2):
                query=brief['mathematical_capabilities']['methods'][key]['request_template_query']
                self.assertEqual(query['pointer'],'/methods/'+key)
                self.assertTrue(set(query['fields'])<=set(view['methods'][key]))
            prerequisites=view['methods'][T2]['action_prerequisites']
            self.assertEqual(prerequisites['required_agent_fields'],['nonlinear_response'])
            self.assertEqual(prerequisites['unmet'],view['methods'][T2]['missing'])
            self.assertNotIn('initial_state',prerequisites)
            self.assertNotIn('per_request_limits',prerequisites)
            host.store.reserve.assert_not_called();host.store.transaction.assert_not_called()
        finally:archive.archive.close()

    def test_source_shape_refusal_preserves_actual_reason_without_worker(self):
        import json
        from tools.state_io import digest
        from tools.research.physical_replay import binding
        from tools.research.agent import error_feedback
        inp=SessionInput.model_validate(self.f.cfg)
        order=[t['id'] for t in self.f.cfg['robot']['structure']['data']['tendons']]
        count=round(inp.task.timing.duration_s/inp.task.timing.control_period_s)
        trajectory=dict(tensions_n=[[0.]*len(order)]*(count+1),
            times_s=[i*inp.task.timing.control_period_s for i in range(count+1)],
            tendon_order=order,model_identity='fixture-model',design_identity='fixture-design',task_identity=digest(plain(inp.task)))
        model=(inp,dict(tendons=[dict(entity=k) for k in order]),dict(control=dict(tension_execution_mode='ideal_tension')),
            dict(identity='fixture-model',design_identity='fixture-design'))
        with patch('tools.research.physical_replay.model_context',return_value=model):
            with self.assertRaisesRegex(ValueError,'PHYSICAL_REPLAY_CANDIDATE_TASK_MODEL_OR_SEQUENCE_MISMATCH') as caught:
                binding(self.f.cfg,trajectory)
        facts=json.loads(str(caught.exception).split(': ',1)[1])
        self.assertEqual(facts['received_tension_shape'],[count+1,len(order)])
        self.assertEqual(facts['expected_tension_shape'],[count,len(order)])
        host,s=offline_host({})
        with patch('tools.research.agent.record',return_value=self.f.ref):
            feedback=error_feedback(host,dict(name='research_plan',input=dict(action='initialize_control')),caught.exception,s)
        self.assertEqual(feedback['reason'],str(caught.exception))
        self.assertFalse(feedback['worker_started'])
        self.assertTrue(all(v==0 for v in feedback['charged_method_counts'].values()))


if __name__=='__main__':unittest.main()
