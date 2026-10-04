from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
from extensions.tendon_family.milestone5_validation import aligned_interval,local_score,direction,diagnose
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.state_io import read
from examples import milestone5_validation as stage


class AlignmentTests(TestCase):
    def test_actual_applied_input_and_next_physical_time_required(self):
        o=dict(time_s=.3,actual_tension_n=[2.],one_step_prediction=dict(time_s=.31,applied_tension_n=[2.]))
        aligned_interval(o,dict(time_s=.31),.01)
        bad=deepcopy(o);bad['one_step_prediction']['applied_tension_n']=[3.]
        with self.assertRaisesRegex(ValueError,'APPLIED_INPUT'):aligned_interval(bad,dict(time_s=.31),.01)
        with self.assertRaisesRegex(ValueError,'INTERVAL'):aligned_interval(o,dict(time_s=.32),.01)

    def test_projection_offset_cannot_be_mistaken_for_speed_change(self):
        pred=dict(endpoint_speed_m_s=.011,initial_projected_speed_m_s=.001,initial_backend_speed_m_s=.02,
            endpoint_velocity_m_s=[.011,0,0],endpoint_position_m=[0,0,0])
        actual=dict(speed_m_s=.012,velocity_m_s=[.012,0,0],position_m=[0,0,0])
        score=local_score(pred,actual)
        self.assertAlmostEqual(score['predicted_speed_change_m_s'],.01)
        self.assertAlmostEqual(score['observed_speed_change_m_s'],-.008)
        self.assertEqual(score['direction_verdict'],'incorrect')
        self.assertEqual(direction(1e-7,1e-6),'practically_unchanged')

    def test_new_stage_handoff_and_immutable_predecessor_offline(self):
        with TemporaryDirectory(prefix='m5-validation-',dir=stage.ROOT/'runs') as tmp:
            with patch.object(stage,'RUN',Path(tmp)/'single_context'):
                w=stage.prepare();w.current_stage='offline_planning'
                check=w.store.artifact(w.chain['feedback'])
                from tools.diagnostic_facts import handover
                handover(w.host('design'),check['result'],w.store.artifact(check['result']),origin=dict(kind='saved_check'),kind='performed_check_result')
                packet=stage.shared.planning_packet(w,2)
                packet.update(campaign_limits=stage.LIMITS,primary_reference=w.incumbent['candidate'],development_exclusions=stage.DEVELOPMENT)
                w.instructions={**w.instructions,'improvement':stage.PLAN}
                with patch.object(stage.ValidationWorkflow,'check_provider_payload',side_effect=RuntimeError('OFFLINE_STOP')):
                    with self.assertRaisesRegex(RuntimeError,'OFFLINE_STOP'):
                        w.phase('improvement','search_batch_plan','unused',study_packet=packet,research_records=w.historical_results,
                            latest_tested=w.latest_tested,require_source_binding=True,predecessor_decision=w.predecessor_decision,
                            planned_backend_count=2,allowed_batch_variables=['control/recipe/holding_tip_speed_weight'],max_variable_count=1)
                payload=payload_for(w.host('design'),EvidenceDrivenAdapter());view=json.loads(payload['messages'][1]['content'])
                self.assertEqual(view['role_context']['study_packet']['primary_reference']['execution_id'],stage.INCUMBENT)
                self.assertEqual(view['role_context']['study_packet']['campaign_limits']['backend_solves'],2)
                self.assertEqual(w.store.remaining()['used']['model_calls'],0)
                stage.assert_predecessor(w)
                del w
                import gc
                gc.collect()

    def test_saved_diagnosis_has_no_historical_warm_plan(self):
        from tools.platform_store import Store
        result=diagnose(Store(stage.predecessor.RUN),stage.DEVELOPMENT)
        self.assertEqual(result['differences'][0]['first_command']['time_s'],.2)
        self.assertEqual(result['differences'][0]['first_position']['time_s'],.21)
        self.assertFalse(result['records'][0]['availability']['historical_warm_plans'])
