"""Focused saved-evidence checks; no provider, optimizer solve or backend execution."""
from copy import deepcopy
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch
from tempfile import TemporaryDirectory
from tools.platform_store import plain
from tools.state_io import read
from tools.study_history import study_history
from tools.batch_budget import budget_capacity
from tools.platform_search import validate_batch_plan
from tools.working_state import project_working_state
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from examples import milestone4 as campaign


class MilestonePlanningTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(prefix='m4-check-',dir=campaign.ROOT/'runs')
        with patch('tools.model_transports.deepseek.request_completion',side_effect=AssertionError('OFFLINE')):
            cls.w=campaign.prepare(Path(cls.temp.name)/'shared')

    @classmethod
    def tearDownClass(cls):
        import gc
        gc.collect();cls.temp.cleanup()

    def test_complete_history_dynamic_branch_and_distinct_identities(self):
        w=self.w
        history=study_history(w.store,w.historical_results,retained_baseline=w.retained_baseline['candidate'],latest_tested=w.latest_tested)
        self.assertEqual(len(history['rows']),6)
        self.assertEqual({(r['weights']['holding'],r['weights']['terminal']) for r in history['rows']},
            {(0.,0.),(.05,0.),(.3,0.),(.1,0.),(0.,.05),(0.,.1)})
        self.assertFalse(history['joint_positive_weight_tested'])
        fixture=deepcopy(w.historical_results[-2]);before=w.store.artifact(fixture['facts']['configuration'])
        before['effective']['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight']=.05
        with w.store.transaction() as db:ref=plain(w.store.put(db,before))
        fixture['facts']['configuration']=ref;fixture['facts']['candidate']['configuration']=ref
        fixture['facts']['execution_id']='offline-joint-fixture';fixture['facts']['candidate']['execution_id']='offline-joint-fixture'
        updated=study_history(w.store,[*w.historical_results,fixture])
        self.assertTrue(updated['joint_positive_weight_tested'])
        incomplete=deepcopy(fixture);incomplete.pop('facts');incomplete['candidate']=deepcopy(fixture['facts']['candidate'])
        self.assertFalse(study_history(w.store,[*w.historical_results,incomplete])['joint_positive_weight_tested'])

    def test_selected_predecessor_actual_changes_budget_and_public_consumers(self):
        w=self.w;source=w.historical_results[-2]['facts']['candidate']
        def offline_plan(host):
            state=w.store.session(host.run_id)['state'];packet=campaign.planning_packet(w,1)
            self.assertEqual(len(packet['history']['rows']),6)
            proposal=deepcopy(read(campaign.prior.RUN/'search_plan.json')['plan'])
            proposal.update(source_candidate=source,predecessor_decision=w.predecessor_decision,
                evidence=packet['evidence_aliases']['performed_check_result'],
                variables={'control/recipe/holding_tip_speed_weight':[0.,1.]},candidates=[{'control/recipe/holding_tip_speed_weight':.05}],
                max_candidates=1,max_backend_attempts=1,target_changed_configurations=1,step=None,
                planned_budget=dict(model_calls=8,tool_calls=20,backend_solves=1,worker_calls=0,wall_s=2500.))
            view=project_working_state(w.store,host.run_id)
            result=validate_batch_plan(w.store,view,proposal)
            with w.store.transaction() as db:
                state=w.store.session(host.run_id,db)['state'];state['role_context']['phase_budget']['limit']['model_calls']=2;w.store.update_state(db,host.run_id,state)
            # Two planning slots do not remove the separately protected four
            # interpretation slots from the cumulative project grant.
            self.assertTrue(validate_batch_plan(w.store,project_working_state(w.store,host.run_id),proposal)['available_capacity']['sufficient'])
            self.assertEqual(result['bindings']['subject'],source)
            self.assertNotEqual(source,view.latest_tested)
            self.assertEqual(result['actual_differences'][0]['actual_changes'],[dict(path='control/recipe/holding_tip_speed_weight',before=0.,after=.05)])
            low=deepcopy(proposal);low['planned_budget']['wall_s']=1200.
            with self.assertRaisesRegex(ValueError,'CAPACITY_INSUFFICIENT'):validate_batch_plan(w.store,view,low)
            empty=deepcopy(proposal);empty['candidates'][0]['control/recipe/holding_tip_speed_weight']=0.
            with self.assertRaisesRegex(ValueError,'NEVER_CHANGES'):validate_batch_plan(w.store,view,empty)
            unknown=deepcopy(proposal);unknown['source_candidate']['execution_id']='unverified'
            with self.assertRaisesRegex(ValueError,'SOURCE_NOT_VERIFIED'):validate_batch_plan(w.store,view,unknown)
            # Same projector used by both organizations; role label changes do not alter public history.
            with w.store.transaction() as db:
                state=w.store.session(host.run_id,db)['state'];state['role_context']['role']='diagnostic';w.store.update_state(db,host.run_id,state)
            dual=project_working_state(w.store,host.run_id)
            self.assertEqual(view.research_study,dual.research_study)
            self.assertEqual(view.research_study['identities']['latest_tested']['execution_id'],campaign.SOURCES[-1][2])
            raise RuntimeError('OFFLINE_ACCEPTANCE_CAPTURED')
        with patch('tools.diagnostic_workflow.run_loop',side_effect=offline_plan):
            with self.assertRaisesRegex(RuntimeError,'OFFLINE_ACCEPTANCE_CAPTURED'):
                campaign.plan(w,'control',1,campaign.CONTROL_PLAN)
        self.assertEqual(w.store.remaining()['used']['model_calls'],0)
        self.assertEqual(w.store.remaining()['used']['backend_solves'],0)

    def test_budget_requirements_share_execution_allowances(self):
        capacity=budget_capacity(1,dict(model_calls=5,tool_calls=9,backend_solves=1,worker_calls=0,wall_s=1590.))
        self.assertTrue(capacity['sufficient'])
        self.assertEqual(sum(capacity['operation_reservations_s'].values()),990.)
        self.assertEqual(budget_capacity(1,dict(model_calls=5,tool_calls=9,backend_solves=1,worker_calls=0,wall_s=900.))['shortfalls']['wall_s'],690.)
