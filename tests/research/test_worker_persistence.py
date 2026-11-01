"""Filesystem/SDK fixtures only: no live Provider, scientific Worker or integration."""
import asyncio
import json
import os
import posixpath
import shutil
from pathlib import Path,PurePosixPath
from types import SimpleNamespace
import unittest
from unittest.mock import patch
from uuid import uuid4
import httpx

from tools import state_io
from tools.state_io import io_path,atomic_json,read,digest
from tools.research import agent,analysis,reporter,execution_worker
from tools.research.config import ROOT
from tools.research.state import state,update
from tests.research.test_r3_b_stage1 import integrated_host
from tests.research.test_p63a_math_interface import t1_request,offline_dispatch,synthetic_t1


class WorkerPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.folder=ROOT/'runs'/('io-fixture-'+uuid4().hex[:8])
        self.folder.mkdir(parents=True)
        self.addCleanup(lambda:shutil.rmtree(io_path(self.folder)))
        for target in ('tools.service_execution._run_contained','mujoco.mj_step'):
            p=patch(target,side_effect=AssertionError('NO_REAL_SCIENTIFIC_EXECUTION'))
            p.start();self.addCleanup(p.stop)

    def deep_folder(self):
        folder=self.folder
        while len(str(folder))<300:folder=folder/'checkpoint-depth-123456789'
        return folder

    def test_json_atomic_roundtrip_preserves_bytes_hashes_and_cleans_tmp(self):
        path=self.deep_folder()/'checkpoint.json'
        value=dict(scope='Synthetic filesystem fixture',units='m',value=[1,2,3])
        atomic_json(path,value)
        expected=(json.dumps(value,indent=2,allow_nan=False,ensure_ascii=False)+'\n').encode()
        self.assertEqual(io_path(path).read_bytes(),expected)
        self.assertEqual(read(path),value)
        self.assertEqual(digest(read(path)),digest(value))
        self.assertFalse(io_path(path.with_suffix('.json.tmp')).exists())
        atomic_json(path,{**value,'value':[4]})
        self.assertEqual(read(path)['value'],[4])
        self.assertEqual(len(list(io_path(path.parent).glob('*.json'))),1)

    def test_windows_absolute_unc_and_existing_extended_and_posix(self):
        if os.name=='nt':
            self.assertTrue(str(io_path(self.folder/'../relative.json')).startswith('\\\\?\\'))
            self.assertEqual(str(io_path(r'\\server\share\folder\file.json')),r'\\?\UNC\server\share\folder\file.json')
            path=io_path(self.folder);self.assertEqual(io_path(path),path)
        with patch.object(state_io,'os',SimpleNamespace(name='posix',fspath=os.fspath,path=posixpath)), \
                patch.object(state_io,'Path',PurePosixPath):
            self.assertEqual(state_io.io_path('relative/file.json'),PurePosixPath('relative/file.json'))
            self.assertEqual(state_io.io_path('/tmp/file.json'),PurePosixPath('/tmp/file.json'))

    def test_worker_long_checkpoint_result_and_no_checkpoint_overwrite(self):
        path=self.deep_folder()/'request.json'
        atomic_json(path,dict(kind='candidate_analysis',implementation='fixture',configuration={},binding={},query={}))
        def calculate(*args,checkpoint,**kwargs):
            checkpoint('native_progress_0000',dict(stage='synthetic',completed_rollouts=0))
            with self.assertRaisesRegex(ValueError,'PRESERVE_NUMERICAL_CHECKPOINT'):
                checkpoint('native_progress_0000',dict(completed_rollouts=99))
            return dict(status='computed',fixture='No numerical calculation',completed_rollouts=0)
        with patch('sys.argv',['worker',str(path)]),patch.object(execution_worker,'contain_worker_children'), \
                patch.object(analysis,'calculate',side_effect=calculate):
            execution_worker.main()
        self.assertEqual(read(path.with_name('numerical_native_progress_0000.json'))['completed_rollouts'],0)
        self.assertEqual(read(path.with_name('result.json'))['status'],'computed')
        self.assertIn('python',read(path.with_name('worker_runtime.json')))

    def test_worker_checkpoint_failure_is_incomplete_and_unknown_never_relaunches(self):
        h,c=integrated_host();q=t1_request(h,c)
        calls=[]
        def failed(command,log,timeout,**kwargs):
            calls.append(command)
            atomic_json(Path(command[-1]).with_name('result.json'),dict(status='execution_incomplete',
                error='FileNotFoundError',reason='Synthetic initial checkpoint failure before rollout'))
            return SimpleNamespace(returncode=0)
        with patch('tools.service_execution._run_contained',side_effect=failed):
            result=analysis.dispatch(h,q,'failed-checkpoint-fixture',guard=lambda *a:None,origin='engineering_preflight')
            reused=analysis.dispatch(h,q,'failed-checkpoint-fixture',guard=lambda *a:None,origin='engineering_preflight')
        raw=h.store.artifact(result['reference'])
        self.assertEqual(raw['status'],'execution_incomplete')
        self.assertEqual(raw['error'],'FileNotFoundError')
        self.assertEqual(state(h)['mathematical_evaluations'],1)
        self.assertEqual(len(calls),1);self.assertEqual(reused['reference'],result['reference'])
        self.assertNotIn('native_dynamics',raw)
        with patch('tools.service_execution._run_contained',side_effect=RuntimeError('Synthetic unknown termination')):
            with self.assertRaisesRegex(ValueError,'UNKNOWN_ANALYSIS_TERMINATION'):
                analysis.dispatch(h,q,'unknown-checkpoint-fixture',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(state(h)['mathematical_evaluations'],2)
        with self.assertRaisesRegex(ValueError,'PENDING_ANALYSIS_RECOVER_WITHOUT_RECOMPUTATION'):
            analysis.dispatch(h,q,'unknown-checkpoint-fixture',guard=lambda *a:None,origin='engineering_preflight')
        self.assertIsNotNone(state(h)['pending'])

    def test_long_result_recovery_settles_original_receipt_without_relaunch(self):
        h,c=integrated_host();q=t1_request(h,c)
        with patch('tools.service_execution._run_contained',side_effect=RuntimeError('Synthetic missing termination boundary')):
            with self.assertRaisesRegex(ValueError,'UNKNOWN_ANALYSIS_TERMINATION'):
                analysis.dispatch(h,q,'long-recovery-fixture',guard=lambda *a:None,origin='engineering_preflight')
        pending=state(h)['pending'];old=Path(pending['folder']);folder=self.deep_folder()
        request=read(old/'request.json')
        atomic_json(folder/'request.json',request)
        atomic_json(folder/'result.json',synthetic_t1(request))
        atomic_json(folder/'boundary.json',dict(termination_confirmed=True,returncode=0,timed_out=False,worker_started=True,elapsed_s=.01))
        atomic_json(folder/'numerical_native_progress_0001.json',dict(cost=dict(physics_steps=400),fixture='Synthetic progress, no physics'))
        io_path(folder/'worker.log').write_text('Synthetic mock worker only',encoding='utf-8')
        update(h,pending={**pending,'folder':str(folder)})  # Isolated fixture state only.
        result=analysis.recover(h)
        receipt=json.loads(h.store.lookup(h.run_id,pending['worker_request_id'])['receipt'])
        self.assertEqual(receipt['output'],result['reference'])
        self.assertEqual(h.store.artifact(result['reference'])['status'],'computed')
        self.assertEqual(h.store.artifact(result['reference'])['native_progress']['cost']['physics_steps'],400)
        self.assertIsNone(state(h)['pending'])
        self.assertEqual(state(h)['mathematical_evaluations'],1)
        again=analysis.dispatch(h,q,'long-recovery-fixture',guard=lambda *a:None,origin='engineering_preflight')
        self.assertEqual(again['reference'],result['reference'])
        self.assertEqual(state(h)['mathematical_evaluations'],1)

    def test_reporter_request_eight_pauses_and_restores_feedback_without_ninth_send(self):
        h,c=integrated_host();result=offline_dispatch(h,t1_request(h,c),'fixture-result')['reference']
        sent=[];created=False
        original=agent.deliver_science_before_decision
        async def deliver(host,*args,**kwargs):
            nonlocal created
            if host.store.remaining()['used']['model_calls']==7 and not created:
                reporter._save(host,reporter.assemble(host,[result]));created=True
            return await original(host,*args,**kwargs)
        def respond(request):
            wire=json.loads(request.content);sent.append(wire)
            if 'tools' not in wire:
                self.assertEqual(len(sent),8)
                payload=json.loads(wire['messages'][-1]['content'])
                text=json.dumps(dict(interpretations=[dict(kind='new_information',text='Synthetic Reporter retained across pause',
                    source_ids=[next(iter(payload['source_catalog']))])]))
                message=dict(role='assistant',content=text)
            elif len(sent)<=7:
                name='research_route' if len(sent)==1 else 'evidence_read'
                args=dict(tool='evidence_read') if name=='research_route' else dict(reference=state(h)['public_prior_manifest'],view='summary')
                from tools.research.object_choices import main_projection
                if name=='evidence_read':args=main_projection(h,args)
                message=dict(role='assistant',content=None,tool_calls=[dict(id='persist-'+str(len(sent)),type='function',
                    function=dict(name=name,arguments=json.dumps(args)))])
            else:
                self.assertIn('Synthetic Reporter retained across pause',json.dumps(wire))
                message=dict(role='assistant',content='Synthetic continuation consumed saved feedback')
            return httpx.Response(200,json=dict(id='fixture',object='chat.completion',created=1,model=wire['model'],
                choices=[dict(index=0,finish_reason='tool_calls' if message.get('tool_calls') else 'stop',message=message)],
                usage=dict(prompt_tokens=10,completion_tokens=4,total_tokens=14)))
        with patch('tools.research.provider.load_credential'),patch.dict(os.environ,{'DEEPSEEK_API_KEY':'offline'}), \
                patch('tools.research.core.guard'),patch('tools.research.agent.guard'), \
                patch('tools.research.tool_readiness.execution_environment',return_value=dict(status='ready')), \
                patch('httpx.AsyncHTTPTransport',return_value=httpx.MockTransport(respond)), \
                patch.object(agent,'deliver_science_before_decision',side_effect=deliver):
            asyncio.run(agent.converse(h,session_handoff=False,max_new_provider_requests=8))
            self.assertEqual(len(sent),8);self.assertEqual(h.store.remaining()['used']['model_calls'],8)
            self.assertTrue(any(e['kind']=='supervisor_pause' for e in h.store.events(h.run_id)))
            self.assertFalse(any(e['kind']=='r3_send_rejected' for e in h.store.events(h.run_id)))
            asyncio.run(agent.converse(h,session_handoff=False,restore_only=True))
            self.assertEqual(len(sent),8)
            asyncio.run(agent.converse(h,session_handoff=False,max_new_provider_requests=1,pause_after_completed_invocations=1))
        self.assertEqual(len(sent),9);self.assertEqual(h.store.remaining()['used']['model_calls'],9)
        self.assertEqual(state(h)['mathematical_evaluations'],1)


if __name__=='__main__':unittest.main()
