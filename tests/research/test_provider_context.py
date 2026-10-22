"""Offline capacity regressions: real tokenizer and Store, explicit HTTP fixtures."""
import asyncio
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
import httpx
from tools.research.agent import LiveBoundary, pending
from tools.research.provider_context import capacity_estimate, official_tokenizer
from tools.research.state import state, update
from tests.research.test_s127_provider_output import wire, reply
from tests.research.test_s126_checkpoint import cold_host


class ProviderContextTests(unittest.TestCase):
    def test_large_request_keeps_all_bytes_and_original_charge(self):
        h=cold_host();p=deepcopy(state(h)['pilot']);p['provider']['context_guard']['context_limit_tokens']=100000
        update(h,pilot=p);payload=wire(h);payload['messages'][0]['content']='Offline repeated input. '*10000
        sent=[]
        def respond(request):
            sent.append(request.content)
            return httpx.Response(200,json=reply('stop'))
        boundary=LiveBoundary(h,httpx.MockTransport(respond))
        async def exercise():
            request=httpx.Request('POST',p['provider']['base_url']+'/chat/completions',json=payload)
            self.assertGreater(len(request.content),100000)
            await boundary.handle_async_request(request)
            self.assertEqual(sent,[request.content]);self.assertEqual(json.loads(sent[0]),payload)
            self.assertEqual(h.store.remaining()['used']['model_calls'],1)
            event=next(e for e in h.store.events(h.run_id) if e['kind']=='r3_request')
            metadata=h.store.artifact(event['outputs'][0]);estimate=metadata['context_capacity']
            self.assertIn('official',estimate['method'])
            self.assertEqual(estimate['context_limit_tokens'],100000)
            self.assertEqual(estimate['reserved_output_tokens'],p['provider']['max_tokens'])
            boundary.consumed();await boundary.aclose()
        asyncio.run(exercise())

    def test_actual_capacity_excess_rejects_before_send_or_charge(self):
        h=cold_host();p=deepcopy(state(h)['pilot']);p['provider']['context_guard']['context_limit_tokens']=100000
        update(h,pilot=p);before=h.store.remaining();payload=wire(h)
        payload['messages'][0]['content']='0 1 2 3 '*30000
        def forbidden(request):raise AssertionError('CAPACITY_EXCESS_MUST_NOT_SEND')
        boundary=LiveBoundary(h,httpx.MockTransport(forbidden))
        async def exercise():
            with self.assertRaisesRegex(ValueError,'CONTEXT_CAPACITY'):
                await boundary.handle_async_request(httpx.Request('POST',p['provider']['base_url']+'/chat/completions',json=payload))
            self.assertEqual(h.store.remaining(),before);self.assertFalse(pending(h))
            await boundary.aclose()
        asyncio.run(exercise())

    def test_small_request_never_loads_tokenizer(self):
        provider=state(cold_host())['pilot']['provider']
        with patch('tools.research.provider_context.official_tokenizer',side_effect=AssertionError('NO_TOKENIZER_NEEDED')):
            estimate=capacity_estimate(b'{}',provider)
        self.assertEqual(estimate['input_estimate'],2)

    def test_tokenizer_tampering_blocks_capacity_refinement(self):
        official_tokenizer.cache_clear()
        try:
            with patch('tools.research.provider_context.TOKENIZER_SHA256','wrong'):
                with self.assertRaisesRegex(ValueError,'TOKENIZER_HASH_MISMATCH'):official_tokenizer()
        finally:official_tokenizer.cache_clear()


if __name__=='__main__':unittest.main()
