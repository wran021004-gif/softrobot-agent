"""Changed native control boundaries; fixtures are not scientific evidence."""
from copy import deepcopy
import unittest
import numpy as np
from tools.platform_store import plain
from tools.research.contracts import AnalysisRequest
from tools.research.native_analysis import applicability, assessment
from tools.research.local_control_search import search
from tests.research import test_mujoco_analysis as native_fixtures
from tests.research import test_local_control_search as search_fixtures
from schemas.platform import SessionInput


class NativeControlTests(unittest.TestCase):
    def test_study_limits_reject_before_worker_or_reservation(self):
        from unittest.mock import Mock, patch
        from tools.research import analysis
        from tools.research.config import ROOT, resolve
        from tests.research.test_research_reporting import offline_host
        spec=resolve(ROOT/'configs/research/study_c3_autonomous.json')
        family_spec=resolve(ROOT/'configs/research/study_c3_blank_autonomous.json')
        self.assertEqual(family_spec['native_control_limits'],spec['native_control_limits'])
        ref=dict(artifact_id='a'*64,media_type='application/json')
        host,_=offline_host({},spec=spec)
        host.store.lookup.return_value=None
        query=dict(candidate=ref,operation='mujoco_direct_control_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=spec['analysis_protocol'],
            control_optimization=dict(source=ref,settings=dict(version='local_control_search_v2',
                correction_window_s=[0,.35],knots_s=[0,.12,.23,.34],evaluation_requests=60,iterations=2)))
        for field,value in (('evaluation_requests',61),('iterations',3)):
            oversized=deepcopy(query);oversized['control_optimization']['settings'][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'STUDY_NATIVE_CONTROL_LIMIT: '+field):
                analysis.dispatch(host,oversized,'test',guard=Mock())
        with patch.object(analysis,'verify_candidate',side_effect=ValueError('PASSED_LIMIT_ADMISSION')):
            with self.assertRaisesRegex(ValueError,'PASSED_LIMIT_ADMISSION'):
                analysis.dispatch(host,query,'test',guard=Mock())
        host.store.reserve.assert_not_called();host.store.transaction.assert_not_called()

    def test_native_limits_visible_and_legacy_catalog_unchanged(self):
        from tests.research.test_c1_method_context import C1Archive
        from tools.research.task_constraints import mathematical_method_view, mathematical_catalog
        archive=C1Archive();host,s=archive.host();reference=s['reference_candidate']
        legacy=mathematical_catalog(mathematical_method_view(host,reference))
        self.assertNotIn('execution_limits',legacy['methods']['mujoco_direct_control_v1'])
        limits=dict(evaluation_requests=60,iterations=2,knots_s=4)
        s['spec']['native_control_limits']=limits
        current=mathematical_catalog(mathematical_method_view(host,reference))
        self.assertEqual(current['methods']['mujoco_direct_control_v1']['execution_limits'],limits)
        self.assertEqual(set(current['methods']),set(legacy['methods']))
        host.store.transaction.assert_not_called();host.store.reserve.assert_not_called()
        archive.archive.close()

    def test_schema_requires_source_and_explicit_v2_window(self):
        native_fixtures.NativeAnalysisTests.setUpClass();f=native_fixtures.NativeAnalysisTests();f.setUp()
        q=plain(f.q);q['operation']='mujoco_direct_control_v1'
        with self.assertRaises(ValueError):AnalysisRequest.model_validate(q)
        q['control_optimization']=dict(source=f.t.ref,settings=dict(version='local_control_search_v2',
            knots_s=[.30,.34],correction_window_s=[.30,.35]))
        query=AnalysisRequest.model_validate(q)
        inp=SessionInput.model_validate(f.t.cfg)
        fit=applicability(f.t.req,query,assessment(inp,f.t.req),dict(actual_time_s=.30,integration_state=[1]))
        self.assertFalse(fit['full_task_supported'])
        q['control_optimization']['settings']['correction_window_s']=[.31,.35]
        q['control_optimization']['settings']['knots_s']=[.31,.34]
        query=AnalysisRequest.model_validate(q)
        fit=applicability(f.t.req,query,assessment(inp,f.t.req),dict(actual_time_s=.31,integration_state=[1]))
        self.assertTrue(any('All task' in r for r in fit['reasons']))

    def test_native_stop_does_not_claim_physical_acceptance(self):
        f=search_fixtures.LocalSearchTests();f.setUp();callback=f.evaluator()
        def evaluate(*args):
            row=callback(*args);row['task_gap']['accepted']=False
            return row
        result=search([search_fixtures.start()],evaluate,dict(evaluation_requests=15),evaluation_kind='native_short_rollout',
            stop_when=lambda row:row['task_gap']['normalized_gap']==0)
        self.assertEqual(result['stop_reason'],'local_target_reached')
        self.assertFalse(result['best']['task_gap']['accepted'])
        self.assertEqual(result['cost_feedback']['new_physical_evaluations'],0)
        self.assertTrue(result['best']['local_solver']['success'])

    def test_recorded_sequence_search_matches_without_new_integrations(self):
        from pathlib import Path
        from tools.state_io import read
        from tools.research.numerics import archived
        root=Path(__file__).resolve().parents[2]
        summary=read(root/'evidence/mujoco_direct_stage_b/summary.json')
        value=archived('evidence/mujoco_direct_stage_b/study',summary['optimization_reference'])
        raw=value['native_dynamics'];old=raw['optimization'];settings=value['requested_operation']['control_optimization']['settings']
        initial=dict(id='native',schedule=raw['original_schedule'],limits=[8]*6,
            task_options=dict(target=[.29,.035,.19],holding_start=.30,position_limit=.01,terminal_position_limit=.01,speed_limit=.02))
        calls=[]
        def recorded(start,schedule,metadata):
            row=deepcopy(old['candidates'][len(calls)])
            # SLSQP's last bits vary with the installed numerical runtime.
            # Original archived arrays and physical schedule identities stay exact.
            np.testing.assert_allclose(metadata['coefficients_n'],row['coefficients_n'],rtol=1e-10,atol=1e-12)
            calls.append(metadata)
            return {k:row[k] for k in ('reference','outputs','measure','task_gap','cost_s','independent_evaluation_executed')}
        result=search([initial],recorded,settings,evaluation_kind='native_short_rollout',
            rank_key=lambda row:(row['measure']['signed_maximum_excess'],row['measure']['sum_normalized_excess']),
            stop_when=lambda row:row['measure']['signed_maximum_excess']<=-settings['safety_margin_fraction'])
        np.testing.assert_allclose(result['best']['coefficients_n'],old['best']['coefficients_n'],rtol=1e-10,atol=1e-12)
        self.assertEqual(len(calls),23)
        self.assertEqual(result['iterations_started'],2)
        self.assertEqual(len(result['local_responses']),1)
        # A newly replayed structure can reenter native math without NMPC.
        from tools.research.numerics import native_point
        from tests.research.test_research_reporting import offline_host
        replay_ref=summary['replays']['baseline']['reference']
        replay=archived('evidence/mujoco_direct_stage_b/study',replay_ref)
        replay_raw=archived('evidence/mujoco_direct_stage_b/study',replay['raw_reference'])
        candidate=archived('evidence/mujoco_direct_stage_b/study',summary['candidate'])
        host,_=offline_host({replay_ref['artifact_id']:replay,replay['raw_reference']['artifact_id']:replay_raw},physical_replays=[replay_ref])
        query=AnalysisRequest.model_validate(value['requested_operation']).model_copy(update=dict(saved_state=None,execution=replay_ref,update_id=30))
        point=native_point(host,query,candidate['configuration'])
        self.assertEqual(point['qpos_rad'],raw['initial_state']['qpos_rad'])
        self.assertEqual(point['qvel_rad_s'],raw['initial_state']['qvel_rad_s'])
        self.assertEqual(len(point['native_replay']['rows']),30)
        self.assertTrue(all(r['time_s']<=.30+1e-12 for r in point['native_replay']['rows']))

    def test_protected_replay_keeps_only_its_linked_raw_evidence_readable(self):
        from unittest.mock import patch
        from tests.research.test_research_reporting import offline_host
        from tools.research.core import read_evidence
        result=dict(artifact_id='a'*64,media_type='application/json')
        raw=dict(artifact_id='b'*64,media_type='application/json')
        other=dict(artifact_id='c'*64,media_type='application/json')
        values={result['artifact_id']:dict(raw_reference=raw),raw['artifact_id']:dict(samples=[{'time_s':.30}]),other['artifact_id']:dict(secret_fixture=True)}
        host,current=offline_host(values,physical_replays=[result])
        before=deepcopy(current)
        with patch('tools.research.core.protected',return_value=True):
            self.assertEqual(read_evidence(host,dict(reference=raw,pointer='/samples/0/time_s'),record_read=False),.30)
            with self.assertRaisesRegex(ValueError,'PROTECTED_EVIDENCE'):
                read_evidence(host,dict(reference=other),record_read=False)
        self.assertEqual(current,before)


    def test_rejected_proxy_resumes_without_reintegrating_prefix(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from tools.research.config import ROOT, resolve
        from tools.research.native_control import calculate
        from tools.state_io import read
        spec=resolve(ROOT/'configs/research/study_tracking_public.json')
        cfg=spec['configuration'];times=np.arange(31)*.02
        from tools.research_tasks import task_adapter
        options=task_adapter(cfg).control_search_options()
        # Synthetic position-only fixture; the Native engine itself is mocked.
        reference=task_adapter(cfg).reference_at(times)[0]
        source=dict(trajectory=dict(times_s=times.tolist(),tensions_n=np.full((30,6),.2).tolist(),
            tendon_order=['t'+str(i) for i in range(6)],task_identity='task',model_identity='model',design_identity='design'),provenance={})
        ref=dict(artifact_id='a'*64,media_type='application/json')
        settings=read(ROOT/'configs/research/bf4_tracking_freeze_v1.json')['search_settings']
        settings.update(evaluation_requests=101,iterations=4,safety_margin_fraction=0)
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
