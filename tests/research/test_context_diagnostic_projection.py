"""Generic L0 diagnostic deduplication and local capacity errors; synthetic fixtures."""
import asyncio
import json
from copy import deepcopy
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
import httpx
from openai import APIConnectionError
from tools.research.research_context import compact_result_diagnostics
from tools.research.provider import live_model_class,LiveBoundary,request_settings
from tools.research.provider_context import ProviderCapacityError,capacity_estimate
from tools.research.object_choices import main_packet


def fixture():
    ref=dict(artifact_id='a'*64,media_type='application/json')
    rows=[dict(constraint_id=name,signal='synthetic_observation',observed_value=value,bound=.006,
        bound_type='lower',unit='m',passed=passed,signed_violation=violation,time_window=[1.,2.],
        observable=dict(synthetic_tendons=[dict(channel='one',low=0.,high=.1,classification='fixture')]),
        missing_reason='synthetic_missing' if value is None else None,
        source=dict(reference=ref,pointer='/synthetic/'+name))
        for name,value,passed,violation in [('measured',.007,True,-.001),('missing',None,None,None)]]
    q=dict(validity='incomplete',reason='synthetic_missing_dense_grid',category='fixture',
        measurements=[dict(load_condition='case',stage='tail',window_s=[1.,2.],frozen_qualification_coverage=False,
            measurements=dict(speed=dict(value=.001,threshold=.002,passed=True,unit='m/s')),
            qualification=dict(checks=dict(speed=True)),source=dict(reference=ref,pointer='/synthetic/qualification'))],
        failed_qualifications=[],new_physics_steps=0)
    diagnosis=dict(source=dict(reference=ref,pointer='/synthetic/gap'),conditions=[dict(condition_id='case',observations=rows)],
        qualification=q,diagnostic_status='partial',formal_task_gap=dict(comparable=False,value=None),
        comparable=False,valid_complete=False,coverage=dict(expected=3,measured=2),hard_gate_status='unknown',
        maximum_normalized_violation=None,diagnostic_maximum_normalized_violation=None,
        diagnostic_worst_constraints=[deepcopy(rows[0])]*20,
        detail_query=dict(reference=ref,view='working_set',pointer='/task_diagnosis'),
        numerical_qualification_query=dict(reference=ref,view='working_set',pointer='/numerical_qualification'))
    return dict(task_diagnosis=diagnosis,structure_research=dict(qualification_diagnosis=deepcopy(q)),cost=dict(physics_steps=123))


class ContextDiagnosticProjection(unittest.TestCase):
    def test_all_component_facts_unknowns_and_qualifications_survive_without_mutation(self):
        value=fixture();before=deepcopy(value);compact=compact_result_diagnostics(value)
        self.assertEqual(value,before);self.assertEqual(compact_result_diagnostics(compact),compact)
        source=before['task_diagnosis'];target=compact['task_diagnosis']
        for key in ('formal_task_gap','comparable','valid_complete','coverage','hard_gate_status','detail_query'):
            self.assertEqual(target[key],source[key])
        for old,new in zip(source['conditions'][0]['observations'],target['conditions'][0]['observations']):
            for key in ('constraint_id','signal','observed_value','bound','unit','passed','time_window','observable'):
                self.assertEqual(old[key],new[key])
            self.assertEqual(new['source_pointer'],old['source']['pointer'])
        for old,new in zip(source['qualification']['measurements'],target['qualification']['measurements']):
            self.assertEqual(new,{k:v for k,v in old.items() if k not in ('source','qualification')})
        self.assertEqual(compact['structure_research']['qualification_diagnosis']['facts_at'],'task_diagnosis.qualification')
        self.assertEqual(compact['cost'],before['cost'])

    def test_different_qualifications_and_non_diagnostic_results_are_not_conflated(self):
        value=fixture();value['structure_research']['qualification_diagnosis']['reason']='different_source'
        compact=compact_result_diagnostics(value)
        self.assertEqual(compact['structure_research'],value['structure_research'])
        plain=dict(status='computed',value=1.,fixture=True)
        self.assertEqual(compact_result_diagnostics(plain),plain)

    def test_pending_exact_certificate_feedback_is_not_compacted_or_given_credit(self):
        body=json.dumps(dict(complete_acceptance_view=True,synthetic_values=list(range(1000)),formal_read_credit=False))
        delivery=dict(items=[dict(tool='evidence_read',status='success',preserve_once=True,
            result=dict(status='success',content=[dict(text=body)]))])
        packet=dict(research=dict(verified_facts=[dict(result_reference='fixture',mathematics=fixture())],
            tool_continuation=dict(pending_feedback=delivery),
            research_trace=dict(recent=[dict(observed_facts=dict(results=[dict(reference='fixture',**fixture())]))])))
        before=deepcopy(packet)
        with patch('tools.research.object_choices.state',return_value={'spec':{}}),\
                patch('tools.research.object_choices.main_projection',side_effect=lambda host,value:value):
            result=main_packet(Mock(),packet)
        self.assertEqual(result['research']['tool_continuation']['pending_feedback'],delivery)
        trace=result['research']['research_trace']['recent'][0]['observed_facts']['results'][0]['task_diagnosis']
        self.assertEqual(len(trace['metrics']),2)
        self.assertEqual(trace['metrics'][1]['value'],None)
        self.assertEqual(trace['detail_query'],fixture()['task_diagnosis']['detail_query'])
        self.assertNotIn('conditions',trace)
        self.assertEqual(packet,before)

    def test_sdk_connection_wrapper_exposes_the_original_local_capacity_error(self):
        class WrappedModel:
            async def stream(self,*args,**kwargs):
                try:raise ProviderCapacityError('R3_CONTEXT_CAPACITY_EXCEEDED_CONSERVATIVE_UTF8_ESTIMATE')
                except ProviderCapacityError as exc:raise APIConnectionError(request=httpx.Request('POST','https://fixture.invalid')) from exc
                yield  # pragma: no cover
        boundary=SimpleNamespace(host=Mock(),require_complete=Mock(),consumed=Mock())
        with patch('tools.research.provider.pilot',return_value={'provider':{}}),patch('tools.research.provider.model_type',return_value=WrappedModel):
            model=live_model_class(boundary)()
            async def invoke():
                async for _ in model.stream():pass
            with self.assertRaisesRegex(ProviderCapacityError,'CONSERVATIVE_UTF8'):
                asyncio.run(invoke())
        boundary.consumed.assert_not_called()

    def test_capacity_rejection_does_not_send_or_charge(self):
        p=dict(adapter='chatgpt_gateway',base_url='https://fixture.invalid/v1',model='fixture',reasoning='medium',max_tokens=None,
            model_capabilities=dict(verification='account_verified'),context_guard=dict(context_limit_tokens=100,framing_headroom_tokens=10))
        host=SimpleNamespace(run_id='fixture',store=Mock());host.store.session.return_value={'state':{'spec':{}}}
        wire={**request_settings(p),'messages':[dict(role='user',content='Synthetic oversized context')]}
        sends=[]
        with patch('tools.research.provider.pilot',return_value={'provider':p}),patch('tools.research.provider.pending',return_value=[]),\
                patch('tools.research.config.role_provider',return_value=p):
            boundary=LiveBoundary(host,transport=httpx.MockTransport(lambda request:sends.append(request)))
            with self.assertRaises(ProviderCapacityError):
                asyncio.run(boundary.handle_async_request(httpx.Request('POST',p['base_url']+'/chat/completions',json=wire)))
        self.assertFalse(sends);host.store.reserve.assert_not_called();host.store.transaction.assert_not_called()


if __name__=='__main__':unittest.main()
