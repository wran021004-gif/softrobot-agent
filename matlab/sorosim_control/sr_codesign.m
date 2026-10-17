function out=sr_codesign(model,r)
% Full frozen task, shared dynamic callbacks, explicit task-gap epigraph slacks.
started=tic;request=r.control;request.full_task=true;request.prepare_only=true;
prepared=sr_nmpc(model,request);c=prepared.context;c.export_output_jacobians=true;
[~,~,inspect]=sr_nmpc_callbacks(model,c);nv=numel(prepared.initial_vector);
assert(c.elapsed==0,'CODESIGN_REQUIRES_FROZEN_INITIAL_STATE');
requirements=r.requirements.constraints;
feasibility=ismember(r.arguments.objective_mode,{'maximum_original_violation','minimum_signed_task_excess','task_capability'});
interior=ismember(r.arguments.objective_mode,{'minimum_signed_task_excess','task_capability'});
freeEpigraph=strcmp(r.arguments.objective_mode,'task_capability');
performance=strcmp(r.arguments.objective_mode,'task_feasible_effort');
nodes=[];groups=[];radii=[];references=[];labels={};
for j=1:numel(requirements)
    t=requirements(j);
    assert(strcmp(t.kind,'norm_bound') && strcmp(t.signal.frame,'world') && ...
        strcmp(t.signal.phase,'post_step'),'UNSUPPORTED_CODESIGN_CONSTRAINT');
    group=1+strcmp(t.signal.name,'tip_velocity');
    assert(ismember(t.signal.name,{'tip_position','tip_velocity'}),'UNSUPPORTED_CODESIGN_SIGNAL');
    for k=1:numel(t.indices)
        time=r.requirements.time_grid_s(t.indices(k)+1);node=round(time/c.h);
        assert(node>=1 && node<=c.steps && abs(node*c.h-time)<1e-12,'UNSUPPORTED_CODESIGN_SAMPLE_GRID');
        nodes(end+1)=node;groups(end+1)=group;radii(end+1)=t.radius;
        references(:,end+1)=t.reference(k,:)';labels{end+1}=t.constraint_id;
    end
end
optimizedIndices=1:numel(nodes);originalForOptimized=num2cell(optimizedIndices);
if feasibility || performance
    optimizedIndices=[];originalForOptimized={};
    for k=1:numel(nodes)
        match=find(arrayfun(@(j) nodes(j)==nodes(k) && groups(j)==groups(k) && ...
            radii(j)==radii(k) && isequal(references(:,j),references(:,k)),optimizedIndices),1);
        if isempty(match)
            optimizedIndices(end+1)=k;originalForOptimized{end+1}=k;
        else
            originalForOptimized{match}(end+1)=k;
        end
    end
end
if ismember(r.operation,{'replay','cross_replay'})
    given=r.trajectory;U=given.tensions_n';
    if strcmp(r.operation,'cross_replay')
        % Transfer only physical commands. The destination model supplies every state.
        X=prepared.initial.states;
        gap=task_values(prepared.initial);
        given.slacks=struct('position',max([0;gap(groups==1)]), ...
            'speed',max([0;gap(groups==2)]));
    else
        X=given.states';
    end
    assert(isequal(size(X),[2*c.n,c.steps+1]) && isequal(size(U),[c.m,c.horizon]),'REPLAY_DIMENSION_MISMATCH');
    assert(norm(X(:,1)-c.measured,inf)<1e-12,'REPLAY_INITIAL_STATE_MISMATCH');
    z=[reshape(X./c.state_scale,[],1);reshape(U./c.input_scale,[],1);given.slacks.position;given.slacks.speed];
    e=inspect(z(1:nv));[ci,ce]=constraints(z);physical=zeros(2*c.n,c.steps);
    for k=1:c.steps
        a=X(:,k);b=X(:,k+1);u=U(:,ceil(k/c.recipe.substeps));
        d=sr_dynamics(model,b(1:c.n),b(c.n+1:end),u,(b(c.n+1:end)-a(c.n+1:end))/c.h,[],false);
        physical(:,k)=[(b(1:c.n)-a(1:c.n)-c.h*b(c.n+1:end))/10;d.residual/.001];
    end
    difference=max(abs((X-prepared.initial.states)./c.state_scale),[],'all');
    if performance
        slackLower=[0;0];slackUpper=[0;0];
    elseif interior
        if freeEpigraph
            slackLower=[-inf;0];
        else
            slackLower=[-1;0];
        end
        slackUpper=[inf;0];
    elseif feasibility
        slackLower=[0;0];slackUpper=[inf;0];
    else
        slackLower=[0;0];slackUpper=[inf;inf];
    end
    violation=max([abs(ce);ci;c.lower-z(1:nv);z(1:nv)-c.upper; ...
        slackLower-z(end-1:end);z(end-1:end)-slackUpper;abs(physical(:))]);
    out=struct('status','computed','passed',violation<=1e-5 && difference<=1e-5, ...
        'independent_scaled_violation',violation,'reintegrated_scaled_state_error',difference, ...
        'force_residual_max_nm2',max(abs(physical(c.n+1:end,:)),[],'all')*.001, ...
        'task',task_report(e),'objective',objective(z),'full_task_horizon_s',r.requirements.duration_s, ...
        'trajectory',struct('states',X','tensions_n',U','times_s',(0:c.steps)*c.h), ...
        'method','fresh implicit roots from actual initial state plus separate sr_dynamics force balance', ...
        'roots',{prepared.roots},'total_s',toc(started));return;
