"""Three offline checks. Mock Provider decisions/usage are fixtures, not evidence."""
import asyncio
import gc
import json
import os
import shutil
import unittest
from unittest.mock import patch
from uuid import uuid4

import httpx
from tests.research import agent_math_decision_probe as probe
from tools.state_io import read


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.out = probe.ROOT / 'runs' / ('probe-fixture-' + uuid4().hex)
        self.summary = self.out.parent / (self.out.name + '-summary.json')
        self.summary_patch = patch.object(probe, 'SUMMARY', self.summary)
        self.summary_patch.start()
        self.addCleanup(self.cleanup)

    def cleanup(self):
        self.summary_patch.stop()
        gc.collect()
        assert self.out.resolve().parent == (probe.ROOT / 'runs').resolve()
        if self.out.exists():
            shutil.rmtree(self.out)
        self.summary.unlink(missing_ok=True)

    def test_pairs_have_only_evidence_difference_and_no_future_or_rubric(self):
        frozen = probe.freeze(self.out)
        schema = probe.decision_schema()
        self.assertNotIn('revise_selection', schema['properties'])
        self.assertNotIn('revise_selection', schema['$defs']['ResearchDecision']['properties'])
        self.assertFalse(schema['additionalProperties'])
        data = frozen['cases']
        for case in data['cases']:
            for turn in (1, 2):
                b = probe.wire(frozen['provider'], data, case, 'baseline', turn)
                e = probe.wire(frozen['provider'], data, case, 'evidence', turn)
                bp = json.loads(b['messages'][-1]['content'])
                ep = json.loads(e['messages'][-1]['content'])
                self.assertEqual(ep.pop('diagnostic_evidence'), data['cases'][case]['evidence'])
                self.assertEqual(bp.pop('diagnostic_evidence'), [])
                self.assertEqual(bp, ep)
                b['messages'][-1] = e['messages'][-1] = {'content': 'compared above'}
                self.assertEqual(b, e)
                text = json.dumps(probe.wire(frozen['provider'], data, case, 'evidence', turn))
                self.assertNotIn('rubric_offline_only', text)
                self.assertNotIn('sources_offline_only', text)
                self.assertNotIn('.md', text)
                if turn == 1:
                    self.assertNotIn('new_observations', bp)
                    for future in data['cases'][case]['round2']:
                        self.assertNotIn('"' + future['id'] + '"', text)
                    self.assertNotIn('-0.050734', text)
                    self.assertNotIn('0.022752409', text)
        actual = read(probe.ROOT / 'evidence/mujoco_reoptimized_structure/summary.json')['results']
        rows = list(actual.values())
        st = data['cases']['structure']
        self.assertEqual(st['common'][0]['values']['J'], [r['fixed']['signed_maximum_excess'] for r in rows])
        self.assertEqual(st['round2'][0]['raw_values']['J'], [r['warm']['best']['signed_maximum_excess'] for r in rows])

    def test_c3_template_reuses_packet_and_cannot_inherit_prior_approval(self):
        template=probe.ROOT/'tests/research/fixtures/c3_math_decision_template.json'
        frozen=probe.freeze(self.out,cases_path=template)
        self.assertEqual(frozen['request_ceiling'],4)
        self.assertTrue(frozen['authorization'].startswith('PENDING_EXPLICIT_APPROVAL'))
        a=probe.packet(frozen['cases'],'c3_next_decision','baseline',1)
        b=probe.packet(frozen['cases'],'c3_next_decision','evidence',1)
        a.pop('diagnostic_evidence');b.pop('diagnostic_evidence');self.assertEqual(a,b)
        with self.assertRaisesRegex(ValueError,'EXPLICIT_PROBE_APPROVAL'):
            asyncio.run(probe.live(self.out,test_transport=httpx.MockTransport(lambda r:(_ for _ in ()).throw(AssertionError('NO_SEND')))))
        self.assertFalse((self.out/'provider').exists())

    def test_eight_single_decisions_exact_usage_and_isolated_history_no_dispatch(self):
        probe.freeze(self.out)
        requests = []

        def respond(request):
            requests.append(json.loads(request.content))
            plan = dict(action='diagnose', hypothesis='Fixture competing mechanisms A and B',
                expected_observation='Fixture metric', weakening_observation='Fixture falsifier',
                fixed_conditions='Fixture fixed inputs', stopping_condition='Fixture budget',
                interpretation='Fixture conditional decision', decision=dict(hypothesis_id=f'fixture-{len(requests)}',
                    research_intent='DIAGNOSE', selected_method='native_dynamics_v1', requested_budget=1))
            return httpx.Response(200, json=dict(choices=[dict(finish_reason='tool_calls', message=dict(
                role='assistant', content=None, tool_calls=[dict(id=f'call-{len(requests)}', type='function',
                function=dict(name='research_plan', arguments=json.dumps(plan)))]))],
                usage=dict(prompt_tokens=10, completion_tokens=5, total_tokens=15,
                           prompt_cache_hit_tokens=2, prompt_cache_miss_tokens=8,
                           completion_tokens_details=dict(reasoning_tokens=3))))

        with patch.dict(os.environ, DEEPSEEK_API_KEY='offline-fixture'), \
             patch('tools.research.core.dispatch', side_effect=AssertionError('NO_SCIENCE')) as dispatch:
            result = asyncio.run(probe.live(self.out, test_transport=httpx.MockTransport(respond)))
        self.assertEqual(len(requests), 8)
        self.assertEqual(result['usage']['total_tokens'], 120)
        self.assertEqual(result['usage']['reasoning_tokens'], 24)
        self.assertEqual(result['provider_ledger']['used']['model_calls'], 8)
        self.assertEqual(result['provider_ledger']['used']['backend_solves'], 0)
        self.assertEqual(result['provider_ledger']['used']['worker_calls'], 0)
        self.assertTrue(all(r['schema_check'] == 'passed' for r in result['results']))
        dispatch.assert_not_called()
        for second, own_first, other_first in ((2, 1, 2), (3, 2, 1), (6, 5, 6), (7, 6, 5)):
            messages = json.dumps(requests[second]['messages'])
            self.assertIn(f'fixture-{own_first}', messages)
            self.assertNotIn(f'fixture-{other_first}', messages)
        with self.assertRaises(ValueError):
            probe.parse(dict(content='unstructured fixture without a tool call'))
        self.assertIsNone(result['money'])

    def test_unknown_outcome_stops_and_existing_attempt_cannot_resend(self):
        probe.freeze(self.out)
        attempts = []

        def fail(request):
            attempts.append(request)
            raise httpx.ReadError('offline fixture unknown outcome')

        with patch.dict(os.environ, DEEPSEEK_API_KEY='offline-fixture'):
            with self.assertRaises(httpx.ReadError):
                asyncio.run(probe.live(self.out, test_transport=httpx.MockTransport(fail)))
            with self.assertRaisesRegex(ValueError, 'NO_AUTOMATIC_RESEND'):
                asyncio.run(probe.live(self.out, test_transport=httpx.MockTransport(fail)))
        result = read(self.summary)
        self.assertEqual(len(attempts), 1)
        self.assertEqual(result['actual_requests'], 1)
        self.assertEqual(result['confirmed_responses'], 0)
        self.assertEqual(result['provider_ledger']['occupied']['provider_request'], 1)
        self.assertIsNone(result['usage']['total_tokens'])

    def test_c3_rounds_share_twelve_request_cap_and_never_dispatch(self):
        from types import SimpleNamespace
        from tools.platform_store import Store
        from tools.state_io import atomic_json
        provider=read(probe.ROOT/'configs/research/runtime_c3_ab.json')['provider']
        self.out.mkdir(parents=True)
        order=[(c,a) for c in ('A','B','C') for a in probe.C3_ARMS]
        atomic_json(self.out/'frozen.json',dict(offline_passed=True,scope=probe.C3_SCOPE,
            authorization='EXPLICIT OFFLINE MOCK ONLY',provider=provider,order=order))
        for case,arm in order:
            atomic_json(self.out/f'{case}-{arm}.json',dict(handoff_wire=dict(model=provider['model'],
                tools=[],messages=[dict(role='system',content='Explicit mock fixture'),dict(role='user',content='No scientific facts')])) )
        sends=[]
        def respond(request):
            sends.append(request)
            return httpx.Response(200,json=dict(choices=[dict(finish_reason='stop',message=dict(
                role='assistant',content='Mock decision only'))],usage=dict(prompt_tokens=1,completion_tokens=1,total_tokens=2)))
        def feedback(case,arm,output,tool_input):atomic_json(output,[])
        project_config=probe.ProjectConfig
        def isolated_grant(**values):
            return project_config(**{**values,'grant_id':'explicit-mock-c3-'+self.out.name})
        transport=httpx.MockTransport(respond)
        with patch.dict(os.environ,DEEPSEEK_API_KEY='offline-fixture'),\
                patch('httpx.AsyncHTTPTransport',return_value=transport),\
                patch.object(probe,'ProjectConfig',side_effect=isolated_grant),\
                patch.object(probe,'c3_boundary',side_effect=feedback),\
                patch('tools.research.core.dispatch',side_effect=AssertionError('NO_SCIENCE')) as dispatch:
            first=asyncio.run(probe.c3_live(self.out));self.assertEqual(first['actual_requests'],6)
            second=asyncio.run(probe.c3_live(self.out,True));self.assertEqual(second['actual_requests'],12)
            with self.assertRaisesRegex(ValueError,'NO_AUTOMATIC_RESEND'):asyncio.run(probe.c3_live(self.out))
            with self.assertRaisesRegex(ValueError,'FOLLOWUP_REQUIRES'):asyncio.run(probe.c3_live(self.out,True))
            host=SimpleNamespace(store=Store(self.out/'provider'),run_id='c3-agent-decision-efficiency')
            boundary=probe.LiveBoundary(host,transport)
            wire=json.loads(sends[-1].content)
            with self.assertRaisesRegex(ValueError,'PROVIDER_COUNT_EXHAUSTED'):
                asyncio.run(boundary.handle_async_request(httpx.Request('POST',provider['base_url']+'/chat/completions',json=wire)))
            self.assertEqual(len(sends),12);dispatch.assert_not_called()
        self.assertEqual(second['provider_ledger']['remaining']['model_calls'],0)
        self.assertEqual(second['provider_ledger']['used']['worker_calls'],0)

    def test_c4_unseen_boundary_denies_later_physics_without_state_writes(self):
        from copy import deepcopy
        from tests.research.c3_readiness_audit import FrozenDecisionBoundary
        protocol=read(probe.ROOT/'tests/research/fixtures/c4_decision_protocol.json')
        definition=protocol['cases']['B']
        boundary=FrozenDecisionBoundary(probe.ROOT,'B',source=(definition['folder'],definition['sequence']))
        self.addCleanup(boundary.archive.close)
        before=deepcopy(boundary.saved_state)
        packet,tools=boundary.projection()
        self.assertEqual(len(before['analysis_results']),1)
        self.assertEqual(before['physical_replays'],[])
        future=dict(artifact_id='0f87cf01869d1892043a8c52f3893c9b0b433ff305f769d2fbb3ad28a991baca',media_type='application/json')
        with self.assertRaisesRegex(ValueError,'FUTURE_OR_UNPUBLISHED_REFERENCE'):
            boundary.host.store.artifact(future)
        self.assertNotIn(future['artifact_id'],json.dumps(packet))
        self.assertEqual(boundary.host.store.session()['state'],before)
        boundary.host.store.transaction.assert_not_called()
        boundary.host.store.reserve.assert_not_called()

    def test_c4_missing_approval_stops_before_transport_or_account_creation(self):
        from tools.state_io import atomic_json
        self.out.mkdir(parents=True)
        atomic_json(self.out/'frozen.json',dict(offline_passed=True,protocol={},
            scope=probe.C3_SCOPE.replace('C3 is','C4 is')))
        with patch.object(probe,'LiveBoundary') as transport,patch.object(probe,'Store') as store:
            with self.assertRaisesRegex(ValueError,'C4_EXPLICIT_EGRESS_APPROVAL_REQUIRED'):
                asyncio.run(probe.c3_live(self.out))
            transport.assert_not_called();store.assert_not_called()

    def test_probe_preserves_production_unsupported_setting_feedback(self):
        from tools.state_io import atomic_json
        from tests.research.c3_readiness_audit import FrozenDecisionBoundary,c3_frozen_audit
        boundary=FrozenDecisionBoundary(probe.ROOT,'B',source=('b3_t2_pilot_050_c',354))
        self.addCleanup(boundary.archive.close)
        candidate=list(boundary.saved_state['candidates'].values())[-1]
        request=dict(candidate=candidate,operation='mujoco_direct_control_v1',model_source='mujoco',
            protocol=boundary.saved_state['spec']['analysis_protocol'],
            control_optimization=dict(source=boundary.saved_state['control_initializations'][-1]['source'],
                settings=dict(version='local_control_search_v2',knots_s=[0.,.5],
                    correction_window_s=[0.,.5],regularization=.000001)))
        self.out.mkdir(parents=True)
        uses=self.out/'uses.json';feedback=self.out/'feedback.json'
        atomic_json(uses,[dict(id='fixture-native-setting',function=dict(name='research_analysis',arguments=json.dumps(request)))])
        c3_frozen_audit(probe.ROOT,'B',feedback,uses,source=('b3_t2_pilot_050_c',354))
        result=read(feedback)[0]
        self.assertEqual(result['status'],'error')
        self.assertEqual(result['result']['field'],'control_optimization.settings.regularization')
        self.assertIn('regularization is not supported',result['result']['expected'])
        self.assertFalse(result['result']['scientific_execution_started'])


if __name__ == '__main__':
    unittest.main()
