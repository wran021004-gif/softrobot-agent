function out = sv_terms(S, D, cfg, q, u, tangent)
% All outputs use repository curvature coordinates and robot-base frames.
qs = D*q(:);
[T,J,ell,dl] = chord(S,D,cfg,q);
R = T(1:3,1:3);
out.pose = T;
out.tip_jacobian = [R*J(1:3,:); R*J(4:6,:)]; % angular; linear at tip
[r,A] = S.Equilibrium(qs, [], struct('magnifier',false));
out.residual = D'*r; out.residual_jacobian = D'*A*D;
out.stiffness = D'*S.K*D;
out.gravity_force = out.residual + out.stiffness*q(:);
out.tendon_lengths = ell;
out.tendon_length_jacobian = dl;
out.tendon_force_map = -out.tendon_length_jacobian';
out.tendon_force = out.tendon_force_map*cfg.probe_tensions_n(:);
if nargin >= 5
    % V2 reverses V1's force-balance sign: R=elastic-gravity-B*u.
    if nargin < 6, tangent = true; end
    out.A0 = -out.residual_jacobian;
    out.R = -out.residual-out.tendon_force_map*u(:);
    out.Ru = -out.tendon_force_map;
    out.p = T(1:3,4); out.J = out.tip_jacobian(4:6,:);
    out.Rq = out.A0;
    if tangent
        out.Rq = out.A0 + sv_fd(@(v) chord_gradient(S,D,cfg,v,u), ...
            q,cfg.v2.chord_tangent_step_rad_m);
    end
    return
end
% Native continuously guided cable is a DIFFERENT path, shown for diagnosis.
offsets = cfg.tendon_offsets_m';
native = zeros(S.ndof,size(offsets,2));
for k = 1:S.N
    rod = S.CVRods{k}(2); ix = (k-1)*4+(1:4);
    for j = 1:rod.nip
        rows = (j-1)*6+(1:6); P = rod.Phi(rows,:);
        xi = P*qs(ix)+rod.xi_star(rows,1);
        xihat = [dinamico_tilde(xi(1:3)), xi(4:6)];
        for a = 1:size(offsets,2)
            phi = SoftActuator(-1,offsets(:,a),zeros(3,1),xihat);
            % Upstream +u extends the cable; tensile magnitude maps to -u.
            native(ix,a) = native(ix,a)-rod.Ws(j)*P'*phi;
        end
    end
end
out.native_guided_tendon_force_map = D'*native;
end

function [T,J,ell,dl] = chord(S,D,cfg,q)
g = S.FwdKinematics(D*q(:)); T = g(end-3:end,:);
J = S.Jacobian(D*q(:)); J = J(end-5:end,:)*D;
R = T(1:3,1:3); offsets = cfg.tendon_offsets_m';
ell = zeros(size(offsets,2),1); dl = zeros(size(offsets,2),numel(q));
for k = 1:size(offsets,2)
    d = offsets(:,k); delta = T(1:3,4)+R*d-d;
    ell(k) = norm(delta);
    Ja = R*(J(4:6,:)-dinamico_tilde(d)*J(1:3,:));
    dl(k,:) = delta'/ell(k)*Ja;
end
end

function y = chord_gradient(S,D,cfg,q,u)
[~,~,~,dl] = chord(S,D,cfg,q); y = dl'*u(:);
end
