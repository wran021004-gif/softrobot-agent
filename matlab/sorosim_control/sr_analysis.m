function out=sr_analysis(model,r)
% Candidate-local mathematical analysis; Python owns work-point definitions.
started=tic;p=r.protocol;n=model.S.ndof;m=numel(model.spec.routes);
x=r.x(:);u=r.u(:);qs=r.state_scales(1:n);qs=qs(:);
limits=[model.spec.routes.force_limit_n]'; R=model.spec.mount_rotation;
assert(numel(x)==2*n && numel(u)==m && all(isfinite([x;u])),'INVALID_ANALYSIS_POINT');
assert(all(u>=0 & u<=limits),'ANALYSIS_INPUT_OUT_OF_BOUNDS');
out=struct('operation',r.operation,'model_identity',model.spec.identity,'status','computed', ...
    'failure_code','','physical_task_acceptance','unmeasured');
construction=struct('method','provided candidate operating point','static_equilibrium',false);
switch r.operation
    case 'target_equilibrium'
        opt=optimoptions('fmincon','Algorithm','sqp','Display','off', ...
            'SpecifyObjectiveGradient',true,'SpecifyConstraintGradient',true, ...
            'MaxIterations',p.construction_max_iterations,'OptimalityTolerance',1e-12, ...
            'ConstraintTolerance',p.static_force_tolerance/.001,'StepTolerance',1e-12);
        [z,~,flag,info]=fmincon(@target_cost,[x(1:n)./qs;u/p.input_scale_n],[],[],[],[], ...
            [-inf(n,1);zeros(m,1)],[inf(n,1);limits/p.input_scale_n],@static_constraint,opt);
        x=[z(1:n).*qs;zeros(n,1)];u=min(limits,max(0,z(n+1:end)*p.input_scale_n));
        d=sr_derivatives(model,x(1:n),zeros(n,1),u,zeros(n,1));
        position_error=norm(world(d.tip_position)-r.target(:));res=norm(d.residual,inf);
        construction=struct('method','bounded target-associated MATLAB SQP','solver','MATLAB fmincon SQP', ...
            'success',flag>0,'status',flag,'iterations',info.iterations,'function_evaluations',info.funcCount, ...
            'position_residual_m',position_error,'static_residual_inf',res,'computed_tensions_n',u, ...
            'requested_world_point_m',r.target(:),'achieved_world_point_m',world(d.tip_position), ...
            'static_equilibrium',res<=p.static_force_tolerance,'maximum_iterations',p.construction_max_iterations);
        if flag<=0 || res>p.static_force_tolerance || position_error>r.position_tolerance_m+p.endpoint_check_atol
            out.status='unavailable';out.failure_code='STATIC_TARGET_CONSTRUCTION_FAILED';
        end
    case 'halfway_waypoint'
        opt=optimoptions('lsqnonlin','Display','off','SpecifyObjectiveGradient',true, ...
            'MaxFunctionEvaluations',p.construction_max_iterations,'MaxIterations',p.construction_max_iterations, ...
            'FunctionTolerance',1e-12,'StepTolerance',1e-12,'OptimalityTolerance',1e-12);
        [z,~,~,flag,info]=lsqnonlin(@waypoint,x(1:n)./qs,[],[],opt);
        x=[z.*qs;zeros(n,1)];[rr,~]=waypoint(z);
        construction=struct('method','geometric halfway waypoint; not equilibrium','solver','MATLAB lsqnonlin', ...
            'success',flag>0,'status',flag,'iterations',info.iterations,'function_evaluations',info.funcCount, ...
            'position_residual_m',norm(rr)*p.output_scale_m,'static_equilibrium',false);
        if flag<=0 || any(~isfinite(x)),out.status='unavailable';out.failure_code='WAYPOINT_CONSTRUCTION_FAILED';end
    case {'static_input','design_sensitivity'}
        [q,construction]=equilibrium(model,x(1:n),u);
        x=[q;zeros(n,1)];
        if ~construction.success,out.status='unavailable';out.failure_code='STATIC_EQUILIBRIUM_FAILED';end
    case 'linearize'
        % The exact saved/configuration point is unchanged, including its rate.
    otherwise
        error('SOROSIM_UNSUPPORTED_ANALYSIS_OPERATION');
