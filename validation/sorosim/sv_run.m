function sv_run(referenceRoot, outputDir, caseId, validationVersion)
% Run one bounded validation case; Python comparison gates the next case.
here = fileparts(mfilename('fullpath'));
cfg = jsondecode(fileread(fullfile(here,'cases.json')));
model = cfg.cases(strcmp({cfg.cases.id},caseId));
assert(numel(model)==1, 'Unknown validation case');
if ~isfolder(outputDir), mkdir(outputDir); end
assert(~isfile(fullfile(outputDir,['matlab_' caseId '.json'])),'Preserve existing evidence');
entryUnix = posixtime(datetime('now','TimeZone','UTC')); envStart = tic;
env = sv_environment(referenceRoot); env.setup_seconds = toc(envStart); env.entry_unix_s = entryUnix;
if nargin >= 4 && validationVersion == 2
    result = sv_v2(cfg,model); result.environment = env;
    save_result(result,outputDir,caseId); return
end
result.environment = env;
result.case_id = caseId;
result.coordinate_convention = 'q_g rad/m; r_g N*m^2; tip J=[world angular;world linear]';
allStart = tic;
for level = 1:numel(model.levels)
    setting = model.levels(level);
    buildStart = tic;
    [S,D] = sv_model(cfg,model,setting.gauss);
    row.setting = setting; row.build_seconds = toc(buildStart);
    row.nsig = S.nsig; row.nj = S.nj;
    row.quadrature_x = S.CVRods{1}(2).Xs;
    row.quadrature_weights_m = S.CVRods{1}(2).Ws;
    for j = 1:size(model.probes_rad_m,1)
        q = model.probes_rad_m(j,:)';
        start = tic; terms = sv_terms(S,D,cfg,q);
        sample.q = q; sample.terms = terms; sample.seconds = toc(start);
        for hidx = 1:numel(cfg.fd_steps_rad_m)
            h = cfg.fd_steps_rad_m(hidx);
            poseFD = sv_fd(@(v) pose_vector(S,D,v),q,h);
            jt = pose_derivative(poseFD,terms.pose);
            jr = sv_fd(@(v) residual(S,D,v),q,h);
            jl = sv_fd(@(v) lengths(S,D,cfg,v),q,h);
            check.step_rad_m = h;
            check.tip_max_abs = max(abs(jt-terms.tip_jacobian),[],'all');
            check.residual_max_abs = max(abs(jr-terms.residual_jacobian),[],'all');
            check.tendon_max_abs = max(abs(jl-terms.tendon_length_jacobian),[],'all');
            sample.fd(hidx) = check;
        end
        row.probes(j) = sample;
    end
    opts = optimoptions('fsolve','Display','off','SpecifyObjectiveGradient',true, ...
        'FunctionTolerance',1e-14,'StepTolerance',1e-12,'OptimalityTolerance',1e-14, ...
        'MaxIterations',100,'MaxFunctionEvaluations',500);
    start = tic;
    [q,r,flag,info] = fsolve(@(v) residual(S,D,v),zeros(S.ndof,1),opts);
    eq.seconds = toc(start); eq.q = q; eq.residual_norm = norm(r,inf);
    eq.exitflag = flag; eq.iterations = info.iterations; eq.function_evaluations = info.funcCount;
    eq.message = info.message;
    eq.terms = sv_terms(S,D,cfg,q);
    eq.tangent_condition = cond(eq.terms.residual_jacobian);
    % At u=0, d(B(q)u)/dq=0; upstream tangent is exact for this chord problem.
    dqdu = -eq.terms.residual_jacobian\eq.terms.tendon_force_map;
    eq.tip_sensitivity_m_n = eq.terms.tip_jacobian(4:6,:)*dqdu;
    for hidx = 1:numel(cfg.sensitivity_forward_steps_n)
        h = cfg.sensitivity_forward_steps_n(hidx);
        sens = zeros(3,size(cfg.tendon_offsets_m,1));
        flags = zeros(2,size(sens,2)); errors = flags;
        for a = 1:size(sens,2)
            positions = zeros(3,2);
            for m = 1:2
                u = zeros(size(sens,2),1); u(a) = m*h;
                % FD solver Jacobian here includes configuration-dependent chord loads.
                o = optimoptions(opts,'SpecifyObjectiveGradient',false);
                [qh,rh,fh] = fsolve(@(v) loaded_residual(S,D,cfg,v,u),q,o);
                T = reshape(pose_vector(S,D,qh),4,4);
                positions(:,m) = T(1:3,4); flags(m,a) = fh; errors(m,a) = norm(rh,inf);
            end
            sens(:,a) = (-3*eq.terms.pose(1:3,4)+4*positions(:,1)-positions(:,2))/(2*h);
        end
        sc.step_n = h; sc.tip_sensitivity_m_n = sens;
        sc.max_abs = max(abs(sens-eq.tip_sensitivity_m_n),[],'all');
        sc.exitflags = flags; sc.residual_norms = errors;
        eq.sensitivity_fd(hidx) = sc;
    end
    assert(flag>0 && eq.residual_norm<cfg.solver_residual_tolerance_nm2,'Equilibrium failed');
    row.equilibrium = eq;
    result.levels(level) = row;
    fprintf('%s Gauss=%d: fsolve flag=%d residual=%.3g elapsed=%.3fs\n', ...
        caseId,setting.gauss,flag,eq.residual_norm,eq.seconds);
    clear row sample eq;
end
result.elapsed_seconds = toc(allStart);
save_result(result,outputDir,caseId);
end

function save_result(result,outputDir,caseId)
here = fileparts(mfilename('fullpath'));
[status,sha] = system(['git -C "' fileparts(fileparts(here)) '" rev-parse HEAD']);
assert(status==0,'Cannot capture repository identity'); result.source_sha = strtrim(sha);
[~,mexFiles] = inmem('-completenames');
result.loaded_mex = mexFiles;
fid = fopen(fullfile(outputDir,['matlab_' caseId '.json']),'w','n','UTF-8');
cleanup = onCleanup(@() fclose(fid));
fprintf(fid,'%s\n',jsonencode(result,PrettyPrint=true));
end

function [r,A] = residual(S,D,q)
[rs,As] = S.Equilibrium(D*q(:),[],struct('magnifier',false));
r = D'*rs; A = D'*As*D;
end

function y = pose_vector(S,D,q)
g = S.FwdKinematics(D*q(:)); T = g(end-3:end,:); y = T(:);
end

function J = pose_derivative(fd,T)
J = zeros(6,size(fd,2));
for k = 1:size(fd,2)
    dT = reshape(fd(:,k),4,4); W = dT(1:3,1:3)*T(1:3,1:3)';
    W = (W-W')/2;
    J(:,k) = [W(3,2);W(1,3);W(2,1);dT(1:3,4)];
end
end

function ell = lengths(S,D,cfg,q)
T = reshape(pose_vector(S,D,q),4,4);
d = cfg.tendon_offsets_m';
ell = vecnorm(T(1:3,4)+T(1:3,1:3)*d-d)';
end

function r = loaded_residual(S,D,cfg,q,u)
terms = sv_terms(S,D,cfg,q);
r = terms.residual+terms.tendon_force_map*u;
end
