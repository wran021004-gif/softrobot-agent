"""Three targeted checks; synthetic views are not new scientific evidence."""
from copy import deepcopy
import unittest

from tools.research.capability import task_control_capability_comparison
from tools.research.numerics import archived
from tools.state_io import read
from tools.research.experiments.b3_t1_t2_predictivity import ROOT, RUN, EVIDENCE


class PredictivityTests(unittest.TestCase):
    def fixtures(self):
        acceptance=archived('evidence/b3_t2_pilot_050_c',dict(
            artifact_id='0f87cf01869d1892043a8c52f3893c9b0b433ff305f769d2fbb3ad28a991baca',
            media_type='application/json'))['acceptance']
        role=dict(acceptance=acceptance,J=1.,reference=dict(fixture=True))
        row=dict(conditions=dict(task=dict(identity=acceptance['task_identity'])),
            mathematics=dict(trajectory=dict(replayed_violation=-.2,
                dual_checks=dict(support_lower_estimate=-.200000001),
                replay=dict(numerically_valid=True),optimality_status='numerically_checked')),
            fixed=deepcopy(role),reoptimized=deepcopy(role),native=dict(cost={},stop_reason='iteration_limit'))
        return dict(a=deepcopy(row),b=deepcopy(row))

    def test_flat_model_and_observed_search_difference_do_not_choose_winner(self):
        rows=self.fixtures();rows['b']['reoptimized']['J']=.5
        result=task_control_capability_comparison(rows,t2=dict(direction_status='directional_comparisons_only'))
        pair=result['pairs'][0]
        self.assertEqual(pair['direction_relation'],'model_indistinguishable_physical_difference_observed')
        self.assertFalse(pair['model_direction_supported'])
        self.assertIsNone(result['preferred_candidate']);self.assertEqual(pair['ranking'],'unresolved')
        self.assertEqual(result['feedback_closed_loop'],'not_executed')

    def test_mismatched_task_or_control_conditions_are_not_comparable(self):
        for changed in ('conditions','acceptance'):
            rows=self.fixtures()
            if changed=='conditions':rows['b']['conditions']['settings']='different budget'
            else:rows['b']['fixed']['acceptance']['task_identity']='other task'
            self.assertEqual(task_control_capability_comparison(rows,t2={})['pairs'][0]['status'],'not_comparable')

    def test_saved_original_evaluator_and_accounting_alignment(self):
        if not (EVIDENCE/'summary.json').exists():self.skipTest('Real experiment not executed yet')
        plan=read(EVIDENCE/'frozen_plan.json');summary=read(EVIDENCE/'summary.json')
        total=0
        for label,row in summary['candidates'].items():
            item=read(RUN/'inputs.json')[label]
            for role in ('fixed','reoptimized'):
                saved=read(RUN/label/role/'evaluation.json')['acceptance']
                self.assertEqual(saved,row[role]['acceptance'])
                self.assertEqual(saved['task_identity'],plan['task']['identity'])
                J=max(saved['metrics'][k]/v for k,v in plan['task']['limits'].items())-1
                self.assertEqual(J,row[role]['J']);total+=row[role]['physics_steps']
            cost=row['native']['cost'];total+=cost['physics_steps']
            self.assertLessEqual(cost['optimization_evaluations'],12)
            self.assertLessEqual(cost['optimization_iterations'],2)
            self.assertLessEqual(max(row['reoptimized']['native_replay_difference'].values()),1e-10)
            self.assertEqual(item['parameters']['segments']['1']['young_pa'],plan['moduli_pa'][label])
        self.assertEqual(total,summary['resources']['physics_steps'])
        self.assertLessEqual(total,50000)
        self.assertEqual(plan['r1_before'],summary['resources']['r1_after'])
