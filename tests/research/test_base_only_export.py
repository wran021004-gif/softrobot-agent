"""Fabricated fixtures only. Mocked steps never call the physics integrator."""
from contextlib import contextmanager
from pathlib import Path
import sys
import shutil
from uuid import uuid4
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import mujoco
import numpy as np
from extensions.tendon_family.backends import playback_tensions
from tools.base_only_export import portable_kernel,reference_rows

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
from package_io import observation,joint_map,digest
from tools.state_io import digest as original_digest

XML='''<mujoco><option timestep="0.001"/><worldbody><body name="fixed_base">
<site name="start" pos="0 .1 0"/><body name="link"><joint name="hinge" axis="0 0 1"/>
<geom type="capsule" fromto="0 0 0 .1 0 0" size=".01"/><site name="tip_site" pos=".1 0 0"/>
</body></body></worldbody><tendon><spatial name="cable"><site site="start"/>
<site site="tip_site"/></spatial></tendon><actuator><general name="cable_direct_tension"
tendon="cable" gainprm="-1" ctrllimited="true" ctrlrange="0 2"/></actuator></mujoco>'''


@contextmanager
def fixture_directory():
    parent=(ROOT/'runs').resolve();parent.mkdir(exist_ok=True)
    folder=parent/('export-fixture-'+uuid4().hex);folder.mkdir()
    try:yield folder
    finally:
        if not folder.resolve().is_relative_to(parent):raise ValueError('UNSAFE_FIXTURE_CLEANUP')
        shutil.rmtree(folder)


class ExportTests(unittest.TestCase):
    def fixture(self):
        inp=SimpleNamespace(task=SimpleNamespace(family='task.reach'))
        physics=dict(identity='fabricated-fixture',dofs=['hinge'],tendons=[dict(entity='cable')])
        scene=dict(control=dict(tension_execution_mode='ideal_tension'),duration_s=.004,control_period_s=.002,
            qpos_rad=[.2],qvel_rad_s=[.1],forces=[],semantics={},identity='fabricated-fixture')
        return inp,physics,scene

    @staticmethod
    def fake_step(model,data):
        # Deliberately stale pose cache; this is not a physical trajectory.
        data.qpos[0]+=.001;data.qvel[0]+=.01;data.time+=model.opt.timestep

    def test_detached_observer_and_extracted_loop_preserve_default_samples(self):
        with fixture_directory() as temp:
            folder=Path(temp);xml=folder/'robot.xml';xml.write_text(XML)
            inp,p,s=self.fixture();seen=[]
            def observer(m,d,step,interval):
                row=observation(m,d,step,interval,joint_map(m,['hinge']),[1,0,0],[])
                seen.append(row)
                d.qpos[:]=999;d.qvel[:]=888;d.qacc_warmstart[:]=777;d.ctrl[:]=1.9
            with patch('mujoco.mj_step',self.fake_step):
                baseline=playback_tensions(inp,p,s,[[.5],[.7]],folder/'base',xml_path=xml)
                observed=playback_tensions(inp,p,s,[[.5],[.7]],folder/'observed',xml_path=xml,step_observer=observer)
                namespace={};exec(compile(portable_kernel(),'generated_playback_kernel.py','exec'),namespace)
                extracted=namespace['playback_tensions'](inp,p,s,[[.5],[.7]],folder/'portable',xml_path=xml)
            self.assertEqual(baseline['samples'],observed['samples'])
            self.assertEqual(baseline['samples'],extracted['samples'])
            self.assertEqual(baseline['cost']['forward_evaluations'],observed['cost']['forward_evaluations'])
            self.assertEqual(len(seen),5)
            self.assertEqual([r['control_interval_index'] for r in seen],[-1,0,0,1,1])
            for i,row in enumerate(seen):
                self.assertAlmostEqual(row['qpos_rad__hinge'],.2+.001*i)
                np.testing.assert_allclose([row['tip_position_m_x'],row['tip_position_m_y']],
                    [.1*np.cos(.2+.001*i),.1*np.sin(.2+.001*i)],atol=1e-15,rtol=0)

    def test_reference_grid_is_marked_separately_from_evaluator_inputs(self):
        task=dict(definition=dict(family='task.reach',goal=dict(data=dict(target_m=[.1,.2,.3])),
            timing=dict(duration_s=.004,timestep_s=.001,sample_period_s=.002),sampling=dict(window_s=[.002,.004])),
            holding_window_s=[.002,.004])
        rows=reference_rows(task)
        self.assertEqual([r['evaluator_input_sample'] for r in rows],[0,0,1,0,1])
        self.assertEqual([r['holding_window_sample'] for r in rows],[0,0,1,0,1])
        self.assertEqual([r['tool_axis_reference_defined'] for r in rows],[0]*5)

    def test_canonical_identity_matches_original_for_unicode(self):
        self.assertEqual(digest({'说明':'人工构造夹具'}),original_digest({'说明':'人工构造夹具'}))

    def test_portable_force_ticks_preserve_world_com_semantics(self):
        ns={};exec(compile(portable_kernel(),'generated_playback_kernel.py','exec'),ns)
        model=SimpleNamespace(opt=SimpleNamespace(timestep=.001),body=lambda name:SimpleNamespace(id=1))
        forces=ns['_bind_mujoco_forces'](model,dict(forces=[dict(entity='load',start_s=.001,
            end_s=.003,force_n=[0.,.1,-.2])]))
        data=SimpleNamespace(time=0.,xfrc_applied=np.ones((2,6)))
        for t,expected in [(0.,[0,0,0]),(.001,[0,.1,-.2]),(.003-1e-17,[0,0,0])]:
            data.time=t;ns['_apply_mujoco_forces'](model,data,forces)
            np.testing.assert_array_equal(data.xfrc_applied[1,:3],expected)
            self.assertFalse(data.xfrc_applied[:,3:].any())
            self.assertFalse(data.xfrc_applied[0].any())


if __name__=='__main__':unittest.main()
