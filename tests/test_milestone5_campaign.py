"""Focused evidence/causality checks; never repeat integrations, solves or API calls."""
import hashlib
import json
import unittest
import numpy as np
from examples import milestone5_predictor_campaign as stage
from examples import milestone5_predictor_development as previous
from tools.platform_store import Store
from tools.state_io import read,digest
from extensions.tendon_family.milestone5_campaign_reference import STEP,GUARD_S,RESERVATION_S


class CampaignChecks(unittest.TestCase):
    def test_causal_local_interface_reuses_saved_computations(self):
        from extensions.tendon_family.milestone5_campaign_local import report
        for c in read(stage.RUN/'accuracy.json')['cases']:
            p=c['prediction'];r=report(p['initial'],c['results'],p['input_n'],c['interval_s'][0])
            self.assertEqual(r['direction'],c['score']['predicted_direction'])
            self.assertEqual(r['position_m'],p['position_m'])
            self.assertEqual(r['velocity_m_s'],p['velocity_m_s'])
            self.assertEqual(r['input_information_time_s'],c['interval_s'][0])
            self.assertIsNone(r['model_error_bound'])

    def test_reference_continuation_reuses_exact_eight_and_preserves_scope(self):
        a=read(stage.RUN/'reference.json');old=read(previous.RUN/'reference.json')
        self.assertEqual(a['results'][:8],old['results'])
        self.assertEqual((STEP,GUARD_S,RESERVATION_S),(.00000390625,800.,1200.))
        self.assertEqual(a['results'][-1]['step_count'],2560)
        self.assertLess(a['results'][-1]['integration_s'],GUARD_S)
        self.assertTrue(a['numerical_stability_supported'])
        self.assertTrue(all(r['max_scaled_residual']<=1e-5 for r in a['results']))
        mappings=read(stage.RUN/'accuracy.json')['reference_assessments']
        for name in ('continuous','represented_serial'):
            self.assertTrue(mappings[name]['passed'])
            self.assertTrue(all(r['velocity_m_s']<=1e-4 and r['speed_m_s']<=1e-4 for r in mappings[name]['final_differences']))

    def test_projected_rate_alignment_and_mechanics_are_nonadvancing(self):
        loc=read(stage.RUN/'localization-r1.json')
        for c in loc['cases']:
            self.assertLess(c['projection_roundtrip_norm'],1e-10)
            self.assertLess(c['projection_rate_fd_norm'],1e-6)
            self.assertGreater(c['reduced_mass_min_eigenvalue'],0.)
            self.assertEqual(c['input_information_time_s'],c['interval_s'][0])
            self.assertTrue(c['backend_clock_unchanged'])
            self.assertEqual(np.asarray(c['continuous_acceleration']).shape,np.asarray(c['serial_pullback_acceleration']).shape)

    def test_numerical_resolution_never_substitutes_for_physical_accuracy(self):
        a=read(stage.RUN/'accuracy.json');self.assertEqual(a['distinct_intervals'],4)
        self.assertEqual(len({c['case'] for c in a['cases']}),4)
        for c in a['cases']:
            self.assertTrue(c['numerical_pass'])
            self.assertEqual(len(c['results']),3)
            self.assertFalse(c['score']['vector_pass'])
            self.assertFalse(c['score']['position_pass'])
            for r in c['results']:
                self.assertEqual(r['backend_clock_s'],0.)
                self.assertEqual(r['backend_steps'],0)
                self.assertLessEqual(r['max_scaled_residual'],1e-5)
        self.assertTrue(next(c for c in a['cases'] if c['case']=='holding075')['score']['holding_false_safe'])

    def test_independent_causal_complete_forecasts_and_cost(self):
        histories=[read(stage.RUN/(name+'.json')) for name in ('history075','history15')]
        for h in histories:
            self.assertTrue(h['complete']);self.assertEqual(len(h['rows']),35)
            self.assertEqual(h['solves'],7)
            for i,r in enumerate(h['rows']):
                self.assertEqual(r['input_information_time_s'],r['time_s'])
                self.assertLessEqual(r['plan_start_s'],r['time_s'])
                self.assertAlmostEqual(r['endpoint_s']-r['time_s'],.01)
                self.assertEqual(r['backend_clock_s'],0.)
                if i:
                    self.assertEqual(r['initial_state'],h['rows'][i-1]['state'])
                    self.assertEqual(r['previous_input_n'],h['rows'][i-1]['input_n'])
                if not r['replanned']:self.assertEqual(r['plan_identity'],h['rows'][i-1]['plan_identity'])
            self.assertEqual([r['update_id'] for r in h['rows'] if r['replanned']],[0,5,10,15,20,25,30])
        self.assertNotEqual(histories[0]['configuration_identity'],histories[1]['configuration_identity'])
        self.assertNotEqual(digest(histories[0]['rows']),digest(histories[1]['rows']))
        a=read(stage.RUN/'assessment.json');e=a['economics'];d=a['screening']['decision']
        self.assertAlmostEqual(e['incremental_screening_cost_s'],e['new_pair_forecast_receipt_s']+e['required_research_decision_s'])
        self.assertAlmostEqual(e['counterfactual_net_savings_s'],e['selected_skipped_evaluation_s']-e['incremental_screening_cost_s'])
        if d['status']=='abstain':self.assertEqual(e['selected_skipped_evaluation_s'],0.)

    def test_receipts_budgets_and_predecessor_immutability(self):
        stage.check_previous();s=Store(stage.RUN)
        with s.connect(True) as db:
            receipts=[json.loads(r[0]) for r in db.execute('SELECT receipt FROM calls WHERE receipt IS NOT NULL')]
            work=json.loads(db.execute("SELECT value FROM meta WHERE key='diagnostic_work'").fetchone()[0])
        for k,v in s.remaining()['used'].items():
            self.assertAlmostEqual(sum(r['charged'][k] for r in receipts),v,places=6)
            self.assertLessEqual(v,stage.LIMITS[k])
        self.assertEqual(work['used']['reference_integrations'],1)
        self.assertEqual(work['used']['prediction_evaluations'],12)
        self.assertEqual(work['used']['preview_attempts'],2)
        self.assertEqual(work['used']['local_solves'],15)
        self.assertTrue(all(r['tool_id']!='simulation.run' for r in receipts))
        # Resolve the production implementation from the preserved registered identity.
        identity=read(previous.RUN/'protocol.json')['implementation_identity']
        for name in ('controller','model'):
            for path,sha in identity[name]['sources'].items():
                self.assertEqual(hashlib.sha256((stage.ROOT/path).read_bytes()).hexdigest(),sha)

    def test_actual_native_decision_binding_and_no_implicit_grants(self):
        s=Store(stage.RUN);p=read(stage.RUN/'protocol.json')
        if not (stage.RUN/'interpretation_response.json').exists():
            self.assertFalse(p['research_interpretation_complete'])
            self.assertNotIn('interpretation',p['research_decisions'])
            self.assertFalse(p['ready_for_bounded_prospective_experiment'])
            self.assertFalse(read(stage.RUN/'protocol_seal.json')['backend_grant_materialized'])
            self.assertEqual(p['status'],'development_completed_research_blocked')
            return
        self.assertTrue(p['research_interpretation_complete'])
        ref=p['research_decisions']['interpretation']
        self.assertEqual(s.artifact(ref),read(stage.RUN/'interpretation_response.json'))
        with s.connect(True) as db:receipts=[json.loads(r[0]) for r in db.execute("SELECT receipt FROM calls WHERE status='completed' AND receipt IS NOT NULL")]
        self.assertTrue(any(r['tool_id']=='research.milestone5_preparation' and s.artifact(r['output']).get('reference')==ref for r in receipts))
        self.assertFalse(p['ready_for_bounded_prospective_experiment'])
        self.assertFalse(read(stage.RUN/'protocol_seal.json')['backend_grant_materialized'])
        self.assertEqual([b['scenario_id'] for b in p['batches']],['incumbent_checkpoint_20_new_clock','incumbent_checkpoint_30_new_clock'])
        self.assertEqual(read(stage.RUN/'accounting.json')['cumulative']['backend_solves'],6)


if __name__=='__main__':unittest.main()
