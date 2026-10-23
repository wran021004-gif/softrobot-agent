"""Cross-branch regressions; physical transitions here are explicitly mocked."""
from copy import deepcopy
import subprocess
import sys
import unittest
from unittest.mock import patch

import numpy as np

from schemas.platform import SessionInput
from tools.research.config import effective_input
from tools.research.physical_replay import model_context, binding
from tools.state_io import digest
from tests.research.test_s135_control import configuration, workspace_temp


class CodesignIntegrationTests(unittest.TestCase):
    def test_saved_snapshot_extraction_stays_lightweight(self):
        script = '''
import importlib.abc, sys
class NoResearchDependencies(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in ('pydantic', 'casadi') or fullname in (
                'tools.platform_store', 'tools.research.config'):
            raise AssertionError('unexpected heavyweight import: '+fullname)
sys.meta_path.insert(0, NoResearchDependencies())
from tools.research_tasks import ResearchTaskAdapter, effective_input
cfg = dict(task=dict(family='task.reach', goal=dict(data=dict(target_m=[1.,2.,3.]))))
assert effective_input(dict(effective=dict(configuration=dict(input=cfg)))) == cfg
assert ResearchTaskAdapter(effective_input(dict(configuration=cfg))).reference_at([0.])[0].tolist() == [[1.,2.,3.]]
'''
        subprocess.run([sys.executable, '-c', script], check=True, capture_output=True, text=True)
        cfg=configuration()
        self.assertEqual(effective_input(dict(configuration=SessionInput.model_validate(cfg))), cfg)

    def test_math_mode_and_legacy_alias_retain_model_checks(self):
        from extensions.tendon_family import gvs_profile, generated_serial
        cfg=configuration(True)
        cfg['task']['goal']['data'].update(time_requirement='timed',times_s=[0.,.2,.4])
        cfg['task']['sampling']['window_s']=[.02,.4]
        cfg['policy']['controller']['parameters']['data']['recipe']['reference_mode']='timed'
        for module in (gvs_profile,generated_serial):
            self.assertIs(module.checked_reach,module.checked_control)
            module.checked_reach(cfg,execution=False)
            with self.assertRaisesRegex(ValueError,'TIMED_TRACKING_PHYSICAL_ROUTE_UNSUPPORTED'):
                module.checked_control(cfg)
        cfg['policy']['controller']['parameters']['data']['numerical_source']='bundled_guess'
        with self.assertRaisesRegex(ValueError,'CANDIDATE_PRETENSION'):
            gvs_profile.mathematical_numerical(cfg)

    def test_replay_uses_task_grid_and_rejects_prediction_mismatch(self):
        import mujoco
        from extensions.tendon_family.backends import playback_tensions
        cfg=configuration(True)
        cfg['task']['timing']['timestep_s']=.002
        inp,physics,scene,spec=model_context(cfg)
        timing=inp.task.timing
        count=round(timing.duration_s/timing.control_period_s)
        times=(np.arange(count+1)*timing.control_period_s).tolist()
        commands=np.full((count,len(physics['tendons'])),.1)
        trajectory=dict(times_s=times,tensions_n=commands.tolist(),tendon_order=spec['tendon_order'],
            task_identity=digest(cfg['task']),model_identity=spec['identity'],design_identity=spec['design_identity'])
        outputs=dict(model_identity=spec['identity'],times_s=times,samples=count+1,
            tip_positions_m=np.zeros((count+1,3)).tolist(),tip_velocities_m_s=np.zeros((count+1,3)).tolist())
        binding(cfg,trajectory,mathematical_outputs=outputs)
        for field,value in (('samples',36),('times_s',[t+.001 for t in times]),('tip_positions_m',[[0.,0.,0.]])):
            wrong=deepcopy(outputs);wrong[field]=value
            with self.assertRaisesRegex(ValueError,'MATHEMATICAL_OUTPUT_BINDING_MISMATCH'):
                binding(cfg,trajectory,mathematical_outputs=wrong)
        def synthetic_step(model,data):
            data.time+=model.opt.timestep
            mujoco.mj_forward(model,data)
        with workspace_temp() as folder,patch.object(mujoco,'mj_step',side_effect=synthetic_step) as step:
            result=playback_tensions(inp,physics,scene,commands,folder)
            self.assertEqual(result['status'],'completed')
            self.assertEqual(result['physics_steps'],count*10)
            self.assertEqual(step.call_count,count*10)
            np.testing.assert_allclose([r['engine_time_s'] for r in result['samples']],times,atol=1e-12)
            step.reset_mock()
            scene['duration_s']+=.001
            with self.assertRaisesRegex(ValueError,'GRID_OR_TENSION_MISMATCH'):
                playback_tensions(inp,physics,scene,commands,folder)
            step.assert_not_called()


if __name__=='__main__':unittest.main()
