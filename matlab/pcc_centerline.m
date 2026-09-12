function points = pcc_centerline(L, theta, phi, n)
% Sample the existing PCC geometry; no planning or numerical-settings changes.
s = linspace(0, 1, n)';
if abs(theta) < 1e-8
    points = [L*s zeros(size(s)) zeros(size(s))];
else
    points = [L*sin(theta*s)/theta, ...
        2*L*sin(theta*s/2).^2/theta*cos(phi), ...
        2*L*sin(theta*s/2).^2/theta*sin(phi)];
end
end
