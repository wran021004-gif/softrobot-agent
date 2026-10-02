"""Focused handle, receipt, handoff and common-phase fixtures; no live science."""
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from tests import test_shared_diagnosis as fixtures
from tools.diagnostic_workflow import DiagnosticWorkflow, ROOT, save
from tools.diagnostic_facts import resolve_handles, handover, context_view
from tools.diagnostic_inventory import validate_gaps
from tools.diagnostic_native import BoundSavedStateAdapter
from tools.platform_diagnosis_coordinator import configure_role
from tools.platform_models import payload_for, ToolProtocolError
from tools.platform_handoff import submit, validate_selector
from schemas.platform import ModelResponse
from schemas.platform_handoff import InventoryDiagnosisSubmission, InventoryGap, EvidenceSelector
from tools.state_io import read
from unittest import TestCase

native=fixtures.native


class Stage349Tests(TestCase):
    setUp=fixtures.SharedWorkflowTests.setUp
    cleanup=fixtures.SharedWorkflowTests.cleanup

    def workflow(self,mode='dual_context',suffix='case',initial_only=False):
        experiment=read(ROOT/'examples/stage349_experiment.json')
        experiment['evidence_directory']=str(Path(self.temp.name)/'exports')
        w=DiagnosticWorkflow(Path(self.temp.name)/suffix,mode,initial_only=initial_only,experiment=experiment)
        w.prepare(dict(test_fixture=True));return w

    def configure(self,w,h):
        configure_role(h,'diagnostic','fixture',binding=w.binding,inventory=w.inventory,
            memory_identity=h.run_id,native_store_root=str(w.directory),native_fixed=w.fixed('initial'),
            phase_tools=['diagnosis.inspect_evidence','evidence.read','diagnosis.submit'],request=w.chain['request'])

    def test_handles_exact_scoped_and_mandatory_numeric_result(self):
        w=self.workflow();h=w.host('diagnostic');w.chain['request']=save(w.store,dict(binding=w.binding))
        self.configure(w,h)
        handover(h,w.summary,w.store.artifact(w.summary),origin='fixture explicit summary',kind='summary')
        state=w.store.session(h.run_id)['state'];catalog=state['fact_catalog']
        handle=next(k for k,v in catalog.items() if v['selector']['pointer']=='/detail/summary/terminal_error_m')
        selector=resolve_handles(state,{'fact':[handle]})['fact'][0]
        self.assertEqual(validate_selector(w.store,EvidenceSelector.model_validate(selector)),catalog[handle]['value'])
        with self.assertRaisesRegex(ValueError,'OUT_OF_SCOPE'):resolve_handles(w.store.session(w.host('design').run_id)['state'],{'fact':[handle]})
        with self.assertRaisesRegex(ValueError,'unknown'):resolve_handles(state,{'fact':['unknown']})
        other=self.workflow(suffix='other')
        handover(other.host('diagnostic'),other.summary,other.store.artifact(other.summary),origin='fixture',kind='summary')
        with self.assertRaisesRegex(ValueError,'OUT_OF_SCOPE'):resolve_handles(other.store.session(other.host('diagnostic').run_id)['state'],{'fact':[handle]})
        adapter=BoundSavedStateAdapter();payload=payload_for(h,adapter)
        schema=next(t['function']['parameters'] for t in payload['tools'] if t['function']['name']=='diagnosis_submit')
        self.assertNotIn('fact_selectors',schema['properties']);self.assertNotIn('evidence',schema['$defs']['DiagnosticFact']['properties'])
        self.assertNotIn('gates',schema['$defs']['DiagnosticReport']['properties'])
        business=dict(report=dict(subject='control',facts=[dict(fact_id='fact',statement='Rounded prose, approximately 0.01 m.')]),fact_handles={'fact':[handle]},missing_evidence=[],recommendations=[])
        decoded=adapter.decode(ModelResponse(raw=native('diagnosis.submit',business)),0,{'diagnosis.submit':'2.0.0'},payload['tools'])
        args=InventoryDiagnosisSubmission.model_validate(decoded['arguments'])
        ctx=SimpleNamespace(store=w.store,run_id=h.run_id,artifact=w.store.artifact)
        with patch('tools.platform_handoff.transition',return_value='accepted'):self.assertEqual(submit(ctx,args),'accepted')
        result=save(w.store,dict(detail=dict(endpoint_speed_m_s=.35000000000000003,update_id=34)))
        feedback=dict(reference=result,result=result,receipt=dict(execution_status='completed'))
        configure_role(h,'diagnostic','revision',binding=w.binding,inventory=w.inventory,request=w.chain['request'],check_feedback=[feedback])
        args=args.model_copy(update=dict(check_results=[EvidenceSelector.model_validate(dict(reference=result,pointer='',value=None)).reference]))
        with self.assertRaisesRegex(ValueError,'NUMERICAL_RESULT_SELECTOR'):submit(ctx,args)
        handover(h,result,w.store.artifact(result),origin='executed check fixture',kind='numerical_result')
        state=w.store.session(h.run_id)['state'];numeric=next(k for k,v in state['fact_catalog'].items()
            if v['selector']['reference']==result and v['selector']['pointer']=='/detail/endpoint_speed_m_s')
        s=resolve_handles(state,{'fact':[numeric]})
        body=args.model_dump(mode='json');body['fact_selectors']=s;body['report']['facts'][0]['evidence']=[result]
        with patch('tools.platform_handoff.transition',return_value='accepted'):self.assertEqual(submit(ctx,InventoryDiagnosisSubmission.model_validate(body)),'accepted')
        body['fact_selectors']={'fact':[dict(reference=result,pointer='/detail/update_id',value=34)]}
        with self.assertRaisesRegex(ValueError,'NUMERICAL_RESULT_SELECTOR'):submit(ctx,InventoryDiagnosisSubmission.model_validate(body))

    def test_receipts_failed_raw_read_and_explicit_handoff(self):
        w=self.workflow();h=w.host('diagnostic');w.chain['request']=save(w.store,dict(binding=w.binding));self.configure(w,h);h.resume()
        r=h.invoke(dict(request_id='motion',tool_id='diagnosis.inspect_evidence',tool_version='1.0.0',arguments=dict(binding=w.binding,view='motion'),reason='fixture'))
        self.assertEqual(r['execution_status'],'completed')
        entry=next(e for e in w.inventory['entries'] if e['type']=='backend_motion')
        r2=h.invoke(dict(request_id='gzip',tool_id='evidence.read',tool_version='1.0.0',arguments=dict(reference=entry['reference']),reason='fixture'))
        self.assertNotEqual(r2['execution_status'],'completed');self.assertIn('motion',r2['error'])
        state=w.store.session(h.run_id)['state'];view=context_view(state)
        self.assertEqual(len(view['read_ledger']),2);self.assertTrue(view['read_ledger'][0]['coverage']['sample_count'])
        with self.assertRaisesRegex(ValueError,'READ_LEDGER'):
            validate_gaps([InventoryGap(inventory_id='source.backend_motion',status='not_read',needed='motion',basis='fixture')],w.inventory,view['read_ledger'])
        configure_role(h,'diagnostic','new phase')
        self.assertEqual(w.store.session(h.run_id)['state']['read_ledger'],state['read_ledger'])
        dest=w.host('design');self.assertFalse(w.store.session(dest.run_id)['state'].get('read_ledger'))
        one=state['fact_catalog'][view['read_ledger'][0]['handles'][0]]['selector']
        handover(dest,r['output'],{},origin=dict(context=h.run_id,receipt=r),kind='selected evidence',selectors=[one],inventory_ids=['source.backend_motion'])
        transferred=w.store.session(dest.run_id)['state']
        self.assertEqual(len(transferred['fact_catalog']),1);self.assertEqual(len(transferred['read_ledger']),1)

    test_both_modes_share_phase_accounting=fixtures.SharedWorkflowTests.test_shared_flow_feedback_memory_permissions_inventory_and_accounting

    def test_initial_only_has_no_numerical_or_backend_grant(self):
        w=self.workflow(initial_only=True)
        self.assertEqual(w.freeze['limits']['model_calls'],8)
        self.assertEqual(w.freeze['limits']['tool_calls'],20)
        self.assertEqual(w.freeze['numerical_limits'],dict(local_solves=0,prediction_evaluations=0))
        self.assertNotIn('diagnosis.saved_state_check',w.store.session(w.hosts['executor'].run_id)['snapshot']['input']['policy']['tool_bindings'])
        self.assertIsNone(w.fixed('request')['diagnosis.request']['saved_state_check'])

    def test_partial_coverage_gaps_distinguish_unread_subsets_offline(self):
        # Directly supported by the two rejected live products; no replay or relabeling.
        inventory=dict(entries=[dict(inventory_id='source.one_step_predictions',retained=True,total_records=35),
            dict(inventory_id='source.backend_motion',retained=True,time_coverage_s=[.01,.35000000000000003],sample_times_s=[i/100 for i in range(1,36)])])
        ledger=[dict(status='completed',inventory_ids=['source.one_step_predictions','source.backend_motion'],handles=['prediction'],coverage=dict(update_ids=list(range(27,35)),sample_times_s=[i/100 for i in range(28,36)])),
            dict(status='completed',inventory_ids=['source.backend_motion'],handles=['motion'],coverage=dict(sample_times_s=[i/100 for i in range(30,36)],time_coverage_s=[.3,.35000000000000003]))]
        def gap(identity,status,**scope):
            return InventoryGap(inventory_id=identity,status=status,needed='Selected missing coverage',basis='Fixture receipt',**scope)
        validate_gaps([gap('source.one_step_predictions','not_read',update_ids=list(range(27))),
            gap('source.backend_motion','not_displayed',time_range_s=[.01,.27])],inventory,ledger,['prediction','motion'])
        for g in [gap('source.one_step_predictions','not_read'),
                  gap('source.one_step_predictions','not_read',update_ids=[26,27]),
                  gap('source.one_step_predictions','queried',update_ids=[26,27]),
                  gap('source.backend_motion','not_displayed',time_range_s=[.01,.29]),
                  gap('source.backend_motion','not_displayed',time_range_s=[.29,.31])]:
            with self.subTest(g=g),self.assertRaises(ValueError):validate_gaps([g],inventory,ledger,['prediction','motion'])
