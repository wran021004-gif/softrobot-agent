"""Focused A4 contracts. Fabricated arrays here are test fixtures, not evidence."""
from types import SimpleNamespace
import unittest
import numpy as np

from extensions.tendon_family.mujoco_analysis import NativeModel


class NativeTaskSensitivityTests(unittest.TestCase):
    def test_contact_failure_retains_geometry_time_and_actual_cost(self):
        native=object.__new__(NativeModel)
        native.cost=dict(model_builds=1,physics_steps=17)
        native.model=SimpleNamespace(geom=lambda i:SimpleNamespace(name=['arm','guide'][i]))
        data=SimpleNamespace(ncon=1,nefc=4,time=.0085,warning=[],qacc=np.array([0.]),
            contact=[SimpleNamespace(geom1=0,geom2=1,dist=-.001)])
        with self.assertRaisesRegex(ValueError,'CONTACT_FREE') as caught:
            native.check_supported(data,.008)
        diagnostic=caught.exception.native_diagnostic
        self.assertEqual(diagnostic['cost']['physics_steps'],17)
        self.assertEqual(diagnostic['evaluation_interval_s'],[.008,.0085])
        self.assertEqual(diagnostic['contacts'][0]['geom2'],'guide')


if __name__=='__main__':unittest.main()
