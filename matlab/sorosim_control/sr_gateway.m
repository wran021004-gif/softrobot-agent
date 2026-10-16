function encoded = sr_gateway(operation, payload)
% One Engine process owns one candidate. Never use the MATLAB base workspace.
persistent model;
started = tic;
request = jsondecode(payload);
switch operation
    case 'environment'
        assert(isempty(model),'SOROSIM_SESSION_ALREADY_CONFIGURED');
        base = fullfile(request.root,'Differentiable_SoRoSim');
        addpath(fullfile(base,'Basic_functions'),fullfile(base,'SorosimLink_files'), ...
            fullfile(base,'SorosimRod_files'),fullfile(base,'SorosimRod_files','Strain bases'), ...
            fullfile(base,'SorosimContact_files'));
        addpath(genpath(fullfile(base,'SorosimLinkage_files')));
        out.version = version; out.release = version('-release');
        assert(strcmp(out.release,'2024a'),'MATLAB_R2024A_REQUIRED');
        assert(license('test','Optimization_Toolbox'),'OPTIMIZATION_TOOLBOX_REQUIRED');
        out.optimization = ver('optim'); out.architecture = computer;
        out.process_id = feature('getpid');
        names = {'variable_expmap_g_mex','variable_expmap_gTg_mex', ...
            'variable_expmap_gTgTgd_mex','RigidJointKinematics_mex', ...
            'compute_dSTdqFC_Z4_mex'};
        for k=1:numel(names)
            assert(~isempty(which(names{k})),['MISSING_MEX: ' names{k}]);
            [~,name,ext] = fileparts(which(names{k}));
            out.binaries{k} = [name ext];
        end
        [a,b,c] = variable_expmap_gTgTgd_mex(zeros(6,1),zeros(6,1));
        assert(all(isfinite([a(:);b(:);c(:)])),'MEX_SMOKE_FAILED');
        opt = optimoptions('fmincon','Algorithm','sqp','Display','off');
        [x,f,flag] = fmincon(@(x)(x-1)^2,0,[],[],[],[],-2,2,[],opt);
        assert(flag>0 && abs(x-1)<1e-5,'FMINCON_SQP_SMOKE_FAILED');
        out.fmincon_probe = struct('x',x,'objective',f,'exitflag',flag);
        out.path_policy = 'Explicit pinned paths; no upstream startup, savepath, build or desktop';
    case 'construct'
        assert(isempty(model),'ONE_CANDIDATE_PER_MATLAB_SESSION');
        model = sr_model(request);
        out = model.description;
    case 'clear'
        model = []; out = struct('cleared',true);
    otherwise
        assert(~isempty(model),'SOROSIM_MODEL_REQUIRED');
        assert(strcmp(request.model_identity,model.spec.identity),'SOROSIM_MODEL_IDENTITY_MISMATCH');
        switch operation
            case 'routing'
                out = sr_routing(model,request.q,request.u,true);
            case 'dynamics'
                out = sr_dynamics(model,request.q,request.qd,request.u,request.qdd);
            case 'derivatives'
                out = sr_derivatives(model,request.q,request.qd,request.u,request.qdd);
            case 'nmpc'
                out = sr_nmpc(model,request);
            case 'checks'
                out = sr_checks(model,request);
            case 'diagnose'
                out = sr_diagnose(model,request);
            case 'analysis'
                out = sr_analysis(model,request);
            case 'codesign'
                out = sr_codesign(model,request);
            otherwise
                error('SOROSIM_UNSUPPORTED_OPERATION: %s',operation);
        end
end
out.gateway_s = toc(started);
encoded = jsonencode(out);
end
