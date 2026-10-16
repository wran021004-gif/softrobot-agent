function out=sr_nmpc(model,r)
% Full scaled multiple shooting. No wall/CPU early-return policy.
started=tic;c=context(model,r);
c.profile=isfield(r,'profile') && r.profile;
[objective,constraint,inspect,step,callbackProfile]=sr_nmpc_callbacks(model,c);history=[];
warmStart=tic;
if isfield(r,'warm') && ~isempty(r.warm)
    U=r.warm.tensions';U=[U(:,2:end),U(:,end)];
    U=U(:,min(1:c.horizon,size(U,2)));
else
    U=repmat(c.previous,1,c.horizon);
end
U=min(max(U,0),c.input_scale);
[initial,roots]=regenerate(c,U,step);warm_s=toc(warmStart);
initialEvaluation=inspect(initial);
if isfield(r,'check_only') && r.check_only
    out=check_callbacks(initial,c,objective,constraint);
    initialEvaluation.jacobian=[];
    out.initial=initialEvaluation;out.context=c;out.initial_vector=initial;
    out.warm_preparation_s=warm_s;out.roots=roots;return
end
best=[];bestObjective=inf;selectedIteration=[];
opt=optimoptions('fmincon','Algorithm','sqp','Display','off', ...
    'SpecifyObjectiveGradient',true,'SpecifyConstraintGradient',true, ...
    'MaxIterations',c.recipe.max_iterations,'MaxFunctionEvaluations',100000, ...
    'OptimalityTolerance',model.spec.solver.optimality_tolerance, ...
    'ConstraintTolerance',model.spec.solver.constraint_tolerance, ...
    'StepTolerance',model.spec.solver.step_tolerance,'OutputFcn',@observe);
solveStart=tic;
[returned,rawObjective,flag,info]=fmincon(objective,initial,[],[],[],[],c.lower,c.upper,constraint,opt);
solve_s=toc(solveStart);
validationStart=tic;
raw=verify(returned,model,c);statusEligible=flag>=0;
if raw.feasible && statusEligible && raw.objective<bestObjective
    best=returned;bestObjective=raw.objective;selectedIteration=info.iterations;
end
recovery=struct('enabled',c.recipe.recover_returned_tensions,'attempted',false,'selected',false, ...
    'error',[],'wall_s',0,'source','returned_fmincon_tensions_reintegrated_from_current_measurement');
if c.recipe.recover_returned_tensions && statusEligible && raw.objective<bestObjective
    recovery.attempted=true; recoveryStart=tic;
    try
        rawU=reshape(returned(2*c.n*(c.steps+1)+1:end),c.m,c.horizon).*c.input_scale;
        [repaired,recovery.roots]=regenerate(c,min(max(rawU,0),c.input_scale),step);
        check=verify(repaired,model,c);recovery.constraint_violation=check.constraint_violation;
        if check.feasible && check.objective<bestObjective
            best=repaired;bestObjective=check.objective;recovery.selected=true;selectedIteration=info.iterations;
        end
    catch failure
        recovery.error=failure.message;
    end
    recovery.wall_s=toc(recoveryStart);
end
accepted=~isempty(best) && statusEligible;
if accepted, selected=verify(best,model,c);else, selected=raw;end
boundProjection=0;
if accepted
    bounded=min(max(best,c.lower),c.upper);
    boundProjection=max(abs(bounded(end-c.m*c.horizon+1:end)-best(end-c.m*c.horizon+1:end)).*repmat(c.input_scale,c.horizon,1));
    selected=verify(bounded,model,c); % physical export bounds are exact, then defects are rechecked
end
accepted=accepted && selected.feasible;
validation_s=toc(validationStart);
out=struct('accepted',accepted,'optimization_converged',flag>0,'exitflag',flag, ...
    'message',info.message,'iterations',info.iterations,'function_evaluations',info.funcCount, ...
    'raw_objective',rawObjective,'initial_objective',initialEvaluation.objective, ...
    'bound_projection_max_n',boundProjection, ...
    'returned_constraint_violation',raw.constraint_violation,'selected_iteration',selectedIteration, ...
    'objective',selected.objective,'constraint_violation',selected.constraint_violation, ...
    'states',selected.states','tensions',selected.tensions','tip_positions',selected.tip_positions', ...
    'tip_velocities',selected.tip_velocities','recovery',recovery,'independent_validation',selected, ...
    'warm_preparation_s',warm_s,'optimization_s',solve_s,'validation_s',validation_s, ...
    'update_s',toc(started),'model_identity',model.spec.identity,'horizon',c.horizon, ...
    'solver','MATLAB fmincon SQP','roots',{roots},'state_scale',c.state_scale,'input_scale',c.input_scale, ...
    'initial_state',c.measured,'previous_input',c.previous,'elapsed_s',c.elapsed);
if c.profile,out.callback_profile=callbackProfile();out.iteration_trace=history;end

    function stop=observe(z,values,state)
        stop=false;
        if c.profile
            history(end+1,:)= [values.iteration,values.funccount,values.fval,values.constrviolation,values.firstorderopt];
        end
        if strcmp(state,'iter') && values.iteration>0
            e=inspect(z);
            violation=max([abs(e.constraints);c.lower-z;z-c.upper]);
            if all(isfinite(z)) && isfinite(e.objective) && violation<=1e-5 && e.objective<bestObjective
                best=z;bestObjective=e.objective;selectedIteration=values.iteration;
            end
        end
    end
end

