function out=sr_checks(model,request)
% Independent differences use a different step and do not call routing tangent.
q=request.q(:);u=request.u(:);n=numel(q);h=1e-4;
base=sr_routing(model,q,u,true);
dl=zeros(numel(u),n);J=zeros(3,n);D=zeros(n);
for j=1:n
    d=zeros(n,1);d(j)=h;
    plus=sr_routing(model,q+d,u,false);minus=sr_routing(model,q-d,u,false);
    dl(:,j)=(plus.lengths-minus.lengths)/(2*h);
    J(:,j)=(plus.tip_pose(1:3,4)-minus.tip_pose(1:3,4))/(2*h);
    D(:,j)=(plus.tendon_force-minus.tendon_force)/(2*h);
end
out=struct('step_rad_m',h,'routing_jacobian_error',max(abs(dl-base.length_jacobian),[],'all'), ...
    'tip_jacobian_error',max(abs(J-base.tip_jacobian(4:6,:)),[],'all'), ...
    'force_state_derivative_error',max(abs(D-base.force_state_derivative),[],'all'));
end
