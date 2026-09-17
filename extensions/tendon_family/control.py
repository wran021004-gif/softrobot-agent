"""Ideal actuator commands and end-point resolved-rate feedback, no PCC reuse."""
import numpy as np


class Controller:
    def __init__(self, parameters, period_s):
        self.parameters, self.period_s = parameters, period_s

    def configure(self, physics, target):
        self.physics = physics
        self.target = np.array(target)
        self.u = np.zeros(len(physics['actuators']))
        self.observations = []

    def command(self, t, geometry, q, v):
        p,c,dt = self.physics,self.parameters,self.period_s
        B = np.array(p['transmission'])
        if c.mode == 'deterministic':
            wanted = np.array([c.commands.get(a['id'],0.) for a in p['actuators']])*min(1.,(t+dt)/c.ramp_s)
        else:
            J = geometry['Jtip']; error = self.target-geometry['tip']
            dq = c.feedback_gain*dt*J.T@np.linalg.solve(J@J.T+c.damping**2*np.eye(3),error)
            dq = np.clip(dq,-c.max_joint_update_rad,c.max_joint_update_rad)
            wanted = self.u+np.linalg.pinv(B)@geometry['Jlength']@dq
        limits = np.array([a['limits'] for a in p['actuators']]); speed = np.array([a['velocity_limit'] for a in p['actuators']])
        self.u = np.clip(self.u+np.clip(wanted-self.u,-speed*dt,speed*dt),limits[:,0],limits[:,1])
        target = np.array(p['reference_lengths_m'])+B@self.u-np.array([t['pretension_n']/t['kp_n_m'] for t in p['tendons']])
        self.observations.append(dict(time_s=t,phase='current_state_before_integration',tip_position_m=geometry['tip'].tolist(),
            qpos_rad=q.tolist(),qvel_rad_s=v.tolist(),tendon_length_m=geometry['lengths'].tolist(),actuator_command=self.u.tolist(),target_lengths_m=target.tolist()))
        return target
