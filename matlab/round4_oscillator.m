function output=round4_oscillator(input_json)
% Independent one-hinge validation, gravity/contact disabled, SI.
p=jsondecode(input_json);
t=(0:p.dt_s:p.duration_s)';
opt=odeset('RelTol',1e-10,'AbsTol',1e-12,'MaxStep',p.dt_s);
[t,x]=ode45(@(t,x)[x(2);(p.torque_nm-p.damping*x(2)-p.stiffness*x(1))/p.inertia],t,[p.q0;0],opt);
output=jsonencode(struct('status','pass','time_s',t,'q_rad',x(:,1),'velocity_rad_s',x(:,2),...
    'model','single_hinge_linear_oscillator_v1','reason','completed same generalized torque dynamics'));
end
