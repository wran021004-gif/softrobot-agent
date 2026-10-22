"""Focused zero-science production-entry regression; all HTTP is synthetic."""
import asyncio
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import httpx
from tests.research import f30_provider_check as check
from tools.research import agent, core, reporter
from tools.research.budget import protected, science_fits, closeout_operations
from tools.research.config import resolve
from tools.research.state import state, update
from tools.state_io import atomic_json


class F30Tests(unittest.TestCase):
    def test_production_delivery_reopens_with_zero_science(self):
        original=check.ROOT/'runs/research'/check.SEALED_ID
        def hashes():
            return {str(p.relative_to(original)):hashlib.sha256(p.read_bytes()).hexdigest()
                for p in original.rglob('*') if p.is_file()}
        before=hashes()
        with patch.object(reporter,'read_evidence',wraps=core.read_evidence) as reads:
            result=asyncio.run(check.run())
        self.assertIsNone(result['execution_error'])
        self.assertTrue(result['technical_checks_passed'],result)
        self.assertEqual(result['ledger']['used']['model_calls'],3)
        self.assertEqual(result['ledger']['used']['tool_calls'],1)
        self.assertEqual([r['purpose'] for r in result['requests']],['conversation','reporter','conversation'])
        self.assertTrue(result['study_id'].startswith('f30-revalidate-offline-'))
        self.assertEqual(result['scientific_admission'],'not_admitted_offline_fixture')
        self.assertFalse(result['f3_started'])
        h=check.Host(check.ROOT/'runs/research'/result['study_id'],result['study_id'],actor='unified-research')
        scope=check.read(h.store.root/'scope.json')
        self.assertEqual(scope['revalidation_scope']['proposed_study_id'],check.LIVE_ID)
        self.assertEqual(scope['revalidation_scope']['proposed_store'],'runs/research/'+check.LIVE_ID)
        self.assertEqual(scope['revalidation_scope']['request_limits'],dict(main=2,reporter=1,total=3))
        self.assertIsNone(scope['approved_commit'])
        self.assertEqual(result['ledger']['limit']['model_calls'],3)
        self.assertEqual(result['ledger']['limit']['worker_calls'],0)
        self.assertEqual(result['ledger']['limit']['backend_solves'],0)
        request=next(r for r in result['requests'] if r['purpose']=='reporter')
        wire=h.store.artifact(request['request_reference'])
        catalog=json.loads(wire['messages'][-1]['content'])['source_catalog']
        self.assertTrue(catalog)
        for source in catalog.values():
            self.assertTrue(any(call.args[1]==source and call.kwargs.get('record_read') is False
                for call in reads.call_args_list))
        self.assertNotIn('/trajectory/score_semantics',[s['pointer'] for s in catalog.values()])
        self.assertEqual(hashes(),before)

    def test_new_live_identity_requires_approved_commit_and_cannot_reset(self):
        self.assertEqual(check.LIVE_ID,'f30-revalidate-20261022-01')
        self.assertNotEqual(check.LIVE_ID,check.SEALED_ID)
        self.assertFalse((check.ROOT/'runs/research'/check.LIVE_ID).exists())
        for approved in (None,'0'*40):
            with self.assertRaisesRegex(ValueError,'EXPLICIT_APPROVED_COMMIT'):
                check.prepare(True,approved_commit=approved)
        with patch.object(Path,'exists',return_value=True):
            with self.assertRaisesRegex(ValueError,'SINGLE_ATTEMPT_ALREADY_EXISTS'):
                check.prepare(True,approved_commit='0'*40)
        with self.assertRaisesRegex(ValueError,'SEALED_HISTORY_READ_ONLY'):check.audit(check.SEALED_ID)
        self.assertFalse((check.ROOT/'runs/research'/check.LIVE_ID).exists())

    def test_saved_source_id_response_recovers_at_reporter_cap_without_send(self):
        from tests.research.test_s129_agent_reporting import reporter_response
        h,refs=check.prepare()
        result=reporter.investigate(h,dict(question='Offline recovery fixture',references=refs))
        ref=result['report_reference'];wire=reporter._wire(h,ref,h.store.artifact(ref))
        catalog=json.loads(wire['messages'][-1]['content'])['source_catalog']
        boundary=check.CappedBoundary(h,httpx.MockTransport(reporter_response));boundary.purpose='reporter'
        async def exercise():
            await boundary.handle_async_request(httpx.Request('POST',state(h)['pilot']['provider']['base_url']+'/chat/completions',json=wire))
            before=h.store.remaining()
            with patch('tools.research.agent.LiveBoundary',check.CappedBoundary):
                await reporter.complete_reports(h,httpx.MockTransport(lambda r:self.fail('Must replay original response')),recover_only=True)
            self.assertEqual(h.store.remaining(),before)
        asyncio.run(exercise())
        saved=reporter.entries(h)[-1][1]
        self.assertEqual(saved['interpretation_status'],'available')
        self.assertEqual(saved['report']['interpretations'][0]['sources'],[catalog[next(iter(catalog))]])
        self.assertNotIn('unconsumed_response',state(h)['pilot'])
        self.assertEqual(reporter.provider_usage(h)['reporter']['requests'],1)

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
        for role,count,error in (('conversation',2,'ROLE_CAP_NO_SEND'),('reporter',1,'ROLE_CAP_NO_SEND'),
                ('conversation',1,'ACCEPTED_REPORTER_REQUIRED_NO_SEND')):
            with self.subTest(role=role,count=count):
                h,_=check.prepare()
                for i in range(count):
                    with h.store.transaction() as db:
                        ref=h.store.put(db,dict(purpose=role,input_bytes=0))
                        h.store.event(db,h.run_id,'r3_request','sent',request='offline-request-'+str(i),outputs=[ref])
                before=h.store.remaining()
                boundary=check.CappedBoundary(h,httpx.MockTransport(lambda request:self.fail('Must not send')))
                boundary.purpose=role
                with self.assertRaisesRegex(ValueError,error):
                    asyncio.run(boundary.handle_async_request(httpx.Request('POST','https://api.deepseek.com/chat/completions',
                        json={'tools':[{}]})))
                self.assertEqual(h.store.remaining(),before)


if __name__=='__main__':unittest.main()
