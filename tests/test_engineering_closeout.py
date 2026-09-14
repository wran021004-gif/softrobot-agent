"""Only version propagation, bounded-worker cleanup and one useful math extension."""
import json
import math
import os
from pathlib import Path
import sys
import unittest
from dataclasses import replace
from unittest.mock import patch
from uuid import uuid4

from tools.spec_tools import ROOT
from tools.state_io import read,atomic_json
from tools.artifact_tools import file_hash
from tools.public_services import ServiceSession
from tools.public_catalog import native_tools

CALLER=dict(actor_id='engineering-closeout',origin='development',transport='offline_native_fixture')
ARTIFACTS={}


def session(permissions=('analysis','read_evidence','derived_artifacts')):
    s=ServiceSession(ROOT/'runs/engineering_closeout'/uuid4().hex)
    s.create(dict(profile_id='small-closeout',permissions=list(permissions),tool_calls=6))
    return s


def invoke(s,name,args,**extra):
    return s.invoke(dict(tool_id=name,arguments=args,reason='Targeted closeout verification',evidence=[],**extra),caller=CALLER)


class CloseoutChecks(unittest.TestCase):
    def test_independent_version_native_request_compatibility_and_result(self):
        from tools.tool_registry import service_tools
        from schemas.public_tools import ToolCall,PublicResult
        definitions=service_tools()
        definitions['analysis.pcc_jacobian']=replace(definitions['analysis.pcc_jacobian'],version='7.3.2',compatible_versions=('7.2.0',))
        s=session();args=dict(length_m=.4,bend_rad=[0.,0.])
        with patch('tools.tool_registry.service_tools',return_value=definitions):
            declaration=next(t['function'] for t in native_tools('services') if t['function']['name']=='analysis__pcc_jacobian')
            self.assertIn('@7.3.2:',declaration['description'])
            native=s.apply_tool_call(dict(name=declaration['name'],arguments=json.dumps({**args,'reason':'Version test','evidence':[]})),caller=CALLER)
            compatible=invoke(s,'analysis.pcc_jacobian',args,tool_version='7.2.0')
            rejected=invoke(s,'analysis.pcc_jacobian',args,tool_version='1.1.0')
        self.assertEqual(native['tool_version'],'7.3.2')
        self.assertEqual(native['provenance']['requested_tool_version'],'7.3.2')
        self.assertEqual(compatible['tool_version'],'7.3.2')
        self.assertEqual(compatible['provenance']['requested_tool_version'],'7.2.0')
        self.assertEqual(rejected['error']['code'],'TOOL_VERSION_MISMATCH')
        self.assertEqual(rejected['cost']['charged']['tool_calls'],0)
        self.assertEqual(native['contract_version'],'1.0')
        PublicResult.model_validate(native)
        with self.assertRaises(ValueError):ToolCall(tool_id='x',tool_version='7.3.2',contract_version='2.0',reason='Bad protocol')
        unknown=invoke(s,'unknown.tool',{})
        self.assertIsNone(unknown['tool_version'])

    def test_timeout_returns_and_kills_owned_descendant(self):
        from tools import service_execution
        s=session();atomic_json(s.root/'input.json',{})
        state=s.load();state['evidence']['input.json']=dict(sha256=file_hash(s.root/'input.json'));atomic_json(s.root/'state.json',state)
        # Use the actual worker and containment, replacing only its numerical/
        # rendering binding with a stuck handler that owns a sleeping child.
        script='''
import sys,subprocess,time,json
from pathlib import Path
from tools import service_worker
def stalled(definition,root,registry,arguments):
    child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (root/'child_pid.json').write_text(json.dumps({'pid':child.pid}))
    time.sleep(60)
service_worker.execute_binding=stalled
service_worker.main()
'''
        original=service_execution._run_contained
        def injected(command,log,timeout_s):
            return original([sys.executable,'-c',script,command[-1]],log,2.)
        import time
        start=time.monotonic()
        with patch('tools.service_execution._run_contained',side_effect=injected):
            result=invoke(s,'visualization.render_simulation_video',dict(result_ref='input.json',backend='mujoco'))
        elapsed=time.monotonic()-start
        self.assertEqual(result['error']['category'],'timeout',result)
        self.assertEqual(result['cost']['charged']['tool_calls'],1)
        self.assertLess(elapsed,8.)
        pid=read(s.root/'child_pid.json')['pid']
        if os.name=='nt':
            import ctypes as c
            from ctypes import wintypes as w
            kernel=c.WinDLL('kernel32',use_last_error=True)
            kernel.OpenProcess.argtypes=[w.DWORD,w.BOOL,w.DWORD];kernel.OpenProcess.restype=w.HANDLE
            kernel.WaitForSingleObject.argtypes=[w.HANDLE,w.DWORD]
            kernel.CloseHandle.argtypes=[w.HANDLE]
            handle=kernel.OpenProcess(0x100000,False,pid)
            if handle:
                try:self.assertEqual(kernel.WaitForSingleObject(handle,2000),0,'Owned child still running')
                finally:kernel.CloseHandle(handle)
        ARTIFACTS['timeout']=dict(root=str(s.root),result=result,elapsed_s=elapsed,child_pid=pid,
            validation='Injected stuck binding; actual worker/job termination; no video or engine started')

    def test_saved_video_cache_through_bounded_worker(self):
        source=ROOT/'runs/round9_reach'
        info=next(read(p) for p in (source/'observations/videos').glob('*/native_video.json') if read(p)['parameters']['backend']=='mujoco')
        refs=list(info['source_hashes'])+list(info['artifact_hashes'])+[info['receipt']['metadata_ref']]
        s=ServiceSession(ROOT/'runs/engineering_closeout'/uuid4().hex)
        s.create(dict(profile_id='saved-video-reuse',permissions=['derived_artifacts'],tool_calls=1),source_root=source,evidence_refs=refs)
        result=invoke(s,'visualization.render_simulation_video',info['parameters'])
        self.assertEqual(result['execution_status'],'completed',result)
        self.assertEqual(result['tool_version'],'1.2.0')
        data=read(s.root/result['details_ref']);self.assertTrue(data['cached'])
        for ref,expected in info['artifact_hashes'].items():
            self.assertEqual(file_hash(source/ref),expected)
            self.assertEqual(file_hash(s.root/ref),expected)
        ARTIFACTS['video_cache']=dict(root=str(s.root),result=result,validation='Existing MuJoCo video reused, no frames rendered or encoded')

    def test_tolerance_straight_limit_and_zero_uncertainty(self):
        from tools.pcc_tolerance import analyze
        args=dict(length_m=.4,bend_rad=[0.,0.],length_std_m=.001,bend_std_rad=[.01,.02])
        out=analyze(args)
        expected=[1e-6,4e-6,16e-6]
        for i in range(3):
            for j in range(3):self.assertAlmostEqual(out['tip_covariance_m2'][i][j],expected[i] if i==j else 0.,places=14)
        self.assertAlmostEqual(out['rms_position_deviation_m'],math.sqrt(sum(expected)))
        self.assertEqual(out['parameter_contributions'][0]['parameter'],'bend_v_rad')
        zero=analyze({**args,'length_std_m':0.,'bend_std_rad':[0.,0.]})
        self.assertEqual(zero['rms_position_deviation_m'],0.)
        with self.assertRaises(ValueError):analyze({**args,'length_std_m':-.1})

    def test_real_extension_native_call_and_evidence_read(self):
        s=session()
        name='analysis__pcc_tolerance'
        declaration=next(t['function'] for t in native_tools('services') if t['function']['name']==name)
        self.assertIn('@1.0.0:',declaration['description'])
        args=dict(length_m=.4,bend_rad=[.3,-.2],length_std_m=.001,bend_std_rad=[.01,.02])
        result=s.apply_tool_call(dict(name=name,arguments=json.dumps({**args,'reason':'Rank independent fabrication/bend tolerances','evidence':[]})),caller=CALLER)
        self.assertEqual(result['execution_status'],'completed',result)
        self.assertEqual(result['tool_version'],'1.0.0')
        self.assertEqual(result['task_status'],'NOT_ASSESSED')
        self.assertEqual(result['analysis_status'],'LOCAL_GEOMETRY_ONLY')
        data=read(s.root/result['details_ref'])
        page=invoke(s,'evidence.read_json',dict(evidence_ref=result['details_ref'],pointer='/parameter_contributions'))
        self.assertEqual(read(s.root/page['details_ref'])['content'],data['parameter_contributions'])
        self.assertEqual(s.load()['used']['tool_calls'],2)
        ARTIFACTS['extension']=dict(root=str(s.root),declaration=declaration,result=result,data=data,read_result=page,
            validation='Real isolated mathematics through public native adapter; offline provider response, zero dynamics/API calls')


if __name__=='__main__':unittest.main()