end
initial=prepared.initial_vector;gaps=task_values(prepared.initial);
if feasibility
    slacks=[max(gaps)+1e-4;0];
    if ~interior,slacks(1)=max(0,slacks(1));end
    if freeEpigraph
        minimum=-inf;
    elseif interior
        minimum=-1;
    else
        minimum=0;
    end
    lower=[c.lower;minimum;0];upper=[c.upper;inf;0];
else
    slacks=[max([0;gaps(groups==1)]);max([0;gaps(groups==2)])]+1e-4;
    lower=[c.lower;0;0];upper=[c.upper;inf;inf];
end
z0=[initial;slacks];
if performance
    lower(end-1:end)=0;upper(end-1:end)=0;z0(end-1:end)=0;
    assert(all(gaps<=model.spec.solver.constraint_tolerance), ...
        'PERFORMANCE_REQUIRES_NUMERICALLY_TASK_FEASIBLE_REMATERIALIZED_START');
end
warm_report=struct('used',false);
if isfield(r,'warm_trajectory')
    assert(strcmp(r.operation,'solve') && strcmp(r.arguments.initialization,'saved_candidate_trajectory'), ...
        'CODESIGN_WARM_SOURCE_REQUIRES_SOLVE');
    warm=r.warm_trajectory;X=warm.states';U=warm.tensions_n';
    assert(isequal(size(X),[2*c.n,c.steps+1]) && isequal(size(U),[c.m,c.horizon]), ...
        'CODESIGN_WARM_FULL_TRAJECTORY_DIMENSION_MISMATCH');
    assert(norm(X(:,1)-c.measured,inf)<=1e-12,'CODESIGN_WARM_INITIAL_STATE_MISMATCH');
    z0=[reshape(X./c.state_scale,[],1);reshape(U./c.input_scale,[],1); ...
        warm.slacks.position;warm.slacks.speed];
    [warmIneq,warmEq]=constraints(z0);
    warmViolation=max([0;abs(warmEq);warmIneq;lower-z0;z0-upper]);
    warmGap=task_values(inspect(z0(1:nv)));
    assert(all(isfinite(z0)) && warmViolation<=1e-5 && all(warmGap<=1e-8), ...
        'CODESIGN_WARM_WITNESS_NOT_INDEPENDENTLY_FEASIBLE');
    warm_report=struct('used',true,'scaled_violation',warmViolation, ...
        'maximum_original_task_excess',max(warmGap),'initial_objective',objective(z0), ...
        'source_state_nodes',size(X,2),'source_control_intervals',size(U,2));
end
opt=optimoptions('fmincon','Algorithm','sqp','Display','off','SpecifyObjectiveGradient',true, ...
    'SpecifyConstraintGradient',true,'MaxIterations',c.recipe.max_iterations,'MaxFunctionEvaluations',100000, ...
    'OptimalityTolerance',model.spec.solver.optimality_tolerance,'ConstraintTolerance',model.spec.solver.constraint_tolerance, ...
    'StepTolerance',model.spec.solver.step_tolerance);
