"""Offline real-SDK crash/recovery checks. Mock Provider, no scientific execution."""
import asyncio,json,os,shutil,unittest
from copy import deepcopy
from unittest.mock import patch
from uuid import uuid4
import httpx
from tools.research import core
from tools.research.config import ROOT,resolve
from tools.research.state import state,update
from tools.research.agent import converse
from tools.research.session_handoff import recover_confirmed_incomplete

class IncompleteSessionRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'runs'/('p2-recovery-fixture-'+uuid4().hex[:8])
        spec=resolve(ROOT/'configs/research/study_p2_v3_agent_positive_high.json')
        spec=deepcopy(spec);spec['study_id']=self.folder.name;spec['configuration']['run_id']=spec['study_id']
        with patch('tools.research.config.resolve',return_value=spec):self.h=core.prepare(directory=self.folder)
        update(self.h,freeze='offline-fixture');self.sent=[]
        self.env=patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline','OPENBLAS_NUM_THREADS':'1','OMP_NUM_THREADS':'1','MKL_NUM_THREADS':'1'})
        self.env.start();self.addCleanup(self.env.stop)
        for name in ('tools.research.core.guard','tools.research.agent.guard','tools.research.state.guard'):
            p=patch(name);p.start();self.addCleanup(p.stop)
        p=patch('tools.research.agent.load_credential');p.start();self.addCleanup(p.stop)
        # This recovery fixture never launches a scientific worker. Its frozen
        # host preflight must be explicit so dependency availability cannot mask
        # the SDK crash/restore behavior being tested.
        p=patch('tools.research.tool_readiness.execution_environment',return_value={'status':'ready'})
        p.start();self.addCleanup(p.stop)
        p=patch('httpx.AsyncHTTPTransport',side_effect=lambda **_:httpx.MockTransport(self.respond));p.start();self.addCleanup(p.stop)
        self.addCleanup(self.cleanup)
    def cleanup(self):
        from tools.research.agent import session_storage_path
        import gc
        self.h=None;gc.collect()
        if self.folder.exists():shutil.rmtree(session_storage_path(self.folder),ignore_errors=True)
    def respond(self,request):
        wire=json.loads(request.content);self.sent.append(wire)
        message={'role':'assistant','content':None,'reasoning_content':'offline fixture reasoning'}
        if len(self.sent)==1:
            message['tool_calls']=[{'id':'fixture-read','type':'function','function':{'name':'evidence_read','arguments':json.dumps({'reference':state(self.h)['public_prior_manifest'],'view':'summary'})}}]
            finish='tool_calls'
        elif len(self.sent)==2:
            message['tool_calls']=[{'id':'partial-tool','type':'function','function':{'name':'research_plan','arguments':'{"action":'}}]
            finish='length'
        elif len(self.sent)==3:
            message['tool_calls']=[{'id':'next-read','type':'function','function':{'name':'evidence_read','arguments':json.dumps({'reference':state(self.h)['public_prior_manifest'],'view':'summary'})}}]
            finish='tool_calls'
        else:raise AssertionError('one-new-request limit exceeded')
        return httpx.Response(200,json={'id':'fixture','object':'chat.completion','created':1,'model':wire['model'],'choices':[{'index':0,'finish_reason':finish,'message':message}],'usage':{'prompt_tokens':2,'completion_tokens':3,'total_tokens':5}})
    def truncate(self):
        with self.assertRaises(Exception):asyncio.run(converse(self.h))
        self.assertEqual(len(self.sent),2);self.assertTrue(state(self.h)['pilot'].get('unconsumed_response'))
    def test_recover_reopens_snapshot_and_preserves_ledger_idempotently(self):
        self.truncate();old=deepcopy(state(self.h));budget=self.h.store.remaining()
        asyncio.run(converse(self.h,recover_incomplete=True,restore_only=True))
        current=state(self.h);self.assertFalse(current['pilot'].get('unconsumed_response'))
        self.assertNotEqual(current['pilot']['framework_session_id'],old['pilot']['framework_session_id'])
        self.assertEqual(self.h.store.remaining(),budget);self.assertEqual(len(self.sent),2)
        self.assertEqual(current['candidates'],old['candidates']);self.assertEqual(current['research_status'],old['research_status'])
        events=self.h.store.events(self.h.run_id)
        committed=[e for e in events if e['kind']=='incomplete_provider_disposition' and e['status']=='committed']
        self.assertEqual(len(committed),1)
        asyncio.run(converse(self.h,recover_incomplete=True,restore_only=True))
        self.assertEqual(self.h.store.remaining(),budget);self.assertEqual(len(self.sent),2)
        self.assertEqual(len([e for e in self.h.store.events(self.h.run_id) if e['kind']=='incomplete_provider_disposition' and e['status']=='committed']),1)
    def test_crash_after_prepare_retains_old_then_recovers(self):
        self.truncate();old=deepcopy(state(self.h));budget=self.h.store.remaining()
        async def interrupted(host,agent,build,directory):
            def crash(stage):
                if stage=='prepared':raise RuntimeError('fixture crash')
            return await recover_confirmed_incomplete(host,agent,build,directory,stage=crash)
        with patch('tools.research.session_handoff.recover_confirmed_incomplete',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'fixture crash'):asyncio.run(converse(self.h,recover_incomplete=True,restore_only=True))
        s=state(self.h);self.assertEqual(s['pilot']['unconsumed_response'],old['pilot']['unconsumed_response'])
        self.assertEqual(s['pilot']['framework_session_id'],old['pilot']['framework_session_id']);self.assertEqual(self.h.store.remaining(),budget)
        asyncio.run(converse(self.h,recover_incomplete=True,restore_only=True));self.assertEqual(self.h.store.remaining(),budget)

    def test_crash_after_snapshot_can_reopen_without_repeated_charge(self):
        self.truncate();old=deepcopy(state(self.h));budget=self.h.store.remaining()
        async def interrupted(host,agent,build,directory):
            def crash(stage):
                if stage=='snapshot_saved':raise RuntimeError('fixture snapshot crash')
            return await recover_confirmed_incomplete(host,agent,build,directory,stage=crash)
        with patch('tools.research.session_handoff.recover_confirmed_incomplete',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'fixture snapshot crash'):asyncio.run(converse(self.h,recover_incomplete=True,restore_only=True))
        self.assertEqual(state(self.h)['pilot']['unconsumed_response'],old['pilot']['unconsumed_response'])
        self.assertEqual(self.h.store.remaining(),budget)
        asyncio.run(converse(self.h,recover_incomplete=True,restore_only=True))
        self.assertEqual(self.h.store.remaining(),budget);self.assertEqual(len(self.sent),2)

    def test_crash_before_prepare_does_not_mutate_recovery_state(self):
        self.truncate();old=deepcopy(state(self.h));budget=self.h.store.remaining()
        async def interrupted(host,agent,build,directory):
            def crash(stage):
                if stage=='before_prepare':raise RuntimeError('fixture early crash')
            return await recover_confirmed_incomplete(host,agent,build,directory,stage=crash)
        with patch('tools.research.session_handoff.recover_confirmed_incomplete',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'fixture early crash'):asyncio.run(converse(self.h,recover_incomplete=True,restore_only=True))
        self.assertEqual(state(self.h),old);self.assertEqual(self.h.store.remaining(),budget)

    def test_one_new_request_pauses_after_real_tool_feedback(self):
        self.truncate()
        asyncio.run(converse(self.h,recover_incomplete=True,restore_only=True))
        asyncio.run(converse(self.h,max_new_provider_requests=1))
        self.assertEqual(len(self.sent),3)
        self.assertEqual(self.h.store.remaining()['used']['model_calls'],3)
        self.assertTrue(any(e['kind']=='supervisor_pause' for e in self.h.store.events(self.h.run_id)))
        self.assertTrue(any(e['kind']=='request_feedback_boundary' for e in self.h.store.events(self.h.run_id)))
        self.assertFalse(state(self.h)['pilot'].get('unconsumed_response'))
        self.assertEqual(state(self.h)['research_status'],'ready')

    def test_invalid_v3_section_feedback_reports_exact_station_counts(self):
        from tools.research.design import generate_candidate
        spec=state(self.h)['spec']
        section={'kind':'circle','parameters':{'radius_m':.008}}
        request={'version':'serial_family_generation_v3','family_space_identity':spec['family_space_identity'],
            'segment_count':3,'tendon_count':3,'segments':{'1':{'sections':[section]}}}
        result=generate_candidate(self.h,request,{'origin':'offline-fixture'})
        self.assertEqual(result['reason'],'EXACT_SECTION_STATIONS_REQUIRED')
        self.assertEqual([v['required_stations'] for v in result['diagnostic']['segments']],[1,2,2])
        self.assertIn('Omit sections',result['diagnostic']['instruction'])
        self.assertIsNone(result['candidate'])
