function [S, D] = sv_model(cfg, model, nGauss)
% Construct only the shared bending subspace using upstream no-GUI objects.
S = SorosimLinkage('empty');
S.Z_order = []; % Upstream setters defer updates until construction completes.
S.VLinks = SorosimLink.empty(1,0);
S.N = numel(model.lengths_m);
S.ndof = 4*S.N;
S.iLpre = (0:S.N-1)';
S.g_ini = repmat(eye(4), S.N, 1);
S.LinkIndex = (1:S.N)';
S.CVRods = cell(S.N,1);
for k = 1:S.N
    L = SorosimLink('empty');
    L.jointtype = 'N'; L.linktype = 's'; L.npie = 2;
    len = model.lengths_m(k); radius = model.radii_m(k);
    L.L = len; L.ld = {len}; L.CS = 'C'; L.r = {@(s) radius};
    L.gi = {eye(4)}; L.gf = {eye(4)};
    L.E = cfg.young_pa; L.Rho = cfg.density_kg_m3;
    L.Poi = cfg.poisson_ratio; L.G = L.E/(2*(1+L.Poi));
    L.Eta = 0; L.Kj = []; L.Dj = [];
    S.VLinks(k) = L;
    joint = SorosimRod(L, zeros(6,0));
    rod = SorosimRod();
    % Disable automatic updates while assigning the initial no-GUI state.
    rod.dof = []; rod.Link = L; rod.div = 1;
    rod.Type = 'Legendre Polynomial';
    rod.Phi_h = @Phi_LegendrePolynomial;
    rod.Phi_dof = [0;1;1;0;0;0]; rod.Phi_odr = [0;1;1;0;0;0];
    rod.xi_starfn = @(s) [0;0;0;1;0;0];
    rod.dof = 4;
    rod.UpdateIntegration(nGauss);
    rod.UpdateAll();
    S.CVRods{k} = [joint, rod];
end
[S.nsig, S.nj] = find_nsig_nj(S);
S.Z_order = 4;
S.Gravity = true; S.G = [0;0;0;cfg.gravity_m_s2(:)];
S.CEF = false; S.CA = false; S.CAI = false;
S.CLprecompute = struct('nCLp',0);
S.K = S.findK(); S.D = zeros(S.ndof);
% q_s = D q_g; virtual work gives r_g = D' r_s, A_g = D' A_s D.
D = diag(repelem(model.lengths_m(:),4));
end
