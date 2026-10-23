"""S139 offline contracts and mocked integration; never call real mj_step."""
from copy import deepcopy
import gzip
import hashlib
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import zipfile

import numpy as np

from schemas.platform import SessionInput, BackendResult
from tools.platform_registry import registry
from tools.research.config import ROOT
from tools.research_tasks import task_adapter, assemble_acceptance
from extensions.tendon_family.backends import physics_for, playback_tensions, MujocoBackend
from extensions.tendon_family.scene import assemble, assemble_physical
from extensions.tendon_family.mjcf import compile_xml
from tests.research.test_s135_control import configuration, workspace_temp


class ExecutionTests(unittest.TestCase):
    def test_physical_scene_needs_no_goal_or_controller(self):
        reach=SessionInput.model_validate(configuration())
        tracking=SessionInput.model_validate(configuration(True))
        physics=physics_for(reach)
        # Only physical inputs exist in this fixture. Goal/policy access fails.
        physical=SimpleNamespace(robot=reach.robot,task=SimpleNamespace(
            environment=reach.task.environment,initializer=reach.task.initializer,timing=reach.task.timing))
        a=assemble_physical(physical,physics)
        same_clock=tracking.model_copy(update={'task':tracking.task.model_copy(update={'timing':reach.task.timing})})
        self.assertEqual(a,assemble_physical(same_clock,physics_for(same_clock)))
        self.assertFalse({'target_world_m','time_reference','task_reference','control'} & a.keys())
        scene=assemble(tracking,physics_for(tracking))
        self.assertEqual(scene['task_reference']['kind'],'free_progress')
        self.assertNotIn('target_world_m',scene)
        self.assertNotIn('time_reference',scene)
        self.assertNotIn('target_world_m',scene['control']['reference'])

    def test_tracking_xml_and_actual_failure_evidence_are_preserved(self):
        with zipfile.ZipFile(ROOT/'evidence/s135_development/tracking_evidence.zip') as archive:
            cfg=json.loads(archive.read('configuration.json'))
            inp=SessionInput.model_validate(cfg)
            scene=assemble(inp,physics_for(inp))
            with workspace_temp() as folder:
                xml=compile_xml(physics_for(inp),scene,registry().parse(inp.policy.backend.parameters),folder/'robot.xml')
                self.assertEqual(hashlib.sha256(xml.read_bytes()).hexdigest(),
                    hashlib.sha256(archive.read('robot.xml')).hexdigest())
            observations=json.loads(archive.read('controller_observations.json'))
            self.assertEqual(len(observations),20)
            self.assertTrue(all(o['plan_accepted'] for o in observations))
            self.assertTrue(all(o['optimization_raw_status']=='Maximum_Iterations_Exceeded' for o in observations))
            result=BackendResult.model_validate(json.loads(archive.read('simulation_result.json')))
            saved=json.loads(archive.read('evaluation.json'))
            evaluation=registry().get('evaluate.tracking',kind='evaluator').resolve()(
                inp.task,result,saved['source'],registry(),saved['candidate_id'])
            self.assertEqual(evaluation.validity,'valid')
            self.assertFalse(evaluation.task_success)
            self.assertEqual(evaluation.model_dump(mode='json')['metrics'],saved['metrics'])
            profile=json.loads(archive.read('profile.json'))
            acceptance=assemble_acceptance(cfg,evaluation,profile)
            self.assertEqual(acceptance['status'],'valid_failure')
            self.assertFalse(acceptance['accepted'])

    def test_fixed_playback_without_target_retains_numerical_failure_and_bounds(self):
        import mujoco
        inp=SessionInput.model_validate(configuration(True));physics=physics_for(inp);scene=assemble(inp,physics)
        scene['duration_s']=scene['control_period_s']
        commands=np.zeros((1,len(physics['tendons'])))
        with workspace_temp() as folder,patch.object(mujoco,'mj_step') as step:
            # No engine time advance: existing failure detector must preserve it.
            result=playback_tensions(inp,physics,scene,commands,folder)
            self.assertEqual(step.call_count,1)
            self.assertEqual(result['status'],'incomplete')
            self.assertEqual(result['failure']['reason'],'MUJOCO_NUMERICAL_FAILURE')
            self.assertNotIn('position_error_m',result['samples'][0])
            self.assertIn('tip_velocity_m_s',result['samples'][0])
            step.reset_mock()
            with self.assertRaisesRegex(ValueError,'GRID_OR_TENSION_MISMATCH'):
                playback_tensions(inp,physics,scene,commands-1.,folder)
            step.assert_not_called()

    def test_backend_exports_post_step_velocity_from_engine_jacobian(self):
        import mujoco
        from extensions.tendon_family.signals import observation_specs
        inp=SessionInput.model_validate(configuration(True))
        backend=MujocoBackend();backend.compile(inp,registry())
        backend.scene['duration_s']=inp.task.timing.control_period_s
        backend.scene['control']['mode']='synthetic_fixed_tension_fixture'
        channels=len(backend.physics['tendons'])
        class FixedFixture:
            def configure(self,physics,plan):self.observations=[]
            def command(self,t,geometry,q,v):
                self.last=dict(desired_tension_n=[.1]*channels)
                self.observations.append(dict(time_s=t))
                return np.full(channels,.1)
        backend.initialize(inp.task.initializer.parameters,FixedFixture())
        expected={}
        def synthetic_step(model,data):
            # Fabricated transition only; exercises serialization and phases.
            data.time+=model.opt.timestep
            data.qvel[:]=.001
            mujoco.mj_forward(model,data)
            jac=np.zeros((3,model.nv))
            mujoco.mj_jacSite(model,data,jac,None,model.site('tip_site').id)
            expected['velocity']=(jac@data.qvel).tolist()
        with workspace_temp() as folder,patch.object(mujoco,'mj_step',side_effect=synthetic_step) as step:
            result=backend.run(folder,None)
            self.assertEqual(step.call_count,20)
            velocity=next(s for s in result.signals if s.spec.name=='tip_velocity')
            self.assertEqual(velocity.spec.phase,'post_step')
            self.assertEqual(velocity.spec.units,'m/s')
            self.assertEqual(velocity.times_s,[.02])
            np.testing.assert_allclose(velocity.values,[expected['velocity']],rtol=0,atol=1e-15)
            tension=next(s for s in result.signals if s.spec.name=='tendon_tension')
            self.assertEqual(tension.times_s,[0.])
            self.assertEqual(tension.spec.phase,'pre_step_solver')
            rows=json.loads(gzip.decompress((folder/'trajectory.json.gz').read_bytes()))
            self.assertNotIn('position_error_m',rows[0])
            self.assertIn(velocity.spec,observation_specs(inp,registry()))

    def test_reach_task_diagnostics_derive_error_from_physical_output(self):
        cfg=configuration();adapter=task_adapter(cfg)
        target=adapter.reference_at([0.])[0][0]
        raw=dict(samples=[dict(time_s=cfg['task']['timing']['duration_s'],
            tip_m=(target+[.03,0.,0.]).tolist(),speed_m_s=.04)])
        violations=adapter.violation_samples(raw)['samples']
        positions=[v for v in violations if v['constraint']!='holding_max_speed_m_s']
        self.assertTrue(positions)
        for value in positions:
            self.assertAlmostEqual(value['value'],.03)
            self.assertEqual(value['raw_pointer'],'/samples/0/tip_m')
            self.assertEqual(value['derivation']['reference_m'],target.tolist())
        self.assertNotIn('position_error_m',raw['samples'][0])

    def test_fixed_schedule_binding_and_task_evaluation_for_both_tasks(self):
        from tools.research.physical_replay import model_context, binding, playback_profile
        from tools.state_io import digest
        source=dict(artifact_id='a'*64,media_type='application/json')
        for tracking in (False,True):
            cfg=configuration(tracking)
            inp,physics,scene,spec=model_context(cfg)
            count=round(inp.task.timing.duration_s/inp.task.timing.control_period_s)
            order=[t['entity'] for t in physics['tendons']]
            times=(np.arange(count+1)*inp.task.timing.control_period_s).tolist()
            trajectory=dict(times_s=times,tensions_n=np.full((count,len(order)),.1).tolist(),
                tendon_order=order,task_identity=digest(cfg['task']),model_identity=spec['identity'],
                design_identity=spec['design_identity'])
            binding(cfg,trajectory)
            wrong=deepcopy(trajectory);wrong['task_identity']='b'*64
            with self.assertRaisesRegex(ValueError,'MISMATCH'):binding(cfg,wrong)
            if tracking:
                vertices=np.asarray(inp.task.goal.data['vertices_m'])
                positions=np.vstack([vertices[0],np.linspace(vertices[0],vertices[1],count//2),
                    np.linspace(vertices[1],vertices[2],count-count//2)])
            else:positions=np.tile(task_adapter(cfg).reference_at([0.])[0][0],(count+1,1))
            # Synthetic perfect records exercise settlement; no performance claim.
            raw=dict(status='completed',physics_steps=count*20,tendon_order=order,
                samples=[dict(time_s=t,tip_m=x.tolist(),speed_m_s=0.,actual_tension_n=[.1]*len(order))
                    for t,x in zip(times,positions)])
            result=BackendResult(solver_status='completed',backend_id='synthetic.s139',model_id='synthetic',
                signals=[dict(spec=inp.task.observations[0],times_s=times[1:],values=positions[1:].tolist())],
                data=dict(contract='platform.empty',data={}),limitations=['Synthetic fixture; no physical execution'],
                initial_state=inp.task.initializer.parameters,seed=inp.seed)
            evaluator=registry().get(inp.task.evaluator.extension_id,inp.task.evaluator.version,'evaluator').resolve()
            evaluation=evaluator(inp.task,result,source,registry(),'s139-fixture')
            profile=playback_profile(inp,raw,evaluation)
            acceptance=assemble_acceptance(cfg,evaluation,profile,motion=raw['samples'])
            self.assertTrue(acceptance['accepted'],acceptance)
            if tracking:
                self.assertNotIn('sampled_settling',profile)
                self.assertTrue(profile['tracking_sampling_complete'])
                bad_grid=deepcopy(raw);bad_grid['samples'][1]['time_s']+=.001
                self.assertFalse(playback_profile(inp,bad_grid,evaluation)['tracking_sampling_complete'])
            else:self.assertEqual(profile['sampled_settling']['max_error_m'],0.)
            failed=deepcopy(raw);failed['status']='incomplete'
            self.assertFalse(playback_profile(inp,failed,evaluation)['complete'])
            self.assertEqual(playback_profile(inp,failed,evaluation)['solver_error_count'],1)
            over=deepcopy(raw);over['samples'][-1]['actual_tension_n'][0]=physics['tendons'][0]['force_limit_n']+1.
            profile=playback_profile(inp,over,evaluation)
            self.assertAlmostEqual(profile['force_bound_violation_n'],1.)
            self.assertFalse(assemble_acceptance(cfg,evaluation,profile,motion=raw['samples'])['accepted'])

    def test_reach_rl_uses_frozen_task_without_duplicate_target(self):
        from tools.rl.env import TensionEnv, reward_terms
        from tools.research.config import resolve
        cfg=configuration();inp=SessionInput.model_validate(cfg)
        physics=physics_for(inp);scene=assemble(inp,physics)
        defaults=deepcopy(resolve(ROOT/'configs/research/study.json')['control']['rl_defaults'])
        with workspace_temp() as folder:
            xml=compile_xml(physics,scene,registry().parse(inp.policy.backend.parameters),folder/'robot.xml').read_text()
            defaults.update(mode='direct',reference=None,
                candidate=dict(xml=xml,sha256=hashlib.sha256(xml.encode()).hexdigest(),identity='synthetic.s139',task_identity='fixture'),
                control_object=dict(joint_names=physics['dofs'],tendon_names=[t['entity'] for t in physics['tendons']],
                    actuator_names=[t['entity']+'_direct_tension' for t in physics['tendons']],tip_site='tip_site',semantics='ideal_tension'),
                task=dict(family='task.reach',original=cfg['task'],initializer=scene['initial'],
                    control_period_s=scene['control_period_s'],duration_s=scene['duration_s'],
                    command_intervals=round(scene['duration_s']/scene['control_period_s']),acceptance=dict(holding_steps=[0])))
            env=TensionEnv(defaults)
            obs,info=env.reset()
            error=np.asarray(cfg['task']['goal']['data']['target_m'])-info['tip_m']
            np.testing.assert_allclose(obs[len(physics['dofs'])*2:len(physics['dofs'])*2+3],error/env.position_scale,rtol=1e-6)
            self.assertAlmostEqual(info['position_error_m'],np.linalg.norm(error))
            terms=reward_terms(env.reward,info,info,np.zeros(env.channels),env.upper,env.position_scale,env.speed_scale,True)
            self.assertAlmostEqual(terms['position'],-env.reward['position']*(np.linalg.norm(error)/env.position_scale)**2)
            self.assertEqual(env.counts['attempted_physics_steps'],0)
            env.close()


if __name__=='__main__':unittest.main()
