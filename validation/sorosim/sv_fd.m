function J = sv_fd(fn, q, h)
% Centered difference; caller supplies the absolute step in its input units.
q = q(:); J = zeros(numel(fn(q)), numel(q));
for k = 1:numel(q)
    e = zeros(size(q)); e(k) = h;
    J(:,k) = (fn(q+e)-fn(q-e))/(2*h);
end
end
