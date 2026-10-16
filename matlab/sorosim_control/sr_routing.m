function out=sr_routing(model,q,u,tangent,qd,samples)
% Physical attachment Jacobians and straight, frictionless chord virtual work.
if nargin<4, tangent=false; end
started=tic; q=q(:);u=u(:); S=model.S;
assert(numel(q)==S.ndof && all(isfinite(q)),'INVALID_CONFIGURATION');
assert(numel(u)==numel(model.spec.routes) && all(isfinite(u)),'INVALID_TENSIONS');
[g,J]=kinematics(model,q);
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
if nargin>=6
    frames=cell(numel(samples),1);
    for k=1:numel(samples)
        [pose,jac]=attachment(model,samples(k),g,J);
        frames{k}=struct('pose',pose,'jacobian',jac);
    end
    out.sample_frames=frames;
end
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

function [g,J]=kinematics(model,q)
% One Zanna-4 traversal shares transforms with body Jacobians. The adapter
% constructs only fixed joints and one flexible division per segment.
% Same pinned upstream recurrence, using its already verified expmap MEX.
S=model.S;n=S.ndof;qs=model.T*q;
g=zeros(4*S.nsig,4);J=zeros(6*S.nsig,n);ends=cell(S.N,1);tails=cell(S.N,1);
for k=1:S.N
    c=model.spec.links{k};parent=c.parent;
    if parent==0,pose=c.connection;B=zeros(6,n);
    else,pose=ends{parent}*c.connection;B=dinamico_Adjoint(ginv(c.connection))*tails{parent};end
    indices=model.node_indices{k};joint=indices(1)-1;
    g((joint-1)*4+(1:4),:)=pose;J((joint-1)*6+(1:6),:)=B;
    if strcmp(c.kind,'flexible_segment')
        rod=S.CVRods{k}(2);ix=c.start+(1:rod.dof);local=qs(ix);
        for j=1:rod.nip
            if j>1
                rows=(j-2)*6+(1:6);P1=rod.Phi_Z1(rows,:);P2=rod.Phi_Z2(rows,:);
                xi1=P1*local+rod.xi_star(rows,2);xi2=P2*local+rod.xi_star(rows,3);
                h=(rod.Xs(j)-rod.Xs(j-1))*c.length;ad1=dinamico_adj(xi1);
                omega=h/2*(xi1+xi2)+sqrt(3)*h^2/12*ad1*xi2;
                Z=h/2*(P1+P2)+sqrt(3)*h^2/12*(ad1*P2-dinamico_adj(xi2)*P1);
                [step,Tg]=variable_expmap_gTg_mex(omega);
                B(:,ix)=B(:,ix)+Tg*Z;
                B=dinamico_Adjoint(ginv(step))*B;pose=pose*step;
            end
            index=indices(j);g((index-1)*4+(1:4),:)=pose;J((index-1)*6+(1:6),:)=B;
        end
    else
        shift=eye(4);shift(1:3,4)=c.com(:);
        index=indices(1);g((index-1)*4+(1:4),:)=pose*shift;
        J((index-1)*6+(1:6),:)=dinamico_Adjoint(ginv(shift))*B;
    end
    ends{k}=pose;tails{k}=B;
end
J=J*model.T;
end
