"""Read-only projection checks; fabricated metrics are fixtures, never research evidence."""
from copy import deepcopy
import unittest

from tools.platform_store import plain
from tools.research.core import read_evidence
from tools.research.evidence_views import result_card
from tools.research.feedback import task_gap
from tools.research.research_context import mathematical_decision_view
from tools.research import task_constraints as methods
from tests.research.test_c1_method_context import C1Archive
from tests.research.test_evidence_policy import physical
from tests.research.test_research_reporting import offline_host, ref


class EvidenceClarityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.c1=C1Archive()

    @classmethod
    def tearDownClass(cls):
        cls.c1.archive.close()

    def test_physical_gap_joins_active_metric_without_changing_ranking_or_acceptance(self):
        for active,value,unit in (('holding_speed',.024,'m/s'),('holding_position',.03,'m')):
            result=physical(passed=False)
            components=result['acceptance']['components']
            components['holding_speed'].update(value=.01,limit=.02,unit='m/s')
            components[active]['value']=value
            reference=ref(result);before=deepcopy(result)
            host,current=offline_host({reference['artifact_id']:result},results=[reference])
            gap=task_gap(result);metric,=gap['dominant_constraints']
            self.assertEqual((metric['constraint_id'],metric['value'],metric['limit'],metric['unit']),
                (active,value,components[active]['limit'],unit))
            self.assertEqual(metric['scope'],'physical_task')
            self.assertAlmostEqual(gap['normalized_gap'],max(0.,value/metric['limit']-1))
            self.assertEqual(read_evidence(host,dict(reference=reference,pointer=metric['source_pointer']+'/value'),
                                          record_read=False),value)
            self.assertEqual(gap['accepted'],result['acceptance']['accepted'])
            self.assertEqual(result,before);self.assertEqual(current['evaluation_reads'],[])
        # A clipped zero gap still identifies the tightest signed margin, not arbitrary zero ties.
        result['acceptance']['components']['holding_position']['value']=.002
        self.assertEqual(task_gap(result)['normalized_gap'],0.)
        self.assertEqual(task_gap(result)['dominant_constraints'][0]['constraint_id'],'holding_speed')
        episode=dict(terminal_position_error_m=.001,holding_max_position_error_m=.002,
                     holding_max_speed_m_s=.024,complete=True,holding_coverage_complete=True)
        rl=dict(independent_evaluation_executed=True,episodes=[episode],passed=False,
                acceptance=dict(terminal_position_limit_m=.01,position_limit_m=.01,holding_speed_limit_m_s=.02))
        metric,=task_gap(rl)['dominant_constraints']
        self.assertEqual((metric['value'],metric['unit'],metric['source_pointer']),(.024,'m/s','/episodes/0/holding_max_speed_m_s'))

    def test_saved_native_bottleneck_reaches_l0_as_prediction_with_original_sources(self):
        host,state=self.c1.host();reference=state['analysis_results'][0]
        before=self.c1.artifact(reference);card=result_card(host,reference)
        view=mathematical_decision_view(plain(card))
        for label in ('baseline','best'):
            metric=view['native_analysis']['comparison'][label]['worst_constraint']
            self.assertEqual((metric['constraint_id'],metric['limit'],metric['unit'],metric['scope']),
                ('holding_max_speed_m_s',.02,'m/s','model_sample'))
            self.assertEqual(read_evidence(host,metric['source'],record_read=False),metric['value'])
            self.assertEqual(read_evidence(host,metric['threshold_source'],record_read=False),metric['limit'])
            self.assertEqual(metric['normalized_signed_excess'],before['native_analysis']['comparison'][label]['signed_maximum_excess'])
        self.assertNotEqual(card.evidence_summary.claim_kind,'PHYSICAL_OBSERVATION')
        self.assertEqual(before['task_acceptance'],'unmeasured')
        self.assertEqual(self.c1.artifact(reference),before)
        host.store.transaction.assert_not_called();host.store.reserve.assert_not_called()

    def test_catalog_exposes_scope_cost_and_conditional_admission_without_new_methods(self):
        host,state=self.c1.host();before=deepcopy(state)
        view=methods.mathematical_method_view(host,state['reference_candidate'])
        catalog=methods.mathematical_catalog(view);rows=catalog['methods']
        self.assertEqual(set(rows),set(view['methods']))
        self.assertNotIn('cross_applied_schedule_decomposition',rows)
        self.assertIn('selected_method is proposal text',catalog['limitations'][1])
        self.assertIn('internal force-balance residuals do not establish',rows['native_dynamics_v1']['description'])
        self.assertIn('two integration timesteps',rows['short_input_response_v1']['description'])
        self.assertIn('does not establish finite-horizon',rows['instantaneous_braking_v1']['description'])
        cost=rows['mujoco_direct_control_v1']['cost_scope']
        for fact in ('S baselines','FD probes','candidate evaluation','prefix reconstruction','independent physical_replay','same rollouts, not extra runs'):
            self.assertIn(fact,cost)
        self.assertIn('four FD rollouts per channel',rows['short_input_response_v1']['cost_scope'])
        self.assertEqual(rows['mujoco_direct_control_v1']['execution_status'],'conditional_on_admission')
        self.assertEqual(rows['mujoco_direct_control_v1']['formal_execution_authorized'],
                         view['methods']['mujoco_direct_control_v1']['formal_execution_authorized'])
        saved=self.c1.artifact(state['analysis_results'][0])
        cost=saved['native_analysis']['cost'];callbacks=saved['native_dynamics']['optimization']['cost_feedback']
        self.assertEqual((cost['optimization_evaluations'],cost['rollouts'],callbacks['evaluation_callbacks']),(26,26,26))
        self.assertEqual(cost['physics_steps'],18200)
        self.assertEqual(state,before)
        host.store.transaction.assert_not_called();host.store.reserve.assert_not_called()


if __name__=='__main__':unittest.main()
