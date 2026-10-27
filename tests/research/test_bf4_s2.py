"""S2 protocol and stopped-search continuation checks; no scientific integrations."""
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np

from tools.state_io import read
from tools.research.config import ROOT, resolve
from tools.research.contracts import AnalysisRequest
from tools.research.native_control import calculate


class S2Tests(unittest.TestCase):
    def test_fair_task_and_grants(self):
        f=read(ROOT/'configs/research/bf4_tracking_s2_freeze.json')
        old=read(ROOT/'configs/research/bf4_tracking_freeze_v1.json')
        self.assertEqual(f['candidate_requests'],old['candidate_requests'])
        self.assertEqual(f['canonical_task_identity'],old['canonical_task_identity'])
        self.assertEqual(f['search_settings']['safety_margin_fraction'],0)
        self.assertEqual(len(f['groups']),6)
        specs=[resolve(ROOT/g['study_file']) for g in f['groups']]
        for s in specs:
            self.assertEqual(s['canonical_task_identity'],f['canonical_task_identity'])
            self.assertEqual(s['native_control_limits'],dict(evaluation_requests=101,iterations=4,knots_s=4))
            self.assertEqual(s['budgets']['physical_launches'],3)
        self.assertEqual(len({s['study_id'] for s in specs}),6)
        for name in old['candidate_order']:
            self.assertEqual([g['initial_tension_n'] for g in f['groups'] if g['design']==name],[.2,.6])

    def test_rejected_proxy_resumes_without_reintegrating_prefix(self):
        spec=resolve(ROOT/'configs/research/study_bf4_tracking_s2_full_span_02.json')
        cfg=spec['configuration'];times=np.arange(31)*.02
        from tools.research_tasks import task_adapter
        options=task_adapter(cfg).control_search_options()
        # Synthetic position-only fixture; the Native engine itself is mocked.
        reference=task_adapter(cfg).reference_at(times)[0]
        source=dict(trajectory=dict(times_s=times.tolist(),tensions_n=np.full((30,6),.2).tolist(),
            tendon_order=['t'+str(i) for i in range(6)],task_identity='task',model_identity='model',design_identity='design'),provenance={})
        ref=dict(artifact_id='a'*64,media_type='application/json')
        settings=read(ROOT/'configs/research/bf4_tracking_s2_freeze.json')['search_settings']
        query=AnalysisRequest.model_validate(dict(candidate=ref,operation='mujoco_direct_control_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],control_optimization=dict(source=ref,settings=settings)))
        class Fake:
            def __init__(self,_):
                self.limits=np.array([[0.,8.]]*6);self.tendons=source['trajectory']['tendon_order'];self.scene=dict(forces=[],semantics={})
                self.cost=dict(rollouts=0,physics_steps=0,model_builds=1)
            def restore(self,_):return None
            def rollout_sequence(self,start,t,u,**kw):
                self.cost['rollouts']+=1;self.cost['physics_steps']+=600
                p=reference.copy();p[:,0]+=.0204-.04*np.asarray(u).mean()
                return dict(times_s=t.tolist(),tip_positions_m=p.tolist(),tip_velocities_m_s=np.zeros_like(p).tolist())
        point=dict(actual_time_s=0.,prefix_tensions_n=[],phase='interval_start_native',input_units='N')
        binding=dict(candidate=ref,effective_configuration_identity='cfg')
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',Fake),patch('tools.research.native_analysis.applicability',return_value={}),patch('tools.research.native_analysis.assessment',return_value={}),patch('tools.research.analysis.scoped_result',side_effect=lambda v,*_:v):
            first=calculate(cfg,binding,query,point,SimpleNamespace(),dict(schedule=source,source=ref))
            result=first['native_dynamics']['optimization'];self.assertEqual(result['stop_reason'],'local_target_reached')
            rejected=result['candidates'][-1]['sequence_hash']
            resumed=calculate(cfg,binding,query,point,SimpleNamespace(),dict(schedule=source,source=ref,resume=result,rejected_sequences=[rejected]))
            raw=resumed['native_dynamics'];new=raw['optimization']
            self.assertEqual(raw['cost']['reused_native_callbacks'],len(result['candidates']))
            self.assertEqual(raw['cost']['rollouts']+len(result['candidates']),len(new['candidates']))
            self.assertLessEqual(len(new['candidates']),101)
            self.assertNotEqual(new['candidates'][-1]['sequence_hash'],rejected)
            self.assertFalse(new['best']['task_gap']['accepted'])


if __name__=='__main__':unittest.main()
