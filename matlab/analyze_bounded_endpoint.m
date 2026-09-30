function out = analyze_bounded_endpoint(A,B,drift,Cp,Dp,p0,Cv,Dv,v0,u0,limits,dt,steps,target,position_limit,targetv,speed_limit,input_scale,atol)
% Independent exact-ZOH affine endpoint map and bounded position/braking solves.
n=size(A,1); m=size(B,2); aug=zeros(n+m+1); aug(1:n,1:n)=A;
aug(1:n,n+1:n+m)=B; aug(1:n,end)=drift(:); E=expm(dt*aug);
Ad=E(1:n,1:n); Bd=E(1:n,n+1:n+m); gd=E(1:n,end);
influence=zeros(n,steps*m); affine=zeros(n,1);
for k=1:steps
    power=Ad^(steps-k); influence(:,(k-1)*m+1:k*m)=power*Bd; affine=affine+power*gd;
end
pbase=p0(:)+Cp*affine; P=Cp*influence; P(:,end-m+1:end)=P(:,end-m+1:end)+Dp;
vbase=v0(:)+Cv*affine; V=Cv*influence; V(:,end-m+1:end)=V(:,end-m+1:end)+Dv;
lower=repmat(-u0(:),steps,1); upper=repmat(limits(:)-u0(:),steps,1);
pc=bounded_residual_certificate(P,pbase,target,lower,upper,position_limit,atol);
vc=bounded_residual_certificate(V,vbase,targetv,lower,upper,speed_limit,atol);
scale=repmat(input_scale(:),steps,1);
objective=@(z) dt*sum((z./scale).^2);
nonlinear=@(z) joint_constraints(z,P,pbase,target,position_limit,V,vbase,targetv,speed_limit);
options=optimoptions('fmincon','Algorithm','sqp','Display','off','MaxIterations',100,...
    'OptimalityTolerance',1e-12,'ConstraintTolerance',1e-10,'StepTolerance',1e-14);
[z,energy,exitflag,output]=fmincon(objective,pc.z,[],[],[],[],lower,upper,nonlinear,options);
pend=pbase+P*z; vend=vbase+V*z; applied=reshape(repmat(u0(:)',steps,1)+reshape(z,m,steps)',steps,m);
out.A_d=Ad;out.B_d=Bd;out.drift_d=gd;out.affine_state=affine;out.influence=influence;
out.position_base=pbase;out.position_matrix=P;out.velocity_base=vbase;out.velocity_matrix=V;
out.position_candidate=pc;out.velocity_candidate=vc;out.joint_z=z;out.joint_energy=energy;
out.joint_exitflag=exitflag;out.joint_iterations=output.iterations;out.joint_position=pend;out.joint_velocity=vend;
out.joint_position_error=norm(pend-target(:));out.joint_speed=norm(vend-targetv(:));
out.joint_bounds_satisfied=all(applied>=-atol,'all') && all(applied<=limits(:)'+atol,'all');
out.joint_feasible=all(isfinite(z)) && out.joint_bounds_satisfied && ...
    out.joint_position_error<=position_limit+atol && out.joint_speed<=speed_limit+atol;
end

function [c,ceq]=joint_constraints(z,P,pbase,target,position_limit,V,vbase,targetv,speed_limit)
c=[sum((pbase+P*z-target(:)).^2)-position_limit^2;
   sum((vbase+V*z-targetv(:)).^2)-speed_limit^2];
ceq=[];
end
