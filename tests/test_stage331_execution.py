"""Changed configuration/schema/recovery boundaries; saved responses, no live work."""
from copy import deepcopy
from pathlib import Path
import json
import unittest
from pydantic import ValidationError

from examples.gvs_revision_input import revision_input
from examples.gvs_nmpc_route_experiment import prepare, route_input
from extensions.tendon_family.route import RouteAction, task_result_schema
from extensions.tendon_family.delivery_facts import ReachFacts, TrackingFacts
from schemas.platform import ModelConfig
from tools.platform_models import DeepSeekAdapter, payload_for, input_for, length_without_action
from tools.platform_store import Store
from tools.state_io import atomic_json, read
from tests.test_stage330_revision import SOURCE, workspace_folder
from tests.test_route_model_protocol import Replay, reply, length_reply


class ExecutionBoundaries(unittest.TestCase):
    def test_explicit_config_preparation_and_task_schemas(self):
        inp=revision_input(SOURCE)
        self.assertEqual(inp['policy']['budget'],dict(model_calls=64,tool_calls=160,
            backend_solves=6,wall_s=21600.,worker_calls=0))
        self.assertEqual((inp['policy']['model']['max_turns'],inp['policy']['route']['data']['max_trials']),(64,6))
        # A global default fills omissions; explicit values (including max_turns) win.
        partial=deepcopy(inp);partial['policy']['model']={'max_turns':7}
        resolved=route_input('partial',task_input=partial)['policy']['model']
        self.assertEqual((resolved['model'],resolved['max_turns']),('deepseek-flash',7))
        offline=route_input('offline',offline=True,task_input=inp)['policy']['model']
        self.assertEqual(offline['adapter'],'offline')
        with self.assertRaises(ValidationError): ModelConfig(reasoning_effort='unsupported')
        with workspace_folder() as root:
            atomic_json(root/'input.json',inp)
            host=prepare(root/'live',SOURCE,root/'input.json',historical_failure=SOURCE)
            adapter=DeepSeekAdapter();payload=payload_for(host,adapter)
            config=host.store.session(host.run_id)['snapshot']['input']['policy']['model']
            self.assertEqual(config,read(root/'live/input.json')['policy']['model'])
            for k in ('model','reasoning_effort','max_tokens'):
                self.assertEqual(payload[k],inp['policy']['model'][k])
            self.assertEqual((adapter.timeout_s,adapter.base_url),(600.,'https://api.deepseek.com'))
            self.assertEqual(payload['thinking'],{'type':'enabled'})
            self.assertNotIn('TrackingFacts',json.dumps(payload['tools']))
            model=input_for(host)
            schema=next(d['input_schema'] for d in model.tools if d['extension_id']=='route.advance')
            self.assertEqual(schema['$defs']['ReachFacts'],ReachFacts.model_json_schema())
            self.assertIn('terminal_error_m',schema['$defs']['ReachFacts']['required'])
            self.assertIn('historical_case',model.context['route'])
            self.assertEqual(host.store.remaining()['used']['model_calls'],0)
        original=RouteAction.model_json_schema()
        tracking=task_result_schema(original,'task.tracking')
        self.assertEqual(tracking['$defs']['TrackingFacts'],TrackingFacts.model_json_schema())
        self.assertNotIn('ReachFacts',json.dumps(tracking))
        self.assertIn('ReachFacts',original['$defs'])
        self.assertIn('TrackingFacts',original['$defs'])
        # Existing callers omit the new field from the wire.
        model.context['policy']['model'].pop('reasoning_effort',None)
        self.assertNotIn('reasoning_effort',adapter.encode(model,model.context['policy']['model']))

    def test_saved_reasoning_exhaustion_uses_frozen_recovery_once(self):
        partial=length_reply();partial.raw['choices'][0]['message']['content']=None
        self.assertTrue(length_without_action(partial,{'route.inspect':'1.0.0'}))
        complete=reply(1);complete.raw['choices'][0]['message']['content']=None
        self.assertFalse(length_without_action(complete,{'route.inspect':'1.0.0'}))
        old=Path('runs/stage330_autonomous_design_revision_20260928_225803/live')
        store=Store(old);run=read(old/'workflow.json')['run_id']
        event=next(e for e in store.events(run) if e['kind']=='model_raw_response')
        truncated=store.artifact(event['outputs'][0])['raw']
        self.assertEqual(truncated['choices'][0]['finish_reason'],'length')
        for second in (reply(1),truncated):
            with self.subTest(repeated=isinstance(second,dict)), workspace_folder() as root:
                inp=revision_input(SOURCE);inp['policy']['model']['max_turns']=2
                atomic_json(root/'input.json',inp)
                host=prepare(root/'live',SOURCE,root/'input.json')
                adapter=Replay(host,[truncated,second]);host.run(adapter)
                self.assertEqual([p['max_tokens'] for p in adapter.payloads],[65536,131072])
                self.assertEqual(adapter.timeout_s,900.)
                self.assertTrue(all(p['reasoning_effort']=='high' for p in adapter.payloads))
                self.assertIsNone(host.store.lookup(host.run_id,'model-0-tool'))
                events=[e for e in host.store.events(host.run_id) if e['kind']=='context_delivery']
                configs=[host.store.artifact(e['inputs'][1]) for e in events]
                self.assertEqual([c['timeout_s'] for c in configs],[600.,900.])
                self.assertEqual([json.loads(host.store.lookup(host.run_id,e['request_id'])['reserved'])['wall_s']
                    for e in events],[600.,900.])
                for e,c,p in zip(events,configs,adapter.payloads):
                    self.assertEqual(host.store.artifact(e['inputs'][0]),p)
                    self.assertEqual(json.loads(p['messages'][-1]['content'])['policy']['model'],c)
                used=host.store.remaining()['used']
                self.assertEqual((used['model_calls'],used['backend_solves']),(2,0))
                self.assertEqual(used['tool_calls'],0 if isinstance(second,dict) else 1)
                if not isinstance(second,dict):
                    self.assertEqual(payload_for(host)['max_tokens'],65536)
                self.assertEqual(host.store.session(host.run_id)['state']['length_retries_used'],1)


if __name__=='__main__': unittest.main()
