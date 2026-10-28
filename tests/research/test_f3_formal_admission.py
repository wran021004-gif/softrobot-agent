"""Offline admission regressions; real Store/SDK, mock HTTP, no science worker."""
import asyncio
from copy import deepcopy
import json
import os
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import httpx
from tools.research.agent import LiveBoundary, pause_completed_invocation, converse
from tools.research.config import ROOT, resolve
from tools.research.core import read_evidence
from tools.research.research_context import public_prior_manifest
from tools.research.state import state, update, require_authorization, save
from tools.state_io import digest
from extensions.tendon_family.family_space import decision_summary
from tests.research.test_s125_contract import cold_host
from tests.research.test_s127_session_recovery import factory, complete, response


class FormalAdmissionTests(unittest.TestCase):
    def test_declared_domain_and_defaults_are_preserved(self):
        spec=resolve(ROOT/'configs/research/study_f3_pending.json')
        original=resolve(ROOT/'configs/research/study_s125_cold.json')
        for key in ('canonical_task','canonical_task_identity','family_space','family_space_identity'):
            self.assertEqual(spec[key],original[key])
        before=deepcopy(spec['family_space']);ref={'artifact_id':'a'*64}
        view=decision_summary(before,ref,{})
        self.assertEqual(view['declared_domain']['tendon_count_bounds'],[1,12])
        self.assertEqual(view['executable_domain']['tendon_count_bounds'],[1,7])
        self.assertEqual(view['currently_unavailable']['tendon_counts'],[8,9,10,11,12])
        self.assertEqual(view['declared_domain']['segment_count_bounds'],[1,9])
        self.assertEqual(view['domain_detail_query'],dict(reference=ref,view='full'))
        self.assertEqual(spec['family_space'],before)
        for key in ('segment_domain','tendon_domains','routing_domains'):
            self.assertIn(key,view)

    def test_finite_authorized_counts_and_empty_history_resolve(self):
        s=resolve(ROOT/'configs/research/study_f3_pending.json')
        b=s['budgets']
        self.assertEqual({k:b[k] for k in ('provider_requests','protected_provider_requests',
            'public_operations','protected_public_operations','physical_launches','mathematical_evaluations',
            'offline_nlp','bdf_replays')},dict(provider_requests=128,protected_provider_requests=8,
            public_operations=400,protected_public_operations=20,physical_launches=80,
            mathematical_evaluations=64,offline_nlp=2,bdf_replays=2))
        self.assertEqual(s['nmpc_limits']['executions'],6)
        self.assertEqual(s['rl_limits']['training_stages'],2)
        self.assertEqual(s['rl_limits']['training_actions'],262144)
        self.assertEqual(s['rl_limits']['evaluation_episodes'],2)
        self.assertEqual(s['supplied_evidence'],[])
        for key in ('history','mathematics','control_seeds'):
            self.assertEqual(s['research_decisions'][key],[])
        self.assertTrue(s['authorization'].startswith('PENDING_EXPLICIT_APPROVAL:'))

    def test_prior_manifest_is_content_addressed_readable_and_has_no_observations(self):
        h=cold_host();s=state(h);ref=s['public_prior_manifest']
        manifest=read_evidence(h,dict(reference=ref))
        self.assertEqual(manifest,public_prior_manifest(s['spec']))
        self.assertEqual(manifest['content_identity'],digest(manifest['contents']))
        self.assertEqual(manifest['contents']['family_space'],s['spec']['family_space'])
        self.assertEqual(manifest['contents']['task'],s['spec']['canonical_task'])
        for key in ('candidates','results','research_history','research_mathematics','control_initializations'):
            self.assertFalse(s.get(key))
        manifest['contents']['family_space']['tendon_count_bounds']=[1,1]
        self.assertEqual(h.store.artifact(ref)['contents']['family_space']['tendon_count_bounds'],[1,12])

    def test_approval_must_bind_current_resolved_identity_and_study(self):
        h=cold_host();s=state(h);spec=deepcopy(s['spec'])
        spec['authorization']='PENDING_EXPLICIT_APPROVAL: offline approval contract'
        update(h,spec=spec)
        def approve(scope,scope_identity=None):
            ref=save(h,dict(user_approval=True,scope=scope,
                scope_identity=scope_identity or digest(scope)),'synthetic_approval_fixture')
            with h.store.transaction() as db:
                h.store.event(db,h.run_id,'formal_study_authorization','approved',outputs=[ref])
        scope=dict(study_id=h.run_id,resolved_identity='wrong')
        approve(scope)
        with self.assertRaisesRegex(ValueError,'INDEPENDENT_FORMAL_STUDY_APPROVAL_REQUIRED'):
            require_authorization(h)
        scope['resolved_identity']=spec['resolved_identity'];approve(scope,'invalid digest')
        with self.assertRaises(ValueError):require_authorization(h)
        approve(scope);require_authorization(h)

    def test_pause_waits_for_durable_invocation_and_preserves_ledger(self):
        async def run():
            h=cold_host();transport=LiveBoundary(h,httpx.MockTransport(response))
            agent=factory(h,transport)()
            try:
                await complete(h,agent,'Offline complete invocation fixture')
                before=deepcopy(state(h));ledger=h.store.remaining()
                await pause_completed_invocation(h,agent,1)
                self.assertEqual(state(h),before)
                self.assertEqual(h.store.remaining(),ledger)
                self.assertEqual(h.store.events(h.run_id)[-1]['kind'],'supervisor_pause')
                update(h,pending=dict(kind='offline-active-worker'))
                with self.assertRaisesRegex(ValueError,'PENDING_FEEDBACK_OR_EXECUTION'):
                    await pause_completed_invocation(h,agent,1)
                update(h,pending=None)
                with patch('tools.research.reporter.current_reports',return_value=[({},dict(interpretation_status='deferred'))]):
                    with self.assertRaisesRegex(ValueError,'REPORTER_DELIVERY_REQUIRED'):
                        await pause_completed_invocation(h,agent,1)
                pilot=deepcopy(state(h)['pilot']);pilot['unconsumed_response']='offline-response'
                update(h,pilot=pilot)
                with self.assertRaises(ValueError):await pause_completed_invocation(h,agent,1)
            finally:await transport.aclose()
        asyncio.run(run())

    def test_invalid_pause_count_never_reaches_authorization_or_provider(self):
        for value in (0,-1,True,1.5):
            with self.assertRaisesRegex(ValueError,'POSITIVE_COMPLETED_INVOCATION_COUNT_REQUIRED'):
                asyncio.run(converse(SimpleNamespace(),pause_after_completed_invocations=value))

    def test_converse_pauses_after_feedback_is_consumed_without_new_invocation(self):
        h=cold_host();update(h,freeze='offline-fixture');sent=[]
        def respond(request):
            wire=json.loads(request.content);sent.append(wire)
            if len(sent)==1:
                return httpx.Response(200,json=dict(id='offline-read',object='chat.completion',created=1,
                    model=wire['model'],usage=dict(prompt_tokens=10,completion_tokens=2,total_tokens=12),
                    choices=[dict(index=0,finish_reason='tool_calls',message=dict(role='assistant',content=None,
                        tool_calls=[dict(id='read-priors',type='function',function=dict(name='evidence_read',
                            arguments=json.dumps(dict(reference=state(h)['public_prior_manifest'],view='full'))))]))]))
            self.assertTrue(any(m['role']=='tool' for m in wire['messages']))
            return response(request)
        with patch('tools.research.provider.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}),\
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'),\
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)):
            asyncio.run(converse(h,pause_after_completed_invocations=1))
        self.assertEqual(len(sent),2)
        self.assertEqual(state(h)['research_status'],'ready')
        self.assertEqual(h.store.remaining()['used']['model_calls'],2)
        events=h.store.events(h.run_id)
        self.assertEqual(sum(e['kind']=='model_original_turn' for e in events),1)
        self.assertEqual(events[-1]['kind'],'supervisor_pause')
        self.assertFalse(state(h)['pilot'].get('unconsumed_response'))
        self.assertIsNotNone(h.store.lookup(h.run_id,'native-read-priors')['receipt'])


if __name__=='__main__':unittest.main()
