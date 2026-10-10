"""Focused new safeguards; no scientific NLP or simulation in these checks."""
import os
os.environ['NMPC_SETTLING_FOLLOWUP']='1'
from copy import deepcopy
import unittest
from tools.research_casadi_feedback import host
from tools.nmpc_settling import validate_plan,verify_configuration,scientific_scope,verify_pair_seed,WEIGHTS
from tools.casadi_closed_loop import resolve_candidate
from tools.state_io import digest
from tools.platform_store import plain
from schemas.casadi_feedback import SettlingPlan,ControlChoice


class SettlingChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.h=host();cls.s=cls.h.store.session(cls.h.run_id)['state'];cls.d=cls.h.store.artifact(cls.s['diagnostic_reference'])
        cls.cfg=cls.h.store.artifact(cls.s['source_binding'])['source']['configuration']
    def choice(self,**kw):
        return ControlChoice.model_validate(dict(candidate=self.s['fixed_candidate'],preceding_execution=self.s['source_baseline_reference'],
            holding_tip_speed_weight=.075,terminal_tip_speed_weight=.10,recover_returned_tensions=True,record_update_ids=[29,30],**kw))
    def plan(self,c,action='control_revision'):
        return SettlingPlan(action=action,control=c,hypothesis='fixture',supporting_evidence=[self.s['diagnostic_reference']],
            weakening_observation='fixture',expected_observation='fixture',fixed_conditions='fixture',revision_or_stop_rule='fixture',disposition='fixture',limitations=['fixture'])
    def test_owned_latest_baseline_and_archive(self):
        b=self.h.store.artifact(self.s['source_binding'])
        self.assertEqual(b['execution_id'],'cda6509a699545d7b59b9be854c60d08')
        self.assertEqual(b['owner_run_id'],'nmpc-feasibility-20261011-cl-6d9b9cdfaf69')
        self.assertEqual(self.d['configuration_identity'],digest(scientific_scope(self.cfg)))
    def test_timestamp_alignment_and_active_hold(self):
        self.assertTrue(all(c['matches_rounded'] and c['holding_active'] and c['prediction_exceeds_measurement'] for c in self.d['known_observation_checks']))
        self.assertEqual([c['target_sample_s'] for c in self.d['known_observation_checks']],[.30,.31])
        self.assertFalse(self.d['alignment_missing'])
        for a in self.d['aligned']:self.assertAlmostEqual(a['end_s']-a['start_s'],.01)
    def test_single_factor_and_recovery(self):
        c=self.choice();validate_plan(self.h.store,self.s,self.plan(c))
        for changes in [dict(holding_tip_speed_weight=.05),dict(terminal_tip_speed_weight=.075),dict(recover_returned_tensions=False),dict(substeps=2)]:
            bad=c.model_copy(update=changes)
            with self.assertRaises(ValueError):validate_plan(self.h.store,self.s,self.plan(bad))
    def test_complete_generator_and_frozen_configuration(self):
        c=self.choice();source=self.s['candidate_sources'][c.candidate.artifact_id]
        cfg,_=resolve_candidate(self.h.store,c.candidate,source,c,'focused-test',self.h.store.session(self.h.run_id)['snapshot']['input']['policy'])
        self.assertTrue(verify_configuration(self.h.store,self.s,cfg,c,'control_revision')['full_scope_verified'])
        for field in ['seed','task']:
            bad=deepcopy(cfg)
            if field=='seed':bad['seed']=18
            else:bad['task']['timing']['control_period_s']=.02
            with self.assertRaises(ValueError):verify_configuration(self.h.store,self.s,bad,c,'control_revision')
    def test_confirmation_identity_and_no_second_tuning(self):
        c=self.choice();cfg=deepcopy(self.cfg);cfg['policy']['controller']['parameters']['data']['recipe'][WEIGHTS[0]]=.075
        with self.h.store.transaction() as db:
            cfgref=plain(self.h.store.put(db,cfg))
            ref=plain(self.h.store.put(db,dict(control=plain(c),status='evaluated',resolved_configuration=cfgref)))
        s=deepcopy(self.s);s['results'].append(dict(operation='closed_loop',reference=ref))
        confirm=c.model_copy(update={'preceding_execution':ref})
        validate_plan(self.h.store,s,self.plan(confirm,'control_confirmation'))
        self.assertEqual(verify_configuration(self.h.store,s,cfg,confirm,'control_confirmation')['identity'],digest(scientific_scope(cfg)))
        with self.assertRaises(ValueError):validate_plan(self.h.store,s,self.plan(confirm.model_copy(update={WEIGHTS[0]:.08}),'control_confirmation'))
        with self.assertRaises(ValueError):validate_plan(self.h.store,s,self.plan(c))
        bad=deepcopy(cfg);bad['policy']['controller']['parameters']['data']['recipe']['tolerance']=1e-5
        with self.assertRaises(ValueError):verify_configuration(self.h.store,s,bad,confirm,'control_confirmation')
    def test_local_source_and_one_pair_ceiling(self):
        p=SettlingPlan(action='saved_state_comparison',comparison=dict(update_id=29,changed_parameter=WEIGHTS[0],changed_value=.075),
            hypothesis='fixture',supporting_evidence=[self.s['diagnostic_reference']],weakening_observation='fixture',expected_observation='fixture',
            fixed_conditions='fixture',revision_or_stop_rule='fixture',disposition='fixture',limitations=['fixture'])
        validate_plan(self.h.store,self.s,p)
        s=deepcopy(self.s);s['local_pair_reserved']=True
        with self.assertRaises(ValueError):validate_plan(self.h.store,s,p)
        with self.assertRaises(ValueError):SettlingPlan.model_validate(dict(plain(p),comparison=dict(update_id=29,changed_parameter='substeps',changed_value=2)))
    def test_unknown_historical_costs_remain_unknown(self):
        for r in self.d['rows']:
            self.assertIsNone(r['full_horizon_cost_breakdown']);self.assertIsNone(r['full_iteration_trace'])
        self.assertEqual(self.d['new_nlp_attempts'],0)
    def test_shared_local_seed_and_absolute_time(self):
        seed=dict(states=[[1,2],[3,4]],tensions=[[.2]*6]);timing=dict(node_times_s=[.30,.31],holding_active=[1.,1.])
        self.assertEqual(verify_pair_seed(None,seed,timing,timing),seed)
        self.assertEqual(verify_pair_seed(seed,deepcopy(seed),timing,timing),seed)
        bad=deepcopy(seed);bad['tensions'][0][0]=.3
        with self.assertRaises(ValueError):verify_pair_seed(seed,bad,timing,timing)
        with self.assertRaises(ValueError):verify_pair_seed(seed,seed,timing,dict(node_times_s=[.31,.32],holding_active=[1.,1.]))
    def test_science_budget_and_required_final_accounting(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from tools.casadi_feedback_service import _plan
        state=deepcopy(self.s);state['numerical_s']=3500
        ctx=SimpleNamespace(store=self.h.store,run_id=self.h.run_id,artifact=self.h.store.artifact)
        with patch.object(self.h.store,'session',return_value=dict(state=state)):
            with self.assertRaisesRegex(ValueError,'OPERATION_CANNOT_FIT_REMAINING_BUDGET'):_plan(ctx,self.plan(self.choice()))
        p=SettlingPlan(action='stop',hypothesis='fixture',supporting_evidence=[self.s['diagnostic_reference']],weakening_observation='fixture',expected_observation='fixture',
            fixed_conditions='fixture',revision_or_stop_rule='fixture',disposition='fixture',limitations=['fixture'])
        with self.assertRaisesRegex(ValueError,'FINAL_STOP_REQUIRES_REAL_DECISION_PACKET'):validate_plan(self.h.store,self.s,p)


if __name__=='__main__':unittest.main()
