"""Real SDK with explicit HTTP fixtures; never live Provider/scientific evidence."""
import asyncio
from copy import deepcopy
import json
import unittest
import httpx
from tools.research.agent import (LiveBoundary,IncompleteModelOutput,provider_outcome,
    received,pending,build_harness,live_model_class)
from tools.research.state import state
from tests.research.test_s126_checkpoint import cold_host


def reply(finish='tool_calls',*,partial=False):
    calls=[dict(id='fixture-call',type='function',function=dict(name='fixture',
        arguments='{"x":' if partial else '{}'))] if finish=='tool_calls' or partial else []
    return dict(id='fixture-response',object='chat.completion',created=1,model='deepseek-flash',
        choices=[dict(index=0,finish_reason=finish,message=dict(role='assistant',content=None,
            reasoning_content='Exact fixture reasoning retained.',tool_calls=calls))],
        usage=dict(prompt_tokens=10,completion_tokens=8,total_tokens=18))


def wire(h):
    p=state(h)['pilot']['provider']
    return dict(model=p['model'],thinking=dict(type=p['thinking']),reasoning_effort=p['reasoning_effort'],
        max_tokens=p['max_tokens'],stream=False,messages=[dict(role='user',content='Offline fixture')])


class ProviderOutputTests(unittest.TestCase):
    def test_context_reserves_output_before_any_send_or_charge(self):
        from tools.research.state import update
        h=cold_host();p=deepcopy(state(h)['pilot'])
        p['provider']['context_guard']['context_limit_tokens']=p['provider']['max_tokens']+1
        update(h,pilot=p);before=h.store.remaining()
        def forbidden(request):raise AssertionError('NO_SEND')
        b=LiveBoundary(h,httpx.MockTransport(forbidden))
        async def exercise():
            q=httpx.Request('POST',p['provider']['base_url']+'/chat/completions',json=wire(h))
            with self.assertRaisesRegex(ValueError,'CONTEXT_CAPACITY'):await b.handle_async_request(q)
            self.assertEqual(h.store.remaining(),before);self.assertFalse(pending(h))
            await b.aclose()
        asyncio.run(exercise())

    def test_sdk_restores_local_error_and_never_submits_partial_tools(self):
        from tests.research.test_s127_session_recovery import factory
        for finish,partial in [('length',False),('length',True),('content_filter',True),('aborted',True),('insufficient_system_resource',True)]:
            for inspect_only in (False,True):
                with self.subTest(finish=finish,inspect_only=inspect_only):
                    h=cold_host();sent=[];body=reply(finish,partial=partial)
                    def respond(request):
                        sent.append(request)
                        return httpx.Response(200,json=body)
                    b=LiveBoundary(h,httpx.MockTransport(respond),allow_truncated_response=inspect_only)
                    agent=factory(h,b)()
                    async def exercise():
                        with self.assertRaises(IncompleteModelOutput) as raised:
                            await agent.invoke_async('Offline fixture')
                        d=raised.exception.diagnostic
                        self.assertEqual(d['transport'],'confirmed_http_200')
                        self.assertEqual(d['finish_reasons'],[finish])
                        self.assertTrue(d['provider_charged'] and d['response_saved'])
                        self.assertFalse(d['outcome_unknown'])
                        self.assertEqual(d['native_tool_action'],'fields_present_unvalidated' if partial else 'not_produced')
                        if not inspect_only:
                            from openai import APIConnectionError
                            self.assertIsInstance(raised.exception.__cause__,APIConnectionError)
                        before=deepcopy(h.store.remaining());saved=received(h,b.last_request)
                        raw=h.store.artifact(saved['body'],raw=True)
                        self.assertEqual(json.loads(raw),body)
                        # SDK restart and direct replay both fail closed without another send/charge.
                        restored=factory(h,b)()
                        with self.assertRaises(IncompleteModelOutput):await restored.invoke_async('Offline fixture')
                        request=httpx.Request('POST',state(h)['pilot']['provider']['base_url']+'/chat/completions',content=sent[0].content)
                        if inspect_only:self.assertEqual((await b.handle_async_request(request)).content,raw)
                        else:
                            with self.assertRaises(IncompleteModelOutput):await b.handle_async_request(request)
                        with self.assertRaises(IncompleteModelOutput):b.consumed()
                        self.assertEqual(h.store.remaining(),before)
                        self.assertEqual(len(sent),1);self.assertFalse(pending(h))
                        self.assertEqual(state(h)['pilot']['unconsumed_response'],b.last_request)
                        self.assertFalse(any('toolUse' in block for m in agent.messages for block in m['content']))
                        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
                        await b.aclose()
                    asyncio.run(exercise())

    def test_normal_native_tool_round_retains_reasoning_and_ids(self):
        from strands.tools.executors import SequentialToolExecutor
        from strands.tools.tools import PythonAgentTool
        h=cold_host();sent=[];executed=[]
        def respond(request):
            sent.append(json.loads(request.content));body=reply()
            if len(sent)>1:
                body=reply('stop');body['choices'][0]['message']['content']='Consumed real fixture feedback'
            return httpx.Response(200,json=body)
        def execute(use,**kwargs):
            executed.append(use['toolUseId'])
            return dict(toolUseId=use['toolUseId'],status='success',content=[dict(text='Fixture feedback')])
        b=LiveBoundary(h,httpx.MockTransport(respond))
        tool=PythonAgentTool('fixture',dict(name='fixture',description='Offline fixture',inputSchema={'json':dict(type='object',properties={})}),execute)
        agent=build_harness(h,transport=b,api_key='offline',instructions='Fixture',model_class=live_model_class(b),
            tool_executor=SequentialToolExecutor(),research_tools=[tool],configuration_path=h.store.root/'framework.json',
            session_directory=h.store.root/'sdk')
        async def exercise():
            await agent.invoke_async('Fixture')
            self.assertEqual(executed,['fixture-call']);self.assertEqual(len(sent),2)
            assistant=next(m for m in sent[1]['messages'] if m['role']=='assistant')
            result=next(m for m in sent[1]['messages'] if m['role']=='tool')
            self.assertEqual(assistant['reasoning_content'],'Exact fixture reasoning retained.')
            self.assertEqual(assistant['tool_calls'][0]['id'],result['tool_call_id'])
            self.assertNotIn('unconsumed_response',state(h)['pilot'])
            self.assertEqual(h.store.remaining()['used']['model_calls'],2)
            await b.aclose()
        asyncio.run(exercise())

    def test_unknown_send_blocks_retry_and_differs_from_confirmed_output(self):
        h=cold_host();sent=[]
        def fail(request):sent.append(request);raise httpx.ReadError('Unknown fixture outcome')
        b=LiveBoundary(h,httpx.MockTransport(fail));p=state(h)['pilot']['provider']
        request=lambda:httpx.Request('POST',p['base_url']+'/chat/completions',json=wire(h))
        async def exercise():
            with self.assertRaises(httpx.ReadError):await b.handle_async_request(request())
            before=h.store.remaining();d=provider_outcome(h,b.last_request)
            self.assertTrue(d['outcome_unknown']);self.assertFalse(d['response_saved'])
            self.assertEqual(len(pending(h)),1)
            with self.assertRaisesRegex(ValueError,'UNCONFIRMED'):await b.handle_async_request(request())
            self.assertEqual(h.store.remaining(),before);self.assertEqual(len(sent),1)
            await b.aclose()
        asyncio.run(exercise())

    def test_complete_saved_response_replays_without_new_charge(self):
        h=cold_host();sent=[];p=state(h)['pilot']['provider']
        def respond(request):sent.append(request);return httpx.Response(200,json=reply('stop'))
        b=LiveBoundary(h,httpx.MockTransport(respond))
        request=lambda:httpx.Request('POST',p['base_url']+'/chat/completions',json=wire(h))
        async def exercise():
            first=await b.handle_async_request(request());before=h.store.remaining()
            self.assertEqual((await b.handle_async_request(request())).content,first.content)
            self.assertEqual(h.store.remaining(),before);self.assertEqual(len(sent),1)
            b.consumed();self.assertNotIn('unconsumed_response',state(h)['pilot'])
            await b.aclose()
        asyncio.run(exercise())


if __name__=='__main__':unittest.main()
