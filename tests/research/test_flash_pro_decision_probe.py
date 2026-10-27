"""One mock-HTTP Harness/ledger check; usage below is synthetic, not real cost."""
import asyncio
import json
import unittest
from unittest.mock import patch

import httpx

from tests.research import flash_pro_decision_probe as probe
from tests.research.test_cross_task_integration import fixture_directory, plan


class ProviderProbeTests(unittest.TestCase):
    def test_route_freeze_reuses_public_scalar_owners_and_twentyfour_request_cap(self):
        with fixture_directory() as folder:
            frozen=probe.freeze_routes(folder)
            protocol=frozen['protocol']
            self.assertLessEqual(frozen['prior_actual_requests']+len(frozen['cases'])*len(protocol['models'])*protocol['requests_per_case_model'],24)
            self.assertEqual(protocol['science_workers'],0)
            c=probe.read(probe.ROOT/'evidence/integration_research_next/c4_closeout_review.json')
            case=frozen['cases']['fixed_control_stagnation']['evidence']
            self.assertEqual(case['best_metrics'],c['best_metrics'])
            self.assertEqual(case['attempted']['structural_searches'],0)
            math=frozen['cases']['math_without_physics']['evidence']
            self.assertEqual(frozen['cases']['math_without_physics']['task']['timing']['duration_s'],math['native_prediction']['horizon_s'])
            self.assertGreater(math['native_prediction']['baseline_signed_maximum_excess'],math['native_prediction']['best_signed_maximum_excess'])
            self.assertIn('unmeasured',math['independent_task_acceptance'])
            wire=json.dumps(frozen['cases'])
            for private in ('owner_store','control_schedule_reference','tensions_n','DEEPSEEK_API_KEY'):
                self.assertNotIn(private,wire)
            self.assertEqual(probe.freeze_routes(folder),frozen)

    def test_original_harness_schema_and_ledger_never_dispatch_science(self):
        frozen=probe.freeze()
        calls=[]
        def reply(request):
            wire=json.loads(request.content);calls.append(wire)
            evidence=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']=='evidence_read')
            self.assertEqual(set(evidence['properties']['view']['enum']),{'full','summary','fields','range'})
            schema=next(t['function']['parameters'] for t in wire['tools'] if t['function']['name']=='research_plan')
            self.assertNotIn('control_seed',schema['properties'])
            content=wire['messages'][1]['content']
            packet=json.loads(content if isinstance(content,str) else ''.join(b.get('text','') for b in content))
            self.assertEqual(packet['evidence'],frozen['cases']['bf6_incomplete']['evidence'])
            message=dict(role='assistant',content='Incomplete does not establish a pass.')
            if len(calls)<=2:
                value={k:v for k,v in plan('diagnose').items() if k in schema['properties']}
                if len(calls)==1:value=dict(plan=value)
                else:
                    feedback=next(m['content'] for m in wire['messages'] if m['role']=='tool')
                    if not isinstance(feedback,str):feedback=''.join(b.get('text','') for b in feedback)
                    self.assertIn('reason',json.loads(feedback))
                message.update(content=None,tool_calls=[dict(id='fixture-plan-'+str(len(calls)),type='function',
                    function=dict(name='research_plan',arguments=json.dumps(value)))])
            return httpx.Response(200,json=dict(id='mock-provider-only',object='chat.completion',created=1,
                model=wire['model'],choices=[dict(index=0,finish_reason='tool_calls' if len(calls)<=2 else 'stop',message=message)],
                usage=dict(prompt_tokens=10,completion_tokens=3,total_tokens=13)))
        with fixture_directory() as folder,patch('tools.service_execution._run_contained',side_effect=AssertionError('NO_WORKER')),patch(
                'tools.research.core.dispatch',side_effect=AssertionError('NO_SCIENTIFIC_DISPATCH')):
            result=asyncio.run(probe.run_case(folder,frozen,'bf6_incomplete','deepseek-flash',httpx.MockTransport(reply)))
            self.assertEqual(result['termination'],'completed')
            self.assertEqual(result['actual_requests'],3)
            self.assertEqual(result['usage']['total_tokens'],39)
            self.assertEqual(result['tool_checks'][0]['contract'],'rejected')
            self.assertEqual(result['accepted_decisions'],1)
            self.assertEqual(result['first_valid_decision_request'],2)
            self.assertTrue(result['final_answer_present'])
            self.assertEqual(result['scientific_workers'],0)
            self.assertEqual(result['provider_ledger']['used']['backend_solves'],0)
            self.assertEqual(result['provider_ledger']['used']['worker_calls'],0)


if __name__=='__main__':unittest.main()
