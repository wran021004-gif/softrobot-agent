"""Saved S6 decisions and provider-message regressions, without network requests."""
import unittest, json
from copy import deepcopy
from tools.research.agent import DeepSeekModel, plan_schema
from tools.research.contracts import Plan
from tests.research.s7_audit import context_comparison


class S7ContextTests(unittest.TestCase):
    def test_saved_decisions_preserve_facts_and_reduce_context(self):
        comparison=context_comparison();self.assertGreater(len(comparison['states']),2)
        self.assertTrue(all(all(r['retained_facts'].values()) for r in comparison['states']))
        self.assertGreater(sum(r['old_bytes']-r['new_bytes'] for r in comparison['states'])/sum(r['old_bytes'] for r in comparison['states']),.3)

    def test_pruned_schema_keeps_all_referenced_definitions(self):
        schema=plan_schema(['generate','initialize_control','control_search','select','stop'])
        self.assertNotIn('mechanics',schema['properties']);self.assertIn('control_seed',schema['properties'])
        def check(v):
            if isinstance(v,dict):
                if '$ref' in v:self.assertIn(v['$ref'].rsplit('/',1)[-1],schema['$defs'])
                for x in v.values():check(x)
            elif isinstance(v,list):
                for x in v:check(x)
        check(schema)

    def test_reasoning_and_tool_pairs_survive_conversion_without_mutation(self):
        messages=[dict(role='user',content=[dict(text='fixture')]),
            dict(role='assistant',content=[dict(reasoningContent=dict(reasoningText=dict(text='saved fixture reasoning'))),
                dict(toolUse=dict(toolUseId='fixture-1',name='evidence_read',input=dict(pointer='/acceptance')))]),
            dict(role='user',content=[dict(toolResult=dict(toolUseId='fixture-1',status='success',content=[dict(text='saved result')]))])]
        original=deepcopy(messages)
        wire=DeepSeekModel.format_request_messages(messages,'stable fixture instructions')
        self.assertEqual(wire[2]['reasoning_content'],'saved fixture reasoning')
        self.assertEqual(wire[2]['tool_calls'][0]['id'],wire[3]['tool_call_id'])
        self.assertEqual(messages,original)


if __name__=='__main__':unittest.main()
