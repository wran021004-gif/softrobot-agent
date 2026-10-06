"""Focused case/request/permission checks; zero provider or backend attempts."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
from unittest import TestCase
from examples import research_campaign_v2 as campaign
from tests.test_research_model_v1 import NativePilotTests
from tools.state_io import read
from tools.context_assembly import fit_request,measure_input


class NativeCampaignTests(NativePilotTests):
    @classmethod
    def setUpClass(cls):
        from uuid import uuid4
        cls.root=campaign.ROOT/'runs'/('campaign-v2-test-'+uuid4().hex)
        cls.w=campaign.prepare(cls.root,offline_fixture=True)

    def test_frozen_case_survives_native_plan_and_construction(self):
        args=self.search(mixed=True)
        args['plan'].update(case_id='far_y_minus',seed=18)
        result,payload=self.invoke_native(args)
        cfg=self.w.store.artifact(result['batch_plan']['bindings']['execution_source_configuration'])['effective']
        self.assertEqual(cfg['seed'],18)
        initial=cfg['task']['initializer']['parameters']['data']
        self.assertEqual(initial['qpos_rad']['far_cell_0_y'],-.01/12)
        self.assertEqual(initial['qvel_rad_s']['far_cell_0_y'],-.02/12)
        self.assertEqual(initial['qpos_rad']['near_cell_0_z'],0.)
        from tools.study_history import scientific_match
        original=self.w.store.artifact(self.w.freeze['incumbent']['configuration'])['effective']
        self.assertFalse(scientific_match(cfg,original)['scientific_match'])
        cap=result['capabilities']['legal']['structure_search']
        self.assertEqual(len(cap['frozen_cases']),5)
        self.assertTrue(cap['execution_authorized'])
        instructions=json.loads(payload['messages'][1]['content'])['role_context']['instructions']
        self.assertNotIn('other four cases remain specified but unavailable',instructions)
        self.assertNotIn('four TOTAL',instructions)

    def test_complete_wire_fitting_preserves_exact_failure_and_schema(self):
        saved=read(self.root/'prepared_request.json')['payload']
        config=self.w.freeze['provider_configuration']
        enlarged=deepcopy(saved)
        context=json.loads(enlarged['messages'][1]['content'])
        packet=context['role_context']['research_packet']
        packet['verbose_archive_fixture']={'decisions':[{'reasoning':'historical verbosity '*6000}]}
        enlarged['messages'][1]['content']=json.dumps(context)
        from examples import research_model_v1 as pilot
        fitted,audit=fit_request(enlarged,config,'research_decision',archive=pilot.archive(self.w))
        self.assertGreater(len(audit['fitting_steps']),1)
        after=json.loads(fitted['messages'][1]['content'])['role_context']['research_packet']
        self.assertEqual(after['bound_evidence'],packet['bound_evidence'])
        self.assertEqual(after['known_review_issues'] if 'known_review_issues' in after else after['working_context']['known_review_issues'],
            packet['known_review_issues'] if 'known_review_issues' in packet else packet['working_context']['known_review_issues'])
        self.assertEqual(fitted['tools'],saved['tools'])
        self.assertEqual(fitted['max_tokens'],saved['max_tokens'])
        self.assertEqual(measure_input(fitted,config,'research_decision')['utf8_bytes'],len(json.dumps(fitted,ensure_ascii=False).encode('utf8')))

    def test_unknown_case_rejected_before_expenditure(self):
        args=self.search();args['plan']['case_id']='easier_invented_case'
        from schemas.platform_handoff import ResearchDecision
        from tools.research_scheduler import validate_decision
        from tools.working_state import project_working_state
        with self.assertRaisesRegex(ValueError,'FROZEN_CASE'):
            validate_decision(self.w.store,project_working_state(self.w.store,self.w.host.run_id),ResearchDecision.model_validate(args))

    def test_matching_failures_survive_explicit_nominal_zero_mapping(self):
        from tools.research_spec import apply_frozen_case
        from tools.candidate_parameters import planning_configuration
        from tools.platform_tools import _candidate
        from schemas.platform import SessionInput
        from tools.platform_search import matching_scientific_history
        from tools.platform_store import plain
        source=planning_configuration(self.w.store,self.w.freeze['incumbent'],
            self.w.store.session(self.w.host.run_id)['snapshot']['input']['policy'])
        source=apply_frozen_case(source,'nominal',17,self.w.freeze['frozen_cases'])
        changed=plain(_candidate(SessionInput.model_validate(source),{'control/recipe/holding_tip_speed_weight':.075},self.w.host.reg))
        matches=matching_scientific_history(self.w.store,changed,self.w.records)
        self.assertIn('e3876a1d289f41f08d46c96202f1da0c',[r['candidate']['execution_id'] for r in matches])
        perturbed=apply_frozen_case(changed,'near_z_plus',17,self.w.freeze['frozen_cases'])
        self.assertFalse(matching_scientific_history(self.w.store,perturbed,self.w.records))

    def test_case_and_edits_survive_real_receipt_executor_host(self):
        from tools.platform_search import prepare_offline_batch
        from tools.platform_diagnosis_coordinator import configure_role
        from tools.live_batch_execution import LiveBatchExecution
        from schemas.platform import SessionInput
        from tools.platform_tools import _candidate
        from tools.platform_store import plain
        from uuid import uuid4
        args=self.search(mixed=True);args['plan'].update(case_id='near_z_minus',seed=18)
        result,_=self.invoke_native(args)
        configure_role(self.w.host,'executor','Offline construction fixture; zero backend grant.',phase_budget={})
        batch=prepare_offline_batch(self.w.host,result['search_plan'],starting_facts=self.w.baseline,
            retained_baseline=self.w.baseline,historical_results=self.w.records)
        source=self.w.store.artifact(batch['base_configuration'])['effective']
        point=args['plan']['candidates'][0]
        effective=plain(_candidate(SessionInput.model_validate(source),point,self.w.host.reg))
        with self.w.store.transaction() as db:
            ref=plain(self.w.store.put(db,dict(effective=effective)))
        child=LiveBatchExecution(self.w.host).candidate_host(dict(candidate_id='offline-case-'+uuid4().hex,configuration=ref))
        actual=self.w.store.session(child.run_id)['snapshot']['input']
        initial=actual['task']['initializer']['parameters']['data']
        self.assertEqual(initial['qpos_rad']['near_cell_0_z'],-.01/12)
        self.assertEqual(initial['qvel_rad_s']['near_cell_0_z'],-.02/12)
        self.assertEqual(actual['seed'],18)
        self.assertEqual(actual['policy']['controller']['parameters']['data']['recipe']['holding_tip_speed_weight'],.075)
        self.assertEqual(actual['task'],effective['task'])
        self.assertEqual(self.w.store.remaining()['used']['backend_solves'],0)

    def test_same_project_prelaunch_refresh_restores_settled_state(self):
        from examples import research_model_v1 as pilot
        # The inherited native decision fixture advertises synthetic capacity;
        # migration must compare the real zero-live ledger on both sides.
        for p in self.patches:p.stop()
        before=self.w.store.remaining()['used']
        old=self.w.host.run_id
        revised=campaign.refresh_prelaunch(self.root)
        restored=pilot.restore(self.root)
        self.assertEqual(restored.host.run_id,old+'-prelaunch2')
        self.assertEqual(restored.freeze['context_id'],old)
        self.assertEqual(restored.store.remaining()['used']['tool_calls'],before['tool_calls']+1)
        self.assertEqual(restored.working['current_facts'],revised.working['current_facts'])
        self.assertEqual(restored.status,'prepared')
        self.assertEqual(restored.store.remaining()['used']['backend_solves'],0)
        self.assertFalse(restored.store.session(restored.host.run_id)['state'].get('pending'))


class CampaignBudgetTests(TestCase):
    def test_child_charges_do_not_unlock_final_reservations(self):
        from tools.batch_budget import downstream_available
        class FakeStore:
            def remaining(self,run_id=None,db=None):
                return {'remaining':dict(backend_solves=26 if run_id is None else 8,
                    tool_calls=180 if run_id is None else 125,model_calls=22,wall_s=34000 if run_id is None else 14000,worker_calls=0)}
            def session(self,run_id,db=None):
                return {'state':{'role_context':{'campaign_permissions':{'reserved_verification_backends':20}}}}
        available=downstream_available(FakeStore(),'research')
        self.assertEqual(available['backend_solves'],6)
        self.assertEqual(available['tool_calls'],120)
        self.assertEqual(available['wall_s'],14000)
