function g = tf_geometry(p, scene, q, v)
% Parent-connected three-dimensional kinematics and zero-qdd bias acceleration.
n = numel(q); nb = numel(p.parts);
base = struct('R',scene.mount_rotation,'p',scene.mount_position(:),...
    'J',zeros(3,n),'A',zeros(3,n),'w',zeros(3,1),'alpha',zeros(3,1),'ab',zeros(3,1));
bodies = repmat(base,nb,1);
for i=1:nb
    part=p.parts(i);
    if part.parent<0, parent=base; else, parent=bodies(part.parent+1); end
    r=parent.R*part.position_m(:);
    b=parent; b.p=parent.p+r;
    b.J=parent.J-skew(r)*parent.A;
    b.ab=parent.ab+cross(parent.alpha,r)+cross(parent.w,cross(parent.w,r));
    b.R=parent.R*part.rotation;
    for j=1:numel(part.dofs)
        k=part.dofs(j)+1; axis=b.R(:,j+1);
        b.A(:,k)=axis;
        b.alpha=b.alpha+cross(b.w,axis)*v(k);
        b.w=b.w+axis*v(k);
        c=cos(q(k)); s=sin(q(k));
        if j==1, R=[c 0 s;0 1 0;-s 0 c]; else, R=[c -s 0;s c 0;0 0 1]; end
        b.R=b.R*R;
    end
    bodies(i)=b;
end
g=struct('bodies',bodies,'base',base);
[g.tip,g.Jtip]=tf_point(g,p.tip);
[g.routes,g.lengths,g.Jlength]=tf_routes(g,p.tendons);
end

function S=skew(r)
S=[0 -r(3) r(2);r(3) 0 -r(1);-r(2) r(1) 0];
end