if isfield(r,'check_only') && r.check_only
    if isfield(r,'raw_point')
        raw=r.raw_point;point=raw.z(:);assert(numel(point)==nv+2,'RAW_NLP_POINT_DIMENSION_MISMATCH');
        [f,g]=objective(point);[ci,ce,gi,ge]=constraints(point);lambda=raw.lambda;
        for field={'eqnonlin','ineqnonlin','lower','upper'}
            name=field{1};lambda.(name)=reshape(lambda.(name),[],1);
        end
        assert(numel(lambda.eqnonlin)==numel(ce) && numel(lambda.ineqnonlin)==numel(ci), ...
            'RAW_MULTIPLIER_CONSTRAINT_CORRESPONDENCE_MISMATCH');
        if strcmp(r.diagnostic_mode,'regularity')
            out=sr_optimality(point,g,ci,ce,gi,ge,lower,upper,lambda,c);
            out.kkt=kkt_report(point,lambda,raw.exitflag);
        else
            lo=isfinite(lower);hi=isfinite(upper);nx=2*c.n;
            terms=struct('objective',f,'initial_state',lambda.eqnonlin(1:nx)'*ce(1:nx), ...
                'complete_dynamics',lambda.eqnonlin(nx+1:end)'*ce(nx+1:end), ...
                'task',lambda.ineqnonlin'*ci,'lower_bounds',lambda.lower(lo)'*(lower(lo)-point(lo)), ...
                'upper_bounds',lambda.upper(hi)'*(point(hi)-upper(hi)));
            out=struct('lagrangian_terms',terms,'lagrangian',sum(structfun(@(x)x,terms)), ...
                'semantics','fixed normalized raw variables and exact full multipliers; rebuilt candidate model', ...
                'envelope_gradient','requires paired structural partials and regular branch qualification');
        end
        out.status='computed';out.total_s=toc(started);return;
    end
    [f,g]=objective(z0);[ci,ce,gi,ge]=constraints(z0);v=sin((1:numel(z0))');v=v/norm(v);h=1e-5;
    [ip,ep]=constraints(z0+h*v);[im,em]=constraints(z0-h*v);
    fd=(objective(z0+h*v)-objective(z0-h*v))/(2*h);cd=([ip;ep]-[im;em])/(2*h);
    out=struct('objective_relative_error',abs(fd-g'*v)/max(1e-12,abs(fd)), ...
        'constraint_relative_error',norm(cd-[gi,ge]'*v,inf)/max(1e-12,norm(cd,inf)), ...
        'variables',numel(z0),'equalities',numel(ce),'inequalities',numel(ci), ...
        'warm_start',warm_report,'optimized_task_inequalities',numel(optimizedIndices), ...
        'original_task_predicates',numel(nodes),'dynamics_jacobian_nnz',nnz(ge), ...
        'dense_sqp_hessian_bytes_estimate',8*numel(z0)^2, ...
        'physical_control_commands',c.horizon,'internal_state_nodes',c.steps+1, ...
        'initial_root_count',numel(prepared.roots),'initial_maximum_task_excess',max(gaps), ...
        'initial_dynamics_violation',norm(ce,inf),'initialization',r.arguments.initialization, ...
        'one_callback_s',callback_cost(z0),'total_s',toc(started));return;
end
t=tic;[z,f,flag,info,lambda,gradient]=fmincon(@objective,z0,[],[],[],[],lower,upper,@constraints,opt);solve_s=toc(t);
% Preserve the expensive raw returned iterate before further validation can fail.
if isfield(r,'checkpoint_path')
    assert(~isfile(r.checkpoint_path),'PRESERVE_OPTIMIZER_CHECKPOINT');
    temporary=[r.checkpoint_path '.tmp'];fid=fopen(temporary,'w');assert(fid>=0,'CHECKPOINT_OPEN_FAILED');
    fprintf(fid,'%s',jsonencode(struct('z',z,'objective',f,'exitflag',flag,'output',info, ...
        'lambda',lambda,'objective_gradient',gradient,'solve_s',solve_s)));
    fclose(fid);movefile(temporary,r.checkpoint_path);
end
kkt=kkt_report(z,lambda,flag);rawZ=z;
z=min(max(z,lower),upper);projectionMax=max(abs(z-rawZ));f=objective(z);
e=inspect(z(1:nv));[ci,ce]=constraints(z);
violation=max([abs(ce);ci;lower-z;z-upper]);
raw=struct('objective',f,'scaled_violation',violation,'task',task_report(e), ...
    'slacks',struct('position',z(end-1),'speed',z(end)));
recovery=struct('attempted',false,'selected',false,'error',[],'wall_s',0);
% Honor the existing recipe: recover returned tensions through the same roots.
% Task slacks must be reevaluated on that trajectory, never copied from the NLP.
if c.recipe.recover_returned_tensions && flag>=0
    recovery.attempted=true;t=tic;
    try
        request.initial_tensions=e.tensions';fresh=sr_nmpc(model,request);
        gap=task_values(fresh.initial);
        if feasibility
            repaired=[fresh.initial_vector;max([minimum;gap]);0];
        else
            repaired=[fresh.initial_vector;max([0;gap(groups==1)]);max([0;gap(groups==2)])];
        end
        [ri,re]=constraints(repaired);rv=max([abs(re);ri;lower-repaired;repaired-upper]);
        recovery.objective=objective(repaired);recovery.scaled_violation=rv;
        if rv<=1e-5 && (violation>1e-5 || recovery.objective<f)
            z=repaired;f=recovery.objective;violation=rv;e=inspect(z(1:nv));recovery.selected=true;
        end
    catch failure
        recovery.error=failure.message;
    end
    recovery.wall_s=toc(t);
end
out=struct('status','returned','exitflag',flag,'converged',flag>0,'iterations',info.iterations, ...
    'function_evaluations',info.funcCount,'message',info.message,'objective',f,'initial_objective',objective(z0), ...
    'scaled_violation',violation,'relaxed_feasible',all(isfinite(z)) && violation<=1e-5, ...
    'trajectory',struct('states',e.states','tensions_n',e.tensions','times_s',(0:c.steps)*c.h, ...
        'slacks',struct('position',z(end-1),'speed',z(end))), ...
    'task',task_report(e),'original_feasible',all(task_values(e)<=0) && violation<=1e-5, ...
    'raw_returned',raw,'recovery',recovery, ...
    'kkt',kkt, ...
    'initial_task',task_report(prepared.initial),'optimization_s',solve_s, ...
    'warm_start',warm_report,'optimized_task_inequalities',numel(optimizedIndices), ...
    'original_task_predicates',numel(nodes), ...
    'preparation_s',prepared.warm_preparation_s,'total_s',toc(started),'initial_roots',{prepared.roots}, ...
    'objective_definition',r.arguments,'model_identity',model.spec.identity,'physical_task_acceptance','unmeasured');
out.kkt.same_as_selected_trajectory=~recovery.selected && projectionMax<=1e-12;
out.kkt.bound_projection_max=projectionMax;

    function wall=callback_cost(z)
        t=tic;constraints(z+1e-9);wall=toc(t);
    end
    function [f,g]=objective(z)
        if feasibility
            g=zeros(nv+2,1);g(end-1)=1;f=z(end-1);return;
        end
        g=zeros(nv+2,1);f=r.arguments.position_weight*z(end-1)+r.arguments.speed_weight*z(end);
        g(end-1:end)=[r.arguments.position_weight;r.arguments.speed_weight];
        if performance,f=0;g(:)=0;end
        if performance || strcmp(r.arguments.objective_mode,'task_gap_with_effort')
            ix=2*c.n*(c.steps+1)+(1:c.m*c.horizon);U=reshape(z(ix),c.m,c.horizon);delta=diff(U,1,2);
            effort=sum(U.^2,'all')/numel(U)+.1*sum(delta.^2,'all')/numel(delta);
            G=2*U/numel(U);G(:,2:end)=G(:,2:end)+.2*delta/numel(delta);G(:,1:end-1)=G(:,1:end-1)-.2*delta/numel(delta);
            coefficient=r.arguments.secondary_coefficient;if performance,coefficient=1;end
            f=f+coefficient*effort;g(ix)=coefficient*G(:);
        end
    end
    function gap=task_values(e)
        gap=zeros(numel(nodes),1);
        for k=1:numel(nodes)
            if groups(k)==1,value=e.tip_positions(:,nodes(k));else,value=e.tip_velocities(:,nodes(k));end
            gap(k)=sum(((value-references(:,k))/radii(k)).^2)-1;
        end
    end
    function [ci,ce,gi,ge]=constraints(z)
        e=inspect(z(1:nv));
        if feasibility,slackIndices=ones(size(groups));else,slackIndices=groups;end
        gap=task_values(e);ci=gap(optimizedIndices(:))-z(nv+slackIndices(optimizedIndices(:)));ce=e.constraints;
        if nargout>2
            gi=zeros(nv+2,numel(optimizedIndices));ge=[e.jacobian';zeros(2,numel(ce))];
            for j=1:numel(optimizedIndices)
                k=optimizedIndices(j);
                node=nodes(k);indices=node*2*c.n+(1:2*c.n);
                if groups(k)==1,value=e.tip_positions(:,node);J=[e.position_jacobians(:,:,node),zeros(3,c.n)];
                else,value=e.tip_velocities(:,node);J=e.velocity_jacobians(:,:,node);end
                gi(indices,j)=2*(J'*(value-references(:,k))).*c.state_scale/radii(k)^2;gi(nv+slackIndices(k),j)=-1;
            end
        end
    end
    function audit=kkt_report(z,lambda,flag)
        [~,g]=objective(z);[ci,ce,gi,ge]=constraints(z);
        stationarity=g+gi*lambda.ineqnonlin+ge*lambda.eqnonlin-lambda.lower+lambda.upper;
        lo=isfinite(lower);hi=isfinite(upper);
        primal=max([0;abs(ce);ci;lower-z;z-upper]);
        dual=max([0;-lambda.ineqnonlin;-lambda.lower;-lambda.upper]);
        complementarity=max([0;abs(lambda.ineqnonlin.*ci); ...
            abs(lambda.lower(lo).*(z(lo)-lower(lo))); ...
            abs(lambda.upper(hi).*(upper(hi)-z(hi)))]);
        active=struct('constraint_id',{},'original_constraint_ids',{},'time_s',{},'multiplier',{},'residual',{});
        for a=find(ci>=-1e-5)'
            k=optimizedIndices(a);
            active(end+1)=struct('constraint_id',labels{k}, ...
                'original_constraint_ids',{labels(originalForOptimized{a})},'time_s',nodes(k)*c.h, ...
                'multiplier',lambda.ineqnonlin(a),'residual',ci(a));
        end
        audit=struct('iterate','raw_fmincon_returned_before_projection_or_recovery', ...
            'objective_mode',r.arguments.objective_mode,'solver_exitflag',flag, ...
            'primal_inf',primal,'stationarity_inf',max(abs(stationarity)), ...
            'dual_violation',dual,'complementarity_inf',complementarity, ...
            'active_task_constraints',active,'multipliers',lambda, ...
            'optimized_task_inequalities',numel(optimizedIndices),'original_task_predicates',numel(nodes), ...
            'gradient_source','fresh complete NLP objective and nonlinear constraint Jacobians', ...
            'design_lagrangian_derivative','not_computed; explicit dynamics and initial-condition design terms required', ...
            'conditioning','not_measured', ...
            'global_optimality','unclaimed');
    end
    function result=task_report(e)
        gap=task_values(e);values=radii(:).*sqrt(max(0,1+gap));
        margins=radii(:)-values;
        result=struct('squared_normalized_excess',gap,'actual_norm',values, ...
            'signed_margin',margins,'normalized_signed_margin',margins./radii(:), ...
            'maximum_original_violation',max([0;-margins]),'constraint_ids',{labels}, ...
            'times_s',nodes*c.h,'original_sampled_requirements_satisfied',all(gap<=0), ...
            'required_slacks',struct('position',max([0;gap(groups==1)]),'speed',max([0;gap(groups==2)])), ...
            'scope','Declared sampled rod-model task requirements; physical MuJoCo acceptance unmeasured');
    end
end
