"""Contact-free fixed-payout native assembly and material-point force geometry.

Selective extraction from 9d6d160e. No campaign, Store, acceptance or duplicate
compiler. Ideal hard equilibrium and native soft tendon limits remain distinct.
"""
import numpy as np
import mujoco
from io import BytesIO
from .mjcf import compile_xml
from .contracts import ConstrainedPhysicalProblem


def material_point(physics,s):
    if isinstance(s,dict):return s
    if not 0<=s<=1:raise ValueError('MATERIAL_S_OUT_OF_RANGE')
    cells=[(i,p) for i,p in enumerate(physics['parts']) if p['dofs']]
    target=s*sum(p['length_m'] for _,p in cells)
    for k,(i,p) in enumerate(cells):
        if target<p['length_m']-1e-14 or k==len(cells)-1:
            return dict(body=i,position_m=[float(np.clip(target,0,p['length_m'])),0.,0.])
        target-=p['length_m']


SOLVER=dict(version='passive_equilibrium_v1',hessian_step_rad=1e-5,active_tolerance_m=1e-7,rank_relative_tolerance=1e-8,
    stationarity_tolerance_nm=1e-7,length_tolerance_m=1e-8,complementarity_tolerance_nm=1e-8,
    minimum_reduced_eigenvalue=1e-8,ftol=1e-12,max_iterations=150,
    positive_multiplier_tolerance_n=1e-7,multiplier_max_iterations=1000,
    qp_ftol=1e-12,qp_max_iterations=200,qp_increment_n=.001,
    native_iterations=100,native_tolerance=1e-10)


class PassiveModel:
    def __init__(self,physics,problem,path=None):
        problem=ConstrainedPhysicalProblem.model_validate(problem)
        if not physics.get('fixed_payout_lengths_m') or physics['actuators']:raise ValueError('COMPILED_PASSIVE_ASSEMBLY_REQUIRED')
        self.physics=physics;self.problem=problem;self.unrestricted=False
        self.protocol=dict(static_solver=dict(SOLVER),monitor_s=problem.monitor_s)
        self.payout=np.array([physics['fixed_payout_lengths_m'][t['entity']] for t in physics['tendons']])
        scene=dict(mount_position=problem.mount_position,mount_rotation=problem.mount_rotation,gravity=problem.gravity,
            floor_id='floor',floor_z_m=-100.,timestep_s=.001,control=dict(tension_execution_mode='passive_fixed_payout_v1'))
        xml=BytesIO();compile_xml(physics,scene,None,xml)
        if path is not None:path.write_bytes(xml.getvalue())
        self.model=mujoco.MjModel.from_xml_string(xml.getvalue().decode('utf-8'))
        self.model.opt.iterations=SOLVER['native_iterations'];self.model.opt.tolerance=SOLVER['native_tolerance']
        self.body_ids=[self.model.body(p['entity']).id for p in physics['parts']];self.base=self.model.body('fixed_base').id
        self.points=[material_point(physics,s) for s in problem.monitor_s]+[physics['tip']]
        if self.model.nu or self.model.nq!=self.model.nv:raise ValueError('PASSIVE_HINGES_WITHOUT_ACTIVE_CHANNELS_REQUIRED')
        self.cost=dict(model_builds=1,native_forward_calls=0,physics_steps=0,rollouts=0,
            material_point_jacobian_calls=0,tendon_jacobian_extractions=0)

    def point(self,data,binding):
        self.cost['material_point_jacobian_calls']+=1
        bid=self.base if binding['body']<0 else self.body_ids[binding['body']]
        pos=data.xpos[bid]+data.xmat[bid].reshape(3,3)@binding['position_m']
        J=np.zeros((3,self.model.nv));mujoco.mj_jac(self.model,data,J,None,pos,bid)
        return pos,J,bid

    def tendon_jac(self,data):
        self.cost['tendon_jacobian_extractions']+=1
        J=np.zeros((self.model.ntendon,self.model.nv));m=self.model
        mujoco.mju_sparse2dense(J,data.ten_J,m.ten_J_rownnz,m.ten_J_rowadr,m.ten_J_colind)
        return J

    def load(self,condition):
        return next(x for x in self.problem.loads if x.name==condition)

    def apply_force(self,data,s,force):
        vector=np.asarray(force if np.ndim(force) else [force,0.,0.],dtype=float)
        data.qfrc_applied[:]=0.;data.xfrc_applied[:]=0.
        p,J,bid=self.point(data,material_point(self.physics,s))
        mujoco.mj_applyFT(self.model,data,vector,np.zeros(3),p,bid,data.qfrc_applied)
        return p,J
