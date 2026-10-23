"""Focused S135 interface/numerical checks; no physical stepping or providers."""
from copy import deepcopy
import json
import unittest
import numpy as np
from schemas.platform import SessionInput
from tools.research.config import ROOT, resolve
from tools.research_tasks import task_adapter, assemble_acceptance
from tools.platform_tasks import compile_input
from tools.state_io import digest
from extensions.tendon_family.gvs_profile import reach_numerical, checked_control
from extensions.tendon_family.gvs_trajectory import TrajectoryWorkspace
from extensions.tendon_family.contracts import GVSTrajectoryParameters
from tests.research.test_tracking import TASK, fixture, evaluate
from contextlib import contextmanager


@contextmanager
def workspace_temp():
    import shutil
    from uuid import uuid4
    # Windows 0700 TemporaryDirectory ACL excludes the sandbox's reader token.
    folder=ROOT/'runs'/('s135-fixture-'+uuid4().hex)
    folder.mkdir(parents=True)
    try:yield folder
    finally:
        assert folder.resolve().is_relative_to((ROOT/'runs').resolve())
        shutil.rmtree(folder)


def configuration(tracking=False):
    cfg=deepcopy(resolve(ROOT/'configs/research/study.json')['configuration'])
    if tracking:
        initial=cfg['task']['initializer']
        cfg['task']=deepcopy(TASK)
        cfg['task'].update(status='development_valid', initializer=initial,
            source='S135 authorized development review of S132 geometry; original draft retained')
        cfg['seed']=cfg['task']['sampling']['seeds'][0]
        cfg['policy']['controller']['version']='12.0.0'
        cfg['policy']['backend']['version']='1.2.0'
        control=cfg['policy']['controller']['parameters']['data']
        control['settling']=None
        control['recipe'].update(reference_mode='free_progress',velocity_weight=0.,
            terminal_velocity_weight=0.,terminal_tip_speed_weight=0.,holding_tip_speed_weight=0.,
            progress_weight=.1,regression_weight=1.)
    return cfg


