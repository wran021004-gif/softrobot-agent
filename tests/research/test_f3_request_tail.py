"""Public SDK formatter plus accounted mock HTTP; no real Provider."""
import asyncio
from copy import deepcopy
import json
import unittest
import httpx
from tools.research.agent import LiveBoundary,live_model_class
from tools.research.state import state
from tools.state_io import atomic_json
from tests.research import test_s129_agent_reporting as fixture
from tests.research.test_s127_session_recovery import response


class RequestTailTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):fixture.AgentReportingTests.setUpClass()

    def setUp(self):
        self.f=fixture.AgentReportingTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.h=self.f.h

    def test_tail_does_not_change_history_and_saved_request_replays_exactly(self):
        sent=[]
        def receive(request):sent.append(json.loads(request.content));return response(request)
        boundary=LiveBoundary(self.h,httpx.MockTransport(receive));p=state(self.h)['pilot']['provider']
        model=live_model_class(boundary)(model_id=p['model'],stream=False,
            params=dict(max_tokens=p['max_tokens'],reasoning_effort=p['reasoning_effort'],extra_body=dict(thinking=dict(type=p['thinking']))),
            client_args={'api_key':'offline'})
        history=[dict(role='user',content=[dict(text='saved research question')]),
            dict(role='assistant',content=[dict(toolUse=dict(toolUseId='native-id',name='evidence_read',input={}))]),
            dict(role='user',content=[dict(toolResult=dict(toolUseId='native-id',status='success',content=[dict(text='saved result')]))])]
        original=deepcopy(history)
        def wire():
            value=model.format_request(history,system_prompt='fixed rules')
            value.update(value.pop('extra_body',{}));return value
        boundary.research_packet={'latest_L1':'first'};first=wire()
        boundary.research_packet={'latest_L1':'after Reporter'};second=wire()
        self.assertEqual(first['messages'][0],second['messages'][0])
        self.assertIn('after Reporter',second['messages'][-1]['content'])
        self.assertEqual(first['messages'][:-1],second['messages'][:-1])
        self.assertEqual(history,original)
        self.assertEqual(second['messages'][-2]['tool_call_id'],'native-id')
        async def exercise():
            url=p['base_url'].rstrip('/')+'/chat/completions'
            await boundary.handle_async_request(httpx.Request('POST',url,json=second))
            boundary.research_packet={'latest_L1':'must not overwrite saved request'}
            restored=wire();self.assertEqual(restored,second)
            await boundary.handle_async_request(httpx.Request('POST',url,json=restored))
            self.assertEqual(len(sent),1)
            boundary.consumed();await boundary.aclose()
        asyncio.run(exercise())
        measurement=dict(source='actual SDK formatted MockTransport request',native_history_unchanged=history==original,
            fixed_prefix_unchanged=first['messages'][0]==second['messages'][0],saved_request_exact_replay=True,
            requests=[dict(bytes=len(json.dumps(v).encode()),roles=[m['role'] for m in v['messages']],
                packet_indices=[i for i,m in enumerate(v['messages']) if isinstance(m.get('content'),str) and m['content'].startswith('CURRENT_RESEARCH_PACKET\n')]) for v in (first,second)])
        atomic_json(self.h.store.root/'request_tail_measurements.json',measurement)
        # Redacted, reproducible size/order evidence is kept outside temporary Store.
        atomic_json('runs/f3_request_tail_measurements.json',measurement)


if __name__=='__main__':unittest.main()
