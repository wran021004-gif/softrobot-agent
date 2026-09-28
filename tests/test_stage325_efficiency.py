"""Original Stage 3.24 failures replayed offline; no transport or backend calls."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
from contextlib import nullcontext
from uuid import uuid4
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from schemas.platform import ModelResponse, SessionInput
from tools.platform_host import Host
from tools.platform_store import Store, plain
from tools.platform_models import DeepSeekAdapter, _argument_rejection, run_loop, payload_for
from tools.platform_registry import dependency_closure
from extensions.tendon_family import route
from extensions.tendon_family.delivery_facts import bound_tracking_facts, check_tracking_statement
from extensions.tendon_family.gvs_reporting import markdown

SOURCE=Path('runs/stage324_time_reference_tracking_20260928')
RUN='gvs-live-6971718592bc'


class OfflineRecoveryTests(unittest.TestCase):
    def test_public_deterministic_render_uses_sealed_binding_without_execution(self):
        import io
        from contextlib import redirect_stdout
        from examples import gvs_parameterized_reach as example
        host=Host(SOURCE/'deterministic','gvs-time-tracking')
        receipts=[json.loads((SOURCE/'deterministic'/(name+'_receipt.json')).read_text())
            for name in ('simulate','evaluate','report')]
        folder=Path('runs/stage325_tracking_efficiency_20260928')/('offline_render_'+uuid4().hex)
        folder.mkdir(parents=True)
        with patch.object(example,'prepare',return_value=host), \
             patch.object(example,'call',side_effect=[(r,host.store.artifact(r['output'])) for r in receipts]), \
             patch('tools.platform_tools.simulate',side_effect=AssertionError('NO_BACKEND')), redirect_stdout(io.StringIO()):
            example.run(folder)
        summary=json.loads((folder/'summary.json').read_text())
        self.assertEqual(summary['factual_result']['report']['reference'],receipts[-1]['output'])
        self.assertEqual(summary['factual_result']['deadline_misses'],40)
        self.assertIn('"real_time_demonstrated": false',(folder/'report.md').read_text())

    def test_original_rejections_and_bounded_corrected_transition(self):
        source=Store(SOURCE/'live')
        before_bytes=(SOURCE/'live/platform.sqlite').read_bytes()
        original=source.session(RUN)
        continuation=json.loads((SOURCE/'protocol_continuation.json').read_text())
        first_stop=source.artifact(continuation['previous_failure'])
        events=source.events(RUN)
        rejected=[e for e in events if e['kind']=='tool' and e['status']=='rejected']
        self.assertEqual(len(rejected),5)
        folder=Path('runs/stage325_tracking_efficiency_20260928')/('offline_replay_'+uuid4().hex)
        folder.mkdir(parents=True)
        with nullcontext(folder) as tmp:
            shutil.copyfile(SOURCE/'live/platform.sqlite',Path(tmp)/'platform.sqlite')
            host=Host(tmp,RUN,actor='model');host.folder.mkdir(parents=True)
            # Isolated replay copy: dependencies are deliberately migrated to this
            # implementation. Original artifacts/counters remain copied verbatim.
            # Authority check is bypassed ONLY here; transport/backend are blocked.
            with patch.object(Store,'check_root'), \
                 patch.object(DeepSeekAdapter,'respond',side_effect=AssertionError('NO_PROVIDER')), \
                 patch('tools.platform_tools.simulate',side_effect=AssertionError('NO_BACKEND')):
                snapshot=deepcopy(original['snapshot'])
                snapshot['dependencies']=dependency_closure([host.reg.get(*k.rsplit('@',1)) for k in snapshot['dependencies']],host.reg)
                state=deepcopy(first_stop['state']);state['route']['final']=None
                state.pop('stop_reason',None)
                with host.store.transaction() as db:
                    ref=host.store.put(db,snapshot)
                    db.execute('UPDATE sessions SET snapshot=? WHERE run_id=?',(ref.artifact_id,RUN))
                    host.store.update_state(db,RUN,state,'running')
                initial_usage=host.store.remaining()
                for event in rejected:
                    request=source.artifact(event['inputs'][0])
                    model_id=request['request_id'].removesuffix('-tool')
                    raw_event=next(e for e in events if e['kind']=='model_raw_response' and e['request_id']==model_id)
                    raw=ModelResponse.model_validate(source.artifact(raw_event['outputs'][0]))
                    decoded=DeepSeekAdapter().decode(raw,int(model_id.split('-')[1]),snapshot['input']['policy']['tool_bindings'])
                    self.assertEqual(decoded['arguments'],request['arguments'])
                    actual=host.invoke(decoded)
                    self.assertEqual(actual['execution_status'],'rejected')
                    self.assertEqual(actual['execution_id'],'not_executed')
                    self.assertTrue(actual['error'].startswith('INVALID_TOOL_ARGUMENTS:'))
                    self.assertEqual(host.store.remaining(),initial_usage)
                    fixed=deepcopy(decoded)
                    if fixed['tool_id']=='route.advance':fixed['arguments'].pop('combination')
                    else:fixed['arguments'].pop('reason')
                    definition=host.reg.get(fixed['tool_id'],fixed['tool_version'],'tool')
                    from tools.platform_validation import validate_arguments
                    args=validate_arguments(definition.input_schema,fixed['arguments'])
                    if definition.hook('preflight'):
                        definition.hook('preflight')(SessionInput.model_validate(snapshot['input']),args,host.reg)
                    if fixed['tool_id']=='evidence.read':corrected=fixed;last_rejected=decoded;receipt=actual
                saved=host.store.session(RUN)
                config=snapshot['input']['policy']['model']
                self.assertGreater(saved['state']['repairs'],config['max_repairs'])
                self.assertIsNone(_argument_rejection(host,last_rejected,receipt,config))
                scheduled=host.store.session(RUN)
                self.assertEqual(scheduled['state']['turn'],saved['state']['turn'])
                self.assertEqual(scheduled['state']['repairs'],saved['state']['repairs'])
                self.assertEqual(scheduled['state']['route'],saved['state']['route'])
                self.assertEqual(host.store.remaining(),initial_usage)
                corrected['request_id']='offline-corrected-read'
                with host.store.transaction() as db:
                    st=host.store.session(RUN,db)['state']
                    st['pending']=dict(decision=corrected,parent=None,input=None)
                    host.store.update_state(db,RUN,st,'needs_input')
                invoke=Host.invoke
                def stop_after_read(current,value,**kwargs):
                    result=invoke(current,value,**kwargs)
                    self.assertEqual(result['execution_status'],'completed')
                    with current.store.transaction() as db:
                        st=current.store.session(RUN,db)['state']
                        current.store.update_state(db,RUN,st,'stopped')
                    return result
                with patch.object(Host,'invoke',stop_after_read):
                    completed=run_loop(host,DeepSeekAdapter())
                self.assertEqual(completed['state']['turn'],saved['state']['turn']+1)
                self.assertEqual(completed['state']['repairs'],0)
                self.assertTrue(completed['state']['argument_limit_correction_used'])
                self.assertEqual(completed['snapshot']['input'],snapshot['input'])
                usage=host.store.remaining()['used']
                self.assertEqual(usage['model_calls'],initial_usage['used']['model_calls'])
                self.assertEqual(usage['backend_solves'],initial_usage['used']['backend_solves'])
                self.assertEqual(usage['tool_calls'],initial_usage['used']['tool_calls']+1)
                with host.store.transaction() as db:
                    st=host.store.session(RUN,db)['state'];st['repairs']=config['max_repairs']+1
                    host.store.update_state(db,RUN,st,'running')
                terminal=_argument_rejection(host,last_rejected,receipt,config)
                self.assertEqual(terminal['status'],'needs_input')
                route.finalize_stop(host)
                self.assertIsNone(host.store.session(RUN)['state']['route']['final'])
                with self.assertRaisesRegex(ValueError,'BOUNDED_ARGUMENT_CORRECTION_FAILED'):host.resume()
        self.assertEqual((SOURCE/'live/platform.sqlite').read_bytes(),before_bytes)

    def test_shared_facts_and_original_negative_prose(self):
        store=Store(SOURCE/'live');saved=store.session(RUN)
        node=next(n for n in saved['state']['route']['nodes'] if n['action']=='run')
        trial=store.artifact(node['result'])
        candidate=route.trial_facts(store,saved['snapshot']['input'],trial)
        facts=bound_tracking_facts(store,trial,candidate)
        self.assertEqual(facts['deadline_misses'],40)
        self.assertFalse(facts['real_time_demonstrated'])
        self.assertEqual(facts['control_updates'],40)
        self.assertTrue(check_tracking_statement(facts,deepcopy(facts))['accepted'])
        wrong=deepcopy(facts);wrong['deadline_misses']=0
        self.assertFalse(check_tracking_statement(facts,wrong)['accepted'])
        ctx=SimpleNamespace(store=store,host=Host(SOURCE/'live',RUN))
        with self.assertRaisesRegex(ValueError,'TRACKING_RESULT_STATEMENT_MISMATCH'):
            route.delivery(ctx,saved['state']['route'],SimpleNamespace(run_id=candidate['owner_run_id']),
                trial,'Unchanged provider reasoning',candidate,wrong)
        wrong=deepcopy(facts);wrong['real_time_demonstrated']=True
        self.assertFalse(check_tracking_statement(facts,wrong)['accepted'])
        broken=deepcopy(trial);broken['profile_report']['execution_id']='wrong'
        with self.assertRaisesRegex(ValueError,'BINDING_MISMATCH'):bound_tracking_facts(store,broken,candidate)
        summary=store.artifact(trial['profile_report']['reference'])['detail']
        rendered=markdown(dict(summary,factual_result=facts))
        self.assertIn('"deadline_misses": 40',rendered)
        self.assertIn('"real_time_demonstrated": false',rendered)
        self.assertIn('zero deadline-nonconforming updates',(SOURCE/'live/model_final.txt').read_text())
        review=json.loads((SOURCE/'provider_interpretation_review.json').read_text())
        self.assertFalse(review['provider_final_prose_accurate'])
        # The same object is retained in model summaries and report rendering.
        self.assertEqual(route.summarize(dict(trial,factual_result=facts))['factual_result'],facts)
        context=json.loads(payload_for(Host(SOURCE/'live',RUN))['messages'][-1]['content'])
        self.assertEqual(context['route']['selected_summary']['factual_result'],facts)
        self.assertEqual(context['route']['incumbent']['factual_result'],facts)


if __name__=='__main__':unittest.main()