class ControlTests(unittest.TestCase):
    def test_model_preparation_and_registered_route(self):
        from extensions.tendon_family.backends import physics_for
        reach=SessionInput.model_validate(configuration())
        tracking=SessionInput.model_validate(configuration(True))
        a,b=reach_numerical(reach),reach_numerical(tracking)
        for field in ('coordinate_order','tendon_order','force_limits_n','measured_initial_state','nominal'):
            self.assertEqual(a[field],b[field])
        self.assertEqual(physics_for(reach)['identity'],physics_for(tracking)['identity'])
        from extensions.tendon_family.math_analysis import calculate_candidate_configuration
        from schemas.platform_analysis import TaskAnalysisProtocol
        models=[]
        for inp,numerical in ((reach,a),(tracking,b)):
            spec=resolve(ROOT/'configs/research/study.json')
            protocol=TaskAnalysisProtocol.model_validate({**spec['analysis_protocol'],
                'duration_s':inp.task.timing.duration_s,'period_s':inp.task.timing.control_period_s})
            binding=dict(candidate_id='offline-s135',configuration=dict(artifact_id='a'*64,media_type='application/json'),
                task_identity=digest(inp.task.model_dump(mode='json')),
                basis=inp.policy.controller.parameters.data['recipe']['basis'],coordinate_order=numerical['coordinate_order'])
            result=calculate_candidate_configuration(inp,binding,protocol,binding['configuration'],
                operating_points=['controller_start_input'])
            models.append(result.records[1]['model'] if hasattr(result,'records') else result['records'][1]['model'])
        for field in ('A','B','C','D','drift','x0','u0'):
            np.testing.assert_allclose(models[0][field],models[1][field])
        self.assertEqual(compile_input(configuration(True))['approval']['capabilities_ready'],True)
        for family in ('constant','free_progress'):
            cfg=configuration(family=='free_progress')
            self.assertEqual(task_adapter(cfg).control_reference()['kind'],family)
        invalid=configuration(True);invalid['policy']['controller']['version']='11.0.0'
        with self.assertRaisesRegex(ValueError,'TRACKING_CONTROLLER_UNSUPPORTED'):checked_control(invalid)

    def test_ordered_progress_pauses_and_independent_stationary_failure(self):
        cfg=configuration(True);adapter=task_adapter(cfg)
        v=np.asarray(cfg['task']['goal']['data']['vertices_m'])
        a=adapter.local_path_reference(v[0],0,.003,.001)
        self.assertEqual(a,adapter.local_path_reference(v[0],0,.003,.001))
        self.assertGreater(np.linalg.norm(np.asarray(a['position_m'])-v[0]),0)
        self.assertEqual(adapter.local_path_reference(v[-1],0,.003,.001)['segment'],0)
        self.assertEqual(adapter.local_path_reference(v[1],0,.003,.001)['segment'],1)
        out=evaluate(fixture([v[0].tolist()]*3,task=cfg['task']),cfg['task'])
        result=assemble_acceptance(cfg,out,dict(complete=True,solver_error_count=0,
            force_bound_violation_n=0,tracking_sampling_complete=True))
        self.assertFalse(result['accepted'])
        self.assertFalse(result['components']['evaluator:path_end']['passed'])
        self.assertEqual(len([c for c in adapter.analysis_requirements({}).constraints if c.kind=='unsupported']),5)

    def test_shared_nmpc_reach_geometric_and_timed_offline(self):
        for mode in ('constant','free_progress','timed'):
            cfg=configuration(mode!='constant')
            inp=SessionInput.model_validate(cfg)
            numerical=reach_numerical(inp)
            if mode=='timed':
                inp.task.goal.data.update(time_requirement='timed',times_s=[0.,.2,.4])
                inp=inp.model_copy(update={'task':inp.task.model_copy(update={'sampling':inp.task.sampling.model_copy(update={'window_s':(.02,.4)})})})
            recipe=deepcopy(inp.policy.controller.parameters.data['recipe'])
            recipe.update(reference_mode=mode,horizon=2,substeps=1,max_iterations=3,
                stopping_policy='research_work_v1',recover_returned_tensions=False,
                progress_weight=.1 if mode=='free_progress' else 0.,
                regression_weight=1. if mode=='free_progress' else 0.,
                relative_velocity_weight=.1 if mode=='timed' else 0.)
            p=GVSTrajectoryParameters.model_validate(recipe)
            x=numerical['measured_initial_state'];u=numerical['nominal']['u0']
            ws=TrajectoryWorkspace(inp.task,inp.robot,p,x,u,settling=cfg['policy']['controller']['parameters']['data']['settling'])
            result=ws.solve(x,u,elapsed_s=0.)
            self.assertTrue(result['accepted'],result['result'])
            self.assertEqual(np.asarray(result['tensions']).shape,(2,len(u)))
            self.assertEqual(np.asarray(result['states']).shape,(3,len(x)))
            self.assertTrue(np.isfinite(result['result']['objective_value']))
            from extensions.tendon_family.control_evidence import objective_components
            ws._prepare_tail()
            components=objective_components(ws,np.asarray(result['states']),np.asarray(result['tensions']),np.asarray(u))
            self.assertAlmostEqual(components['total'],result['result']['objective_value'],places=6)
            if mode=='free_progress':
                self.assertFalse(result['prediction_timing']['horizon_is_task_deadline'])
            if mode=='timed':
                ref=task_adapter(dict(task=inp.task.model_dump(mode='json')))
                expected,velocity=ref.reference_at(result['prediction_timing']['node_times_s'])
                np.testing.assert_allclose(result['prediction_timing']['positions_m'],expected)
                np.testing.assert_allclose(result['prediction_timing']['velocities_m_s'],velocity)
                with self.assertRaisesRegex(ValueError,'OUTSIDE_HORIZON'):ws.solve(x,u,elapsed_s=.4)

    def test_reward_components_and_saved_stage_configuration(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tools.rl.env import reward_terms
        from tools.rl import run
        from tools.research.config import rl_configuration
        from tools.research.contracts import RLRequest, RewardConfiguration
        from tools.rl.continuation import validate_compatibility
        defaults=resolve(ROOT/'configs/research/study.json')['control']['rl_defaults']
        cfg=rl_configuration(defaults,reward=dict(holding_speed=0.,path_error=2.,progress=3.,regression=4.))
        self.assertEqual(set(RewardConfiguration.model_fields),set(run.REWARD_TERMS))
        info=dict(position_error_m=.02,speed_m_s=.2,path_error_m=.005,path_progress_m=.012)
        before=dict(path_progress_m=.01)
        terms=reward_terms(cfg['reward'],info,before,np.array([1.,-2.]),np.array([10.,10.]),.01,.02)
        self.assertAlmostEqual(terms['position'],-4.)
        self.assertAlmostEqual(terms['path_error'],-.5)
        self.assertAlmostEqual(terms['progress'],.6)
        self.assertEqual(terms['holding_speed'],0.)
        self.assertAlmostEqual(terms['smoothness'],-.000025)
        info['path_progress_m']=.007
        self.assertAlmostEqual(reward_terms(cfg['reward'],info,before,np.zeros(2),np.ones(2),.01,.02)['regression'],-1.2)
        self.assertEqual(reward_terms(cfg['reward'],dict(numerical_failure=True),{},[],[],1,1),
                         dict(numerical_failure=cfg['reward']['failure_penalty']))
        with self.assertRaises(ValueError):rl_configuration(defaults,reward=dict(arbitrary_python='pass'))
        with self.assertRaises(ValueError):RLRequest(operation='resume',run_id='fixture',reward_overrides=dict(progress=2),rationale='forbidden')
        cfg.update(candidate=dict(identity='fixture'),control_object=dict(semantics='ideal_tension'),
                   task=dict(family='task.tracking'),seed=17,mode='direct',reference=None)
        changed=rl_configuration(cfg,reward=dict(progress=5.))
        validate_compatibility(cfg,changed)
        self.assertEqual(cfg['task'],changed['task'])
        with workspace_temp() as temp, patch.object(run,'RUNS',Path(temp)), \
                patch.object(run,'launch',return_value=dict(status='test_no_worker')):
            run.start(cfg,'s135-fixture')
            self.assertEqual(run.read_json(Path(temp)/'s135-fixture/config.json'),cfg)
            with patch.object(run,'reconcile',return_value=dict(consumed=dict(attempted_actions=0,active_seconds=0.))), \
                    patch.object(run,'worker_alive',return_value=False),patch('tools.rl.train.valid_checkpoint') as checkpoint:
                run.resume('s135-fixture')
                self.assertEqual(checkpoint.call_args.args[1],cfg)

    def test_rl_observation_and_direct_residual_mapping_without_physical_steps(self):
        import tempfile,hashlib
        from pathlib import Path
        from extensions.tendon_family.backends import physics_for
        from extensions.tendon_family.scene import assemble
        from extensions.tendon_family.mjcf import compile_xml
        from tools.platform_registry import registry
        from tools.rl.env import TensionEnv
        cfg=configuration(True);inp=SessionInput.model_validate(cfg);physics=physics_for(inp);scene=assemble(inp,physics)
        defaults=deepcopy(resolve(ROOT/'configs/research/study.json')['control']['rl_defaults'])
        with workspace_temp() as temp:
            xml=compile_xml(physics,scene,registry().parse(inp.policy.backend.parameters),Path(temp)/'robot.xml').read_text()
            defaults.update(mode='direct',reference=None,candidate=dict(xml=xml,sha256=hashlib.sha256(xml.encode()).hexdigest(),
                identity='fixture',task_identity='fixture-task'),control_object=dict(joint_names=physics['dofs'],
                tendon_names=[t['entity'] for t in physics['tendons']],
                actuator_names=[t['entity']+'_direct_tension' for t in physics['tendons']],tip_site='tip_site',semantics='ideal_tension'),
                task=dict(family='task.tracking',original=cfg['task'],initializer=scene['initial'],
                    control_period_s=scene['control_period_s'],duration_s=scene['duration_s'],
                    command_intervals=round(scene['duration_s']/scene['control_period_s'])))
            defaults['reward'].update(holding_speed=0.,path_error=1.,progress=1.)
            env=TensionEnv(defaults);obs,info=env.reset()
            self.assertEqual(obs.shape,env.observation_space.shape)
            self.assertIn('path_progress_m',info)
            np.testing.assert_allclose(env.map_action(np.zeros(env.channels))[0],env.upper/2)
            self.assertEqual(env.counts['attempted_physics_steps'],0)
            path=Path(temp)/'reference.npz';u=np.tile(env.upper/2,(env.horizon,1));np.savez(path,saved_tensions_n=u)
            defaults.update(mode='residual',reference=dict(path=str(path),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                candidate_identity='fixture',task_identity='fixture-task',tendon_order=env.tendons,control_period_s=env.control_dt))
            residual=TensionEnv(defaults);residual.reset()
            np.testing.assert_allclose(residual.map_action(np.zeros(env.channels))[0],u[0])
            defaults['reference']['task_identity']='wrong'
            with self.assertRaisesRegex(ValueError,'compatible'):TensionEnv(defaults)
            env.close();residual.close()


if __name__=='__main__':unittest.main()
