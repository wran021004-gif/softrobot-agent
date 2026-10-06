"""Focused case/request/permission checks; zero provider or backend attempts."""
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch
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
