function [u,target,observation]=tf_control(p,control,g,u,time_s,dt)
% Ideal shared displacement transmission. All actual commands are logged.
B=p.transmission;
if strcmp(control.mode,'deterministic')
    wanted=control.command_vector(:)*min(1,(time_s+dt)/control.ramp_s);
elseif strcmp(control.mode,'tip_feedback')
    error=control.target_world_m(:)-g.tip;
    dq=control.feedback_gain*dt*g.Jtip'*((g.Jtip*g.Jtip'+control.damping^2*eye(3))\error);
    dq=max(-control.max_joint_update_rad,min(control.max_joint_update_rad,dq));
    wanted=u+pinv(B)*(g.Jlength*dq);
else
    desired=control.desired_tendon_tensions_n(:);
    kp=[p.tendons.kp_n_m]'; pretension=[p.tendons.pretension_n]';
    target_for_tension=g.lengths(:)-desired./kp;
    wanted=pinv(B)*(target_for_tension-p.reference_lengths_m(:)+pretension./kp);
end
lo=arrayfun(@(a)a.limits(1),p.actuators); hi=arrayfun(@(a)a.limits(2),p.actuators);
speed=[p.actuators.velocity_limit]';
u=max(lo(:),min(hi(:),u+max(-speed*dt,min(speed*dt,wanted-u))));
target=p.reference_lengths_m(:)+B*u-[p.tendons.pretension_n]'./[p.tendons.kp_n_m]';
observation=struct('time_s',time_s,'phase','current_state_before_integration','tip_position_m',g.tip',...
    'tendon_length_m',g.lengths','actuator_command',u','target_lengths_m',target');
if strcmp(control.mode,'tension_reference')
    limits=[p.tendons.force_limit_n]'; predicted=min(limits,max(0,kp.*(g.lengths(:)-target)));
    observation.requested_tension_n=control.requested_tendon_tensions_n(:)';
    observation.desired_tension_n=desired'; observation.predicted_tension_n=predicted';
    observation.tension_tracking_error_n=(predicted-desired)';
    observation.force_limit_saturated=control.force_limit_saturated(:)';
    observation.actuator_saturated=(abs(u-wanted)>1e-12)';
    observation.tension_command_unrealizable=(abs(predicted-desired)>1e-9)';
end
end
