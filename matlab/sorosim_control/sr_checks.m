function out=sr_checks(model,request)
% Independent differences use a different step and do not call routing tangent.
q=request.q(:);u=request.u(:);n=numel(q);h=1e-4;
if isfield(request,'qd')
    out=dynamic_checks(model,request);return
end
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

function out=dynamic_checks(model,r)
started=tic;q=r.q(:);v=r.qd(:);a=r.qdd(:);u=r.u(:);
base=sr_derivatives(model,q,v,u,a);h=1e-4;n=numel(q);
names={'q','qd','qdd','u'};expected={base.Rq,base.Rqd,base.Rqdd,base.Ru};
out=struct('step',h,'base',base);
for k=1:4
    point={q,v,a,u};jac=zeros(n,numel(point{k}));motion=zeros(3,numel(point{k}));
    for j=1:numel(point{k})
        plus=point;minus=point;plus{k}(j)=plus{k}(j)+h;minus{k}(j)=minus{k}(j)-h;
        p=sr_dynamics(model,plus{1},plus{2},plus{4},plus{3},[],false);
        m=sr_dynamics(model,minus{1},minus{2},minus{4},minus{3},[],false);
        jac(:,j)=(p.residual-m.residual)/(2*h);
        motion(:,j)=(p.tip_velocity-m.tip_velocity)/(2*h);
    end
    out.errors.(names{k})=struct('absolute',max(abs(jac-expected{k}),[],'all'), ...
        'relative',max(abs(jac-expected{k}),[],'all')/max(max(abs(jac),[],'all'),1e-15));
    if k<=2
        if k==1,expectedMotion=base.tip_velocity_q;else,expectedMotion=base.tip_velocity_qd;end
        out.tip_velocity_errors.(names{k})=max(abs(motion-expectedMotion),[],'all');
    end
end
out.forward=sr_dynamics(model,q,v,u,[]);
out.validation_s=toc(started);
end
