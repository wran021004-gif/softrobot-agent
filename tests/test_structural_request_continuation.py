"""Actual six-run state and 20 synthetic final slots; no paid entry points."""
from copy import deepcopy
import json
from unittest import TestCase
from unittest.mock import patch
from tests import test_structural_history_continuation as saved_fixture
from examples import research_model_v1 as pilot
from examples import research_campaign_v3 as campaign
from tools.context_assembly import assemble_working_context,fit_request,measure_input
from tools.diagnostic_reference_adapter import EvidenceDrivenAdapter
from tools.fixed_research import prepare_candidate,schedule,select_candidate
from tools.platform_host import Host
from tools.platform_models import payload_for
from tools.platform_store import plain,zero
from tools.research_spec import load_spec
from tools.research_tasks import aggregate_acceptance,compare_acceptance
from tools.state_io import atomic_json,digest,read
from extensions.tendon_family.gvs_profile import execution_scope


class StructuralRequestContinuationTests(TestCase):
    needs_original_batch=False
    def setUp(self):
        saved_fixture.StructuralHistoryContinuationTests.setUp(self)
        self.w.repairs=7
        start=read(self.w.directory.parent/'research_native_development_v3_20261007/structural_repair7_start.json')
        r=start['reservation']
        self.w.store.complete(r,dict(request_id=r['request_id'],execution_id=r['execution_id'],caller='engineering',
            tool_id='offline.synthetic.repair7',tool_version='3.6.0',execution_status='completed',charged=zero()),
            dict(synthetic_engineering_fixture=True),.001)

    def tearDown(self):
        saved_fixture.StructuralHistoryContinuationTests.tearDown(self)

    def request(self):
        pilot.configure(self.w)
        adapter=EvidenceDrivenAdapter();payload=payload_for(self.w.host,adapter)
        pilot.adopt_current_working(self.w)
        return payload,adapter.context_assembly_audit

    def check_all_inline_facts(self,payload):
        content=json.loads(payload['messages'][1]['content'])['role_context']['research_packet']
        if 'inline_strings' in content:
            strings=content['inline_strings']
            def expand(value):
                if isinstance(value,dict):
                    if set(value)=={'$s'}:return strings[value['$s']]
                    return {k:expand(v) for k,v in value.items()}
                if isinstance(value,list):return [expand(v) for v in value]
                return value
            content=expand(content)
        def expand_tables(value):
            if isinstance(value,dict):
                if set(value)=={'$e'}:return dict(artifact_id=value['$e'],media_type='application/json')
                if set(value)=={'table_columns','table_rows'}:
                    return [{k:expand_tables(v) for k,v in zip(value['table_columns'],row) if v!={'$absent':True}} for row in value['table_rows']]
                return {k:expand_tables(v) for k,v in value.items()}
            if isinstance(value,list):return [expand_tables(v) for v in value]
            return value
        content=expand_tables(content)
        for block in [content['current_feedback'],*content.get('performed_batch_evidence',[])]:
            if 'alias_columns' in block:
                block['aliases']={a:dict(pointer=block['alias_pointer_prefixes'][v[0]]+'/'+v[1],value=v[2]) for a,v in block['aliases'].items()}
            full=next((r for r in [self.w.working['packet']['current_feedback'],*self.w.working['packet']['performed_batch_evidence']] if r['reference']==block['reference']),None)
            self.assertIsNotNone(full)
            for a,selector in block['aliases'].items():self.assertEqual(selector,full['aliases'][a])
        bound=content['bound_evidence']
        expected=self.w.working['current_facts']
        if 'fact_columns' in bound:
            self.assertEqual(bound['fact_columns'],['metric_index','fact_id','value','source_index'])
            actual={cell[1]:dict(metric=bound['metric_columns'][cell[0]][0],value=cell[2],unit=bound['metric_columns'][cell[0]][1],execution_id=row['execution_id'])
                for row in bound['executions'] for cell in row['facts']}
            for row in bound['executions']:
                for cell in row['facts']:self.assertEqual(row['sources'][cell[3]],expected[cell[1]]['source_artifact'])
        else:
            actual={fid:dict(metric=metric,**bound['facts'][fid],execution_id=row['execution_id'])
                for row in bound['executions'] for metric,fid in row['facts'].items()}
        self.assertEqual(set(expected),set(actual))
        for fid,fact in expected.items():
            self.assertEqual(actual[fid],{k:fact[k] for k in ('metric','value','unit','execution_id')})
        cap=content['capabilities']
        self.assertEqual(cap,self.w.working['packet']['capabilities'])
        self.assertEqual(content['capabilities']['authority_snapshot'],self.w.working['packet']['capabilities']['authority_snapshot'])
        return content

    def test_actual_post_far_feedback_and_reversible_fact_join(self):
        payload,audit=self.request()
        content=self.check_all_inline_facts(payload)
        self.assertTrue(audit['measurement']['passed'])
        self.assertEqual(self.w.store.remaining()['used']['model_calls'],7)
        self.assertEqual(self.w.store.remaining()['used']['backend_solves'],6)
        self.assertEqual(content['current_feedback']['reference'],self.w.working['packet']['current_feedback']['reference'])
        # The recorded six-run request exceeded the identical frozen settings.
        source=read(self.w.directory.parent/'research_native_development_v3_20261007/context_assembly/audits/96164ac806eda852f4856011394d4c1f16fd98589426b3605ec432985bb6c761.json')
        self.assertFalse(source['measurement']['passed'])
        self.assertEqual(source['measurement']['input_budget_tokens'],audit['measurement']['input_budget_tokens'])
        print('POST_FAR_REQUEST',audit['measurement'])

    def synthetic_record(self,spec,role,slot,changes):
        cid='offline-'+role+'-'+slot['case_id']+'-'+str(slot['seed'])
        cfg,initial=prepare_candidate(spec,candidate_id=cid,changes=changes,case_id=slot['case_id'],seed=slot['seed'])
        child=Host(self.directory,cid);child.create(cfg)
        baseline=deepcopy(self.w.records[-1]);facts=deepcopy(baseline['facts'])
        receipts={}
        with self.w.store.transaction() as db:config=plain(self.w.store.put(db,dict(effective=cfg)))
        for name,tool in (('simulation','simulation.run'),('evaluation','evaluation.run'),('profile','control.profile_report')):
            reservation,_=self.w.store.reserve(cid,name,digest((cid,name)),'offline.synthetic',
                {**zero(),'tool_calls':1,'backend_solves':int(name=='simulation'),'wall_s':1.})
            if name=='simulation':document=dict(synthetic_engineering_fixture=True)
            elif name=='evaluation':
                document=deepcopy(self.w.store.artifact(baseline['facts']['evaluation']))
                document.update(candidate_id=cid,source=receipts['simulation']['output'],
                    source_execution_id=receipts['simulation']['execution_id'],original_execution_id=receipts['simulation']['execution_id'])
                document['synthetic_engineering_fixture']=True
            else:
                document=deepcopy(self.w.store.artifact(baseline['facts']['report']['reference']))
                document['detail'].update(candidate_id=cid,owner_run_id=cid,configuration=config,
                    execution_id=receipts['simulation']['execution_id'],simulation=receipts['simulation']['output'],
                    evaluation=receipts['evaluation']['output'],execution_scope=execution_scope(cfg),task=cfg['task'])
                document['synthetic_engineering_fixture']=True
            receipts[name]=self.w.store.complete(reservation,dict(request_id=name,execution_id=reservation['execution_id'],
                caller='offline.synthetic',tool_id=tool,tool_version='1.0.0',execution_status='completed',
                cache_hit=False,original_execution_id=reservation['execution_id'] if name=='simulation' else None,charged=zero()),document,.001)
        eid=receipts['simulation']['execution_id']
        candidate=dict(candidate_id=cid,configuration=config,owner_run_id=cid,execution_id=eid)
        facts.update(candidate=candidate,configuration=config,execution_id=eid,simulation=receipts['simulation']['output'],
            evaluation=receipts['evaluation']['output'],report=dict(reference=receipts['profile']['output'],owner_run_id=cid,execution_id=eid,request_id='profile'))
        acceptance=deepcopy(baseline['acceptance']);acceptance.update(execution_id=eid,task_identity=digest(cfg['task']),
            sources=dict(evaluation=receipts['evaluation']['output'],profile=receipts['profile']['output']))
        record=dict(baseline,role='verification_'+role,phase='verification',facts=facts,acceptance=acceptance,
            execution_id=eid,owner_run_id=cid,case_id=slot['case_id'],seed=slot['seed'],repetition=slot['repetition'],
            implementation=campaign.seal(),execution_scope=execution_scope(cfg),source_store=str(self.directory),receipts=receipts,
            synthetic_engineering_fixture=True)
        self.w.records.append(record)
        return dict(candidate_id=cid,changes=changes,**slot,purpose='offline.synthetic.final_gate',
            status='completed',initial_state=initial,configuration=config,acceptance=acceptance,
            receipt=receipts['simulation'],receipts=list(receipts.values()),evaluation=receipts['evaluation']['output'],
            profile=receipts['profile']['output'],synthetic_engineering_fixture=True)

    def test_twenty_final_slots_real_feedback_and_next_report_request(self):
        spec=load_spec();chosen=select_candidate(campaign.previous.search_rows(self.w))
        self.assertEqual(chosen['candidate_id'],'batch-396bdbbae02626d3-0')
        # Pressure only: include the last two still-legal research slots too.
        # These synthetic records are never evidence of actual scientific work.
        for seed,scale in ((17,1.01),(18,1.02)):
            self.synthetic_record(spec,'future_research_pressure',dict(case_id='nominal',seed=seed,repetition=1),
                {'design/near_section_scale':scale})
            self.w.records[-1]['phase']='search'
        groups=[dict(role='unchanged_incumbent',changes={},records=[]),
            dict(role='selected_candidate',changes=chosen['changes'],records=[])]
        slots=schedule(spec)
        for slot in slots:
            for group in groups:group['records'].append(self.synthetic_record(spec,group['role'],slot,group['changes']))
        aggregates=[dict(role=g['role'],acceptance=aggregate_acceptance(g['records'],10,schedule=slots)) for g in groups]
        result=dict(plan=dict(schedule=slots,selected_candidate=chosen,groups=[dict(role=g['role'],changes=g['changes']) for g in groups]),
            groups=groups,aggregates=aggregates,complete=True,comparison=compare_acceptance(aggregates[1]['acceptance'],aggregates[0]['acceptance']),
            improvement_supported=False,usage=self.w.store.remaining(),synthetic_engineering_fixture=True)
        atomic_json(self.directory/'verification_progress.json',result)
        atomic_json(self.directory/'verification.json',result)
        pilot.reusable.feedback(self.w,dict(status='verification_delivered',verification=result),'offline.synthetic.frozen_verification_feedback')
        self.w.status='model_stopped';self.w.stop_reason='Offline synthetic STOP; no scientific claim'
        self.w.freeze['final_reporting']=True
        payload,audit=self.request();content=self.check_all_inline_facts(payload)
        self.assertTrue(audit['measurement']['passed'])
        self.assertEqual(set(content['capabilities']['legal']),{'stop'})
        self.assertEqual(len(content['verification']['outcomes']),20)
        self.assertEqual(self.w.store.remaining()['used']['model_calls'],7)
        self.assertEqual(self.w.store.remaining()['used']['backend_solves'],28)
        self.assertIn('valid_failure',{r['acceptance']['status'] for r in self.w.records})
        print('TWENTY_SLOT_REPORT_REQUEST',audit['measurement'])
