function [x,J]=tf_point(g,point)
% Local point and geometric Jacobian; body index -1 denotes the fixed mount.
if point.body<0, b=g.base; else, b=g.bodies(point.body+1); end
r=b.R*point.position_m(:);
x=b.p+r;
S=[0 -r(3) r(2);r(3) 0 -r(1);-r(2) r(1) 0];
J=b.J-S*b.A;
end
