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
        from tools.platform_models import payload_for
        from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
        adapter=EvidenceDrivenAdapter();payload=payload_for(restored.host,adapter)
        packet=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        self.assertEqual(set(packet['capabilities']['legal']),{'stop'})
        self.assertEqual(packet['capabilities']['remaining']['backend_solves'],0)
        self.assertEqual(adapter.context_id,restored.host.run_id)
        self.assertEqual(adapter.role['archive_context_id'],old)
        adapter.retain('research.decide',{'action':'stop'},[])
        self.assertEqual(restored.store.session(restored.host.run_id)['state']['unaccepted_draft']['arguments'],{'action':'stop'})
        self.assertNotIn('unaccepted_draft',restored.store.session(old)['state'])

    def saved_verification_row(self):
        event=self.w.freeze['subsequent_event']
        f=event['facts']
        return dict(candidate_id=f['candidate']['candidate_id'],case_id='near_z_plus',seed=17,repetition=1,
            purpose='engineering_saved_receipt_binding_fixture',configuration=f['configuration'],
            acceptance=event['acceptance'],receipt=event['receipts']['simulation'],
            receipts=list(event['receipts'].values()),profile=f['report']['reference'],evaluation=f['evaluation'])

    def test_saved_historical_receipt_cannot_be_new_verification(self):
        from tools.verification_evidence import verification_record
        with self.assertRaisesRegex(ValueError,'NOT_OWNED_BY_CURRENT_PROJECT'):
            verification_record(self.w.store,self.saved_verification_row(),self.w.freeze['implementation'])
        self.assertEqual(self.w.store.remaining()['used']['backend_solves'],0)

    def test_bound_verification_failure_survives_next_request_and_restore(self):
        from tools.verification_evidence import verification_record
        from examples import research_model_v1 as pilot
        from tools.platform_models import payload_for
        from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
        from tools.state_io import atomic_json
        original=pilot.restore(self.root)
        self.addCleanup(lambda:pilot.persist(original))
        progress_path=self.root/'verification_progress.json'
        self.addCleanup(lambda:progress_path.unlink(missing_ok=True))
        final_path=self.root/'verification.json'
        self.addCleanup(lambda:final_path.unlink(missing_ok=True))
        row=self.saved_verification_row()
        receipts={r['request_id']:r for r in row['receipts']}
        # Saved-record binding fixture substitutes only current receipt ownership;
        # it creates no fresh execution or claim about repeatability.
        with patch.object(self.w.store,'lookup',side_effect=lambda owner,request_id:{'receipt':json.dumps(receipts[request_id])}):
            bound=verification_record(self.w.store,row,self.w.freeze['implementation'])
            wrong=deepcopy(row);wrong['case_id']='near_z_minus'
            with self.assertRaisesRegex(ValueError,'CONFIGURATION_OR_CASE_MISMATCH'):
                verification_record(self.w.store,wrong,self.w.freeze['implementation'])
            altered=deepcopy(row);altered['acceptance']['accepted']=True
            with self.assertRaisesRegex(ValueError,'ACCEPTANCE_DIFFERS_FROM_SEALED_SOURCES'):
                verification_record(self.w.store,altered,self.w.freeze['implementation'])
        self.w.records=[r for r in self.w.records if r['execution_id']!=bound['execution_id']]+[bound]
        self.w.working=None
        progress=dict(plan=dict(schedule=[{k:row[k] for k in ('case_id','seed','repetition')}],
            fixture_scope='Saved receipt binding, no fresh execution'),groups=[dict(role='unchanged_incumbent',records=[row])],
            usage=self.w.store.remaining())
        atomic_json(progress_path,progress)
        from tools.research_tasks import aggregate_acceptance
        from tools.fixed_research import schedule
        from tools.research_spec import load_spec
        aggregate=aggregate_acceptance([row],10,schedule=schedule(load_spec()))
        atomic_json(final_path,dict(complete=False,comparison=dict(relation='unavailable',reason='Engineering fixture: nine slots missing'),
            improvement_supported=False,aggregates=[dict(role='unchanged_incumbent',acceptance=aggregate)]))
        self.w.freeze['final_reporting']=True
        packet=pilot.configure(self.w)
        self.assertFalse(packet['verification']['outcomes'][0]['accepted'])
        self.assertFalse(packet['verification']['complete'])
        self.assertEqual(packet['verification']['aggregates'][0]['acceptance']['unrecorded'],9)
        self.assertEqual(set(packet['capabilities']['legal']),{'stop'})
        entry=self.w.working['experiments'][bound['execution_id']][-1]['entry']
        self.assertEqual(entry['phase'],'verification')
        self.assertEqual(entry['case_id'],'near_z_plus')
        self.assertFalse(entry['observed_metrics']['accepted'])
        payload=payload_for(self.w.host,EvidenceDrivenAdapter())
        view=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        self.assertEqual(view['verification']['outcomes'][0]['metrics'],row['acceptance']['metrics'])
        pilot.persist(self.w);restored=pilot.restore(self.root)
        self.assertEqual(restored.working['experiments'][bound['execution_id']][-1]['entry'],entry)
        self.assertFalse(campaign.search_rows(restored))
        self.assertEqual(restored.store.remaining()['used']['backend_solves'],0)


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
