"""Targeted usability checks. Synthetic cases are protocol tests, not physics validation."""
import json
import re
import unittest
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4

from examples.platform_route import prepare, main
from extensions.tendon_family.route import create, overview, view, finalize_stop
from tools.platform_host import Host
from tools.platform_models import payload_for
from tools.platform_store import plain, encode
from tools.state_io import read


class RouteUsability(unittest.TestCase):
    def setup_route(self):
        root=Path('runs/route_usability_checks')/uuid4().hex
        prepare(root,True)
        host=Host(root,'family-route');host.store.create(read(root/'inputs/project.json'))
        create(root,read(root/'inputs/route.json'))
        return root,host

    def action(self,host,node,action,**args):
        nodes=view(host)['route']['nodes']
        evidence=[n['result'] for n in nodes if n.get('result')][-1:]
        receipt=host.invoke(dict(request_id=node,tool_id='route.advance',arguments=dict(
            node_id=node,action=action,evidence=evidence,reason='Targeted usability verification',next_step='Inspect saved evidence',**args),
            reason='Targeted usability verification'))
        self.assertEqual(receipt['execution_status'],'completed',receipt)
        self.check_payload(host)
        return host.store.artifact(host.store.artifact(receipt['output'])['detail']['result'])

    def check_payload(self,host):
        payload=payload_for(host)
        self.assertIsNone(re.search(r'[\u4e00-\u9fff]',encode(payload)))
        self.assertLess(len(encode(payload).encode()),60000)
        return payload

    def test_exact_built_candidate_run_diagnosis_delivery_and_reuse(self):
        # One real MuJoCo integration, no model API requests.
        root,host=self.setup_route()
        built=self.action(host,'built','build',combination='family_mujoco',candidate_id='selected-tube',
            changes={'template':'tube_distal','components/near/length_m':.19,
                     'discretization/cells/near':4,'control/feedback_gain':5.})
        self.assertFalse(built['evaluated']);self.assertFalse(built['simulated'])
        saved=host.store.artifact(built['configuration'])
        run=self.action(host,'executed','run',source_node='built')
        effective=host.store.artifact(run['configuration'])['effective']
        self.assertEqual(saved,effective)
        self.assertEqual(run['candidate_id'],'selected-tube')
        self.assertEqual(run['evaluation_data']['candidate_id'],'selected-tube')
        self.assertEqual(run['evaluation_data']['source_execution_id'],run['simulation']['execution_id'])
        self.assertNotIn('search',host.store.session(run['run_id'])['state'])
        before=view(host)['counts']
        again=self.action(host,'reuse','run',source_node='built')
        self.assertEqual(run,again)
        self.assertEqual(view(host)['counts'],before)
        diagnosis=self.action(host,'diagnosis','diagnose',source_node='executed')
        self.assertEqual(diagnosis['candidate_id'],run['candidate_id'])
        final=self.action(host,'delivered','finish',source_node='executed')
        self.assertEqual(final['configuration'],run['configuration'])
        self.assertEqual(final['evaluation_ref'],run['evaluation'])
        self.assertEqual(final['delivery_status'],'evaluated')
        self.assertTrue(final['explicit_delivery'])
        self.assertIn('no search ranking',final['best_scope'])
        self.assertEqual(view(host)['counts']['solves'],1)
        self.assertEqual(view(host)['counts']['evaluations'],1)
        used=host.store.remaining()['used'];host.run()
        self.assertEqual(used,host.store.remaining()['used'])
        print('REAL_INTEGRATION',root,encode(dict(counts=view(host)['counts'],task_success=final['task_success'],metrics=final['evaluation']['metrics'])))

    def test_compact_payload_nested_evidence_and_incomplete_delivery(self):
        root,host=self.setup_route()
        payload=self.check_payload(host)
        descriptions=' '.join(t['function']['description'] for t in payload['tools'])
        self.assertIn('no solve, score or trajectory',descriptions)
        self.assertIn('bounds are not sample values',descriptions)
        self.assertLess(len(encode(overview(host)).encode()),6500)
        original=host.store.session(host.run_id)['snapshot']['input']['task']
        self.assertRegex(original['name'],r'[\u4e00-\u9fff]')
        context=json.loads(payload['messages'][-1]['content'])
        self.assertEqual(context['task']['goal'],original['goal'])
        self.assertEqual(context['task']['evaluator'],original['evaluator'])
        document={'detail':{'a/b~c':[[i]*30 for i in range(500)],'large':'x'*20000}}
        with host.store.transaction() as db: ref=plain(host.store.put(db,document))
        def page(pointer,offset=0):
            receipt=host.invoke(dict(request_id='read-'+uuid4().hex,tool_id='evidence.read',
                arguments=dict(reference=ref,pointer=pointer,offset=offset,limit=100,byte_limit=8192),reason='Navigate oversized synthetic evidence'))
            self.assertEqual(receipt['execution_status'],'completed',receipt)
            observation=host.observation(receipt)
            self.assertFalse(observation['truncated'])
            self.assertLessEqual(len(encode(observation).encode()),8192)
            self.check_payload(host)
            return observation['content']
        root_page=page('');self.assertEqual(root_page['kind'],'overview')
        self.assertEqual(root_page['content'][0]['pointer'],'/detail')
        detail=page('/detail');self.assertEqual(detail['kind'],'overview')
        self.assertEqual(detail['content'][0]['pointer'],'/detail/a~1b~0c')
        values=page('/detail/a~1b~0c')
        self.assertEqual(values['kind'],'content');self.assertIsNotNone(values['next_offset'])
        next_page=page('/detail/a~1b~0c',values['next_offset'])
        self.assertEqual(next_page['content'][0],document['detail']['a/b~c'][values['next_offset']])
        self.assertEqual(host.store.artifact(ref),document)
        snapshot=context['route']['frozen_input']['reference']
        translated=host.invoke(dict(request_id='translated-name',tool_id='evidence.read',arguments=dict(
            reference=snapshot,pointer='/input/task/name',limit=10),reason='Read an English projection of original task prose'))
        translated_page=host.observation(translated)['content']
        self.assertEqual(translated_page['presentation'],'english_projection')
        self.assertEqual(translated_page['content'],context['task']['name'][:10])
        self.assertEqual(translated_page['next_offset'],10)
        with host.store.transaction() as db:
            state=host.store.session(host.run_id,db)['state'];state['stop_reason']='MODEL_TURN_LIMIT'
            host.store.update_state(db,host.run_id,state,'stopped')
        finalize_stop(host)
        self.assertEqual(view(host)['route']['final']['delivery_status'],'incomplete')
        self.assertFalse(view(host)['route']['final']['evaluated'])
        from contextlib import redirect_stdout
        import io
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(['resume',str(root)]),2)

    def test_optimize_source_and_charged_failure_accounting(self):
        # Synthetic optimizer failure after the charged simulation, before trial append.
        from extensions.tendon_family.optimization import optimize
        from tests.test_family_route import synthetic_run
        root,host=self.setup_route()
        built=self.action(host,'built','build',combination='family_mujoco',changes={'components/near/length_m':.19})
        captured={}
        def capture(root,value,**kwargs):
            captured.update(value)
            return dict(status='completed',best=None,actual_solves=0)
        with patch('extensions.tendon_family.optimization.optimize',capture):
            self.action(host,'search','optimize',source_node='built',variables={'components/near/length_m':[.14,.2]})
        saved=host.store.artifact(built['configuration'])
        self.assertEqual(captured['session']['robot'],saved['robot'])
        self.assertEqual(captured['session']['task'],saved['task'])
        for key in ('dynamics_model','backend','controller','discretization'):
            self.assertEqual(captured['session']['policy'][key],saved['policy'][key])
        captured['session']['run_id']='charged-failure'
        with patch('extensions.tendon_family.backends.MujocoBackend.run',synthetic_run), \
             patch('tools.platform_tools.evaluate',side_effect=ValueError('SYNTHETIC_EVALUATION_FAILURE')):
            outcome=optimize(root,captured,parent_run_id=host.run_id)
        self.assertEqual(outcome['status'],'failed')
        self.assertEqual(outcome['trials'],[])
        self.assertEqual(outcome['actual_solves'],1)
        self.assertEqual(view(host)['counts']['solves'],1)
        self.assertEqual(view(host)['counts']['evaluations'],0)

    def test_synthetic_provider_correction_sealed_recovery_and_review(self):
        """Synthetic provider responses and backend outputs; zero network/integration."""
        from tools.platform_models import DeepSeekAdapter, provider_name
        from tests.test_family_route import synthetic_run
        root=Path('runs/route_usability_checks')/uuid4().hex
        prepare(root)
        host=Host(root,'family-route');host.store.create(read(root/'inputs/project.json'))
        create(root,read(root/'inputs/route.json'))
        case=self

        class SyntheticProvider(DeepSeekAdapter):
            def __init__(self): self.turns=[]
            def respond(self,payload,turn):
                self.turns.append(turn)
                case.assertIsNone(re.search(r'[\u4e00-\u9fff]',encode(payload)))
                context=json.loads(payload['messages'][-1]['content'])
                case.assertFalse((context['observation'] or {}).get('truncated',False))
                if turn==0:
                    tool='route.inspect';args={}
                elif turn==3:
                    tool='route.inspect';args={}
                    case.assertIn('run',[a['action'] for a in context['recent_actions']])
                elif turn==4:
                    tool='evidence.read';args=dict(reference=context['route']['selected_summary']['evaluation_ref'])
                else:
                    tool='route.advance'
                    args={1:dict(node_id='build',action='build',combination='family_mujoco',changes={'components/near/length_m':.19}),
                          2:dict(node_id='run',action='run',source_node='build'),
                          5:dict(node_id='review',action='crosscheck',source_node='run',combination='matlab_spatial'),
                          6:dict(node_id='finish',action='finish',source_node='run')}[turn]
                    args.update(reason='Synthetic protocol verification only',next_step='Use saved evidence')
                    args['evidence']=[n['result'] for n in context['route']['route']['nodes'] if n.get('result')][-1:]
                call=dict(id='synthetic-'+str(turn),type='function',function=dict(name=provider_name(tool),
                    arguments=json.dumps(dict(arguments=args,reason='Synthetic protocol response',tool_version='1.0.0'))))
                return dict(choices=[dict(message=dict(tool_calls=[call,deepcopy(call)] if turn==0 else [call]))])

        adapter=SyntheticProvider();original=Host.invoke;crashed=False
        class Crash(BaseException): pass
        def interrupt(h,value,**kwargs):
            nonlocal crashed
            receipt=original(h,value,**kwargs)
            if h.run_id==host.run_id and value['request_id']=='model-2-tool' and not crashed:
                case.assertEqual(receipt['execution_status'],'completed',receipt)
                crashed=True;raise Crash()
            return receipt
        with patch('extensions.tendon_family.backends.MujocoBackend.run',synthetic_run), \
             patch('extensions.tendon_family.backends.MatlabBackend.run',synthetic_run):
            with patch.object(Host,'invoke',interrupt),self.assertRaises(Crash): host.run(adapter)
            host.run(adapter)
        final=view(host)['route']['final']
        self.assertEqual(adapter.turns,list(range(7)))
        self.assertTrue(final['explicit_delivery'])
        self.assertEqual(final['crosscheck_status'],'reviewed')
        self.assertEqual(view(host)['counts']['solves'],2)
        self.assertEqual(view(host)['counts']['evaluations'],2)
        self.assertEqual(host.store.remaining()['used']['model_calls'],7)
        self.assertEqual(host.store.session(host.run_id)['state']['protocol_corrections_used'],1)
        print('SYNTHETIC_PROTOCOL_ONLY',root,encode(view(host)['counts']))


if __name__=='__main__': unittest.main()
