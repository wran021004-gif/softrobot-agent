"""Paid request phases and legacy recovery, using only real SDK/MockTransport."""
import asyncio
from copy import deepcopy
import json
import os
from uuid import uuid4
import unittest
from unittest.mock import patch
import httpx
from tools.research.config import ROOT
from tools.research.core import prepare
from tools.research.state import state, update
from tools.research.budget import provider_request_scope, protected, decision_budget
from tools.research.provider import LiveBoundary, request_settings
from tests.research.test_recent_round_tools import run_fixture


def provision():
    value=json.loads((ROOT/'configs/research/study_harness_v2.json').read_text(encoding='utf8'))
    value['study_id']='p5-mock-'+uuid4().hex[:8]
    value['authorization']='Offline engineering fixture, no real Provider or scientific Worker.'
    path=ROOT/'configs/research'/('._'+value['study_id']+'.json')
    path.write_text(json.dumps(value),encoding='utf8')
    try:h=prepare(path,directory=ROOT/'runs'/value['study_id'])
    finally:path.unlink()
    s=state(h);update(h,freeze='p5-offline-fixture',pilot={**s['pilot'],
        'session_handoff_live_admitted':True,'session_handoff_boundary':'request_feedback'})
    return h


def plan(h,action):
    value=dict(action=action,hypothesis='Synthetic admission fixture; no task-performance claim.',
        expected_observation='A valid protocol receipt.',weakening_observation='Admission rejection.',
        fixed_conditions='Frozen fixture domain.',stopping_condition='No scientific Worker.',
        interpretation='Physical acceptance is unmeasured.',decision=dict(hypothesis_id='p5-mock',
            research_intent='DESIGN_MODIFICATION' if action=='generate' else 'STOP',selected_method=action))
    if action=='generate':value['generation']=dict(version='serial_family_generation_v2',
        family_space_identity=state(h)['spec']['family_space_identity'],segment_count=2,tendon_count=6)
    return value


class P5BudgetTests(unittest.TestCase):
    def test_frozen_legacy_and_new_initial_allowance(self):
        h=provision();before=state(h);view=decision_budget(h)
        self.assertEqual(view['provider_budget']['science_capable_main_requests'],5)
        self.assertFalse(view['closeout']['next_request_will_protect'])
        spec=deepcopy(before['spec']);spec['budgets'].pop('provider_reserve_policy');update(h,spec=spec)
        self.assertEqual(decision_budget(h)['provider_budget']['science_capable_main_requests'],4)
        self.assertEqual(h.store.remaining()['remaining']['model_calls'],8)

    def test_fifth_request_can_submit_and_last_three_cannot_explore_through_handoff(self):
        h=provision();reference=state(h)['family_space_reference'];generate=plan(h,'generate')
        responses=[('research_route',dict(tool='evidence_read')),
            ('evidence_read',dict(reference=reference,view='working_set',fields=['candidate_index'])),
            ('research_route',dict(tool='research_plan',action='generate')),
            ('research_route',dict(tool='evidence_read')),('research_plan',generate),
            ('research_plan',generate),
            ('evidence_read',dict(reference=reference,view='working_set',pointer='/all_fresh_results')),
            ('research_plan',plan(h,'stop'))]
        with patch.dict(os.environ,state(h)['spec']['runtime']['threads']):wires=run_fixture(h,responses,limit=8)
        self.assertEqual(len(wires),8)
        actions=lambda w:next(t['function']['parameters']['properties']['action']['enum'] for t in w['tools'] if t['function']['name']=='research_plan')
        self.assertEqual(actions(wires[4]),['generate'])
        self.assertTrue(all(actions(w)==['stop'] for w in wires[5:]))
        self.assertEqual(len(state(h)['candidates']),1)
        self.assertEqual([h.store.artifact(r)['original_plan']['action'] for r in state(h)['plans']],['generate','stop'])
        self.assertEqual(state(h)['research_status'],'stopped')
        packet=json.loads(wires[4]['messages'][-1]['content'].split('\n',1)[1])['research']
        self.assertEqual(packet['tool_continuation']['plan_selection']['status'],'selected_not_submitted')
        self.assertNotIn('action_menu',packet);self.assertNotIn('loaded_tool',packet)
        phases=[h.store.artifact(e['outputs'][0])['request_phase'] for e in h.store.events(h.run_id) if e['kind']=='r3_request']
        self.assertEqual(phases,['exploration']*5+['closeout']*3)
        self.assertEqual(h.store.remaining()['used']['model_calls'],8)
        self.assertEqual(h.store.remaining()['used']['backend_solves'],0)
        self.assertFalse(getattr(h,'_provider_request_phase',None))

    def test_reporter_shares_ledger_and_last_response_replays_without_ninth_send(self):
        h=provision();sends=[];p=state(h)['pilot']['provider']
        wire=dict(**request_settings(p),messages=[dict(role='user',content='Synthetic protocol fixture.')])
        def reply(request):
            sends.append(request)
            return httpx.Response(200,json=dict(choices=[dict(finish_reason='stop',message=dict(role='assistant',content='Fixture.'))]))
        async def run():
            boundary=LiveBoundary(h,httpx.MockTransport(reply),max_model_calls=8)
            request=httpx.Request('POST',p['base_url'].rstrip('/')+'/chat/completions',json=wire)
            for number in range(8):
                boundary.purpose='reporter' if number==4 else 'conversation'
                await boundary.handle_async_request(request)
                self.assertEqual(boundary.request_phase,'exploration' if number<5 else 'closeout')
                if number==4:
                    self.assertTrue(protected(h))
                    with provider_request_scope(h,boundary.request_phase):self.assertFalse(protected(h))
                    self.assertTrue(decision_budget(h)['closeout']['next_request_will_protect'])
                if number<7:boundary.consumed()
            restored=LiveBoundary(h,httpx.MockTransport(reply),max_model_calls=8)
            await restored.handle_async_request(request)
            self.assertEqual(restored.request_phase,'closeout');restored.consumed()
            with self.assertRaisesRegex(ValueError,'PROVIDER_REQUEST_LIMIT|COUNT_EXHAUSTED'):
                await restored.handle_async_request(request)
            await restored.aclose();await boundary.aclose()
        asyncio.run(run())
        self.assertEqual(len(sends),8)
        self.assertEqual(decision_budget(h)['provider_budget']['reporter_requests_used'],1)
        self.assertEqual(h.store.remaining()['remaining']['model_calls'],0)


if __name__=='__main__':unittest.main()
