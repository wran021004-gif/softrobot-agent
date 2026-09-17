function result=tf_static(input_json)
% Validation only: static terms/geometry, no integration or engine data.
input=jsondecode(input_json); p=input.physics; scene=input.scene;
q=scene.qpos_rad(:); v=scene.qvel_rad_s(:);
target=p.reference_lengths_m(:)-[p.tendons.pretension_n]'./[p.tendons.kp_n_m]';
a=tf_terms(p,scene,input.config,q,v,target,0);
[u,command,observation]=tf_control(p,input.control,a.geometry,zeros(numel(p.actuators),1),0,scene.control_period_s);
result=jsonencode(struct('mass',a.mass,'bias',a.bias,'gravity',a.gravity,...
    'tip',a.geometry.tip','lengths',a.geometry.lengths','Jlength',a.geometry.Jlength,...
    'acceleration',a.acceleration','tension',a.tension','actuator_command',u',...
    'target_lengths_m',command','observation',observation));
end
