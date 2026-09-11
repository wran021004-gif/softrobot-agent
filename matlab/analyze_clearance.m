function [points, lower_bound, sample_clearance, point_index, box_index, spacing] = ...
    analyze_clearance(L, theta, phi, radius, boxes, max_spacing)
    % Low/geometric: swept-radius PCC centreline against EnvironmentSpec boxes.
    % Python supplies box centres and half sizes. No environment constants here.
    n = max(1, ceil(L / max_spacing));
    s = linspace(0, L, n + 1)';
    spacing = L / n;
    if abs(theta) < 1e-8
        points = [s, zeros(n + 1, 2)];
    else
        angle = theta * s / L;
        rho = 2 * L / theta * sin(angle / 2).^2;
        points = [L / theta * sin(angle), rho * cos(phi), rho * sin(phi)];
    end
    distances = zeros(n + 1, size(boxes, 1));
    for j = 1:size(boxes, 1)
        q = abs(points - boxes(j, 1:3)) - boxes(j, 4:6);
        distances(:, j) = sqrt(sum(max(q, 0).^2, 2)) + min(max(q, [], 2), 0) - radius;
    end
    [sample_clearance, index] = min(distances(:));
    [point_index, box_index] = ind2sub(size(distances), index);
    % Signed distance is 1-Lipschitz: every arc location is within spacing/2
    % of a sample. This lower bound cannot certify a gap hidden between samples.
    lower_bound = sample_clearance - spacing / 2;
end
