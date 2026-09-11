function [theta, phi, tip, position_error, model_task_success, lengths, deltas] = ...
    plan_pcc_reach(L, N, r_t, tx, ty, tz, tolerance)
    % M1: single-section PCC kinematics, base at origin, straight along +x.
    % Search the simple non-looping branch 0 <= theta <= pi (radians).
    % No dynamics, gravity, stiffness/load, or contact model is included.
    target = [tx, ty, tz];
    phi = atan2(tz, ty);
    objective = @(angle) sum((pcc_tip(L, angle, phi) - target).^2);
    interior = fminbnd(objective, 0, pi);
    % Include the exact straight and maximum-bend endpoints.
    candidates = [0, interior, pi];
    errors = arrayfun(objective, candidates);
    [~, best] = min(errors);
    theta = candidates(best);
    tip = pcc_tip(L, theta, phi);
    position_error = norm(tip - target);
    model_task_success = position_error <= tolerance;
    alpha = 2 * pi * (0:N-1) / N;
    lengths = L - r_t * theta * cos(alpha - phi);
    deltas = lengths - L;
end

function tip = pcc_tip(L, theta, phi)
    if abs(theta) < 1e-8
        tip = [L, 0, 0];
    else
        x = L * sin(theta) / theta;
        % Equivalent to L*(1-cos(theta))/theta, stable near zero.
        rho = 2 * L * sin(theta / 2)^2 / theta;
        tip = [x, rho * cos(phi), rho * sin(phi)];
    end
end
