function output = round4_mechanics(input_json)
% Independent one-mode discrete rod analysis, SI; never changes MuJoCo.
p = jsondecode(input_json); timer = tic;
trigger=struct(); accepted_t=[]; accepted_x=[];
try
    assert(p.n >= 4 && p.n <= 24 && p.length_m > 0);
    assert(numel(p.mass_kg)==p.n && numel(p.inertia_y_kg_m2)==p.n);
    assert(all(p.mass_kg>0) && all(p.inertia_y_kg_m2>0));
    assert(p.stiffness_scale>0 && p.damping_scale>0);
    assert(all(p.tension_n(:)>=0) && all(p.tension_n(:)<=20));
    if strcmp(p.operation,'static')
        opt=optimset('TolX',1e-10,'MaxIter',120,'MaxFunEvals',160);
        [q,~,flag,info]=fminbnd(@(q)potential(q,0,p),-2.8,2.8,opt);
        residual=gradient_potential(q,0,p);
        [line,~,~]=geometry(q,p);
        r=struct('status','pass','q_rad',q,'joint_bend_rad',ones(1,p.n)*q/p.n,...
            'centerline_m',line,'tip_m',line(end,:),'equilibrium_residual_nm',residual,...
            'solver_exitflag',flag,'iterations',info.iterations,'reason','interior stationary energy minimum');
        if flag<=0 || abs(residual)>1e-6 || abs(q)>2.799
            r.status='fail'; r.reason='bounded solver did not establish interior equilibrium';
        end
    elseif strcmp(p.operation,'dynamic')
        assert(p.duration_s>0 && p.duration_s<=4 && p.sample_dt_s>=.001);
        times=0:p.sample_dt_s:p.duration_s;
        opt=odeset('RelTol',1e-7,'AbsTol',1e-9,'MaxStep',.01,'OutputFcn',@timeout);
        [t,x]=ode15s(@rhs,times,[p.initial_q_rad;p.initial_velocity_rad_s],opt);
        assert(numel(t)==numel(times),'Incomplete integration');
        tip=zeros(numel(t),3); energy=zeros(numel(t),1); residual=zeros(numel(t),1);
        for j=1:numel(t)
            [line,~,~]=geometry(x(j,1),p); tip(j,:)=line(end,:);
            energy(j)=.5*mass(x(j,1),p)*x(j,2)^2+potential(x(j,1),t(j),p);
            residual(j)=gradient_potential(x(j,1),t(j),p);
        end
        if max(abs(x(:,1)))>2.8
            k=find(abs(x(:,1))>2.8,1);
            capture('accepted_output_limit',2.8,t(k),x(k,:)', 'accepted_output');
            error('round4:guard','State outside output domain');
        end
        assert(all(isfinite(x(:))),'Nonfinite state');
        r=struct('status','pass','reason','integration completed','time_s',t,'q_rad',x(:,1),...
            'velocity_rad_s',x(:,2),'tip_m',tip,'mechanical_potential_energy_j',energy,...
            'instantaneous_static_residual_nm',residual,'final_velocity_rad_s',x(end,2));
    elseif strcmp(p.operation,'fit')
        % Fixed split, torque-equilibrium residual loss, one bounded scale.
        assert(numel(p.train_q_rad)>=3 && numel(p.validation_q_rad)>=2);
        opt=optimset('TolX',1e-9,'MaxIter',80,'MaxFunEvals',100);
        [scale,loss,flag,info]=fminbnd(@loss_train,.5,2.,opt);
        p.stiffness_scale=scale;
        validation=zeros(numel(p.validation_q_rad),1);
        for j=1:numel(validation)
            p.tip_force_n=[0 0 p.validation_force_n(j)];
            validation(j)=gradient_potential(p.validation_q_rad(j),0,p);
        end
        r=struct('status','pass','reason','bounded training-only stiffness fit','stiffness_scale',scale,...
            'training_mse_nm2',loss,'validation_mse_nm2',mean(validation.^2),...
            'validation_residuals_nm',validation,'solver_exitflag',flag,'iterations',info.iterations,...
            'scientific_status','SYNTHETIC_VALIDATION','parameter_version','analysis_fit_v1');
        if flag<=0 || ~isfinite(loss), r.status='fail'; r.reason='fit failed'; end
    else
        error('Unsupported mechanics operation');
    end
    r.elapsed_s=toc(timer); r.model='one_mode_discrete_rod_diagnostics_v2';
    r.coordinate_frame='world_base_x_forward_yz_cross_section';
catch ex
    r=struct('status','fail','reason',ex.message,'identifier',ex.identifier,'elapsed_s',toc(timer));
    r.failure_kind='NUMERICAL_OR_PROGRAM_ERROR';
    if ~isempty(fieldnames(trigger)), r.failure_kind='IMPLEMENTATION_GUARD_STOP'; end
    r.diagnostics=struct('trigger',trigger,'partial_time_s',accepted_t,'partial_state',accepted_x,...
        'partial_use','DIAGNOSTIC_ONLY_NOT_COMPLETE_PREDICTION','last_valid_source','MATLAB OutputFcn accepted outputs');
    if ~isempty(accepted_t)
        r.diagnostics.last_valid_time_s=accepted_t(end);r.diagnostics.last_valid_state=accepted_x(end,:);
    else
        r.diagnostics.last_valid_source='unavailable';
    end
    r.model='one_mode_discrete_rod_diagnostics_v2';
    r.coordinate_frame='world_base_x_forward_yz_cross_section';
end
output=jsonencode(r);
    function stop=timeout(t,x,flag)
        if isempty(flag)
            keep=abs(x(1,:))<=2.8 & all(isfinite(x),1);
            selected=t(keep);accepted_t=[accepted_t;selected(:)];accepted_x=[accepted_x;x(:,keep)'];
        end
        stop=toc(timer)>30;
    end
    function dx=rhs(t,x)
        if toc(timer)>30
            capture('wall_timeout',30,t,x,'solver_internal_trial');error('round4:guard','Solver timeout');
        end
        if abs(x(1))>3.2
            capture('internal_trial_angle_limit',3.2,t,x,'solver_internal_trial');error('round4:guard','Reduced-model domain exceeded');
        end
        h=1e-5; m=mass(x(1),p); dm=(mass(x(1)+h,p)-mass(x(1)-h,p))/(2*h);
        d=sum(p.damping_nm_s_rad(:))/p.n^2*p.damping_scale;
        dx=[x(2);(-gradient_potential(x(1),t,p)-d*x(2)-.5*dm*x(2)^2)/m];
    end
    function capture(name,limit,t,x,kind)
        tensions=p.tension_n(:)';
        if isfield(p,'input_time_s')
            k=find(p.input_time_s<=t,1,'last');if isempty(k),k=1;end
            tensions=p.input_tension_n(k,:);
        end
        trigger=struct('limit',name,'threshold',limit,'actual_value',abs(x(1)),...
            'unit','rad','time_s',t,'state_rad',x(1),'velocity_rad_s',x(2),...
            'tension_n',tensions,'tip_force_n',p.tip_force_n,'state_kind',kind,...
            'interpretation','Implementation choice; not a proven physical validity boundary');
    end
    function loss=loss_train(scale)
        assert(toc(timer)<=30,'Fit timeout');
        pp=p; pp.stiffness_scale=scale; residual=zeros(numel(p.train_q_rad),1);
        for k=1:numel(residual)
            pp.tip_force_n=[0 0 p.train_force_n(k)];
            residual(k)=gradient_potential(p.train_q_rad(k),0,pp);
        end
        loss=mean(residual.^2);
    end
end

function [line,com,lengths]=geometry(q,p)
angles=(1:p.n)'*q/p.n; ds=p.length_m/p.n;
directions=[cos(angles) zeros(p.n,1) sin(angles)];
line=[zeros(1,3);cumsum(ds*directions,1)];
com=line(1:end-1,:)+.5*ds*directions;
routes=p.offset_yz_m; lengths=zeros(size(routes,1),1);
for i=1:size(routes,1)
    y=routes(i,1); z=routes(i,2);
    sites=[0 y z;line(2:end,:)+[-z*sin(angles) y*ones(p.n,1) z*cos(angles)]];
    lengths(i)=sum(sqrt(sum(diff(sites).^2,2)));
end
end

function value=potential(q,t,p)
[line,com,lengths]=geometry(q,p);
force=p.tip_force_n(:); tension=p.tension_n(:);
if isfield(p,'input_time_s')
    index=find(p.input_time_s<=t,1,'last');
    if isempty(index), index=1; end
    tension=p.input_tension_n(index,:)';
end
if isfield(p,'pulse_start_s') && t>=p.pulse_start_s && t<p.pulse_end_s
    force=force+p.pulse_force_n(:); tension=tension+p.pulse_tension_n(:);
end
assert(all(tension>=0) && all(tension<=20));
value=.5*sum(p.stiffness_nm_rad(:))*p.stiffness_scale*(q/p.n)^2 ...
    -sum(p.mass_kg(:).*(com*p.gravity_m_s2(:))) -line(end,:)*force + tension'*lengths;
end

function value=gradient_potential(q,t,p)
h=1e-5; value=(potential(q+h,t,p)-potential(q-h,t,p))/(2*h);
end

function value=mass(q,p)
h=1e-5; [~,a,~]=geometry(q+h,p); [~,b,~]=geometry(q-h,p);
jac=(a-b)/(2*h);
value=sum(p.mass_kg(:).*sum(jac.^2,2))+sum(p.inertia_y_kg_m2(:).*((1:p.n)'/p.n).^2);
assert(isfinite(value) && value>0,'Invalid reduced mass');
end
