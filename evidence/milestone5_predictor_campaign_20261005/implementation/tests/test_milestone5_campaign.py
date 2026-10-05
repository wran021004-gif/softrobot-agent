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
        admitted=read(stage.RUN/'interpretation_response.json')['readiness'].startswith('GO_EXPERIMENT_RANKING_ONLY')
        if p['status']=='validation_completed_stopped':
            self.assertTrue(p['development_admission_passed'])
            self.assertFalse(p['ready_for_bounded_prospective_experiment'])
            self.assertTrue(p['accepted_final_research_judgment']['readiness'].startswith('STOP'))
        else:self.assertEqual(p['ready_for_bounded_prospective_experiment'],admitted)
        if admitted:
            future=read(stage.RUN/'prospective_protocol.json')
            self.assertFalse(future['role']['safety_authority'])
            self.assertFalse(future['role']['eligibility_authority'])
            self.assertEqual(future['local_checkpoints'],[20,30])
            original=read(stage.RUN/'interpretation_correction.json')['original_phase_budget']
            self.assertEqual(s.session('m5campaign-research')['state']['role_context']['phase_budget'],original)
        self.assertEqual([b['scenario_id'] for b in p['batches']],['incumbent_checkpoint_20_new_clock','incumbent_checkpoint_30_new_clock'])
        ledger=read(stage.RUN/'accounting.json')
        self.assertEqual(ledger['cumulative']['backend_solves'],6+ledger['validation']['backend_solves'])

    def test_campaign_pair_seal_requires_current_method_and_prebackend_timing(self):
        from copy import deepcopy
        from tests.test_milestone5_preparation import MemoryStore
        from examples import milestone5_campaign_validation as validation
        p=read(stage.RUN/'prospective_protocol.json');scenario=p['scenarios'][0];forecasts=[]
        for i,recipe in enumerate(p['recipes']):
            cfg=validation.configuration(p,1,recipe)
            f=deepcopy(read(stage.RUN/('history075.json' if i==0 else 'history15.json')))
            f.update(recipe_id=recipe['recipe_id'],scenario_id=scenario['scenario_id'],scientific_identity=digest(validation.execution_scope(cfg)))
            forecasts.append(f)
        store=MemoryStore()
        with self.assertRaisesRegex(ValueError,'BOTH'):validation.seal_pair(store,'fixture',p,scenario,forecasts[:1])
        ref=validation.seal_pair(store,'fixture',p,scenario,forecasts)
        self.assertEqual(store.artifact(ref)['predictor_version'],validation.VERSION)
        forecasts[0]['metrics']['holding_max_speed_m_s']+=.01
        with self.assertRaisesRegex(ValueError,'IMMUTABLE'):validation.seal_pair(store,'fixture',p,scenario,forecasts)
        store.backend=True
        with self.assertRaisesRegex(ValueError,'STARTED'):validation.seal_pair(store,'fixture',p,scenario,forecasts)

    def test_campaign_local_seal_precedes_step_and_uses_current_command(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from tests.test_milestone5_preparation import MemoryStore
        from examples import milestone5_campaign_validation as validation
        store=MemoryStore();store.connect=lambda *args:store.transaction()
        seal=dict(artifact_id='pair',media_type='application/json');store.state['m5_pair_seal']=seal
        h=SimpleNamespace(store=store,run_id='fixture')
        controller=SimpleNamespace(last=dict(desired_tension_n=[1.]),observations=[dict(measured_initial_state=[0.,0.])])
        observer=validation.checkpoint_observer(h,{},seal,dict(local_checkpoints=[20,30]))
        with patch.object(validation,'static_model',return_value=object()),patch.object(validation,'diagnose',return_value=dict(start_s=.2,end_s=.21)) as call:
            observer(20,.2,controller,dict(tip=np.zeros(3)),np.zeros(3),np.array([1.]))
            store.events.append(('backend','advance',{}))
            self.assertEqual(store.events[0][1],'sealed_before_step')
            self.assertEqual(call.call_args.args[2].tolist(),[1.])
            self.assertEqual(call.call_args.args[3],.2)
            with self.assertRaisesRegex(ValueError,'CAUSAL'):observer(20,.2,controller,dict(tip=np.zeros(3)),np.zeros(3),np.array([2.]))

    def test_prospective_evidence_and_recovered_research_are_bound_without_replay(self):
        from examples import milestone5_campaign_validation as v
        from examples import milestone5_campaign_closeout as closeout
        from extensions.tendon_family.control_evidence import ControlEvidence
        s=Store(v.folder(1));a=read(v.folder(1)/'assessment.json');p=read(v.folder(1)/'protocol.json')
        v.check_protocol(p)
        self.assertFalse(v.folder(2).exists())
        self.assertFalse(a['continue_batch2'])
        self.assertTrue(a['research_judgment']['readiness'].startswith('STOP'))
        self.assertEqual(s.artifact(a['research_reference']),a['research_judgment'])
        with s.connect(True) as db:
            calls=[dict(r) for r in db.execute('SELECT * FROM calls')]
        self.assertTrue(all(r['status'] not in ('running','unknown') for r in calls))
        receipts=[json.loads(r['receipt']) for r in calls]
        self.assertEqual(sum(r['tool_id']=='simulation.run' for r in receipts),2)
        self.assertEqual(sum(r['request_id']=='campaign-preview' for r in receipts),2)
        self.assertEqual(sum(r['tool_id']=='model.deepseek' for r in receipts),3)
        self.assertTrue(any(r['execution_status']=='completed' and r['tool_id']=='research.milestone5_preparation'
            and s.artifact(r['output'])['reference']==a['research_reference'] for r in receipts))
        for k,value in s.remaining()['used'].items():self.assertAlmostEqual(value,sum(r['charged'][k] for r in receipts),places=6)
        research_cost=sum(r['charged']['wall_s'] for r in receipts if r['tool_id'] in ('model.deepseek','research.milestone5_preparation','evidence.read'))
        self.assertAlmostEqual(a['economics']['required_research_s'],research_cost)
        self.assertEqual(a['economics']['one_skipped_evaluation_s'],0.)
        self.assertAlmostEqual(a['economics']['counterfactual_net_savings_s'],-a['economics']['incremental_screening_s'])
        phase=s.phase_remaining(closeout.REVISED)
        self.assertEqual(phase['used']['model_calls'],3)
        self.assertEqual(phase['used']['tool_calls'],4)
        self.assertAlmostEqual(phase['used']['wall_s'],research_cost)
        seal=s.artifact(a['pair_seal']);self.assertEqual(seal['protocol_identity'],digest(p))
        reader=ControlEvidence(s);unique=set()
        pair_event=next(e for e in s.events('m5campaign-b1-r1') if e['kind']=='m5_pair_forecast')
        for i,f in enumerate(seal['forecasts'],1):
            self.assertEqual(f['initial_state'],p['scenarios'][0]['reduced_initial_state'])
            self.assertEqual(len(f['rows']),35)
            for j,row in enumerate(f['rows']):
                self.assertEqual(row['input_information_time_s'],row['time_s'])
                if j:self.assertEqual(row['initial_state'],f['rows'][j-1]['state'])
            run=f'm5campaign-b1-r{i}';events=s.events(run)
            reservation=next(e for e in events if e['request_id']=='complete-simulation' and e['status']=='reserved')
            self.assertLess(pair_event['sequence'],reservation['sequence'])
            result=read(v.folder(1)/(run+'_result.json'));source=reader.resolve(result['execution_id'])
            updates=reader.read_file(source,'controller_observations.json')
            for event in (e for e in events if e['kind']=='m5_local_prediction'):
                pred=s.artifact(event['outputs'][0]);update=updates[pred['update_id']]
                self.assertEqual(event['status'],'sealed_before_step')
                self.assertEqual(pred['pair_seal'],a['pair_seal'])
                self.assertEqual(pred['input_n'],update['actual_tension_n'])
                self.assertEqual(pred['initial_state'],update['measured_initial_state'])
                self.assertEqual(pred['input_information_time_s'],update['time_s'])
                unique.add(digest([pred['start_s'],pred['initial_state'],pred['input_n']]))
        self.assertEqual(len(unique),2)


if __name__=='__main__':unittest.main()
