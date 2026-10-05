"""Predictor-only observation map: represented serial tip and its SAME Jacobian.

Continuous reduced dynamics and production NMPC objectives remain unchanged.
Only mj_forward/mj_jacSite are used; this is kinematic reconstruction, no stepping.
"""
import time
import numpy as np
import mujoco
from schemas.platform import SessionInput
from .gvs_basis import resolve_basis
from .gvs_projection import discretization_jacobian, PROJECTOR_ID
from .diagnostic_math import NonlinearModel
from .milestone5_first_interval import integrate
from .milestone5_recovery import norm

VERSION='represented_serial_output@1.0.0'


class SerialOutput:
    def __init__(self,configuration,physics,compiled,xml):
        start=time.perf_counter();inp=SessionInput.model_validate(configuration)
        basis=resolve_basis(inp.robot.structure.data,inp.policy.controller.parameters.data['recipe']['basis'])
        self.mapping=discretization_jacobian(physics,basis,convention=PROJECTOR_ID)
        self.n=basis.dimension;self.compiled=compiled
        self.model=mujoco.MjModel.from_xml_string(xml);self.data=mujoco.MjData(self.model)
        self.site=self.model.site('tip_site').id;self.setup_s=time.perf_counter()-start

    def raw(self,q,v):
        self.data.qpos[self.compiled['qpos_indices']]=q;self.data.qvel[self.compiled['qvel_indices']]=v
        mujoco.mj_forward(self.model,self.data)
        J=np.zeros((3,self.model.nv));Jr=np.zeros_like(J);mujoco.mj_jacSite(self.model,self.data,J,Jr,self.site)
        velocity=J@self.data.qvel
        return dict(position_m=self.data.site_xpos[self.site].tolist(),velocity_m_s=velocity.tolist(),
            speed_m_s=float(np.linalg.norm(velocity)),body_positions_m=self.data.xpos[self.compiled['body_ids']].tolist(),
            jacobian=J[:,self.compiled['qvel_indices']]@self.mapping)

    def motion(self,state):
        x=np.asarray(state,dtype=float)
        if x.shape!=(2*self.n,) or not np.isfinite(x).all():raise ValueError('SERIAL_OUTPUT_STATE')
        r=self.raw(self.mapping@x[:self.n],self.mapping@x[self.n:])
        if norm(r['velocity_m_s'],r['jacobian']@x[self.n:])>1e-12:raise ValueError('OUTPUT_JACOBIAN_MISMATCH')
        return {k:r[k] for k in ('position_m','velocity_m_s','speed_m_s','body_positions_m')}

    def differential_check(self,state):
        x=np.asarray(state);v=x[self.n:];dt=1e-7;motion=self.motion(x)
        plus=x.copy();minus=x.copy();plus[:self.n]+=dt*v;minus[:self.n]-=dt*v
        derivative=(np.asarray(self.motion(plus)['position_m'])-self.motion(minus)['position_m'])/(2*dt)
        return norm(derivative,motion['velocity_m_s'])


def local_prediction(configuration,state,command,t,output,*,step_s=.000125,deadline=None):
    """Causal fixed current command; offline use only. No future data accepted."""
    start=time.perf_counter();end_by=deadline if deadline is not None else start+120.
    endpoints=[]
    for h in (2*step_s,step_s):
        model=NonlinearModel(configuration,state,command,h)
        result=integrate(model,state,command,end_by)
        endpoints.append(dict(**result,serial_output=output.motion(result['state'])))
    coarse,fine=[e['serial_output'] for e in endpoints];initial=output.motion(state)
    uncertainty=dict(velocity_m_s=norm(coarse['velocity_m_s'],fine['velocity_m_s']),
        speed_m_s=abs(coarse['speed_m_s']-fine['speed_m_s']),position_m=norm(coarse['position_m'],fine['position_m']))
    delta=fine['speed_m_s']-initial['speed_m_s']
    direction='indeterminate' if min(abs(delta-1e-4),abs(delta+1e-4))<=uncertainty['speed_m_s'] else 'increasing' if delta>1e-4 else 'decreasing' if delta< -1e-4 else 'approximately_unchanged'
    return dict(version=VERSION,start_s=t,end_s=t+.01,frame='world',position_m=fine['position_m'],
        velocity_m_s=fine['velocity_m_s'],speed_m_s=fine['speed_m_s'],direction=direction,
        input_n=list(command),input_information_time_s=t,numerical_uncertainty=uncertainty,
        numerical_stability_supported=False,stability_note='A working two-grid comparison alone does not establish the two-successive-comparison reference criterion',
        reference_scope='Only separately assessed development intervals; no automatic transfer to this state',
        maximum_residual=max(e['max_scaled_residual'] for e in endpoints),cost_s=time.perf_counter()-start,
        supported_use='Experimental offline local diagnosis; quantitative and safety failures must be scored. Screening not validated.')
