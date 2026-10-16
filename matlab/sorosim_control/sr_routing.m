function out=sr_routing(model,q,u,tangent,qd)
% Physical attachment Jacobians and straight, frictionless chord virtual work.
if nargin<4, tangent=false; end
started=tic; q=q(:);u=u(:); S=model.S;
assert(numel(q)==S.ndof && all(isfinite(q)),'INVALID_CONFIGURATION');
assert(numel(u)==numel(model.spec.routes) && all(isfinite(u)),'INVALID_TENSIONS');
g=S.FwdKinematics(model.T*q); J=S.Jacobian(model.T*q)*model.T;
[tip,Jtip]=attachment(model,model.spec.tip,g,J);
m=numel(model.spec.routes); ell=zeros(m,1); dl=zeros(m,S.ndof); positions=cell(m,1);
for i=1:m
    route=model.spec.routes(i); points=route.points;
    p=zeros(3,numel(points)); dp=zeros(3,S.ndof,numel(points));
    for j=1:numel(points)
        [pose,jac]=attachment(model,points(j),g,J);
        p(:,j)=pose(1:3,4); dp(:,:,j)=jac(4:6,:);
    end
    for j=1:numel(points)-1
        delta=p(:,j+1)-p(:,j); len=norm(delta);
        assert(len>1e-12,'DEGENERATE_TENDON_SPAN');
        ell(i)=ell(i)+len;
        dl(i,:)=dl(i,:)+delta'/len*(dp(:,:,j+1)-dp(:,:,j));
    end
    positions{i}=p';
end
out=struct('lengths',ell,'length_jacobian',dl,'force_map',-dl', ...
    'tendon_force',-dl'*u,'tip_pose',tip,'tip_jacobian',Jtip, ...
    'routing_positions', {positions},'coordinate_order',{model.spec.coordinate_order}, ...
    'tendon_order',{model.spec.tendon_order},'model_identity',model.spec.identity);
if tangent
    h=model.spec.solver.routing_difference_step; D=zeros(S.ndof);
    if nargin<5, qd=zeros(S.ndof,1); end
    velocityQ=zeros(3,S.ndof);
    for j=1:S.ndof
        d=zeros(S.ndof,1);d(j)=h;
        plus=sr_routing(model,q+d,u,false);minus=sr_routing(model,q-d,u,false);
        D(:,j)=(plus.tendon_force-minus.tendon_force)/(2*h);
        velocityQ(:,j)=(plus.tip_jacobian(4:6,:)-minus.tip_jacobian(4:6,:))*qd(:)/(2*h);
    end
    out.force_state_derivative=D;
    out.tip_velocity_q=velocityQ;
    out.derivative_method='Centered MATLAB-local differences of analytical chord force map';
    out.derivative_step_rad_m=h;
end
out.routing_s=toc(started);
end

function [pose,jac]=attachment(model,a,g,J)
offset=a.offset(:);
if a.link==0
    base=eye(4); local=zeros(6,model.S.ndof);
else
    grid=model.nodes{a.link};
    [distance,j]=min(abs(grid-a.s));assert(distance<1e-12,'MISSING_ROUTING_STATION');
    idx=model.node_indices{a.link}(j);
    base=g((idx-1)*4+(1:4),:);local=J((idx-1)*6+(1:6),:);
    if ~strcmp(model.spec.links{a.link}.kind,'flexible_segment')
        % Upstream rigid sample is at COM, while physical attachment is at origin.
        offset=offset-model.spec.links{a.link}.com(:);
    end
end
R=base(1:3,1:3);
pose=base;pose(1:3,4)=base(1:3,4)+R*offset;
pose(1:3,1:3)=R*a.rotation;
jac=[R*local(1:3,:); R*(local(4:6,:)-dinamico_tilde(offset)*local(1:3,:))];
end
