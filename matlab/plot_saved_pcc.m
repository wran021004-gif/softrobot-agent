function plot_saved_pcc(run_dir, output_dir, visible)
% DEBUG_ONLY / NON_CANONICAL. Read saved results, never call a numerical tool.
% Saved plotting inputs are derived from the run snapshots by the Python adapter.
p = jsondecode(fileread(fullfile(output_dir, 'matlab_inputs.json')));
if ~exist(output_dir, 'dir'), mkdir(output_dir); end
visibility = 'off';
if visible, visibility = 'on'; end
fig = figure('Visible', visibility, 'Color', 'w', 'Position', [80 80 1100 750], ...
    'Name', 'DEBUG_ONLY / NON_CANONICAL PCC');
cleanup = onCleanup(@() close_hidden(fig, visible));
ax = axes(fig); hold(ax, 'on'); grid(ax, 'on'); axis(ax, 'equal'); view(ax, 3);
m = p.model;
theta = m.theta_rad; phi = m.phi_rad; L = p.total_length_m;
u = linspace(0, 1, 301)';
if abs(theta) < 1e-8
    points = [L*u zeros(size(u)) zeros(size(u))];
else
    points = L/theta * [sin(theta*u), (1-cos(theta*u))*cos(phi), (1-cos(theta*u))*sin(phi)];
end
points = points + reshape(p.base_position_m, 1, 3);
if isfield(p, 'centerline_m'), points = p.centerline_m; end
plot3(ax, points(:,1), points(:,2), points(:,3), 'b-', 'LineWidth', 2, 'DisplayName', 'PCC predicted centerline');
b = p.base_position_m; target = p.target_m; tip = m.predicted_tip_m;
plot3(ax, b(1), b(2), b(3), 'ks', 'MarkerFaceColor', 'k', 'DisplayName', 'robot base');
plot3(ax, target(1), target(2), target(3), 'ro', 'MarkerFaceColor', 'r', 'DisplayName', 'target');
plot3(ax, tip(1), tip(2), tip(3), 'go', 'MarkerFaceColor', 'g', 'DisplayName', 'PCC predicted tip');
[sx,sy,sz] = sphere(32); r = p.position_tolerance_m;
surf(ax, target(1)+r*sx, target(2)+r*sy, target(3)+r*sz, ...
    'FaceColor', 'r', 'FaceAlpha', .12, 'EdgeColor', 'none', 'DisplayName', 'target tolerance');
xlabel(ax, 'x (m)'); ylabel(ax, 'y (m)'); zlabel(ax, 'z (m)');
annotation = sprintf(['DEBUG_ONLY / NON_CANONICAL\n' ...
    'total_length_m=%.17g | theta_rad=%.17g | phi_rad=%.17g\n' ...
    'predicted_position_error_m=%.17g\ntendon targets (m): %s'], ...
    L, theta, phi, m.predicted_position_error_m, mat2str(m.tendon_target_lengths_m', 17));
title(ax, annotation, 'Interpreter', 'none', 'FontSize', 10);
legend(ax, 'Location', 'best');
exportgraphics(fig, fullfile(output_dir, 'matlab_pcc.png'), 'Resolution', 150);
if isfield(p, 'window_boxes')
    faces = [1 2 4 3; 5 6 8 7; 1 2 6 5; 3 4 8 7; 1 3 7 5; 2 4 8 6];
    signs = [-1 -1 -1; -1 -1 1; -1 1 -1; -1 1 1; 1 -1 -1; 1 -1 1; 1 1 -1; 1 1 1];
    for i=1:size(p.window_boxes,1)
        box = p.window_boxes(i,:);
        vertices = signs .* box(4:6) + box(1:3);
        patch(ax, 'Vertices', vertices, 'Faces', faces, 'FaceColor', [.5 .5 .5], ...
            'FaceAlpha', .3, 'HandleVisibility', 'off');
    end
    ap = p.aperture_m;
    plot3(ax, ap(:,1), ap(:,2), ap(:,3), 'm--', 'DisplayName', 'window aperture');
    c = p.clearance.closest_location_m;
    plot3(ax, c(1), c(2), c(3), 'mx', 'MarkerSize', 12, 'LineWidth', 2, 'DisplayName', 'closest clearance point');
    title(ax, sprintf('%s\npredicted minimum clearance (m)=%.17g', annotation, ...
        p.clearance.predicted_minimum_clearance_m), 'Interpreter', 'none', 'FontSize', 10);
    legend(ax, 'Location', 'best');
    exportgraphics(fig, fullfile(output_dir, 'matlab_clearance.png'), 'Resolution', 150);
end
if visible
    drawnow;
    % Display is optional and never blocks the deterministic simulation.
end
end

function close_hidden(fig, visible)
if ~visible && isgraphics(fig), close(fig); end
end