function c=context(model,r)
c.recipe=r.recipe;c.n=model.S.ndof;c.m=numel(model.spec.routes);
assert(strcmp(c.recipe.integration_method,'implicit_euler'),'UNSUPPORTED_INTEGRATION_METHOD');
assert(strcmp(c.recipe.stopping_policy,'research_work_v1'),'RESEARCH_STOPPING_POLICY_REQUIRED');
c.elapsed=r.elapsed_s;c.period=r.period_s;
remaining=(r.duration_s-r.elapsed_s)/r.period_s;
assert(abs(remaining-round(remaining))<1e-7 && remaining>=1,'CONTROL_TIME_GRID_REQUIRED');
c.horizon=min(c.recipe.horizon,round(remaining));c.steps=c.horizon*c.recipe.substeps;c.h=c.period/c.recipe.substeps;
c.measured=r.measured_state(:);c.previous=r.previous_input(:);c.target=r.target(:);
c.state_scale=[repmat(c.recipe.curvature_scale_rad_m,c.n,1);repmat(c.recipe.rate_scale_rad_m_s,c.n,1)];
c.input_scale=[model.spec.routes.force_limit_n]';
assert(numel(c.measured)==2*c.n && numel(c.previous)==c.m && ...
    all(isfinite([c.measured;c.previous])) && all(c.previous>=0 & c.previous<=c.input_scale),'INVALID_NMPC_INPUT');
if isempty(c.recipe.position_error_scale_m),c.position_scale=r.position_tolerance_m;else,c.position_scale=c.recipe.position_error_scale_m;end
c.holding_start=max(0,r.duration_s-r.settling.window_s-c.recipe.holding_brake_lead_s);
c.holding_normalization=1;
if strcmp(c.recipe.holding_speed_cost_mode,'window_normalized_v1')
    assert(abs(c.recipe.holding_speed_cost_window_s-r.settling.window_s)<1e-12,'HOLDING_WINDOW_MISMATCH');
    c.holding_normalization=c.recipe.holding_speed_cost_window_s;
end
nv=2*c.n*(c.steps+1)+c.m*c.horizon;
c.lower=[-inf(2*c.n*(c.steps+1),1);zeros(c.m*c.horizon,1)];
c.upper=[inf(2*c.n*(c.steps+1),1);ones(c.m*c.horizon,1)];assert(numel(c.lower)==nv);
end

function [z,trace]=regenerate(c,U,step)
X=zeros(2*c.n,c.steps+1);X(:,1)=c.measured;trace=cell(c.steps,1);
opts=optimoptions('fsolve','Display','off','SpecifyObjectiveGradient',true, ...
    'FunctionTolerance',c.recipe.root_tolerance^2,'StepTolerance',1e-12, ...
    'OptimalityTolerance',1e-12,'MaxIterations',60,'MaxFunctionEvaluations',200);
for k=1:c.steps
    u=U(:,ceil(k/c.recipe.substeps));previous=X(:,k);
    [y,residual,flag,info]=fsolve(@(next)step(previous,next,u),previous,opts);
    violation=norm(residual,inf);
    assert(all(isfinite(y)) && violation<=c.recipe.root_tolerance,'WARM_ROOT_FAILED: residual %.9g flag %d',violation,flag);
    X(:,k+1)=y;trace{k}=struct('exitflag',flag,'iterations',info.iterations,'violation',violation);
end
z=[reshape(X./c.state_scale,[],1);reshape(U./c.input_scale,[],1)];
end

function e=verify(z,model,c)
% Fresh callback cache AND separately recomputed physical dynamic defects.
[objective,~,inspect]=sr_nmpc_callbacks(model,c);e=inspect(z);
e.jacobian=[];e.gradient=[];
physical=zeros(2*c.n,c.steps);
for k=1:c.steps
    a=e.states(:,k);b=e.states(:,k+1);u=e.tensions(:,ceil(k/c.recipe.substeps));
    d=sr_dynamics(model,b(1:c.n),b(c.n+1:end),u,(b(c.n+1:end)-a(c.n+1:end))/c.h,[],false);
    physical(:,k)=[(b(1:c.n)-a(1:c.n)-c.h*b(c.n+1:end))/10;d.residual/.001];
end
e.constraint_violation=max([abs(e.constraints);abs(physical(:));c.lower-z;z-c.upper]);
e.feasible=all(isfinite([z;e.objective;e.constraints])) && e.constraint_violation<=1e-5;
e.dynamic_force_residual_max_nm2=max(abs(physical(c.n+1:end,:)),[],'all')*.001;
end

function out=check_callbacks(z,c,objective,constraint)
% Fixed directions exercise states, rates, input scaling and off-diagonal blocks.
[f,g]=objective(z);[~,ce,~,J]=constraint(z);J=J';h=1e-6;
directions=[sin((1:numel(z))'),cos((1:numel(z))'),zeros(numel(z),1)];
directions(2*c.n*(c.steps+1)+1:end,3)=1;
errors=zeros(size(directions,2),4);steps=[h,h,1e-3];
for j=1:size(directions,2)
    h=steps(j); % Input-only objective is exactly quadratic; avoid subtractive cancellation.
    d=directions(:,j);d=d/norm(d);
    fp=objective(z+h*d);fm=objective(z-h*d);
    [~,cp]=constraint(z+h*d);[~,cm]=constraint(z-h*d);
    fd=(fp-fm)/(2*h);cd=(cp-cm)/(2*h);predicted=g'*d;pc=J*d;
    errors(j,:)=[abs(fd-predicted),abs(fd-predicted)/max(abs(fd),1e-12), ...
        norm(cd-pc,inf),norm(cd-pc,inf)/max(norm(cd,inf),1e-12)];
end
out=struct('objective',f,'constraint_violation',norm(ce,inf),'directional_errors',errors, ...
    'decision_dimension',numel(z),'constraint_dimension',numel(ce),'steps_scaled',steps);
end
