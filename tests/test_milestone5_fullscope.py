"""Focused discrete equation, causal scheduling and saved acceptance checks."""
import hashlib
import inspect
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from examples import milestone5_fullscope as stage
from tools.state_io import read,digest
from extensions.tendon_family.milestone5_fullstate import DiscreteFullState,replan_due,history


class FullscopeChecks(unittest.TestCase):
    def test_two_matched_solves_change_only_registered_weight(self):
        from copy import deepcopy
        result=read(stage.RUN/'matched.json');a,b=result['results']
        self.assertEqual(result['controller_attempts'],2)
        for key in ('common_state','previous_input_n','horizon','elapsed_s','initialization'):
            self.assertEqual(a[key],b[key])
        configs=[deepcopy(r['configuration']) for r in (a,b)]
        for c in configs:c['policy']['controller']['parameters']['data']['recipe'].pop('holding_tip_speed_weight')
        self.assertEqual(configs[0],configs[1])
        self.assertGreater(result['max_command_separation_n'],1e-9)
        self.assertTrue(all(r['selected_plan']['accepted'] and r['independent_validation']['feasible'] for r in (a,b)))

    def test_holding_feedback_uses_configured_phase(self):
        self.assertEqual([i for i in range(35) if replan_due(i,.01,.35,.05)],[0,5,10,15,20,25,30,31,32,33,34])
        self.assertFalse(replan_due(32,.01,.40,.05))
        self.assertTrue(replan_due(37,.01,.40,.05))
        self.assertNotIn('trajectory',inspect.signature(history).parameters)

    def test_discrete_update_uses_implicit_damping_and_new_velocity(self):
        # Analytic one-joint constant-force case, no backend or campaign replay.
        model=DiscreteFullState.__new__(DiscreteFullState);model.full_n=1
        model.damping=np.array([[3.]]);model.data=SimpleNamespace(time=0.)
        model.motion=lambda x:dict(position_m=[float(x[0]),0.,0.],velocity_m_s=[float(x[1]),0.,0.],speed_m_s=abs(float(x[1])))
        initial=np.array([.2,.4]);h=.001;steps=10;accel=5./(2.+3.*h)
        with patch('extensions.tendon_family.milestone5_fullstate.forward_terms',return_value=dict(mass=np.array([[2.]]),force=np.array([5.]))):
            result=model.propagate(initial,[1.],grid=dict(max_step_s=h),deadline=float('inf'))
        self.assertAlmostEqual(result['state'][1],.4+steps*h*accel)
        self.assertAlmostEqual(result['state'][0],.2+steps*h*.4+h*h*accel*steps*(steps+1)/2)
        np.testing.assert_array_equal(initial,[.2,.4])
        self.assertEqual(result['backend_steps'],0);self.assertEqual(model.data.time,0.)
        self.assertEqual(result['backend_equivalent_integration_steps'],steps)

    def test_original_thresholds_and_frozen_plans(self):
        p=read(stage.RUN/'plan.json');self.assertEqual(digest(p),read(stage.RUN/'plan_seal.json')['identity'])
        self.assertEqual(p['thresholds']['position_error_m'],1e-6)
        self.assertEqual(p['thresholds']['vector_error_m_s'],1e-4)
        self.assertEqual(p['thresholds']['complete_control_update_deadline_s'],.01)
        for i in (1,2):self.assertEqual(digest(read(stage.RUN/f'revision{i}_plan.json')),read(stage.RUN/f'revision{i}_seal.json')['identity'])
        self.assertEqual(len(p['development_cases']),6)
        stage.check_previous()

    def test_backend_reproduction_does_not_override_numerical_gate(self):
        first=read(stage.RUN/'revision1_local.json');second=read(stage.RUN/'revision2_local.json')
        self.assertEqual(first['counts']['numerical_pass'],6)
        self.assertEqual(first['counts']['position_pass'],0)
        self.assertEqual(second['counts']['position_pass'],6)
        self.assertEqual(second['counts']['vector_pass'],6)
        self.assertEqual(second['counts']['numerical_pass'],3)
        self.assertFalse(first['local_admission']);self.assertFalse(second['local_admission'])
        for c in second['cases']:
            self.assertEqual(c['primary_grid_index'],0)
            self.assertEqual([r['step_s'] for r in c['results']],[.0005,.00025,.000125])
            self.assertTrue(all(r['max_scaled_residual']<=1e-5 for r in c['results']))

    def test_complete_forecasts_are_causal_candidate_histories(self):
        from tools.platform_store import Store
        store=Store(stage.RUN)
        for name in ('original075','original15','reset075','reset15'):
            h=read(stage.RUN/f'forecast_{name}.json')
            self.assertEqual(h,store.artifact(read(stage.RUN/f'forecast_{name}_receipt.json')['output']))
            self.assertEqual(h['solves'],11);self.assertTrue(h['complete'])
            self.assertEqual(h['emulated_physics_steps'],700)
            self.assertEqual(h['rows'][0]['initial_full_state'],h['initial_state'])
            for i,r in enumerate(h['rows']):
                if i:self.assertEqual(r['initial_full_state'],h['rows'][i-1]['state'])
                self.assertLessEqual(r['plan_start_s'],r['time_s'])
                self.assertEqual(r['replanned'],replan_due(i,.01,.35,.05))

    def test_final_gates_accounting_native_binding_and_export(self):
        from tools.platform_store import Store
        a=read(stage.RUN/'assessment.json');account=read(stage.RUN/'accounting.json');audit=read(stage.RUN/'acceptance_audit.json')
        self.assertFalse(a['scientific_development_admission']);self.assertFalse(a['validation_launched'])
        self.assertEqual(audit['milestone5'],'open');self.assertEqual(audit['validation_backend_attempts'],0)
        self.assertTrue(audit['research_accepted'])
        store=Store(stage.RUN);state=store.session('m5full-research')['state']
        self.assertEqual(store.artifact(audit['research_reference']),read(stage.RUN/'interpretation.json'))
        self.assertEqual(audit['research_reference'],state['handoffs']['m5_interpretation'])
        for name in ('research_correction.json','research_correction2.json'):
            self.assertEqual(read(stage.RUN/name)['phase_budget_before'],state['role_context']['phase_budget'])
        self.assertEqual(account['new_campaign']['model_calls'],3)
        self.assertEqual(account['numerical_work']['used'],dict(local_solves=46,prediction_evaluations=36,preview_attempts=4))
        for k,v in account['new_campaign'].items():
            self.assertAlmostEqual(v,account['receipt_sum'][k]);self.assertLessEqual(v,account['development_limit'][k])
        for pair in a['pairs']:
            e=pair['economics'];self.assertAlmostEqual(e['all_in_screening_s'],e['forecast_receipts_s']+e['required_research_s'])
            self.assertAlmostEqual(e['counterfactual_net_savings_s'],e['avoided_one_evaluation_s']-e['all_in_screening_s'])
            if pair['decision']['status']=='abstain':self.assertEqual(e['avoided_one_evaluation_s'],0.)
        for name,expected in read(stage.EVIDENCE/'sha256_manifest.json').items():
            self.assertEqual(hashlib.sha256((stage.EVIDENCE/name).read_bytes()).hexdigest(),expected)


if __name__=='__main__':unittest.main()
