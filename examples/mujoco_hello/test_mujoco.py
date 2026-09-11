import mujoco
import mujoco.viewer
import time

model = mujoco.MjModel.from_xml_path("pendulum.xml")
data = mujoco.MjData(model)

print("MuJoCo version:", mujoco.__version__)
print("nq =", model.nq)
print("nv =", model.nv)

with mujoco.viewer.launch_passive(model, data) as viewer:
    while viewer.is_running():
        mujoco.mj_step(model, data)
        viewer.sync()
        time.sleep(model.opt.timestep)