function env = sv_environment(root)
% Explicit paths avoid startup's unrelated iDCOL build and file deletion.
env.matlab_version = version; env.release = version('-release');
env.arch = computer; env.matlabroot = matlabroot; env.userpath = userpath;
env.original_startup = which('startup','-all');
env.toolboxes = ver; env.mex_extension = mexext;
env.cpp_compiler_selected = ~isempty(mex.getCompilerConfigurations('C++','Selected'));
env.optimization_license = license('test','Optimization_Toolbox');
names = {'fsolve','fmincon','lsqnonlin','imresize','sym'};
for k = 1:numel(names), env.functions.(names{k}) = which(names{k}); end
base = fullfile(root,'Differentiable_SoRoSim');
addpath(fullfile(base,'Basic_functions'), fullfile(base,'SorosimLink_files'), ...
    fullfile(base,'SorosimRod_files'),fullfile(base,'SorosimRod_files','Strain bases'), ...
    fullfile(base,'SorosimContact_files'));
addpath(genpath(fullfile(base,'SorosimLinkage_files')));
env.reference_root = root;
env.startup_policy = 'Audited; explicit paths only. No iDCOL/contact, GUI, savepath or rebuild.';
env.upstream_startup = fullfile(base,'startup.m');
env.idcol_build_script_present = isfile(fullfile(root,'external','iDCOL','build_mex.m'));
names = {'variable_expmap_g','variable_expmap_gTg','RigidJointKinematics', ...
    'SoftJointKinematics_Z4','compute_dSTdqFC_Z4'};
for k = 1:numel(names)
    name = names{k}; mexname = [name '_mex'];
    env.mex_paths.(mexname) = which(mexname);
end
for k = 1:2
    xi = [0;.03*k;-.02; .1;0;0];
    if k == 1, xi = zeros(6,1); end
    a = variable_expmap_g_mex(xi); b = variable_expmap_g(xi);
    env.expmap_mex_max_abs(k) = max(abs(a(:)-b(:)));
    [a,at] = variable_expmap_gTg_mex(xi); [b,bt] = variable_expmap_gTg(xi);
    env.expmap_tangent_mex_max_abs(k) = max([abs(a(:)-b(:));abs(at(:)-bt(:))]);
end
% Actual toolbox function/license smoke tests, bounded and noninteractive.
o = optimoptions('fsolve','Display','off');
[~,r,f] = fsolve(@(x) x-1,0,o); env.fsolve_probe = [f, norm(r)];
o = optimoptions('fmincon','Display','off');
[~,~,f] = fmincon(@(x) (x-1)^2,0,[],[],[],[],-2,2,[],o);
env.fmincon_exitflag = f;
o = optimoptions('lsqnonlin','Display','off');
[~,r,~,f] = lsqnonlin(@(x) x-1,0,-2,2,o); env.lsqnonlin_probe = [f,r];
end
