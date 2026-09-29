"""Focused offline Stage 3.33 boundaries. No backend or provider traffic."""
from copy import deepcopy
import json
import unittest
from unittest.mock import patch
from schemas.platform import ModelConfig, ModelResponse
from tools.platform_host import Host
from tools.platform_store import Store
from tools.platform_models import payload_for, DeepSeekAdapter, provider_name
from tools.state_io import atomic_json, read, digest
from examples.gvs_stage333 import SOURCE, SOURCE32, descriptors
from examples.gvs_revision_input import independent_lengths_input
from examples.gvs_nmpc_route_experiment import prepare
from tests.test_stage330_revision import workspace_folder
from tests.test_route_model_protocol import Replay, reply, Crash


def malformed():
    source=Store(SOURCE32/'live_network')
    event=next(e for e in source.events('gvs-live-b8f4ab5f17f2') if e['kind']=='model_raw_response' and e['request_id']=='model-11')
    return ModelResponse.model_validate(source.artifact(event['outputs'][0]))


class Stage333(unittest.TestCase):
    def setup_host(self,root,turns,legacy=False):
        inp=independent_lengths_input(SOURCE);inp['policy']['model']['max_turns']=turns
        inp['policy']['model']['max_no_progress']=20
        if legacy: inp['policy']['model'].pop('protocol_recovery')
        atomic_json(root/'input.json',inp)
        return prepare(root/'live',SOURCE,root/'input.json')

    def test_recovery_episodes_limits_and_invalid_nonexecution(self):
        bad=malformed();good=reply(1)
        for responses,total,consecutive,stop,tools in (
            ([bad,good,good,bad,good],2,0,'MODEL_TURN_LIMIT',3),
            ([bad,bad,bad],2,2,'CONSECUTIVE_LIMIT',0),
            ([bad,good]*4+[bad],4,0,'TOTAL_LIMIT',4)):
            with self.subTest(stop=stop),workspace_folder() as root:
                host=self.setup_host(root,len(responses));adapter=Replay(host,responses)
                state=host.run(adapter)['state']
                self.assertEqual((state['protocol_corrections_used'],state['protocol_corrections_consecutive']),(total,consecutive))
                self.assertIn(stop,state['stop_reason'])
                used=host.store.remaining()['used']
                self.assertEqual((used['tool_calls'],used['backend_solves'],used['model_calls']),(tools,0,len(responses)))
                for i,r in enumerate(responses):
                    if r==bad:self.assertIsNone(host.store.lookup(host.run_id,f'model-{i}-tool'))

    def test_rejected_and_failed_calls_do_not_reset(self):
        for args in ({'unexpected':1},{'reference':{'artifact_id':'f'*64,'media_type':'application/json'}}):
            with self.subTest(args=args),workspace_folder() as root:
                host=self.setup_host(root,4)
                invalid=reply(1);call=invalid.raw['choices'][0]['message']['tool_calls'][0]['function']
                call.update(name=provider_name('evidence.read'),arguments=json.dumps(dict(arguments=args,reason='Offline boundary',tool_version='1.0.0')))
                state=host.run(Replay(host,[malformed(),invalid,malformed(),malformed()]))['state']
                self.assertEqual(state['protocol_corrections_consecutive'],2)
                self.assertIn('CONSECUTIVE_LIMIT',state['stop_reason'])

    def test_continuation_and_completed_scientific_failure(self):
        # Crash after a completed legal tool receipt, before loop state commit.
        with workspace_folder() as root:
            host=self.setup_host(root,4);adapter=Replay(host,[malformed(),reply(1),malformed(),reply(1)])
            original=Host.invoke
            def crash(h,request,**kwargs):
                result=original(h,request,**kwargs)
                raise Crash()
            with patch.object(Host,'invoke',crash),self.assertRaises(Crash):host.run(adapter)
            self.assertEqual(host.store.session(host.run_id)['state']['protocol_corrections_used'],1)
            # The completed receipt can represent task failure without tool failure.
            def scientific_failure(h,request,**kwargs):
                result=original(h,request,**kwargs)
                self.assertEqual(result['execution_status'],'completed')
                return dict(result,task_success=False)
            with patch.object(Host,'invoke',scientific_failure):
                state=Host(root/'live',host.run_id).run(adapter)['state']
            self.assertEqual(adapter.turns,[0,1,2,3])
            self.assertEqual((state['protocol_corrections_used'],state['protocol_corrections_consecutive']),(2,0))
            self.assertEqual(host.store.remaining()['used']['tool_calls'],2)

    def test_legacy_serialization_and_budget(self):
        old=read(SOURCE/'resolved_frozen_input.json')['policy']['model']
        self.assertEqual(ModelConfig.model_validate(old).model_dump(mode='json'),old)
        with workspace_folder() as root:
            host=self.setup_host(root,5,legacy=True)
            state=host.run(Replay(host,[malformed(),reply(1),malformed()]))['state']
            self.assertIn('MODEL_PROTOCOL_CORRECTION_FAILED',state['stop_reason'])
            self.assertEqual(state['protocol_corrections_used'],1)
        with workspace_folder() as root:
            host=self.setup_host(root,1)
            state=host.run(Replay(host,[malformed()]))['state']
            self.assertIn('BUDGET_EXHAUSTED',state['stop_reason'])
            self.assertEqual(state.get('protocol_corrections_used',0),0)

    def test_seven_bindings_context_and_frozen_science(self):
        before=[(Store(d['directory']+'/'+d['live_store']).remaining(),digest(Store(d['directory']+'/'+d['live_store']).session(d['source_session_id']))) for d in descriptors()]
        with workspace_folder() as root:
            inp=independent_lengths_input(SOURCE);atomic_json(root/'input.json',inp)
            host=prepare(root/'live',SOURCE,root/'input.json',historical_sources=descriptors())
            adapter=DeepSeekAdapter();payload=payload_for(host,adapter);ctx=json.loads(payload['messages'][-1]['content'])
            exp=ctx['route']['exploration_summary'];cases=read(root/'live/historical_case.json')['content']['cases']
            self.assertEqual(len(cases),7)
            self.assertEqual(exp['historical']['sample_count'],7);self.assertIsNone(exp['best_fresh'])
            self.assertTrue(exp['length_coupling']['historical_relationship_unbroken'])
            self.assertFalse(exp['length_coupling']['meaningful_departure_evaluated'])
            self.assertEqual([(r['initialization_selected'],r['accepted_noninitialization_plans']) for r in exp['historical_samples']],[(7,28),(35,0),(13,22),(35,0),(25,10),(35,0),(35,0)])
            self.assertEqual(exp['best_historical']['candidate_id'],'rev_compliant_max')
            self.assertEqual(exp['remaining_resources']['backend_solves'],6)
            self.assertEqual(ctx['policy']['model']['protocol_recovery'],dict(max_total=4,max_consecutive=2))
            self.assertEqual((payload['max_tokens'],payload['reasoning_effort'],adapter.timeout_s),(65536,'high',600.))
            for c in cases:
                detail=host.store.artifact(c['detail_export'])
                self.assertEqual(detail['source_session_id'],c['source_session_id'])
                self.assertAlmostEqual(c['motion_summary']['late_interval_s'][0],.30)
            snap=host.store.session(host.run_id)['snapshot']['input'];old=read(SOURCE/'frozen_input.json')
            self.assertEqual(snap['robot'],old['robot']);self.assertEqual(snap['task'],old['task'])
            for k in ('candidate_builder','controller','backend','dynamics_model','discretization','timeout_s'):
                self.assertEqual(snap['policy'][k],old['policy'][k])
            self.assertTrue(all(v==0 for v in host.store.remaining()['used'].values()))
            from extensions.tendon_family.historical_failure import bind_sources
            retained=deepcopy(descriptors())
            retained[1]['live_store']='absent_retained_ledger_fallback'
            rebound=bind_sources(retained,inp,host.store)
            self.assertEqual([c['factual_result'] for c in rebound['cases']],[c['factual_result'] for c in cases])
            with host.store.connect(True) as db:self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],1)
            db.close()
        after=[(Store(d['directory']+'/'+d['live_store']).remaining(),digest(Store(d['directory']+'/'+d['live_store']).session(d['source_session_id']))) for d in descriptors()]
        self.assertEqual(before,after)


if __name__=='__main__':unittest.main()
