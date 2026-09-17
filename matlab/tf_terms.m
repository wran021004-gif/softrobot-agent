function a=tf_terms(p,scene,config,q,v,target,time_s)
% Full mass matrix and inertial bias from rigid-body Jacobians; MATLAB owns
% every numerical term, independent of Python and MuJoCo numerical outputs.
g=tf_geometry(p,scene,q,v); n=numel(q);
M=zeros(n); bias=zeros(n,1); gravity=zeros(n,1); external=zeros(n,1);
spring=zeros(n,1); damping=zeros(n,1); contact=zeros(n,1);
normal=zeros(numel(p.parts),1); gaps=zeros(numel(p.parts),1);
for i=1:numel(p.parts)
    part=p.parts(i); b=g.bodies(i); r=b.R*part.com_local_m(:);
    S=[0 -r(3) r(2);r(3) 0 -r(1);-r(2) r(1) 0];
    J=b.J-S*b.A; I=b.R*part.inertia_com_local_kg_m2*b.R';
    ab=b.ab+cross(b.alpha,r)+cross(b.w,cross(b.w,r));
    M=M+part.mass_kg*(J'*J)+b.A'*I*b.A;
    bias=bias+part.mass_kg*J'*ab+b.A'*(I*b.alpha+cross(b.w,I*b.w));
    gravity=gravity+part.mass_kg*J'*scene.gravity(:);
    for f=1:numel(scene.forces)
        force=scene.forces(f);
        if force.body==i-1 && time_s>=force.start_s && time_s<force.end_s
            external=external+J'*force.force_n(:);
        end
    end
    k=part.dofs(:)+1;
    spring(k)=-part.stiffness_nm_rad(:).*(q(k)-part.natural_rad(:));
    damping(k)=-part.damping_nm_s_rad(:).*v(k);
    % A lowest-envelope-vertex normal penalty, no tangential friction.
    xyz=part.collision_vertices_m*b.R'+b.p';
    [height,index]=min(xyz(:,3)); gaps(i)=height-scene.floor_z_m;
    if gaps(i)<0
        point=struct('body',i-1,'position_m',part.collision_vertices_m(index,:));
        [~,Jc]=tf_point(g,point);
        normal(i)=max(0,-config.contact_stiffness_n_m*gaps(i)-config.contact_damping_n_s_m*(Jc(3,:)*v));
        contact=contact+Jc(3,:)'*normal(i);
    end
end
kp=[p.tendons.kp_n_m]'; limits=[p.tendons.force_limit_n]';
T=min(limits,max(0,kp.*(g.lengths-target(:)))); drive=-g.Jlength'*T;
a=struct('geometry',g,'mass',M,'bias',bias,'gravity',gravity,'external',external,...
    'spring',spring,'damping',damping,'contact',contact,'normal',normal,'gaps',gaps,...
    'tension',T,'drive',drive);
a.acceleration=M\(gravity+external+spring+damping+drive+contact-bias);
end
