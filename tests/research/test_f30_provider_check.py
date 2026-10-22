"""Focused zero-science production-entry regression; all HTTP is synthetic."""
import asyncio
from copy import deepcopy
import unittest

import httpx
from tests.research import f30_provider_check as check
from tools.research import agent
from tools.research.budget import protected, science_fits, closeout_operations
from tools.research.config import resolve
from tools.research.state import state, update
from tools.state_io import atomic_json


class F30Tests(unittest.TestCase):
    def test_production_delivery_reopens_with_zero_science(self):
        result=asyncio.run(check.run())
        self.assertIsNone(result['execution_error'])
        self.assertTrue(result['technical_checks_passed'],result)
        self.assertEqual(result['ledger']['used']['model_calls'],3)
        self.assertEqual(result['ledger']['used']['tool_calls'],1)
        self.assertEqual([r['purpose'] for r in result['requests']],['conversation','reporter','conversation'])

    def test_zero_science_investigation_and_formal_closeout_are_distinct(self):
        h,_=check.prepare()
        self.assertFalse(science_fits(h))
        self.assertFalse(protected(h))
        self.assertEqual(closeout_operations(h)['research_plan'],['stop'])
        spec=deepcopy(state(h)['spec']);spec['mode']='formal_research'
        update(h,spec=spec)
        self.assertTrue(protected(h))  # Existing scientific exhaustion still closes.

    def test_readonly_mode_rejects_worker_budget(self):
        h,_=check.prepare()
        raw=check.read(check.ROOT/'configs/research/study_s125_cold.json')
        raw.update(mode='engineering_investigation',capabilities=['investigation'],allowed_plan_actions=['stop'])
        path=check.ROOT/'configs/research/._f30-invalid.json'
        atomic_json(path,raw)
        try:
            with self.assertRaisesRegex(ValueError,'ZERO_SCIENCE'):resolve(path)
        finally:path.unlink()

    def test_role_ceiling_rejects_before_reservation(self):
        h,_=check.prepare()
        for i in range(2):
            with h.store.transaction() as db:
                ref=h.store.put(db,dict(purpose='conversation',input_bytes=0))
                h.store.event(db,h.run_id,'r3_request','sent',request='offline-request-'+str(i),outputs=[ref])
        before=h.store.remaining()
        boundary=check.CappedBoundary(h,httpx.MockTransport(lambda request:self.fail('Must not send')))
        with self.assertRaisesRegex(ValueError,'ROLE_CAP_NO_SEND'):
            asyncio.run(boundary.handle_async_request(httpx.Request('POST','https://api.deepseek.com/chat/completions',
                json={'tools':[{}]})))
        self.assertEqual(h.store.remaining(),before)


if __name__=='__main__':unittest.main()
