"""Focused route boundaries with synthetic backend outputs; zero integration."""
import json
from copy import deepcopy
from pathlib import Path
import unittest
from unittest.mock import patch
from uuid import uuid4
from examples.platform_route import prepare
from tools.platform_host import Host
from tools.platform_store import plain
from tools.state_io import read
from extensions.tendon_family.route import create,view
from extensions.tendon_family.optimization import optimize
from extensions.tendon_family.crosscheck import crosscheck
from tools.platform_models import OfflineAdapter


def synthetic_run(backend,folder,timeout_s):
    from schemas.platform import BackendResult,Payload,Signal
    inp=backend.inp
    times=[.01*i for i in range(1,36)]
    target=inp.task.goal.data['target_m']
    return BackendResult(solver_status='completed',backend_id=backend.backend_id,model_id=backend.model,
        signals=[Signal(spec=inp.task.observations[0],times_s=times,values=[target for _ in times])],
        data=Payload(contract='family.backend_data',data=dict(physics_identity='offline',scene_identity='offline',
            timings_s={},numerical_steps=0,applicability={},exported_files=[])),
        limitations=['Synthetic protocol test; no integration'],initial_state=backend.initial,seed=inp.seed)


class Decisions(OfflineAdapter):
    """Explicit test fixture, never described as model reasoning."""
    def respond(self,payload,turn):
        context=json.loads(payload['messages'][-1]['content']); route=context['route']['route']
        if turn==0:
            args=dict(node_id='search',action='optimize',combination='family_mujoco',
                changes={'components/near/length_m':.2},variables={'components/near/length_m':[.14,.2]},max_trials=3,
                reason='Offline boundary proposal',next_step='Read best and finish')
        else:
            args=dict(node_id='finish',action='finish',source_node='search',evidence=[route['nodes'][0]['result']],
                reason='Offline fixture completed',next_step='stopped')
        return dict(request_id=f'model-{turn}-tool',tool_id='route.advance',tool_version='1.0.0',
            arguments=args,reason=args['reason'])


class FamilyRoute(unittest.TestCase):
    def setup_route(self):
        root=Path('runs/route_checks')/uuid4().hex;prepare(root,True)
        host=Host(root,'family-route');host.store.create(read(root/'inputs/project.json'))
        inp=read(root/'inputs/route.json');create(root,inp)
        return root,host,inp

    def test_crosscheck_actual_input_and_source_identity(self):
        root,host,inp=self.setup_route()
        with patch('extensions.tendon_family.backends.MatlabBackend.run',synthetic_run):
            host.run(Decisions())
            final=view(host)['route']['final'];backend=read(root/'inputs/execution.json')['backends']['matlab_spatial']
            a=crosscheck(root,final['run_id'],final['candidate_id'],final['configuration'],backend,parent_run_id=host.run_id)
            before=host.store.remaining()['used']['backend_solves']
            b=crosscheck(root,final['run_id'],final['candidate_id'],final['configuration'],backend,parent_run_id=host.run_id)
            self.assertEqual(a,b);self.assertEqual(host.store.remaining()['used']['backend_solves'],before)
            changed=deepcopy(backend);changed['parameters']['data']['rtol']=2e-5
            c=crosscheck(root,final['run_id'],final['candidate_id'],final['configuration'],changed,parent_run_id=host.run_id)
            self.assertNotEqual(a['run_id'],c['run_id'])
            effective=host.store.artifact(c['configuration'])['effective']
            self.assertEqual(effective['policy']['backend'],changed)
            self.assertEqual(c['source_configuration'],final['configuration'])
            self.assertEqual(host.store.remaining()['used']['backend_solves'],4)

    def test_dedup_public_loop_and_sealed_resume(self):
        root,host,_=self.setup_route();original=Host.invoke;crashed=False
        class Crash(BaseException): pass
        def interrupt_after_seal(h,value,**kwargs):
            nonlocal crashed
            receipt=original(h,value,**kwargs)
            if h.run_id==host.run_id and value['request_id']=='model-0-tool' and not crashed:
                self.assertEqual(receipt['execution_status'],'completed',receipt)
                crashed=True;raise Crash()
            return receipt
        with patch('extensions.tendon_family.backends.MatlabBackend.run',synthetic_run):
            with patch.object(Host,'invoke',interrupt_after_seal):
                with self.assertRaises(Crash):host.run(Decisions())
            self.assertIsNotNone(host.store.session(host.run_id)['state']['pending'])
            host.run(Decisions());out=view(host)
            self.assertEqual(out['counts']['solves'],2)
            self.assertEqual(out['counts']['evaluations'],2)
            first=out['route']['nodes'][0];result=host.store.artifact(first['result'])
            self.assertEqual((result['proposals'],result['distinct_candidates'],len(result['duplicates'])),(3,2,1))
            self.assertEqual(result['duplicates'][0]['original_candidate'],'search-0')
            used=host.store.remaining()['used'];host.run(Decisions())
            self.assertEqual(host.store.remaining()['used'],used)
            final=out['route']['final'];self.assertEqual(final['candidate_id'],final['evaluation']['candidate_id'])
            self.assertEqual(final['crosscheck_status'],'not_reviewed')

    def test_selection_cannot_replace_frozen_input(self):
        root,host,inp=self.setup_route()
        request=dict(request_id='bad',tool_id='route.advance',arguments=dict(node_id='bad',action='optimize',
            combination='nonexistent',reason='invalid selection',next_step='stop'),reason='invalid fixture')
        self.assertEqual(host.invoke(request)['execution_status'],'rejected')
        request['request_id']='bad-session';request['arguments']['session']=inp
        self.assertEqual(host.invoke(request)['execution_status'],'rejected')
        self.assertEqual(host.store.remaining()['used']['backend_solves'],0)
        changed=deepcopy(inp);changed['task']['goal']['data']['target_m'][0]+=.01
        with self.assertRaisesRegex(ValueError,'SESSION_INPUT_CHANGED'):create(root,changed)


if __name__=='__main__': unittest.main()
