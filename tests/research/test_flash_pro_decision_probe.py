"""One mock-HTTP Harness/ledger check; usage below is synthetic, not real cost."""
import asyncio
import json
import unittest
from unittest.mock import patch

import httpx

from tests.research import flash_pro_decision_probe as probe
from tests.research.test_cross_task_integration import fixture_directory, plan


class ProviderProbeTests(unittest.TestCase):
    def test_original_harness_schema_and_ledger_never_dispatch_science(self):
        frozen=probe.freeze()
        calls=[]
        def reply(request):
            wire=json.loads(request.content);calls.append(wire)
            message=dict(role='assistant',content='Incomplete does not establish a pass.')
            if len(calls)==1:
                message.update(content=None,tool_calls=[dict(id='fixture-plan',type='function',
                    function=dict(name='research_plan',arguments=json.dumps(plan('diagnose'))))])
            return httpx.Response(200,json=dict(id='mock-provider-only',object='chat.completion',created=1,
                model=wire['model'],choices=[dict(index=0,finish_reason='tool_calls' if len(calls)==1 else 'stop',message=message)],
                usage=dict(prompt_tokens=10,completion_tokens=3,total_tokens=13)))
        with fixture_directory() as folder,patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')),patch(
                'tools.research.core.dispatch',side_effect=AssertionError('NO_SCIENTIFIC_DISPATCH')):
            result=asyncio.run(probe.run_case(folder,frozen,'bf6_incomplete','deepseek-flash',httpx.MockTransport(reply)))
            self.assertEqual(result['termination'],'completed')
            self.assertEqual(result['actual_requests'],2)
            self.assertEqual(result['usage']['total_tokens'],26)
            self.assertEqual(result['tool_checks'][0]['contract'],'valid')
            self.assertEqual(result['scientific_workers'],0)
            self.assertEqual(result['provider_ledger']['used']['backend_solves'],0)
            self.assertEqual(result['provider_ledger']['used']['worker_calls'],0)


if __name__=='__main__':unittest.main()
