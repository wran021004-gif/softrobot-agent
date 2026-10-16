function result = sv_v2(cfg,model)
% Nonzero chord equilibrium and local IFT checks, in physical q_g throughout.
v = cfg.v2; setting = model.levels(end); allStart = tic;
start = tic; [S,D] = sv_model(cfg,model,setting.gauss);
result.schema = v.schema; result.case_id = model.id; result.setting = setting;
result.model = model; result.units = v.units; result.build_seconds = toc(start);
result.derivative_method = 'Analytical upstream passive/J; centered FD chord tangent; rebuilt FD design partials';
f = @(q,u) sv_terms(S,D,cfg,q,u);
for b = 1:size(v.baseline_tensions_n,1)
    u = v.baseline_tensions_n(b,:)';
    row.u = u; row.equilibrium = solve(f,zeros(S.ndof,1),u);
    if ~row.equilibrium.success || row.equilibrium.residual_norm >= v.tolerances.residual_nm2
        result.baselines(b) = row; continue
    end
    q = row.equilibrium.q; t = f(q,u);
    for name = {'R','Rq','Ru','p','J','A0'}, row.terms.(name{1}) = t.(name{1}); end
    row.tendon_tangent = t.Rq-t.A0;
    for k = 1:v.repeated_calls
        start = tic; loaded(f,q,u); row.static_call_seconds(k) = toc(start);
    end
    for k = 1:numel(cfg.fd_steps_rad_m)
        h = cfg.fd_steps_rad_m(k); start = tic;
        check.Rq = sv_fd(@(x) residual_only(S,D,cfg,x,u),q,h);
        check.step = h; check.seconds = toc(start); row.tangent_fd(k) = check;
    end
    start = tic; row.dqdu = -t.Rq\t.Ru; row.dpdu = t.J*row.dqdu;
    row.omitted_dpdu = -t.J*(t.A0\t.Ru); row.input_ift_seconds = toc(start);
    row.linear_solve_relative = max(abs(t.Rq*row.dqdu+t.Ru),[],'all')/max(abs(t.Ru),[],'all');
    for k = 1:numel(v.input_steps_n)
        h = v.input_steps_n(k); checkInput.step_n = h; count = 0;
        checkInput.Ru = sv_fd(@(up) residual_only(S,D,cfg,q,up),u,h);
        for a = 1:numel(u)
            for sign = [-1,1]
                up = u; up(a) = up(a)+sign*h;
                sol = solve(f,q,up); sol.u = up; count = count+1;
                checkInput.solves(count) = sol;
                if sign < 0, minus = sol; else, plus = sol; end
            end
            checkInput.dqdu(:,a) = (plus.q-minus.q)/(2*h);
            checkInput.dpdu(:,a) = (plus.p-minus.p)/(2*h);
        end
        row.input_fd(k) = checkInput;
    end
    result.baselines(b) = row; clear row
end
if ~isfield(result.baselines(1),'terms'), return; end
base = result.baselines(1); q = base.equilibrium.q; p = base.equilibrium.p; u = base.u; t = base.terms;
diagnostic = sv_terms(S,D,cfg,q);
result.cable_diagnostic.q = q;
result.cable_diagnostic.chord = diagnostic.tendon_force_map;
result.cable_diagnostic.guided = diagnostic.native_guided_tendon_force_map;
for a = 1:numel(v.design_parameters)
    param = v.design_parameters(a); key = param.key; ix = param.index+1;
    if ix == 0, value = cfg.(key); else, value = model.(key)(ix); end
    design.parameter = param; design.value = value; pi = 0; di = 0;
    for fraction = unique([v.partial_relative_steps(:);v.prediction_relative_steps(:)])'
        delta = fraction*value;
        for k = 1:2
            sign = 2*k-3; c = cfg; m = model;
            if ix == 0, c.(key) = value+sign*delta; else, m.(key)(ix) = value+sign*delta; end
            % Rebuild stiffness, quadrature, geometry AND length-dependent D.
            start = tic; [Sp,Dp] = sv_model(c,m,setting.gauss); buildTimes(k) = toc(start);
            fp = @(x,up) sv_terms(Sp,Dp,c,x,up);
            start = tic; partials(k) = fp(q,u); partialTimes(k) = toc(start);
            if ismember(fraction,v.prediction_relative_steps), pair(k) = solve(fp,q,u); end
        end
        if ismember(fraction,v.partial_relative_steps)
            start = tic; part.fraction = fraction;
            part.Rd = (partials(2).R-partials(1).R)/(2*delta);
            part.pd = (partials(2).p-partials(1).p)/(2*delta);
            part.dqdd = -t.Rq\part.Rd; part.dpdd = part.pd+t.J*part.dqdd;
            part.ift_seconds = toc(start); part.build_seconds = buildTimes;
            part.evaluation_seconds = partialTimes;
            di = di+1; design.partials(di) = part;
        end
        if ismember(fraction,v.prediction_relative_steps)
            for k = 1:2
                pred.fraction = fraction; pred.delta = (2*k-3)*delta;
                pred.predicted = pred.delta*design.partials(1).dpdd;
                pred.actual = pair(k).p-p; pred.solve = pair(k); pred.build_seconds = buildTimes;
                pi = pi+1; design.predictions(pi) = pred;
            end
        end
    end
    result.designs(a) = design; clear design
end
result.elapsed_seconds = toc(allStart);
end

function sol = solve(f,initial,u)
opts = optimoptions('fsolve','Display','off','SpecifyObjectiveGradient',true, ...
    'FunctionTolerance',1e-14,'StepTolerance',1e-12,'OptimalityTolerance',1e-14, ...
    'MaxIterations',100,'MaxFunctionEvaluations',500);
start = tic; [q,r,flag,info] = fsolve(@(x) loaded(f,x,u),initial,opts);
sol.seconds = toc(start); t = f(q,u);
sol.q = q; sol.p = t.p; sol.R = r; sol.residual_norm = norm(r,inf);
sol.status = flag; sol.success = flag>0; sol.message = info.message;
sol.function_evaluations = info.funcCount; sol.condition = cond(t.Rq);
end

function [r,A] = loaded(f,q,u)
t = f(q,u); r = t.R; A = t.Rq;
end

function r = residual_only(S,D,cfg,q,u)
% Independent total-residual FD: do not call the numerical chord tangent.
t = sv_terms(S,D,cfg,q,u,false); r = t.R;
end
