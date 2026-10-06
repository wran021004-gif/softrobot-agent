"""Offline risks for the actual shared scheduling projection and validators."""
from copy import deepcopy
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch
import json
import gc

from examples import milestone4_autonomous as campaign
from tools.platform_models import payload_for
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.working_state import project_working_state
from tools.research_scheduler import validate_decision,capabilities
from tools.state_io import read,digest
from tools.platform_store import plain


class ResearchSchedulingTests(TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=TemporaryDirectory(dir=campaign.ROOT/'runs',prefix='scheduler-offline-');cls.directory=Path(cls.temp.name)/'campaign'
        campaign.prepare(cls.directory,successor=True)

    @classmethod
    def tearDownClass(cls):
        gc.collect()
        assert Path(cls.temp.name).resolve().is_relative_to((campaign.ROOT/'runs').resolve())
        cls.temp.cleanup()

    def setUp(self):
        self.w=campaign.restore(self.directory);self.packet=campaign.configure(self.w)
        self.alias=next(iter(self.packet['current_feedback']['aliases']))
        self.source=self.w.freeze['primary']

    def validate(self,value):
        return validate_decision(self.w.store,project_working_state(self.w.store,self.w.host.run_id),value)

    def stop(self):
        return dict(action='stop',evidence=[self.alias],reasoning='The known incumbent passes; further evidence may be deferred.',
            selected_candidate=self.w.freeze['incumbent'],stop_reason='Voluntary delivery',**self.separation())

    def separation(self):
        return dict(observations=[dict(evidence=self.alias,value=self.packet['current_feedback']['aliases'][self.alias]['value'])],
            interpretations=[dict(statement='Further evidence may or may not be valuable',supporting_evidence=[self.alias],
                contradicting_evidence=[],scope='This bounded offline fixture',uncertainty='Dominant cause unresolved')],
            unresolved_uncertainties=['No optimum or dominant physical cause established'])

    def search(self,route='control_search'):
        p=deepcopy(read(campaign.continuation.RUN/'adaptation_plan.json')['plan'])
        path='control/recipe/holding_tip_speed_weight' if route=='control_search' else 'design/section_scale'
        value=.075 if route=='control_search' else 1.
        bounds=[.05,.1] if route=='control_search' else [.95,1.05]
        p.update(source_candidate=self.source,predecessor_decision=self.w.previous_decision,evidence=[self.alias],
            variables={path:bounds},candidates=[{path:value}],max_candidates=1,max_backend_attempts=1,
            target_changed_configurations=1,planned_budget=dict(model_calls=5,tool_calls=9,backend_solves=1,worker_calls=0,wall_s=1595.))
        return dict(action=route,evidence=[self.alias],reasoning='The current feedback motivates this bounded sensitivity check.',plan=p,**self.separation())

    def test_actual_projection_native_schema_all_legal_routes(self):
        adapter=EvidenceDrivenAdapter();payload=payload_for(self.w.host,adapter)
        self.assertEqual(list(adapter.advertised.values()),['research.decide'])
        schema=payload['tools'][0]['function']['parameters']
        self.assertEqual(set(schema['anyOf'][0]['properties']['action']['enum']),
            {'control_search','structure_search','diagnosis','stop'})
        body=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        self.assertEqual(set(body['capabilities']['legal']),{'control_search','structure_search','diagnosis','stop'})
        self.assertNotIn('next required',payload['messages'][0]['content'].lower())
        self.assertIsInstance(schema['$defs']['SearchBatchPlan']['properties']['variables'],dict)
        self.assertIn('observations',schema['anyOf'][0]['required'])
        self.assertIn('interpretations',schema['anyOf'][0]['properties'])

    def test_unexpected_structure_control_repeat_and_voluntary_stop(self):
        for route in ('control_search','structure_search'):
            result=self.validate(self.search(route));self.assertTrue(result['batch_plan']['structurally_operationally_valid'])
        self.assertEqual(self.validate(self.stop())['decision']['action'],'stop')

    def test_invalid_references_and_unaffordable_action_neutral(self):
        bad=self.stop();bad['evidence']=['F999999']
        with self.assertRaisesRegex(ValueError,'Unknown or out-of-scope alias'):self.validate(bad)
        low={**campaign.LIMITS,'backend_solves':0,'wall_s':700.}
        with patch('tools.research_scheduler.downstream_available',return_value=low):
            self.assertIn('stop',capabilities(self.w.store,self.w.host.run_id,self.w.records)['legal'])
            with self.assertRaisesRegex(ValueError,'CAPABILITY_GAP'):self.validate(self.search())

    def test_new_feedback_bound_to_next_plan(self):
        stale=self.search();old_alias=self.alias
        campaign.feedback(self.w,dict(new_result=2.,meaning='Offline fixture, never live evidence'),'offline_fixture')
        campaign.configure(self.w)
        with self.assertRaisesRegex(ValueError,'CURRENT_FEEDBACK_REFERENCE'):self.validate(stale)
        self.packet=campaign.configure(self.w)
        self.alias=next(iter(self.packet['current_feedback']['aliases']))
        result=self.validate(self.search())
        self.assertNotEqual(self.alias,old_alias)
        self.assertEqual(result['batch_plan']['bindings']['check_feedback'],self.w.feedback)

    def test_duplicate_diagnosis_return_and_justified_replication(self):
        request=dict(source_candidate=self.source,hypotheses=['Plan selection changes','Observed motion changes'],
            evidence=[self.alias],missing_observation='Compare saved holding plans.',view='plans',update_ids=[34],
            outcome_actions={'same':'defer','different':'consider control search'},max_wall_s=180.,exit_condition='One saved query')
        decision=dict(action='diagnosis',evidence=[self.alias],reasoning='Resolve the uncertainty using retained data.',diagnosis=request,**self.separation())
        result=self.validate(decision);ref=self.w.store.artifact(self.w.feedback)['result']
        with self.w.store.transaction() as db:
            state=self.w.store.session(self.w.host.run_id,db)['state']
            state.setdefault('research_diagnostics',{})[result['diagnostic_key']]=ref
            self.w.store.update_state(db,self.w.host.run_id,state)
        self.assertTrue(self.validate(decision)['duplicate_without_replication'])
        request['replication_reason']='Re-examine the same plan under a revised competing explanation; measurement is deterministic.'
        self.assertFalse(self.validate(decision)['duplicate_without_replication'])

    def test_cumulative_recovery_and_execution_child_projection(self):
        from tools.platform_diagnosis_coordinator import transfer_recovery
        from tools.structural_study import research_planning_input
        from tools.platform_host import Host
        inp=deepcopy(self.w.store.session(self.w.host.run_id)['snapshot']['input'])
        child=deepcopy(inp);child['policy'].update(budget={**campaign.LIMITS,'model_calls':0},tool_bindings={'simulation.run':'1.0.0'})
        projected=research_planning_input(child,self.w.freeze['profile'],budget=campaign.LIMITS,
            model=self.w.freeze['provider_configuration'],tool_bindings=inp['policy']['tool_bindings'])
        self.assertEqual(projected['policy']['budget']['model_calls'],24)
        self.assertIn('research.decide',projected['policy']['tool_bindings'])
        projected['run_id']='offline-recovery-child';new=Host(self.directory,projected['run_id']);new.create(projected)
        with self.w.store.transaction() as db:
            state=self.w.store.session(self.w.host.run_id,db)['state'];state.update(protocol_corrections_used=3,protocol_corrections_consecutive=1)
            self.w.store.update_state(db,self.w.host.run_id,state)
        before=self.w.store.remaining();transfer_recovery(self.w.host,new)
        self.assertEqual(new.store.session(new.run_id)['state']['protocol_corrections_used'],3)
        self.assertEqual(self.w.store.remaining(),before)
        campaign.configure(self.w)
        self.assertEqual(self.w.store.session(self.w.host.run_id)['state']['protocol_corrections_used'],3)

    def test_stable_path_has_no_native_provider_or_observer(self):
        from extensions.tendon_family.gvs_trajectory import _FUNCTION_PROVIDER
        from extensions.tendon_family.control_evidence import PRE_STEP_OBSERVER
        self.assertIsNone(_FUNCTION_PROVIDER.get());self.assertIsNone(PRE_STEP_OBSERVER.get())
        controller=self.w.store.session(self.w.host.run_id)['snapshot']['input']['policy']['controller']
        self.assertEqual((controller['extension_id'],controller['version']),('controller.gvs_nmpc','7.0.0'))
        self.assertEqual(campaign.revision()['stable_controller'],self.w.freeze['implementation']['stable_controller'])

    def test_real_native_handoff_and_failed_validation_correction_ceiling(self):
        from tools.platform_models import _argument_rejection
        host=self.w.host;host.resume()
        invocation=dict(request_id='offline-decision',tool_id='research.decide',tool_version='1.0.0',
            arguments=self.search(),reason='Offline fixture; no provider/backend',cache='new')
        receipt=host.invoke(invocation)
        self.assertEqual(receipt['execution_status'],'completed',receipt.get('error'))
        self.assertIn('search_batch_plan',host.store.session(host.run_id)['state']['handoffs'])
        campaign.configure(self.w);host.resume()
        invalid=self.stop();invalid['evidence']=['F999999']
        rejected=host.invoke({**invocation,'request_id':'offline-invalid','arguments':invalid})
        self.assertEqual(rejected['execution_status'],'failed')
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state'];state.update(protocol_corrections_used=3,protocol_corrections_consecutive=1)
            host.store.update_state(db,host.run_id,state)
        config=host.store.session(host.run_id)['snapshot']['input']['policy']['model']
        self.assertIsNone(_argument_rejection(host,invocation,rejected,config))
        state=host.store.session(host.run_id)['state']
        self.assertEqual((state['protocol_corrections_used'],state['protocol_corrections_consecutive']),(4,2))
        self.assertIsNotNone(_argument_rejection(host,invocation,rejected,config))

    def test_saved_execution_chronology_ignores_reversed_presentation(self):
        from tools.study_history import execution_chronology
        old=campaign.restore(campaign.PREDECESSOR_RUN)
        rows=old.store.artifact(old.rounds[0]['result'])['candidates']
        selected=deepcopy(old.selected)
        runtime=campaign.ROOT/'evidence/milestone4_autonomous_20261005/delivery_runtime.json'
        before=runtime.read_bytes()
        for presented in (rows,list(reversed(rows))):
            result=execution_chronology(old.store,presented)
            self.assertEqual(result['latest_execution']['execution_id'],'1ffdcbc4f93f4dc4bb16a807c7b4056b')
            self.assertEqual(result['latest_completed_evaluation'],result['latest_complete_result'])
            self.assertEqual(result['latest_complete_result']['execution_id'],'1ffdcbc4f93f4dc4bb16a807c7b4056b')
            self.assertEqual(old.selected,selected)
        self.assertEqual(runtime.read_bytes(),before)

    def test_verified_facts_arithmetic_and_uncertain_stop(self):
        from tools.diagnostic_revision import ensure_aliases
        state=self.w.store.session(self.w.host.run_id)['state'];aliases=ensure_aliases(state)['aliases']
        catalog=state['fact_catalog'];numbers=[a for a,h in aliases.items() if type(catalog[h]['value']) is float][:2]
        a,b=numbers;x=catalog[aliases[a]]['value'];y=catalog[aliases[b]]['value']
        d=self.stop();d['observations']=[dict(evidence=a,comparison_evidence=b,operation='difference',value=x-y)]
        result=self.validate(d)
        self.assertEqual(result['verified_observations'][0]['value'],x-y)
        self.assertEqual(result['decision']['action'],'stop')
        self.assertEqual(result['model_interpretations'],d['interpretations'])
        d['observations'][0]['value']+=.1
        with self.assertRaisesRegex(ValueError,'VALUE_MISMATCH: expected'):self.validate(d)
        d=self.stop();d['observations'][0]['evidence']='F999999'
        with self.assertRaisesRegex(ValueError,'out-of-scope'):self.validate(d)

    def test_frozen_fallback_carries_shared_budget_and_recovery(self):
        from tools.state_io import atomic_json
        original=read(self.directory/'scheduler_state.json')
        self.w.status='model_stopped';self.w.current_case='primary';self.w.sealed_cases=[];self.w.rounds=[]
        before=self.w.store.remaining();host=self.w.host.run_id
        self.assertTrue(campaign.fallback_eligible(self.w))
        with patch.object(self.w.store,'remaining',return_value={**before,'remaining':{**before['remaining'],'backend_solves':1}}):
            self.assertFalse(campaign.fallback_eligible(self.w))
        self.assertTrue(campaign.activate_fallback(self.w))
        self.assertEqual(self.w.host.run_id,host)
        self.assertEqual(self.w.store.remaining(),before)
        self.assertEqual(self.w.current_case,'fallback')
        self.assertEqual(self.w.sealed_cases[0]['case_id'],'primary')
        self.assertFalse(campaign.fallback_eligible(self.w))
        atomic_json(self.directory/'scheduler_state.json',original)

    def test_deliberate_replication_preserves_known_identity(self):
        d=self.search();p=d['plan'];p['candidates']=[{'control/recipe/holding_tip_speed_weight':.09}]
        with self.assertRaisesRegex(ValueError,'NEVER_CHANGES'):self.validate(d)
        p['replication_reason']='Repeat the same scientific configuration to measure run-to-run response; not a novel design.'
        result=self.validate(d)
        self.assertEqual(result['batch_plan']['actual_differences'][0]['actual_changes'],[])
        self.assertEqual(result['batch_plan']['plan']['replication_reason'],p['replication_reason'])
        from tools.platform_search import prepare_offline_batch,run_offline_batch
        from tools.platform_host import Host
        from tools.platform_store import Store,zero
        from uuid import uuid4
        root=Path(self.temp.name)/'replication-offline';store=Store(root)
        budget={**zero(),'tool_calls':20,'wall_s':4000.}
        store.create(dict(project_id='offline-replication',grant_id='offline-'+uuid4().hex,budget=budget,
            authorization_source='Synthetic offline fixture; zero API/backend/workers'))
        host=Host(root,'offline-replication');inp=deepcopy(self.w.store.session(self.w.host.run_id)['snapshot']['input'])
        inp['run_id']=host.run_id;inp['policy'].update(budget=budget,tool_bindings={},allowed_tools=[])
        host.create(inp)
        record=result['batch_plan'];refs=[r['facts']['configuration'] for r in self.w.records]
        refs.append(record['bindings']['execution_source_configuration'])
        with store.transaction() as db:
            for ref in refs:self.assertEqual(plain(store.put(db,self.w.store.artifact(ref,raw=True))),ref)
            record['offline_engineering_fixture']=True;ref=plain(store.put(db,record))
            store.event(db,host.run_id,'role_transition','search_batch_plan',outputs=[ref])
        source=next(r['facts'] for r in self.w.records if r['facts']['candidate']==self.source)
        prepare_offline_batch(host,ref,starting_facts=source,retained_baseline=self.w.baseline,historical_results=self.w.records)
        stages=[]
        def injected(stage,candidate,receipts):
            stages.append(stage);facts=deepcopy(source)
            facts['configuration']=candidate['configuration'];facts['candidate'].update(candidate_id=candidate['candidate_id'],configuration=candidate['configuration'])
            return dict(factual_result=facts,synthetic=True) if stage=='profile' else dict(synthetic=True)
        executed=run_offline_batch(host,injected)
        self.assertEqual(stages,['simulation','evaluation','profile'])
        self.assertEqual(executed['deliberate_replications'],1)
        self.assertEqual(executed['fully_evaluated_new_executions'],1)
        self.assertEqual(executed['fully_evaluated_distinct_changed_configurations'],0)
        self.assertEqual(self.w.selected,self.w.freeze['incumbent'])
