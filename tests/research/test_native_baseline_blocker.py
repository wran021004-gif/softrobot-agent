"""Focused fixtures and compilation only; no Provider or physics integration."""
from copy import deepcopy
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import Mock,patch
import unittest
import mujoco
import numpy as np
from schemas.platform import SessionInput
from tools.platform_store import plain
from tools.research import analysis
from tools.research.contracts import AnalysisRequest
from tools.research.native_control import baseline_identity,calculate
from tools.research.tool_readiness import native_baseline_failures
from extensions.tendon_family.contracts import MujocoParameters
from extensions.tendon_family.mujoco_analysis import NativeModel
from extensions.tendon_family.mjcf import compile_xml
from extensions.tendon_family.execution import resolve_execution
from tools.platform_registry import registry
from tests.research import test_task_analysis_contract as task_fixtures
from tests.research.test_research_reporting import offline_host


class NativeBaselineBlockerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        task_fixtures.TaskAnalysisTests.setUpClass()

    def setUp(self):
        self.cfg=deepcopy(task_fixtures.TaskAnalysisTests.spec['configuration'])
        self.ref=dict(artifact_id='a'*64,media_type='application/json')
        timing=self.cfg['task']['timing'];duration=timing['duration_s'];period=timing['control_period_s']
        order=[t['id'] for t in self.cfg['robot']['structure']['data']['tendons']]
        self.source=dict(source_kind='explicit_control_schedule_v1',task_acceptance='unmeasured',provenance={'fixture':True},
            trajectory=dict(times_s=[i*period for i in range(round(duration/period)+1)],
                tensions_n=[[.2]*len(order) for _ in range(round(duration/period))],tendon_order=order,
                design_identity='fixture-design',model_identity='fixture-model',task_identity='fixture-task'))
        self.point=dict(actual_time_s=0.,qpos_rad=[0.],qvel_rad_s=[0.],dof_order=['fixture'],prefix_tensions_n=[])
        self.query=AnalysisRequest(candidate=self.ref,operation='mujoco_direct_control_v1',model_source='mujoco',
            operating_point='standardized_initial_pretension',protocol=task_fixtures.TaskAnalysisTests.spec['analysis_protocol'],
            control_optimization=dict(source=dict(artifact_id='b'*64),settings=dict(version='local_control_search_v2',
                correction_window_s=[0,duration],knots_s=[0,duration-period],evaluation_requests=2,iterations=1)))

    def test_contact_protocol_is_explicit_and_legacy_identity_preserved(self):
        legacy=MujocoParameters().model_dump(mode='json')
        self.assertEqual(legacy,dict(integrator='implicitfast',timestep_source='task.timing.timestep_s',
            contact_model='mujoco_convex_native',friction=[0.,0.,0.]))
        with self.assertRaisesRegex(ValueError,'REQUIRES_ZERO_FRICTION'):
            MujocoParameters(contact_model='mujoco_frictionless_normal_v1',friction=(.1,0,0))
        old=resolve_execution(SessionInput.model_validate(self.cfg),registry())
        changed=deepcopy(self.cfg);changed['policy']['backend']['parameters']['data']['contact_model']='mujoco_frictionless_normal_v1'
        new=resolve_execution(SessionInput.model_validate(changed),registry())
        self.assertNotEqual(old['identity'],new['identity'])
        self.assertEqual(old['dynamics_model_identity'],new['dynamics_model_identity'])

    def test_native_and_replay_compile_same_contact_and_inertia(self):
        from tools.research.physical_replay import model_context
        native_old=NativeModel(self.cfg)
        cfg=deepcopy(self.cfg);cfg['policy']['backend']['parameters']['data']['contact_model']='mujoco_frictionless_normal_v1'
        native=NativeModel(cfg);inp,physics,scene,_=model_context(cfg)
        scene['control']['tension_execution_mode']='ideal_tension'
        xml=BytesIO();compile_xml(physics,scene,registry().parse(inp.policy.backend.parameters),xml)
        replay=mujoco.MjModel.from_xml_string(xml.getvalue().decode())
        self.assertTrue(np.all(native_old.model.geom_condim==3))
        self.assertTrue(np.all(native.model.geom_condim==1))
        for name in ('geom_condim','geom_friction','body_mass','body_inertia','dof_damping','jnt_stiffness','actuator_ctrlrange','actuator_forcerange'):
            np.testing.assert_array_equal(getattr(native.model,name),getattr(replay,name))
        for name in ('body_mass','body_inertia','dof_damping','jnt_stiffness','geom_contype','geom_conaffinity'):
            np.testing.assert_array_equal(getattr(native_old.model,name),getattr(native.model,name))
        for key in ('solver','jacobian','integrator','timestep'):
            self.assertEqual(getattr(native.model.opt,key),getattr(replay.opt,key))
        self.assertEqual(native.cost['physics_steps'],0)

    def test_baseline_key_tracks_physics_state_input_candidate_and_engine(self):
        key=baseline_identity(self.cfg,self.ref,self.point,self.source)
        other=deepcopy(self.source);other['provenance']={'different_method':'T1'}
        self.assertEqual(key,baseline_identity(self.cfg,self.ref,self.point,other))
        changed=deepcopy(self.source);changed['trajectory']['tensions_n'][0][0]=.3
        self.assertNotEqual(key,baseline_identity(self.cfg,self.ref,self.point,changed))
        point=deepcopy(self.point);point['qvel_rad_s']=[.1]
        self.assertNotEqual(key,baseline_identity(self.cfg,self.ref,point,self.source))
        cfg=deepcopy(self.cfg);cfg['policy']['backend']['parameters']['data']['contact_model']='mujoco_frictionless_normal_v1'
        self.assertNotEqual(key,baseline_identity(cfg,self.ref,self.point,self.source))
        with patch.object(mujoco,'__version__','different-engine'):
            self.assertNotEqual(key,baseline_identity(self.cfg,self.ref,self.point,self.source))
        self.assertNotEqual(key,baseline_identity(self.cfg,dict(artifact_id='c'*64),self.point,self.source))

    def test_original_dispatch_blocks_cross_method_baseline_before_charge(self):
        old=dict(artifact_id='c'*64,media_type='application/json')
        key=baseline_identity(self.cfg,self.ref,self.point,self.source)
        failure=dict(identity=key,failure_class='native_baseline_execution_blocker',scientific_infeasibility=False)
        raw=dict(candidate=self.ref,implementation='fixture-freeze',status='execution_incomplete',
            operation='mujoco_nonlinear_task_capability_v1',native_baseline_failure=failure)
        spec=deepcopy(task_fixtures.TaskAnalysisTests.spec);spec['capabilities']=['analysis']
        host,s=offline_host({old['artifact_id']:raw,'b'*64:self.source},spec=spec,analysis_results=[old],freeze='fixture-freeze')
        host.store.lookup.return_value=None
        candidate=dict(candidate_id='fixture',configuration=self.cfg,configuration_reference=self.ref,
            source_identity='fixture-source',profile_identity='fixture-profile')
        with patch.object(analysis,'verify_candidate',return_value=candidate), \
                patch('tools.research.config.frozen_analysis_protocol',return_value=plain(self.query.protocol)), \
                patch('tools.research.numerics.native_point',return_value=deepcopy(self.point)), \
                patch('tools.research.physical_replay.binding'):
            before=deepcopy(s)
            out=analysis.dispatch(host,self.query,'fixture',guard=Mock())
            self.assertEqual(out['reason'],'KNOWN_NATIVE_BASELINE_EXECUTION_BLOCKER')
            self.assertEqual(out['additional_analysis_evaluations'],0)
            self.assertEqual(out['failure']['reference'],old)
            self.assertEqual(s,before)
            host.store.reserve.assert_not_called();host.store.transaction.assert_not_called()
        s['freeze']='new-implementation'
        self.assertEqual(native_baseline_failures(host,self.ref),[])

    def test_failed_first_rollout_carries_shared_identity_and_no_optimization(self):
        n=len(self.source['trajectory']['tendon_order'])
        native=Mock(limits=np.array([[0.,8.]]*n),tendons=self.source['trajectory']['tendon_order'])
        native.cost=dict(model_builds=1,physics_steps=168,physics_step_attempts=169)
        error=ValueError('fixture-engine-failure');error.mujoco_diagnostic=dict(time_before_call_s=.168)
        native.rollout_sequence.side_effect=error
        checkpoints=[]
        with patch('extensions.tendon_family.mujoco_analysis.NativeModel',return_value=native):
            with self.assertRaisesRegex(ValueError,'fixture-engine-failure'):
                calculate(self.cfg,dict(candidate=self.ref),self.query,deepcopy(self.point),None,
                    dict(schedule=self.source),checkpoint=lambda name,value:checkpoints.append((name,value)))
        self.assertEqual(error.native_baseline_failure['identity'],baseline_identity(self.cfg,self.ref,self.point,self.source))
        self.assertEqual(error.native_baseline_failure['completed_optimization_evaluations'],0)
        self.assertFalse(error.native_baseline_failure['scientific_infeasibility'])
        self.assertEqual(checkpoints[-1][1]['completed_rollouts'],0)
        native.rollout_sequence.assert_called_once()

    def test_snapshot_distinguishes_pre_call_and_partial_new_contacts(self):
        from extensions.tendon_family.backends import MujocoFailureSnapshot
        m=SimpleNamespace(opt=SimpleNamespace(timestep=.001,integrator=3,solver=2,jacobian=2,iterations=100),
            geom=lambda i:SimpleNamespace(name=str(i)))
        d=SimpleNamespace(time=.168,ncon=0,nefc=0,qpos=np.zeros(1),qvel=np.zeros(1),ctrl=np.array([.2]),
            actuator_force=np.array([-.2]),warning=[])
        def failure(model,data):
            data.ncon=2;data.nefc=8;data.contact=[SimpleNamespace(geom1=0,geom2=1,dist=-.0004)]
            raise ValueError('fixture-factorization-failure')
        with patch.object(mujoco,'mj_stateSize',return_value=1),patch.object(mujoco,'mj_getState'):
            snapshot=MujocoFailureSnapshot(m,'fixture-model')
            with self.assertRaises(ValueError) as exc:snapshot.call(d,failure,'fixture')
        diagnostic=exc.exception.mujoco_diagnostic
        self.assertEqual(diagnostic['constraints_before_call'],dict(ncon=0,nefc=0))
        self.assertEqual(diagnostic['partial_failed_call_observations']['ncon'],2)
        self.assertFalse(diagnostic['partial_failed_call_observations']['valid_complete_state'])

    def test_worker_persists_baseline_failure_without_relabeling_success(self):
        from tools.research.execution_worker import main
        request=dict(kind='candidate_analysis',configuration={},binding={},query={},implementation='fixture-freeze')
        error=ValueError('fixture-failure');error.native_baseline_failure=dict(identity='fixture-key',scientific_infeasibility=False)
        with patch('sys.argv',['worker','fixture/request.json']),patch('tools.research.execution_worker.contain_worker_children'), \
                patch('tools.research.execution_worker.read',return_value=request), \
                patch('tools.research.execution_worker.atomic_json') as writer, \
                patch('tools.research.analysis.calculate',side_effect=error):main()
        destination,result=writer.call_args.args
        self.assertEqual(destination.name,'result.json')
        self.assertEqual(result['status'],'execution_incomplete')
        self.assertEqual(result['native_baseline_failure'],error.native_baseline_failure)


if __name__=='__main__':unittest.main()
