"""Rejected cost candidate: exact kinematic elimination; no retained production change."""
import time
import casadi as ca
import numpy as np
from extensions.tendon_family.gvs_trajectory import (TrajectoryWorkspace, GVSModelParameters, GVSModel, SystemContext, functions_for, expression_from_system, quaternion_wxyz_to_rotation, implicit_step_residual)

class VelocityWorkspace(TrajectoryWorkspace):
    def _extend_tail(self,state,tension,guess=None):
        construction=time.perf_counter()
        if self._tail_solver is None:
            p=GVSModelParameters(basis=self.parameters.basis)
            system=GVSModel(p).build_system(self.robot,p,None,SystemContext(
                x0=self.nominal_x,u0=self.nominal_u,scene=self.scene))
            functions=functions_for(expression_from_system(system))
            q=functions.q_symbol;v=ca.MX.sym('motion_rate',self.n)
            local_tip=functions.tip_position_expression
            assembly=self.scene.data
            world_tip=ca.mtimes(ca.DM(quaternion_wxyz_to_rotation(assembly['mount']['quaternion_wxyz'])),local_tip)+ca.DM(assembly['mount']['position_m'])
            self._motion=ca.Function('warm_tip_motion',[q,v],[world_tip,ca.jacobian(world_tip,q)@v])
            self._tail_residual=implicit_step_residual(functions,self.n,self.m,self.period/self.parameters.substeps)
            reduced=True
            y=ca.MX.sym('scaled_next',self.n if reduced else 2*self.n);old=ca.MX.sym('old',2*self.n);u=ca.MX.sym('u',self.m)
            # Eliminate the linear kinematic equality exactly; solve only for
            # next velocity. The original force residual and tolerance remain.
            following=(ca.vertcat(old[:self.n]+self.period/self.parameters.substeps*y*self.state_scales[self.n:],
                y*self.state_scales[self.n:]) if reduced else y*self.state_scales)
            expression=self._tail_residual(old,following,u)
            residual=ca.Function('tail_residual',[y,old,u],
                [expression[self.n:] if reduced else expression],{'ad_weight':1.})
            self._tail_solver=ca.rootfinder('tail_step','newton',residual,{'abstol':1e-10,'max_iter':30})
        construction_s=time.perf_counter()-construction
        start=time.perf_counter()
        repeated_defect=float(np.max(abs(np.asarray(self._tail_residual(state,state,tension)))))
        initial=np.asarray(state if guess is None else guess)/self.state_scales
        if True:
            velocity=np.asarray(self._tail_solver(initial[self.n:],state,tension)).ravel()*self.state_scales[self.n:]
            following=np.r_[np.asarray(state)[:self.n]+self.period/self.parameters.substeps*velocity,velocity]
        else:
            following=np.asarray(self._tail_solver(initial,state,tension)).ravel()*self.state_scales
        defect=float(np.max(abs(np.asarray(self._tail_residual(state,following,tension)))))
        return following,dict(construction_s=construction_s,integration_s=time.perf_counter()-start,
            repeated_terminal_scaled_defect=repeated_defect,extended_tail_scaled_defect=defect)
