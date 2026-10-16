function out = sv_terms(S, D, cfg, q)
% All outputs use repository curvature coordinates and robot-base frames.
qs = D*q(:);
g = S.FwdKinematics(qs); T = g(end-3:end,:);
J = S.Jacobian(qs); J = J(end-5:end,:)*D;
R = T(1:3,1:3);
out.pose = T;
out.tip_jacobian = [R*J(1:3,:); R*J(4:6,:)]; % angular; linear at tip
[r,A] = S.Equilibrium(qs, [], struct('magnifier',false));
out.residual = D'*r; out.residual_jacobian = D'*A*D;
out.stiffness = D'*S.K*D;
out.gravity_force = out.residual + out.stiffness*q(:);
offsets = cfg.tendon_offsets_m';
out.tendon_lengths = zeros(size(offsets,2),1);
out.tendon_length_jacobian = zeros(size(offsets,2),numel(q));
for k = 1:size(offsets,2)
    d = offsets(:,k);
    delta = T(1:3,4)+R*d-d; % base anchor is fixed at d
    ell = norm(delta); tangent = delta/ell;
    % Velocity of offset anchor = R (v_body + omega_body cross d).
    Ja = R*(J(4:6,:)-dinamico_tilde(d)*J(1:3,:));
    out.tendon_lengths(k) = ell;
    out.tendon_length_jacobian(k,:) = tangent'*Ja;
end
out.tendon_force_map = -out.tendon_length_jacobian';
out.tendon_force = out.tendon_force_map*cfg.probe_tensions_n(:);
% Native continuously guided cable is a DIFFERENT path, shown for diagnosis.
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