end
out.x=x;out.u=u;out.construction=construction;
if ~strcmp(out.status,'computed'),out.total_s=toc(started);return;end
d=sr_derivatives(model,x(1:n),x(n+1:end),u,[]);
out.raw=d;out.mass_condition=cond(d.mass_matrix);
if ~regular(d.mass_matrix)
    out.status='unavailable';out.failure_code='ILL_CONDITIONED_MASS';out.total_s=toc(started);return;
end
out.A=[zeros(n),eye(n);-d.mass_matrix\d.Rq,-d.mass_matrix\d.Rqd];
out.B=[zeros(n,m);-d.mass_matrix\d.Ru];out.drift=[x(n+1:end);d.qdd];
out.position=world(d.tip_position);out.velocity=R*d.tip_velocity;
out.C=[R*d.tip_position_q,zeros(3,n)];out.D=zeros(3,m);
out.Cv=[R*d.tip_velocity_q,R*d.tip_velocity_qd];out.Dv=zeros(3,m);
% Independent directional velocity derivative along full passive+input flow.
% Both halves of Cv participate, including Jdot(q)*qdot at nonzero velocity.
if isfield(r,'check_instantaneous_braking') && r.check_instantaneous_braking
    checks=cell(2,1);test_inputs=[u,limits-u];
    for j=1:2
        ut=test_inputs(:,j);
        flow=sr_dynamics(model,x(1:n),x(n+1:end),ut,[],[],false);
        f=[x(n+1:end);flow.qdd];h=p.derivative_step/max(1,norm(f./r.state_scales(:),inf));
        xp=x+h*f;xm=x-h*f;
        vp=sr_dynamics(model,xp(1:n),xp(n+1:end),ut,[],[],false);
        vm=sr_dynamics(model,xm(1:n),xm(n+1:end),ut,[],[],false);
        actual=R*(vp.tip_velocity-vm.tip_velocity)/(2*h);
        predicted=out.Cv*out.drift+out.Cv*out.B*(ut-u);
        checks{j}=struct('input_n',ut,'actual_m_s2',actual,'predicted_m_s2',predicted, ...
            'step_s',h,'verification',compare(actual,predicted,repmat(p.output_scale_m/p.duration_s^2,3,1)));
    end
    out.acceleration_check=struct('cases',{checks},'nonzero_velocity',norm(out.velocity)>1e-9, ...
        'passed',checks{1}.verification.passed && checks{2}.verification.passed, ...
        'scope','Pointwise numerical consistency; no regional or global error bound.');
