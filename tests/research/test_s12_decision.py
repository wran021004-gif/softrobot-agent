"""S12 real sealed failure regressions; no new scientific calculations."""
import unittest
import asyncio,os
from copy import deepcopy
from types import SimpleNamespace
from pathlib import Path
from unittest.mock import patch
from tools.research.research_context import tool_feedback,context,decision_brief
from tools.research.agent import plan_schema
from tools.research.state import state
from tests.research.s12_decision_probe import snapshot


class S12DecisionTests(unittest.TestCase):
    def test_actual_before_model_schema_at_budget_success_and_rl_boundaries(self):
        from tools.research.agent import converse
        from strands.hooks.events import BeforeModelCallEvent
        class Captured(Exception):pass
        for remaining,success,rl,saved in ((8,False,False,False),(5,False,False,False),(4,False,False,False),(8,True,False,False),(5,False,True,False),(5,False,False,True)):
            with self.subTest(remaining=remaining,success=success,rl=rl,saved=saved):
                h,p,values,event=snapshot(450);s=state(h)
                h.store.root=Path('runs/s12-hook-fixture');h.store.remaining.return_value['remaining']['model_calls']=remaining
                if success:s['success_gate']={'evidence':s['physical_replays'][0]}
                if rl:s['rl_runs']={'existing-fixture-job':{'evaluations':0,'allocation':{'actions':512}}}
                if saved:
                    original_event=next(e for e in reversed(h.store.events(h.run_id)) if e['kind']=='r3_request')
                    s['pilot']['unconsumed_response']=original_event['request_id']
                    original=h.store.artifact(h.store.artifact(original_event['outputs'][0])['request'])
                callbacks={};captured={}
                def build(*args,**kwargs):
                    registry={t.tool_name:t for t in kwargs['research_tools']}
                    if saved:registry['retrieve_context']=SimpleNamespace(tool_spec={})
                    agent=SimpleNamespace(tool_registry=SimpleNamespace(registry=registry),
                        hooks=SimpleNamespace(add_callback=lambda event,fn:callbacks.update({event:fn})),system_prompt='')
                    async def invoke(prompt):
                        await callbacks[BeforeModelCallEvent](SimpleNamespace(cancel=None))
                        captured.update({name:deepcopy(t.tool_spec) for name,t in registry.items()})
                        raise Captured()
                    agent.invoke_async=invoke
                    return agent
                async def no_wait(*args):pass
                with patch('tools.research.agent.build_harness',side_effect=build),patch('tools.research.core.guard'),\
                     patch('tools.research.agent.pending',return_value=[]),patch('tools.research.agent.load_credential'),\
                     patch('tools.research.agent.record'),patch('tools.research.agent.wait_training',side_effect=no_wait),\
                     patch.dict(os.environ,{'DEEPSEEK_API_KEY':'synthetic-fixture'}):
                    with self.assertRaises(Captured):asyncio.run(converse(h))
                actions=captured['research_plan']['inputSchema']['json']['properties']['action']['enum']
                if saved:
                    expected={t['function']['name']:t['function']['parameters'] for t in original['tools']}
                    self.assertEqual({k:t['inputSchema']['json'] for k,t in captured.items()},expected)
                elif remaining<=5 or success:
                    self.assertEqual(actions,['select'] if success else ['stop','select'])
                    self.assertNotIn('research_analysis',captured)
                    operations=captured['research_rl']['inputSchema']['json']['properties']['operation']['enum']
                    self.assertEqual(operations,['status','stop','evaluate'] if rl else [])
                else:self.assertIn('mechanics',actions)
                h.store.reserve.assert_not_called();h.store.transaction.assert_not_called()

    def test_cold_mathematics_available_without_eligible_warm_source(self):
        h,p,values,event=snapshot(319)
        rows=[r for r in context(h)['decision_feedback']['actions'] if r['action']=='mechanics']
        self.assertTrue(rows)
        for row in rows:
            self.assertTrue(row['task_applicable'])
            self.assertEqual(row['cold_initializations'],['constant_0_2','ramp_0_2_to_0_4'])
            self.assertEqual(row['status'],'preflight_eligible')
            self.assertEqual(row['warm_sources'],[])
            self.assertTrue(row['missing_warm_source'])

    def test_engineering_context_does_not_project_a_nonexistent_provider_send(self):
        h,p,values,event=snapshot(319)
        state(h)['spec']['mode']='engineering_numerical'
        h.store.remaining.return_value['remaining']['model_calls']=0
        self.assertIn('mechanics',context(h)['actions'])

    def test_historical_best_also_retains_exact_failure_samples(self):
        h,p,values,event=snapshot(34)
        best=decision_brief(context(h))['best_valid']
        self.assertTrue(best['historical_only'])
        self.assertFalse(best['physical_diagnostic']['task_passed'])
        self.assertTrue(best['physical_diagnostic']['critical_samples'])

    def test_wrapper_result_paths(self):
        h,p,values,event=snapshot(319)
        for result in ({'candidate':p['candidates'][0],'source':state(h)['control_initializations'][-1]['source'],'trajectory':{'fixture':True}},
                       {'accepted_stop':True,'claims':{'fixture':True}}):
            wrapper={'artifact_id':'f'*64,'media_type':'application/json'}
            with patch('tools.research.research_context.save',return_value=wrapper):
                feedback=tool_feedback(h,{'result':result,'plan':{}})
            self.assertIsNone(feedback['scientific_reference'])
            self.assertEqual(feedback['new_facts']['pointer'],'/result')
            if 'trajectory' in result:self.assertEqual(feedback['new_facts']['value']['trajectory']['read_pointer'],'/result/trajectory')

    def test_next_request_actions_use_existing_closeout(self):
        h,p,values,event=snapshot(450)
        current=context(h)
        self.assertEqual(current['actions'],['stop','select'])
        self.assertNotIn('mechanics',plan_schema(current['actions'])['properties']['action']['enum'])
        self.assertEqual(h.store.remaining()['remaining']['model_calls'],5)

    def test_fresh_failure_is_compact_measured_diagnostic(self):
        h,p,values,event=snapshot(319)
        brief=decision_brief(context(h));feedback=brief['latest_scientific_feedback']
        diagnostic=feedback['physical_diagnostic']
        self.assertFalse(diagnostic['task_passed'])
        self.assertLessEqual(len(diagnostic['critical_samples']),4)
        self.assertTrue(diagnostic['critical_samples'])
        for row in diagnostic['critical_samples']:
            raw=h.store.artifact(row['raw_reference'])
            sample=raw['samples'][int(row['read_pointer'].rsplit('/',1)[-1])]
            self.assertEqual(row['observed']['tip_m'],sample['tip_m'])
        self.assertIn('not a proven failure cause',' '.join(diagnostic['limitations']))

    def test_no_future_artifacts_or_scientific_writes(self):
        first,p,values,event=snapshot(34)
        last,q,later,_=snapshot(450)
        self.assertNotIn(state(last)['physical_replays'][0]['artifact_id'],values)
        self.assertFalse(state(first)['physical_replays'])
        with self.assertRaises(AssertionError):first.store.reserve()


if __name__=='__main__':unittest.main()
