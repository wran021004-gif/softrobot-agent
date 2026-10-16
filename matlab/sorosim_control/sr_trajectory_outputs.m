function out=sr_trajectory_outputs(model,r)
% Kinematic output audit of saved states; no integration or optimization.
started=tic;X=r.states;U=r.tensions_n;times=r.times_s;
n=model.S.ndof;m=numel(model.spec.routes);N=size(U,1);
assert(isequal(size(X),[N+1,2*n]) && isequal(size(U),[N,m]) && numel(times)==N+1, ...
    'TRAJECTORY_OUTPUT_DIMENSION_MISMATCH');
position=zeros(N+1,3);velocity=zeros(N+1,3);
for k=1:N+1
    command=U(max(1,k-1),:)';
    route=sr_routing(model,X(k,1:n)',command,false);
    qd=X(k,n+1:end)';
    position(k,:)=(model.spec.mount_rotation*route.tip_pose(1:3,4)+model.spec.mount_position(:))';
    velocity(k,:)=(model.spec.mount_rotation*route.tip_jacobian(4:6,:)*qd)';
end
out=struct('status','computed','model_identity',model.spec.identity,'frame','world', ...
    'position_unit','m','velocity_unit','m/s','times_s',times, ...
    'tip_positions_m',position,'tip_velocities_m_s',velocity,'samples',N+1, ...
    'method','saved mathematical states through sr_routing; no dynamics integration', ...
    'total_s',toc(started));
end