end
out.derivative_check=check_derivative(x,u,out);
if ~out.derivative_check.passed,out.status='unavailable';out.failure_code='DERIVATIVE_CHECK_FAILED';end
st=sr_derivatives(model,x(1:n),zeros(n,1),u,zeros(n,1));
out.static_residual=st.residual;out.static_tangent=st.Rq;out.static_tangent_condition=cond(st.Rq);
out.equilibrium=norm(st.residual,inf)<=p.static_force_tolerance && norm(x(n+1:end),inf)<=p.static_force_tolerance;
out.linearization_scope='frozen nonequilibrium local affine model';
if out.equilibrium,out.linearization_scope='local equilibrium linearization';end
asym=norm(st.Rq-st.Rq','fro')/max(1e-30,norm(st.Rq,'fro'));
out.conservative_tangent=struct('relative_asymmetry',asym,'eigenvalues',eig((st.Rq+st.Rq')/2), ...
    'qualification','Stationary potential classification only; not closed-loop or nonlinear dynamic stability.');
out.conservative_tangent.classification='unclassified_nonstationary_or_nonsymmetric';
if out.equilibrium && asym<1e-6
    ev=out.conservative_tangent.eigenvalues;
    if min(ev)>0,out.conservative_tangent.classification='strict_local_potential_minimum';
    elseif min(ev)<0,out.conservative_tangent.classification='not_local_potential_minimum';end
end
if ismember(r.operation,{'static_input','design_sensitivity'}) && out.equilibrium && regular(st.Rq)
    out.input_sensitivity=struct('dq_du',-st.Rq\st.Ru,'direct_position_u',zeros(3,m));
    out.input_sensitivity.dp_du=R*st.tip_position_q*out.input_sensitivity.dq_du;
    if strcmp(r.operation,'static_input')
        du=p.input_scale_n*sin((1:m)');h=p.derivative_step;
        if all(u+h*du>=0 & u+h*du<=limits & u-h*du>=0 & u-h*du<=limits)
            [qp,sp]=equilibrium(model,x(1:n),u+h*du);[qm,sm]=equilibrium(model,x(1:n),u-h*du);
            fp=sr_routing(model,qp,u+h*du,false);fm=sr_routing(model,qm,u-h*du,false);
            actual=R*(fp.tip_pose(1:3,4)-fm.tip_pose(1:3,4))/(2*h);
            predicted=out.input_sensitivity.dp_du*du;
            out.input_sensitivity.verification=compare(actual,predicted,repmat(p.output_scale_m,3,1));
            out.input_sensitivity.perturbed_equilibria={sp,sm};
            out.input_sensitivity.verification.passed=out.input_sensitivity.verification.passed && sp.success && sm.success;
        else
            out.input_sensitivity.verification=struct('passed',false,'reason','PERTURBATION_OUTSIDE_PHYSICAL_BOUNDS');
        end
    else
        assert(r.design_step>0,'INVALID_DESIGN_STEP');
        plus=sr_model(r.plus_specification);minus=sr_model(r.minus_specification);
        assert(isequal(plus.spec.coordinate_order,model.spec.coordinate_order) && ...
            isequal(minus.spec.coordinate_order,model.spec.coordinate_order),'UNSUPPORTED_TOPOLOGY_DERIVATIVE');
        dp=sr_derivatives(plus,x(1:n),zeros(n,1),u,zeros(n,1));
        dm=sr_derivatives(minus,x(1:n),zeros(n,1),u,zeros(n,1));
        Rd=(dp.residual-dm.residual)/(2*r.design_step);
        pd=(world(dp.tip_position)-world(dm.tip_position))/(2*r.design_step);
        dq=-st.Rq\Rd;prediction=pd+R*st.tip_position_q*dq;
        [qp,sp]=equilibrium(plus,x(1:n),u);[qm,sm]=equilibrium(minus,x(1:n),u);
        fp=sr_routing(plus,qp,u,false);fm=sr_routing(minus,qm,u,false);
        actual=R*(fp.tip_pose(1:3,4)-fm.tip_pose(1:3,4))/(2*r.design_step);
        out.design_sensitivity=struct('R_d',Rd,'p_d',pd,'dq_dd',dq,'dp_dd',prediction, ...
            'finite_difference_dp_dd',actual,'step',r.design_step,'variable',r.design_variable, ...
            'plus_identity',plus.spec.identity,'minus_identity',minus.spec.identity, ...
            'perturbed_equilibria',{{sp,sm}},'verification',compare(actual,prediction,repmat(p.output_scale_m,3,1)), ...
            'scope','Fixed q_g/u partial with full rebuilt physical models, including length-dependent T; fixed topology only.');
        out.design_sensitivity.verification.passed=out.design_sensitivity.verification.passed && sp.success && sm.success;
    end
elseif ismember(r.operation,{'static_input','design_sensitivity'})
    out.sensitivity_status='ILL_CONDITIONED_TANGENT_OR_NON_EQUILIBRIUM';
end
out.total_s=toc(started);

    function y=world(position)
        y=R*position+model.spec.mount_position(:);
    end
    function yes=regular(M)
        yes=all(isfinite(M(:))) && rcond(M)>sqrt(eps);
    end
    function [rr,J]=waypoint(z)
        f=sr_routing(model,z.*qs,u,false);
        rr=(world(f.tip_pose(1:3,4))-r.target(:))/p.output_scale_m;
        J=R*f.tip_jacobian(4:6,:).*qs'/p.output_scale_m;
    end
    function [cost,gradient]=target_cost(z)
        f=sr_routing(model,z(1:n).*qs,z(n+1:end)*p.input_scale_n,false);
        e=(world(f.tip_pose(1:3,4))-r.target(:))/p.output_scale_m;
        cost=e'*e+1e-6*sum(z(n+1:end).^2);
        gradient=[2*qs.*(f.tip_jacobian(4:6,:)'*R'*e)/p.output_scale_m;2e-6*z(n+1:end)];
    end
    function [c,ceq,Jc,Jceq]=static_constraint(z)
        f=sr_derivatives(model,z(1:n).*qs,zeros(n,1),z(n+1:end)*p.input_scale_n,zeros(n,1));
        c=[];Jc=[];ceq=f.residual/.001;Jceq=([f.Rq.*qs',f.Ru*p.input_scale_n]/.001)';
    end
    function [q,info]=equilibrium(mod,seed,tension)
        opt=optimoptions('fsolve','Display','off','SpecifyObjectiveGradient',true, ...
            'MaxIterations',p.static_max_iterations,'MaxFunctionEvaluations',2*p.static_max_iterations, ...
            'FunctionTolerance',1e-20,'StepTolerance',1e-12,'OptimalityTolerance',1e-12);
        [z,rr,flag,log]=fsolve(@residual,seed./qs,opt);q=z.*qs;
        info=struct('solver','MATLAB fsolve','status',flag,'iterations',log.iterations, ...
            'function_evaluations',log.funcCount,'static_residual_inf',norm(rr,inf)*.001, ...
            'success',flag>0 && norm(rr,inf)*.001<=p.static_force_tolerance,'computed_tensions_n',tension);
        function [rr,J]=residual(z)
            f=sr_derivatives(mod,z.*qs,zeros(n,1),tension,zeros(n,1));rr=f.residual/.001;J=f.Rq.*qs'/.001;
        end
    end
    function check=compare(actual,predicted,scale)
        a=actual./scale;b=predicted./scale;err=abs(a-b);
        check=struct('passed',all(err<=p.derivative_atol+p.derivative_rtol*abs(b)), ...
            'absolute_norm',norm(actual-predicted),'relative_norm',norm(actual-predicted)/max(1e-30,norm(actual)), ...
            'max_normalized_error',max(err),'max_tolerance_ratio',max(err./(p.derivative_atol+p.derivative_rtol*abs(b))));
    end
    function check=check_derivative(x,u,base)
        dx=r.state_scales(:).*cos((1:2*n)');du=p.input_scale_n*sin((1:m)');h=p.derivative_step;
        xp=x+h*dx;xm=x-h*dx;
        dp=sr_dynamics(model,xp(1:n),xp(n+1:end),u+h*du,[],[],false);
        dm=sr_dynamics(model,xm(1:n),xm(n+1:end),u-h*du,[],[],false);
        check.dynamics=compare([dx(n+1:end);(dp.qdd-dm.qdd)/(2*h)],base.A*dx+base.B*du,r.state_scales(:));
        check.position=compare(R*(dp.tip_position-dm.tip_position)/(2*h),base.C*dx,repmat(p.output_scale_m,3,1));
        check.velocity=compare(R*(dp.tip_velocity-dm.tip_velocity)/(2*h),base.Cv*dx,repmat(p.output_scale_m/p.duration_s,3,1));
        check.passed=check.dynamics.passed && check.position.passed && check.velocity.passed;check.step=h;
    end
end
