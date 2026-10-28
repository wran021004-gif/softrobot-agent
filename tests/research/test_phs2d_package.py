"""Fabricated unit fixtures only; no call to a physical integrator is allowed."""
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import mujoco
import numpy as np

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import phs2d_io as io
from view_phs2d import playback_key
from validate_phs2d import validate_case_label
from portable_xml import load_xml,portable_xml_loading
from tests.research.test_base_only_export import fixture_directory


class PortablePHSTests(unittest.TestCase):
    def test_binary64_csv_round_trip_preserves_bits(self):
        values=np.array([0.,-0.,np.nextafter(0.,1.),np.nextafter(1.,2.),
                         -np.pi,np.finfo(np.float64).max,1e-300],dtype=np.float64)
        restored=np.array([float(format(float(v),'.17g')) for v in values],dtype=np.float64)
        self.assertEqual(values.tobytes(),restored.tobytes())

    def test_initial_row_uses_actual_snapshot_not_first_post_step(self):
        snapshot=dict(time_s=0.,force_n=0.,qpos=np.arange(144).tolist(),qvel=[0.]*144,
                      qacc=[3.25]*144,tendon_lengths=[.39]*4,tensions_n=[0.,.1,0.,.2])
        row=io.initial_row(snapshot)
        self.assertEqual(row.shape,(442,))
        np.testing.assert_array_equal(row[2:146],snapshot['qpos'])
        np.testing.assert_array_equal(row[290:434],snapshot['qacc'])
        self.assertEqual(row.dtype,np.float64)

    def test_material_coordinate_excludes_rigid_spacers_and_keeps_boundary_rule(self):
        physics=dict(parts=[dict(length_m=.1,dofs=[0]),dict(length_m=.5,dofs=[]),dict(length_m=.1,dofs=[1])])
        self.assertEqual(io.material_point(physics,.5),dict(body=2,position_m=[0.,0.,0.]))
        self.assertEqual(io.material_point(physics,1.),dict(body=2,position_m=[.1,0.,0.]))
        with self.assertRaises(ValueError):io.material_point(physics,1.01)

    def test_world_force_at_moving_material_point_matches_jacobian(self):
        model=mujoco.MjModel.from_xml_string('''<mujoco><worldbody><body name="fixed_base" euler="0 0 30">
          <body name="cell"><joint name="hinge" axis="0 0 1"/>
          <geom type="capsule" fromto="0 0 0 .2 0 0" size=".01"/></body></body></worldbody></mujoco>''')
        data=mujoco.MjData(model);data.qpos[0]=.3;mujoco.mj_forward(model,data)
        physics=dict(parts=[dict(entity='cell')]);binding=dict(body=0,position_m=[.17,0.,0.])
        io.apply_force(model,data,physics,binding,.1)
        position,bid=io.point(model,data,physics,binding);jac=np.zeros((3,model.nv))
        mujoco.mj_jac(model,data,jac,None,position,bid)
        np.testing.assert_allclose(data.qfrc_applied,jac[0]*.1,atol=1e-16,rtol=0)
        self.assertFalse(data.xfrc_applied.any())
        self.assertGreater(abs(data.qfrc_applied[0]),.001)

    def test_ramp_uses_preceding_discrete_step(self):
        self.assertEqual(io.ramp_force(0,.000125,.1,.5),0.)
        self.assertEqual(io.ramp_force(2000,.000125,.1,.5),.05)
        self.assertEqual(io.ramp_force(4000,.000125,-.1,.5),-.1)
        self.assertEqual(io.ramp_force(32000,.000125,.1,.5),.1)

    def test_large_stack_loader_isolated_and_restores_stack_setting(self):
        before=threading.stack_size();threads=[]
        def fake(path):
            threads.append(threading.current_thread())
            return SimpleNamespace(opt=SimpleNamespace(iterations=0,tolerance=0.))
        with patch.object(io,'load_xml',fake):
            model=io.load_model('fabricated.xml')
        self.assertNotEqual(threads[0],threading.current_thread())
        self.assertEqual(threading.stack_size(),before)
        self.assertEqual(model.opt.iterations,100)
        self.assertEqual(model.opt.tolerance,1e-10)

    def test_loader_propagates_compile_error(self):
        def fake(path):raise ValueError('fabricated compile error')
        with patch.object(io,'load_xml',fake):
            with self.assertRaisesRegex(ValueError,'fabricated compile error'):io.load_model('fabricated.xml')

    def test_readonly_guard_blocks_all_three_integration_entrypoints(self):
        with patch.object(mujoco,'mj_step'),patch.object(mujoco,'mj_step1'),patch.object(mujoco,'mj_step2'):
            io.forbid_integration()
            for name in ('mj_step','mj_step1','mj_step2'):
                with self.assertRaisesRegex(RuntimeError,'INTEGRATION_FORBIDDEN'):getattr(mujoco,name)(None,None)

    def test_viewer_pause_restart_loop_and_speed_controls(self):
        state=dict(paused=False,restart=False,loop=False,speed=1.)
        for key in (32,82,76,61):playback_key(state,key)
        self.assertEqual(state,dict(paused=True,restart=True,loop=True,speed=2.))
        playback_key(state,45);self.assertEqual(state['speed'],1.)
        for _ in range(20):playback_key(state,45)
        self.assertEqual(state['speed'],1/64)

    def test_csv_schema_retains_passive_semantics(self):
        mapping=dict(joints=[dict(qpos_column=f'qpos_{i}',qvel_column=f'qvel_{i}') for i in range(144)],
                     tendon_order=[f'tendon_{i}' for i in range(4)])
        columns=io.csv_columns(mapping)
        self.assertEqual(len(columns),322)
        self.assertFalse(any('actuator' in c or 'requested_tension' in c or 'control_interval' in c for c in columns))
        self.assertEqual(len([c for c in columns if c.startswith('original_tension_n__')]),4)

    def test_swapped_condition_labels_and_holdout_stage_are_rejected(self):
        protocol=dict(force_n=.1,search_s=[.3,.5,.7])
        entry=dict(condition='s040_negative',directory='s040_negative',s=.4,force_n=-.1,stage='holdout')
        validate_case_label(entry,protocol)
        with self.assertRaises(ValueError):validate_case_label({**entry,'force_n':.1},protocol)
        with self.assertRaises(ValueError):validate_case_label({**entry,'stage':'search'},protocol)

    def test_unicode_xml_adapter_preserves_bytes_model_and_legacy_factory(self):
        xml=b'<mujoco><worldbody><body><joint/><geom type="sphere" size=".01"/></body></worldbody></mujoco>'
        with fixture_directory() as folder:
            path=Path(folder)/'中文 path';path.mkdir();path=path/'robot.xml';path.write_bytes(xml)
            previous=mujoco.MjModel.from_xml_path
            with portable_xml_loading():model=mujoco.MjModel.from_xml_path(str(path))
            self.assertEqual(model.nq,1)
            self.assertEqual(path.read_bytes(),xml)
            self.assertIs(mujoco.MjModel.from_xml_path,previous)
            with self.assertRaises(ValueError):
                with portable_xml_loading():raise ValueError('fixture exception')
            self.assertIs(mujoco.MjModel.from_xml_path,previous)

    def test_portable_loader_rejects_missing_external_assets(self):
        with fixture_directory() as folder:
            path=Path(folder)/'external.xml'
            path.write_text('<mujoco><asset><mesh file="missing.obj"/></asset></mujoco>',encoding='utf8')
            with self.assertRaisesRegex(ValueError,'SELF_CONTAINED_XML'):load_xml(path)


if __name__=='__main__':unittest.main()
