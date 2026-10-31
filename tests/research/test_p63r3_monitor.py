"""Concurrent isolated Store/Mock Provider test; no real Provider or Worker."""
import asyncio,json,os,sqlite3,subprocess,sys,unittest
from contextlib import closing
from unittest.mock import patch
import httpx
from tools.research.agent import decision_packet
from tools.research.config import ROOT,role_provider
from tools.research.provider import LiveBoundary,request_settings,received
from tools.research.reporter import assemble,_save
from tools.research.state import state
from tests.research.test_p63g3_action_handoff import g3_host
from tests.research.test_p63a_math_interface import generate,t1_request,offline_dispatch


class MonitorConcurrencyTests(unittest.TestCase):
    def test_repeated_provider_reporter_main_sequence_with_separate_monitor(self):
        h=g3_host();c=generate(h)
        ref=offline_dispatch(h,t1_request(h,c),'synthetic-r3-monitor')['reference'];report=assemble(h,[ref])
        payload=dict(id='SYNTHETIC-R3',object='chat.completion',created=1,
            choices=[dict(index=0,finish_reason='stop',message=dict(role='assistant',content='Synthetic fixture only.'))],
            usage=dict(prompt_tokens=3,completion_tokens=2,total_tokens=5))
        raw=json.dumps(payload).encode();keys=[]
        class Boundary(LiveBoundary):pass
        def respond(request):return httpx.Response(200,content=raw)
        process=subprocess.Popen([sys.executable,'-m','tests.research.p63r3_monitor',
            '--database',str(h.store.db),'--samples','500','--interval','.002'],cwd=ROOT,
            stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.addCleanup(lambda:process.kill() if process.poll() is None else None)
        async def sequence():
            for i in range(5):
                for purpose in ('reporter','conversation'):
                    b=Boundary(h,httpx.MockTransport(respond));b.purpose=purpose
                    provider=role_provider(state(h)['spec'],state(h)['pilot']['provider'],purpose)
                    wire=dict(**request_settings(provider),messages=[dict(role='user',content='Synthetic concurrency fixture')])
                    response=await b.handle_async_request(httpx.Request('POST',provider['base_url'].rstrip('/')+'/chat/completions',json=wire))
                    self.assertEqual(await response.aread(),raw)
                    row=h.store.lookup(h.run_id,b.last_request);self.assertIsNotNone(row['receipt'])
                    self.assertEqual(h.store.artifact(received(h,b.last_request)['body'],raw=True),raw)
                    keys.append(b.last_request);b.consumed();await b.aclose()
                    if purpose=='reporter':
                        _save(h,report,status='unavailable',error='Synthetic fixture; no interpretation generated')
                self.assertIn('research',decision_packet(h))
        with patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_REAL_WORKER')):
            asyncio.run(sequence())
        stdout,stderr=process.communicate(timeout=30)
        self.assertEqual(process.returncode,0,stderr);self.assertNotIn('database is locked',stdout+stderr)
        observations=[json.loads(line) for line in stdout.splitlines()]
        self.assertTrue(any(r.get('provider',0)>0 for r in observations))
        self.assertEqual(len(keys),10);self.assertEqual(state(h)['pilot']['live_model_requests'],10)
        self.assertFalse(state(h)['pilot'].get('unconsumed_response'))
        with closing(sqlite3.connect(h.store.db,timeout=.1)) as db:
            db.execute('BEGIN EXCLUSIVE');db.rollback()

    def test_monitor_failure_does_not_terminate_writer(self):
        h=g3_host()
        result=subprocess.run([sys.executable,'-m','tests.research.p63r3_monitor','--samples','0'],
            cwd=ROOT,capture_output=True,text=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertNotEqual(result.returncode,0)
        with h.store.transaction() as db:h.store.put(db,dict(synthetic_writer_still_running=True))
        self.assertEqual(state(h)['pilot']['live_model_requests'],0)


if __name__=='__main__':unittest.main()
