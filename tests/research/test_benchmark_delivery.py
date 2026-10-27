import unittest
import numpy as np
import mujoco
from tools.research.delivery_replay import advance

class DeliveryReplayTests(unittest.TestCase):
    def test_force_interval_and_zero_order_hold(self):
        model=mujoco.MjModel.from_xml_string('''<mujoco><option timestep="0.1" gravity="0 0 0"/><worldbody><body name="load"><joint name="slide" type="slide" axis="1 0 0"/><geom type="sphere" size="0.1" mass="1"/></body></worldbody><actuator><motor name="a" joint="slide"/></actuator></mujoco>''')
        data=mujoco.MjData(model)
        force=[dict(entity='load',start_s=0.0,end_s=0.2,force_n=[1,0,0])]
        advance(model,data,{'dt_s':'0.4','tendon_N':'0'},['tendon'],[0],force)
        self.assertAlmostEqual(data.time,0.4)
        self.assertAlmostEqual(data.qvel[0],0.2)
        np.testing.assert_array_equal(data.xfrc_applied[model.body('load').id],np.zeros(6))

    def test_unaligned_grid_rejected(self):
        model=mujoco.MjModel.from_xml_string('<mujoco><option timestep="0.1"/><worldbody/></mujoco>')
        data=mujoco.MjData(model)
        with self.assertRaises(ValueError): advance(model,data,{'dt_s':'0.15'},[],[],[])

if __name__ == '__main__': unittest.main()
