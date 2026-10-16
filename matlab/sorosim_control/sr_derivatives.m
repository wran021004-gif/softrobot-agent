function out=sr_derivatives(model,q,qd,u,qdd)
% Analytical upstream inverse-dynamics Jacobians plus custom chord terms.
% Routing tangent and tip-velocity/q use MATLAB-local centered differences.
started=tic;
routing=sr_routing(model,q,u,true,qd);
out=sr_dynamics(model,q,qd,u,qdd,routing,false);
out.routing_s=routing.routing_s;
out.Rq=out.passive_q-routing.force_state_derivative;
out.Rqd=out.passive_qd;
out.Rqdd=out.mass_matrix;out.Ru=-routing.force_map;
out.tip_position_q=out.tip_jacobian;
out.tip_velocity_q=routing.tip_velocity_q;
out.tip_velocity_qd=out.tip_jacobian;
out.tendon_force_q=routing.force_state_derivative;
out.derivative_method=struct('passive','Pinned SoRoSim analytical DAEJacobians (index 3; no closed constraints)', ...
    'acceleration_input','Exact mass matrix and negative chord force map', ...
    'routing_and_tip_velocity_q','MATLAB-local centered differences of analytical kinematic Jacobians', ...
    'step_rad_m',model.spec.solver.routing_difference_step);
out.derivatives_s=toc(started);
end
