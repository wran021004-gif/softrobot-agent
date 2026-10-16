function out=sr_dynamics(model,q,qd,u,qdd,routing,decompose)
% Upstream recursive inverse dynamics: ID=M*a+C*v-gravity; tau=-K*q-D*v.
% Custom routing is the only actuator. R=ID-tau-natural-B*u (positive LHS).
started=tic;
q=q(:);qd=qd(:);u=u(:);n=model.S.ndof;
assert(numel(q)==n && numel(qd)==n && all(isfinite([q;qd;u])),'INVALID_DYNAMIC_STATE');
if nargin<5 || isempty(qdd), qdd=zeros(n,1); forward=true; else, qdd=qdd(:);forward=false; end
assert(numel(qdd)==n && all(isfinite(qdd)),'INVALID_ACCELERATION');
if nargin<6 || isempty(routing), routing=sr_routing(model,q,u,false); end
if nargin<7, decompose=true; end
S=model.S;T=model.T;qs=T*q;vs=T*qd;as=T*qdd;
[ID,tau,~,IDq,IDv,Ms,~,tauq,tauv]=S.DAEJacobians(0,qs,vs,as,zeros(0,1),zeros(0,1),3);
M=T'*Ms*T;
residual=T'*(ID-tau-model.natural)-routing.tendon_force;
if forward
    qdd=-(M/norm(M,'fro'))\(residual/norm(M,'fro'));
    residual=M*qdd+residual;
    % Report derivatives at the returned acceleration when forward requested.
    [~,~,~,IDq,IDv]=S.DAEJacobians(0,qs,vs,T*qdd,zeros(0,1),zeros(0,1),3);
end
out=struct('q',q,'qd',qd,'qdd',qdd,'mass_matrix',M, ...
    'elastic_force',T'*(S.K*qs-model.natural),'viscous_force',T'*S.D*vs, ...
    'residual',residual,'passive_q',T'*(IDq-tauq)*T,'passive_qd',T'*(IDv-tauv)*T, ...
    'tendon_lengths',routing.lengths,'tendon_force_map',routing.force_map, ...
    'tendon_force',routing.tendon_force,'tip_position',routing.tip_pose(1:3,4), ...
    'tip_velocity',routing.tip_jacobian(4:6,:)*qd,'tip_jacobian',routing.tip_jacobian(4:6,:), ...
    'model_identity',model.spec.identity,'coordinate_order',{model.spec.coordinate_order}, ...
    'tendon_order',{model.spec.tendon_order},'equation','M*qdd+c+elastic+viscous-gravity-B*u=0');
if decompose
    % GeneralizedExternalForce at this upstream pin references obsolete Link.lp.
    % Equilibrium uses the current recursive implementation and returns G-K*q.
    passive=S.Equilibrium(qs,[],struct('magnifier',false));
    gravity=T'*(passive+S.K*qs);
    out.gravity_force=gravity;
    out.velocity_bias=T'*ID-M*(T\as)+gravity;
end
out.valid=all(isfinite([M(:);residual;out.passive_q(:);out.passive_qd(:)])) && ...
    norm(M-M','inf')<1e-10 && min(eig((M+M')/2))>0;
out.dynamics_s=toc(started);
end
