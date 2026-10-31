"""Synthetic unknown-send/SDK fixtures; no live Provider or scientific Worker."""
import asyncio,json,unittest
from pathlib import Path
import httpx
from tools.research.provider import LiveBoundary,record,received,pending,provider_outcome,abandon_unrecoverable_reporter_attempt
from tools.research.reporter import assemble,_save,_wire,current_reports
from tools.research.state import state,update
from tools.research.session_handoff import session_storage_path
from tools.state_io import digest
from tests.research.test_p63g3_action_handoff import g3_host
from tests.research.test_p63a_math_interface import generate,t1_request,offline_dispatch


class ReporterAbandonmentTests(unittest.TestCase):
    def setUp(self):
        self.h=g3_host();c=generate(self.h)
        self.result=offline_dispatch(self.h,t1_request(self.h,c),'SYNTHETIC-R3-ONLY')['reference']
        report=assemble(self.h,[self.result]);self.base=_save(self.h,report)
        self.messages=[dict(role='assistant',content=[dict(toolUse=dict(toolUseId='synthetic-paired',name='evidence_read',input={}))]),
            dict(role='user',content=[dict(toolResult=dict(toolUseId='synthetic-paired',status='success',content=[dict(text='Synthetic fixture, not scientific evidence')]))])]
        session=state(self.h)['pilot']['framework_session_id']
        self.snapshot=Path(session_storage_path(self.h.store.root/'framework_sessions'))/'session'/session/'scopes/agent/default/snapshots/snapshot_latest.json'
        self.snapshot.parent.mkdir(parents=True,exist_ok=True)
        self.snapshot.write_text(json.dumps(dict(data=dict(messages=self.messages))),encoding='utf-8')
        record(self.h,'science_delivery_boundary',dict(session_id=session,sdk_message_identity=digest(self.messages),paired=True,receipts_settled=True))
        record(self.h,'reporter_attempt',dict(base_report=self.base['artifact_id']))
        saved=self.h.store.artifact(self.base);wire=_wire(self.h,self.base,saved)
        class Boundary(LiveBoundary):purpose='reporter'
        def unknown(request):raise httpx.ReadTimeout('Synthetic lost response; no network',request=request)
        async def send():
            b=Boundary(self.h,httpx.MockTransport(unknown));self.boundary=b
            try:await b.handle_async_request(httpx.Request('POST',state(self.h)['pilot']['provider']['base_url'].rstrip('/')+'/chat/completions',json=wire))
            except httpx.ReadTimeout:pass
            finally:await b.aclose()
        asyncio.run(send());self.key=self.boundary.last_request
        self.auth=dict(approved=True,scope='abandon_unrecoverable_reporter_attempt_v1',study_id=self.h.run_id,
            request_id=self.key,expected_provider_requests=1,source_sha256='synthetic-authorization',reason='Synthetic explicit user-authorization fixture')

    def abandon(self):return abandon_unrecoverable_reporter_attempt(self.h,self.key,authorization=self.auth)

    def test_local_cancel_preserves_unknown_charge_results_sdk_and_idempotence(self):
        before=state(self.h);sdk=self.snapshot.read_bytes();ledger=self.h.store.remaining()
        result=self.abandon();self.assertEqual(state(self.h),before)
        self.assertEqual(self.snapshot.read_bytes(),sdk);self.assertEqual(self.h.store.remaining()['used'],ledger['used'])
        self.assertEqual(result['provider_outcome'],'unknown');self.assertIsNone(result['tokens']);self.assertIsNone(result['money'])
        self.assertFalse(result['upstream_cancelled']);self.assertFalse(result['response_saved'])
        self.assertIsNone(received(self.h,self.key));self.assertEqual(pending(self.h),[])
        outcome=provider_outcome(self.h,self.key)
        self.assertTrue(outcome['outcome_unknown']);self.assertTrue(outcome['provider_charged'])
        self.assertEqual(outcome['charged_model_requests'],1);self.assertIsNone(outcome['money'])
        receipt=json.loads(self.h.store.lookup(self.h.run_id,self.key)['receipt'])
        self.assertEqual(receipt['execution_status'],'cancelled');self.assertEqual(receipt['charged']['model_calls'],1)
        revision=next(v for r,v in current_reports(self.h) if v['interpretation_for']==self.base)
        self.assertEqual(revision['interpretation_status'],'unavailable');self.assertEqual(revision['report']['interpretations'],[])
        events=self.h.store.events(self.h.run_id);self.assertEqual(self.abandon(),result)
        self.assertEqual(self.h.store.events(self.h.run_id),events)
        self.assertEqual(len([e for e in events if e['kind']=='reporter_attempt_abandoned_locally']),1)

    def test_unknown_main_cannot_be_abandoned(self):
        with self.h.store.transaction() as db:
            e=next(e for e in self.h.store.events(self.h.run_id,db=db) if e['kind']=='r3_request')
            meta=self.h.store.artifact(e['outputs'][0],db=db);meta['purpose']='conversation'
            ref=self.h.store.put(db,meta);e['outputs']=[ref.model_dump(mode='json')]
            db.execute('update events set body=? where seq=?',(json.dumps(e),e['sequence']))
        with self.assertRaisesRegex(ValueError,'ONLY_READONLY_REPORTER'):self.abandon()
        self.assertEqual(len(pending(self.h)),1)

    def test_saved_response_must_use_original_recovery(self):
        with self.h.store.transaction() as db:
            raw=self.h.store.put(db,b'Synthetic saved response',media='application/octet-stream')
            saved=self.h.store.put(db,dict(body=raw.model_dump(mode='json'),http_status=200,purpose='reporter'))
            self.h.store.event(db,self.h.run_id,'r3_response','received',request=self.key,outputs=[saved])
        with self.assertRaisesRegex(ValueError,'SAVED_RESPONSE_MUST_USE_ORIGINAL_RECOVERY'):self.abandon()

    def test_unsealed_scientific_worker_blocks_abandonment(self):
        path=self.h.store.root/'analyses/synthetic-live/boundary.json';path.parent.mkdir(parents=True)
        path.write_text(json.dumps(dict(termination_confirmed=False)),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'UNSEALED_SCIENTIFIC_WORKER'):self.abandon()

    def test_wrong_study_or_missing_user_authorization_rejected(self):
        for change in (dict(study_id='wrong-study'),dict(approved=False)):
            with self.subTest(change=change),self.assertRaisesRegex(ValueError,'EXACT_USER_AUTHORIZATION'):
                abandon_unrecoverable_reporter_attempt(self.h,self.key,authorization={**self.auth,**change})

    def test_wrong_request_id_rejected(self):
        with self.assertRaisesRegex(ValueError,'ONE_UNKNOWN_PROVIDER_ATTEMPT'):
            abandon_unrecoverable_reporter_attempt(self.h,'wrong-request',authorization={**self.auth,'request_id':'wrong-request'})

    def test_sdk_unpaired_or_altered_feedback_blocks_abandonment(self):
        self.snapshot.write_text(json.dumps(dict(data=dict(messages=self.messages[:-1]))),encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'ORIGINAL_PAIRED_SDK_SNAPSHOT'):self.abandon()

    def test_pending_science_or_unconsumed_response_blocks_abandonment(self):
        update(self.h,pending=dict(kind='synthetic_pending_science'))
        with self.assertRaisesRegex(ValueError,'PAIRED_SETTLED_MAIN_FEEDBACK'):self.abandon()


if __name__=='__main__':unittest.main()
