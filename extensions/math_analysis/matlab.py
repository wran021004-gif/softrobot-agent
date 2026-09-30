"""One Engine lifecycle per public batch, using the existing integration."""
import importlib.metadata
import numpy as np
from tools.matlab_tools import MatlabTools
from .kernels import aligned_steps


class MatlabBatch:
    def __enter__(self):
        self.tools=MatlabTools()
        try:
            e=self.tools.eng
            self.environment=dict(release=str(e.version('-release',nargout=1)),version=self.tools.version(),
                engine=importlib.metadata.version('matlabengine'),control_toolbox=e.ver('control',nargout=1),
                control_license=bool(e.license('test','Control_Toolbox',nargout=1)),
                optimization_toolbox=e.ver('optim',nargout=1),
                optimization_license=bool(e.license('test','Optimization_Toolbox',nargout=1)))
            if not self.environment['control_toolbox'] or not self.environment['control_license']:
                raise RuntimeError('CONTROL_SYSTEM_TOOLBOX_UNAVAILABLE')
            return self
        except BaseException:
            self.tools.close(); raise

    def __exit__(self,*exc): self.tools.close()

    def calculate(self,A,B,C,D,drift,p):
        import matlab
        sampling=[]
        for horizon in p.windows_s:
            steps,effective=aligned_steps(horizon,p.period_s,getattr(p,'horizon_alignment_atol_s',1e-12))
            sampling.append(dict(requested_horizon_s=horizon,effective_horizon_s=effective,
                step_count=steps,period_s=p.period_s))
        values=[matlab.double(np.asarray(v).tolist()) for v in (A,B,C,D,drift.reshape(-1,1))]
        out=self.tools.eng.analyze_linear_model(*values,float(p.period_s),matlab.double([p.windows_s]),
            matlab.double([p.frequency_rad_s]),float(p.pole_margin_s_inv),nargout=1)
        real=np.asarray(out['frequency_real']); imag=np.asarray(out['frequency_imag'])
        return dict(A_d=np.asarray(out['A_d']).tolist(),B_d=np.asarray(out['B_d']).tolist(),
            drift_d=np.asarray(out['drift_d']).reshape(-1).tolist(),poles=np.asarray(out['poles']).tolist(),
            frequency_response=[dict(real=real[:,:,i].tolist(),imag=imag[:,:,i].tolist()) for i in range(len(p.frequency_rad_s))],
            singular_values=np.asarray(out['singular_values']).tolist(),
            continuous_gramians=[np.asarray(w).tolist() for w in out['continuous_gramians']],
            held_gramians=[np.asarray(w).tolist() for w in out['held_gramians']],
            held_sampling=sampling,
            gramian_algorithms=list(out['gramian_algorithms']))

    def residual_certificate(self,P,base,target,lower,upper,limit,atol):
        if not self.environment['optimization_toolbox'] or not self.environment['optimization_license']:
            raise RuntimeError('OPTIMIZATION_TOOLBOX_UNAVAILABLE')
        import matlab
        matrix=lambda value: matlab.double(np.asarray(value,dtype=float).tolist())
        column=lambda value: matlab.double(np.asarray(value,dtype=float).reshape(-1,1).tolist())
        out=self.tools.eng.bounded_residual_certificate(matrix(P),column(base),column(target),column(lower),
            column(upper),float(limit),float(atol),nargout=1)
        return dict(candidate_residual=float(out['candidate_residual']),candidate_delta_input=np.asarray(out['z']).reshape(-1).tolist(),
            candidate_residual_vector=np.asarray(out['residual_vector']).reshape(-1).tolist(),
            solver_success=bool(out['solver_success']),exitflag=int(out['exitflag']),iterations=int(out['iterations']),
            solver_residual_scale=float(out['residual_scale']),certified_infeasible=bool(out['certified_infeasible']),
            separating_direction=dict(direction=np.asarray(out['direction']).reshape(-1).tolist(),
                unit_norm=float(out['direction_norm']),lower_bound=float(out['lower_bound']),raw_bound=float(out['raw_bound']),
                numerical_allowance=float(out['numerical_allowance']),margin_over_limit=float(out['margin_over_limit']),
                matrix_transpose_direction=np.asarray(out['matrix_transpose_direction']).reshape(-1).tolist(),
                box_min_terms=np.asarray(out['box_min_terms']).reshape(-1).tolist()))

    def endpoint(self,model,p,target):
        if not self.environment['optimization_toolbox'] or not self.environment['optimization_license']:
            raise RuntimeError('OPTIMIZATION_TOOLBOX_UNAVAILABLE')
        import matlab
        from .kernels import aligned_steps
        remaining=model.operating_point['remaining_task_s']
        steps,_=aligned_steps(remaining,p.period_s,p.horizon_alignment_atol_s)
        outputs={row.name:row for row in model.endpoint_outputs}
        position,velocity=outputs['tip_position'],outputs['tip_velocity']
        matrix=lambda value: matlab.double(np.asarray(value,dtype=float).tolist())
        column=lambda value: matlab.double(np.asarray(value,dtype=float).reshape(-1,1).tolist())
        out=self.tools.eng.analyze_bounded_endpoint(matrix(model.A),matrix(model.B),column(model.drift),
            matrix(position.C),matrix(position.D),column(position.value0),matrix(velocity.C),matrix(velocity.D),column(velocity.value0),
            column(model.u0),column(model.binding['tension_limits_n']),float(p.period_s),float(steps),column(target.position_m),
            float(target.position_tolerance_m),column(target.tip_velocity_m_s),float(target.tip_speed_limit_m_s),
            column(model.input_scales),float(p.endpoint_check_atol),nargout=1)
        pc=out['position_candidate'];vc=out['velocity_candidate']
        certificate=lambda value: dict(candidate_residual=float(value['candidate_residual']),
            candidate_delta_input=np.asarray(value['z']).reshape(-1).tolist(),solver_success=bool(value['solver_success']),
            certified_infeasible=bool(value['certified_infeasible']),separating_direction=dict(
                direction=np.asarray(value['direction']).reshape(-1).tolist(),unit_norm=float(value['direction_norm']),
                lower_bound=float(value['lower_bound']),numerical_allowance=float(value['numerical_allowance']),
                margin_over_limit=float(value['margin_over_limit'])))
        return dict(A_d=np.asarray(out['A_d']).tolist(),B_d=np.asarray(out['B_d']).tolist(),
            drift_d=np.asarray(out['drift_d']).reshape(-1).tolist(),affine_state=np.asarray(out['affine_state']).reshape(-1).tolist(),
            influence=np.asarray(out['influence']).tolist(),position_base=np.asarray(out['position_base']).reshape(-1).tolist(),
            position_matrix=np.asarray(out['position_matrix']).tolist(),velocity_base=np.asarray(out['velocity_base']).reshape(-1).tolist(),
            velocity_matrix=np.asarray(out['velocity_matrix']).tolist(),position_candidate=certificate(pc),velocity_candidate=certificate(vc),
            joint=dict(delta_input=np.asarray(out['joint_z']).reshape(-1).tolist(),energy=float(out['joint_energy']),
                exitflag=int(out['joint_exitflag']),iterations=int(out['joint_iterations']),
                position_m=np.asarray(out['joint_position']).reshape(-1).tolist(),velocity_m_s=np.asarray(out['joint_velocity']).reshape(-1).tolist(),
                position_error_m=float(out['joint_position_error']),speed_m_s=float(out['joint_speed']),
                bounds_satisfied=bool(out['joint_bounds_satisfied']),feasible=bool(out['joint_feasible'])))
