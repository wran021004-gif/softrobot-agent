"""Focused readable provider-name protocol checks; no network, math or backend work."""
from copy import deepcopy
import json
from pathlib import Path
import unittest
from uuid import uuid4

from examples.platform_route import prepare
from extensions.tendon_family.route import create
from schemas.platform import ModelResponse
from tools.platform_host import Host
from tools.platform_models import (DeepSeekAdapter,READABLE_TOOL_NAMING,ReadableDeepSeekAdapter,
    ToolProtocolError,payload_for,provider_name,provider_name_map,tool_naming_policy)
from tools.platform_store import plain
from tools.state_io import read


TOOLS={'route.advance':'1.0.0','route.inspect':'1.0.0','evidence.read':'1.0.0',
    'analysis.bounded_endpoint':'1.0.0','design.build_proposal':'1.0.0','session.control':'1.0.0'}


def response(name,arguments,turn=0):
    envelope=dict(arguments=arguments,reason='Focused provider-format boundary fixture.',tool_version='1.0.0')
    call=dict(id='fixture-'+str(turn),type='function',
        function=dict(name=name,arguments=json.dumps(envelope)))
    message=dict(role='assistant',content=None,tool_calls=[call])
    return ModelResponse(raw=dict(choices=[dict(index=0,finish_reason='tool_calls',message=message)]))


class ReplayReadable(ReadableDeepSeekAdapter):
    def __init__(self,responses):self.responses=list(responses);self.payloads=[]
    def respond(self,payload,turn):self.payloads.append(deepcopy(payload));return self.responses.pop(0)


class ProviderToolNamingTests(unittest.TestCase):
    def host(self,readable):
        root=Path('runs/provider_tool_naming_checks')/uuid4().hex
        prepare(root);project=read(root/'inputs/project.json');project['budget']['model_calls']=10
        host=Host(root,'family-route');host.store.create(project)
        inp=read(root/'inputs/route.json');inp['policy']['tool_bindings']=dict(TOOLS)
        inp['policy']['model']['max_turns']=2;inp['policy']['model']['protocol_recovery']=dict(max_total=4,max_consecutive=2)
        if readable:
            inp['policy']['model']['adapter_version']='2.0.0'
            inp['policy']['model']['tool_naming']=tool_naming_policy(TOOLS)
        create(root,inp);return host

    def test_readable_round_trip_unknown_and_domain_mismatch_do_not_execute(self):
        host=self.host(True);adapter=ReadableDeepSeekAdapter();payload=payload_for(host,adapter)
        bindings=host.store.session(host.run_id)['snapshot']['input']['policy']['tool_bindings']
        names=provider_name_map(bindings,READABLE_TOOL_NAMING)
        advertised={row['function']['name']:row['function'] for row in payload['tools']}
        self.assertEqual(names['evidence.read'],'evidence_read')
        self.assertEqual(names['route.inspect'],'route_inspect')
        self.assertEqual(names['route.advance'],'route_advance')
        self.assertEqual(names['design.build_proposal'],'design_build_proposal')
        self.assertEqual(names['analysis.bounded_endpoint'],'analysis_bounded_endpoint')
        self.assertEqual(host.store.session(host.run_id)['snapshot']['input']['policy']['model']['tool_naming'],
            tool_naming_policy(bindings))
        self.assertIn('never performs endpoint analysis',advertised['evidence_read']['description'])
        self.assertIn('does not accept evidence reference/pointer paging',advertised['analysis_bounded_endpoint']['description'])

        bad=response('route_build',{},0)
        with self.assertRaises(ToolProtocolError) as caught:
            adapter.decode(bad,0,bindings,payload['tools'])
        error=str(caught.exception)
        self.assertIn("Returned unadvertised function name 'route_build'",error)
        self.assertIn('evidence_read(required: reference)',error)
        self.assertIn('analysis_bounded_endpoint(required: models, protocol, target)',error)
        self.assertIn('is not an evidence reader',error)
        self.assertEqual(host.store.remaining(host.run_id)['used']['tool_calls'],0)

        with host.store.transaction() as db:reference=plain(host.store.put(db,dict(saved=True)))
        mismatched=response('analysis_bounded_endpoint',dict(reference=reference,pointer=''),1)
        decoded=adapter.decode(mismatched,1,bindings,payload['tools'])
        receipt=host.invoke(decoded)
        self.assertEqual(receipt['execution_status'],'rejected')
        self.assertIn('INVALID_TOOL_ARGUMENTS',receipt['error'])
        self.assertEqual(host.store.remaining(host.run_id)['used']['tool_calls'],0)

        valid=response('evidence_read',dict(reference=reference),2)
        decoded=adapter.decode(valid,2,bindings,payload['tools']);receipt=host.invoke(decoded)
        self.assertEqual(receipt['execution_status'],'completed')
        self.assertEqual(host.store.remaining(host.run_id)['used']['tool_calls'],1)

    def test_correction_repeats_exact_readable_names_and_required_arguments(self):
        host=self.host(True);names=provider_name_map(TOOLS,READABLE_TOOL_NAMING)
        invalid=response('tool_evidenceread_placeholder',{},0)
        valid=response(names['route.inspect'],{},1)
        adapter=ReplayReadable([invalid,valid]);session=host.run(adapter)
        correction=json.loads(adapter.payloads[1]['messages'][-1]['content'])['protocol_correction']['requirement']
        self.assertIn("tool_evidenceread_placeholder",correction)
        self.assertIn('evidence_read(required: reference)',correction)
        self.assertIn('analysis_bounded_endpoint(required: models, protocol, target)',correction)
        self.assertEqual(session['state']['protocol_corrections_used'],1)
        self.assertEqual(host.store.remaining(host.run_id)['used']['tool_calls'],1)

    def test_legacy_round_trip_and_collision_resolution_are_unchanged(self):
        host=self.host(False);adapter=DeepSeekAdapter();payload=payload_for(host,adapter)
        bindings=host.store.session(host.run_id)['snapshot']['input']['policy']['tool_bindings']
        legacy=provider_name('route.inspect')
        self.assertTrue(legacy.startswith('tool_'));self.assertEqual(len(legacy),45)
        self.assertIn(legacy,{row['function']['name'] for row in payload['tools']})
        decoded=adapter.decode(response(legacy,{}),0,bindings,payload['tools'])
        self.assertEqual(decoded['tool_id'],'route.inspect')
        self.assertEqual(host.invoke(decoded)['execution_status'],'completed')
        first=provider_name_map(['a.b','a_b'],READABLE_TOOL_NAMING)
        self.assertEqual(first,provider_name_map(['a_b','a.b'],READABLE_TOOL_NAMING))
        self.assertEqual(len(set(first.values())),2)


if __name__=='__main__':unittest.main()
