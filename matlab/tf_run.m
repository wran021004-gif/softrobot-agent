function tf_run(input_json,output_path)
% One Engine call covers control, kinematics, dynamics and adaptive integration.
input=jsondecode(input_json); p=input.physics; scene=input.scene; config=input.config;
n=numel(p.dofs); y=[scene.qpos_rad(:);scene.qvel_rad_s(:)];
u=zeros(numel(p.actuators),1); dt=scene.control_period_s;
rows=cell(round(scene.duration_s/dt),1); observations=rows; count=0; steps=0;
complete=true; reason=''; started=tic;
opts=odeset('RelTol',config.rtol,'AbsTol',config.atol,'MaxStep',config.max_step_s);
try
    for step=1:numel(rows)
        t=(step-1)*dt;
        g=tf_geometry(p,scene,y(1:n),y(n+1:end));
        [u,target,obs]=tf_control(p,input.control,g,u,t,dt);
        obs.qpos_rad=y(1:n)'; obs.qvel_rad_s=y(n+1:end)';
        before=tf_terms(p,scene,config,y(1:n),y(n+1:end),target,t);
        [ts,ys]=ode15s(@rhs,[t t+dt],y,opts);
        steps=steps+numel(ts)-1; y=ys(end,:)';
        if any(~isfinite(y)), error('TF:nonfinite','NONFINITE_STATE'); end
        after=tf_geometry(p,scene,y(1:n),y(n+1:end));
        count=count+1; observations{count}=obs;
        rows{count}=tf_observe(p,after,y,u,target,t,dt,before);
        fields={'requested_tension_n','desired_tension_n','predicted_tension_n','tension_tracking_error_n',...
            'force_limit_saturated','actuator_saturated','tension_command_unrealizable'};
        for field=fields
            if isfield(obs,field{1}), rows{count}.(field{1})=obs.(field{1}); end
        end
    end
catch exc
    complete=false; reason=[exc.identifier ': ' exc.message];
end
output=struct('trajectory',{rows(1:count)},'observations',{observations(1:count)},...
    'complete',complete,'reason',reason,'numerical_steps',steps,'solve_s',toc(started));
fid=fopen(output_path,'w','n','UTF-8'); cleanup=onCleanup(@()fclose(fid));
fwrite(fid,jsonencode(output),'char');

    function dy=rhs(time,state)
        if toc(started)>input.timeout_s, error('TF:timeout','MATLAB_SPATIAL_TIMEOUT'); end
        % Forces use exact half-open windows at the public control grid.
        a=tf_terms(p,scene,config,state(1:n),state(n+1:end),target,min(time,t+dt-eps(t+dt)));
        dy=[state(n+1:end);a.acceleration];
    end
end
